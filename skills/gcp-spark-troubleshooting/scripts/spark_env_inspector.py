#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Read-only environment inspector for Dataproc Serverless and GCE workloads.

Collects factual Google Cloud environment metadata across three planes:
  * `identity`: effective service account, authentication mode, OAuth scopes,
    KMS key, project IAM roles, and optional Secret Manager version states/IAM
    (never accesses secret payloads).
  * `network`: VPC/subnet URIs, CIDR usable host count, Private Google Access,
    Cloud NAT coverage, VPC firewall rules (with optional `--target_port`
    matching), and Cloud DNS private zone bindings.
  * `classpath`: Dataproc runtime/image version, mapped Spark and Scala binary
    versions, attached JARs (with detected `_2.12` / `_2.13` suffixes),
    distributed `--files` / `--py-files` / `--archives`, optional components,
    and classpath/catalog Spark properties.

Secondary Google Cloud inspection calls degrade gracefully when the caller
lacks IAM permissions (HTTP 403 / PERMISSION_DENIED) or when a referenced
cluster was deleted (NOT_FOUND), recording a caveat in `warnings` while still
returning all accessible facts.

Written against the Python standard library only.
"""

import argparse
import ipaddress
import json
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_REGION = "us-central1"
_GCLOUD_TIMEOUT_SECONDS = 60

CommandRunner = Callable[[List[str]], Tuple[int, str, str]]

# Runtime/image version -> (Spark minor version, Scala binary version).
# Dataproc Serverless 2.x/3.0 ship Scala 2.13; Serverless 1.x and GCE Cluster
# 2.x ship Scala 2.12, while GCE Cluster 3.0 ships Spark 4.1 on Scala 2.13.
_SERVERLESS_RUNTIME_MAP: Dict[str, Tuple[str, str]] = {
    "1.0": ("3.2", "2.12"),
    "1.1": ("3.3", "2.12"),
    "1.2": ("3.5", "2.12"),
    "2.0": ("3.3", "2.13"),
    "2.1": ("3.4", "2.13"),
    "2.2": ("3.5", "2.13"),
    "2.3": ("3.5", "2.13"),
    "3.0": ("4.0", "2.13"),
}

_CLUSTER_IMAGE_MAP: Dict[str, Tuple[str, str]] = {
    "1.5": ("2.4", "2.12"),
    "2.0": ("3.1", "2.12"),
    "2.1": ("3.3", "2.12"),
    "2.2": ("3.5", "2.12"),
    "2.3": ("3.5", "2.12"),
    "3.0": ("4.1", "2.13"),
}

_SCALA_SUFFIX_RE = re.compile(r"_(2\.1[123])(?=[-._/:]|$)")
_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|pwd|passphrase|secret|token|credential|authorization|"
    r"private[_.-]?key|access[_.-]?key|account[_.-]?key|client[_.-]?secret|"
    r"api[_.-]?key)",
    re.IGNORECASE,
)
# Keys whose names match _SENSITIVE_KEY_RE only as resource identifiers or
# provider/delegation mode selectors rather than raw credential material.
_SAFE_KEY_SUFFIXES = (
    "secret_id",
    "secret-id",
    "secret_name",
    "secret-name",
    "secret_version",
    "secret-version",
    "token.provider",
    "credentials.provider",
    "vended-credentials",
)
_INLINE_URI_USERINFO_RE = re.compile(r"(://[^/:@\s]+:)([^@\s]+)(@)")
_INLINE_SECRET_KV_RE = re.compile(
    r"((?:^|[?&;\s]|-D)[\w.-]*?(?:password|passwd|pwd|passphrase|secret|token|"
    r"credential|authorization|private[_.-]?key|access[_.-]?key|"
    r"account[_.-]?key|client[_.-]?secret|api[_.-]?key)\s*=\s*)([^&;\s\"']+)",
    re.IGNORECASE,
)


class InspectorError(RuntimeError):
  """Raised when the primary workload cannot be resolved or arguments fail."""


def _default_gcloud_runner(args: List[str]) -> Tuple[int, str, str]:
  """Executes `gcloud` non-interactively and returns (code, stdout, stderr)."""
  gcloud = shutil.which("gcloud")
  if not gcloud:
    raise InspectorError(
        "The Google Cloud CLI ('gcloud') is not installed or not on PATH."
    )
  cmd = [gcloud, *args, "--quiet"]
  try:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=_GCLOUD_TIMEOUT_SECONDS,
        stdin=subprocess.DEVNULL,
    )
  except (OSError, subprocess.SubprocessError) as exc:
    return 1, "", str(exc)
  return proc.returncode, proc.stdout or "", proc.stderr or ""


def _concise_stderr(stderr: str, code: int) -> str:
  lines = [ln.strip() for ln in (stderr or "").splitlines() if ln.strip()]
  if not lines:
    return f"exit code {code}"
  for line in lines:
    if line.startswith("ERROR:"):
      return line
  return lines[-1]


def _run_gcloud_json(
    runner: CommandRunner,
    args: List[str],
    warnings: List[str],
    label: str,
    *,
    fatal: bool = False,
) -> Optional[Any]:
  """Runs a gcloud command with `--format=json` and decodes its output."""
  code, stdout, stderr = runner([*args, "--format=json"])
  if code != 0:
    msg = f"{label}: {_concise_stderr(stderr, code)}"
    if fatal:
      raise InspectorError(msg)
    warnings.append(msg)
    return None
  text = stdout.strip()
  if not text:
    return {}
  try:
    return json.loads(text)
  except ValueError as exc:
    msg = f"{label}: invalid JSON output ({exc})"
    if fatal:
      raise InspectorError(msg) from exc
    warnings.append(msg)
    return None


def resolve_default_project(runner: CommandRunner) -> Optional[str]:
  """Resolves the active `gcloud` project when `--project` is omitted."""
  code, stdout, _ = runner(["config", "get-value", "project"])
  value = stdout.strip()
  if code == 0 and value and value != "(unset)":
    return value
  return None


def _is_safe_key(key: str) -> bool:
  normalized = key.strip().lstrip("-").lower()
  return any(normalized.endswith(sfx) for sfx in _SAFE_KEY_SUFFIXES)


def _scrub_inline_secrets(text: str) -> str:
  """Redacts URI userinfo and inline secret key=value tokens inside strings."""
  scrubbed = _INLINE_URI_USERINFO_RE.sub(r"\1<REDACTED>\3", text)

  def _replace_kv(match: re.Match[str]) -> str:
    prefix = match.group(1)
    key_token = prefix.rstrip("= ").lstrip("?&; \t\n\r")
    if key_token.startswith("-D"):
      key_token = key_token[2:]
    if _is_safe_key(key_token):
      return match.group(0)
    return f"{prefix}<REDACTED>"

  return _INLINE_SECRET_KV_RE.sub(_replace_kv, scrubbed)


def redact_value(key: str, value: Any) -> Any:
  """Redacts sensitive credential values while preserving safe metadata keys."""
  str_val = str(value)
  if _is_safe_key(key):
    return value
  if _SENSITIVE_KEY_RE.search(key) and str_val:
    return "<REDACTED>"
  if isinstance(value, str) and value:
    return _scrub_inline_secrets(value)
  return value


def redact_args(raw_args: List[str]) -> List[str]:
  """Redacts inline secret flags and embedded URL secrets in CLI arg lists."""
  sanitized: List[str] = []
  redact_next = False
  for item in raw_args:
    if redact_next:
      redact_next = False
      if not item.startswith("-"):
        sanitized.append("<REDACTED>")
        continue
    if "=" in item and item.startswith("-"):
      flag, val = item.split("=", 1)
      if _SENSITIVE_KEY_RE.search(flag) and not _is_safe_key(flag):
        sanitized.append(f"{flag}=<REDACTED>")
      else:
        sanitized.append(f"{flag}={_scrub_inline_secrets(val)}")
    elif (
        item.startswith("-")
        and _SENSITIVE_KEY_RE.search(item)
        and not _is_safe_key(item)
    ):
      sanitized.append(item)
      redact_next = True
    else:
      sanitized.append(_scrub_inline_secrets(item))
  return sanitized


def _fetch_workload(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
    warnings: List[str],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
  """Fetches the primary workload resource and, for jobs, its cluster config."""
  if workload_kind == "batch":
    batch = _run_gcloud_json(
        runner,
        [
            "dataproc",
            "batches",
            "describe",
            workload_id,
            f"--project={project}",
            f"--region={region}",
        ],
        warnings,
        f"batches describe '{workload_id}'",
        fatal=True,
    )
    return batch or {}, None

  if workload_kind == "session":
    # Sessions use `--location` and live under `gcloud beta` in current SDKs;
    # fall back to GA `gcloud dataproc sessions` if `beta` is unavailable.
    beta_warnings: List[str] = []
    session = _run_gcloud_json(
        runner,
        [
            "beta",
            "dataproc",
            "sessions",
            "describe",
            workload_id,
            f"--project={project}",
            f"--location={region}",
        ],
        beta_warnings,
        f"sessions describe '{workload_id}'",
        fatal=False,
    )
    if session is not None:
      return session, None
    err_msg = beta_warnings[-1] if beta_warnings else ""
    if "Invalid choice" in err_msg or "components install beta" in err_msg:
      ga_session = _run_gcloud_json(
          runner,
          [
              "dataproc",
              "sessions",
              "describe",
              workload_id,
              f"--project={project}",
              f"--location={region}",
          ],
          warnings,
          f"sessions describe '{workload_id}'",
          fatal=True,
      )
      return ga_session or {}, None
    raise InspectorError(err_msg or f"sessions describe '{workload_id}' failed")

  if workload_kind == "job":
    job = _run_gcloud_json(
        runner,
        [
            "dataproc",
            "jobs",
            "describe",
            workload_id,
            f"--project={project}",
            f"--region={region}",
        ],
        warnings,
        f"jobs describe '{workload_id}'",
        fatal=True,
    )
    job_dict = job or {}
    cluster_name = (job_dict.get("placement") or {}).get("clusterName") or ""
    cluster_dict = None
    if cluster_name:
      cluster_dict = _run_gcloud_json(
          runner,
          [
              "dataproc",
              "clusters",
              "describe",
              cluster_name,
              f"--project={project}",
              f"--region={region}",
          ],
          warnings,
          f"clusters describe '{cluster_name}'",
          fatal=False,
      )
    return job_dict, cluster_dict

  raise InspectorError(f"Unsupported workload kind: {workload_kind}")


def _extract_common_header(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    workload: Dict[str, Any],
    cluster: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
  """Extracts common status and runtime version fields across surfaces."""
  if workload_kind == "job":
    status = workload.get("status") or {}
    state = status.get("state") or ""
    state_message = status.get("details") or ""
    cluster_name = (workload.get("placement") or {}).get("clusterName") or ""
    sw_cfg = ((cluster or {}).get("config") or {}).get("softwareConfig") or {}
    runtime_version = sw_cfg.get("imageVersion") or ""
  else:
    state = workload.get("state") or ""
    state_message = workload.get("stateMessage") or ""
    cluster_name = ""
    runtime_version = (workload.get("runtimeConfig") or {}).get("version") or ""
  return {
      "workload_type": workload_kind,
      "workload_id": workload_id,
      "project": project,
      "region": region,
      "cluster_name": cluster_name,
      "state": state,
      "state_message": state_message,
      "runtime_version": runtime_version,
  }


def _normalize_prop_key(raw_key: Any) -> str:
  """Strips GCE cluster `spark:` prefix so cluster and job keys align."""
  key_str = str(raw_key)
  if key_str.startswith("spark:"):
    return key_str[len("spark:") :]
  return key_str


def _merged_properties(
    workload_kind: str,
    workload: Dict[str, Any],
    cluster: Optional[Dict[str, Any]],
) -> Dict[str, str]:
  """Returns effective Spark/Dataproc properties (cluster + job overrides)."""
  merged: Dict[str, str] = {}
  if workload_kind == "job":
    if cluster:
      sw_props = (
          ((cluster.get("config") or {}).get("softwareConfig") or {}).get(
              "properties"
          )
          or {}
      )
      for k, v in sw_props.items():
        merged[_normalize_prop_key(k)] = str(v)
    for job_key in (
        "pysparkJob",
        "sparkJob",
        "sparkSqlJob",
        "sparkRJob",
        "hadoopJob",
    ):
      sub = workload.get(job_key)
      if isinstance(sub, dict):
        for k, v in (sub.get("properties") or {}).items():
          merged[_normalize_prop_key(k)] = str(v)
  else:
    rt_props = (workload.get("runtimeConfig") or {}).get("properties") or {}
    for k, v in rt_props.items():
      merged[str(k)] = str(v)
    # RuntimeInfo also records effective properties when available.
    eff_props = (workload.get("runtimeInfo") or {}).get("properties") or {}
    for k, v in eff_props.items():
      merged.setdefault(str(k), str(v))
  return merged


def _parse_secret_ref(default_project: str, raw_secret: str) -> Tuple[str, str]:
  """Parses `projects/<p>/secrets/<s>[/versions/<v>]` or bare `<s>`."""
  match = re.match(
      r"^projects/([^/]+)/secrets/([^/]+)(?:/versions/[^/]+)?$",
      raw_secret.strip(),
  )
  if match:
    return match.group(1), match.group(2)
  return default_project, raw_secret.strip()


def inspect_identity(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
    secret_id: Optional[str] = None,
) -> Dict[str, Any]:
  """Collects service account, KMS, IAM, and optional Secret Manager facts."""
  warnings: List[str] = []
  workload, cluster = _fetch_workload(
      project, region, workload_kind, workload_id, runner, warnings
  )
  header = _extract_common_header(
      project, region, workload_kind, workload_id, workload, cluster
  )
  props = _merged_properties(workload_kind, workload, cluster)

  if workload_kind == "job":
    cluster_cfg = (cluster or {}).get("config") or {}
    gce_cfg = cluster_cfg.get("gceClusterConfig") or {}
    enc_cfg = cluster_cfg.get("encryptionConfig") or {}
    configured_sa = gce_cfg.get("serviceAccount") or ""
    auth_type = "SERVICE_ACCOUNT"
    sa_scopes = list(gce_cfg.get("serviceAccountScopes") or [])
    kms_key = enc_cfg.get("gcePdKmsKeyName") or ""
    staging_bucket = cluster_cfg.get("configBucket") or ""
    temp_bucket = cluster_cfg.get("tempBucket") or ""
  else:
    exec_cfg = (
        (workload.get("environmentConfig") or {}).get("executionConfig") or {}
    )
    auth_cfg = exec_cfg.get("authenticationConfig") or {}
    configured_sa = exec_cfg.get("serviceAccount") or ""
    raw_auth_type = auth_cfg.get("userWorkloadAuthenticationType") or ""
    if raw_auth_type == "AUTHENTICATION_TYPE_UNSPECIFIED":
      raw_auth_type = ""
    ver_match = re.match(r"^(\d+)\.", str(header["runtime_version"]).strip())
    is_serverless_3_plus = bool(ver_match and int(ver_match.group(1)) >= 3)
    if not raw_auth_type:
      if not configured_sa and is_serverless_3_plus:
        auth_type = "END_USER_CREDENTIALS"
      else:
        auth_type = "SERVICE_ACCOUNT"
    else:
      auth_type = raw_auth_type
    sa_scopes = []
    kms_key = exec_cfg.get("kmsKey") or ""
    staging_bucket = exec_cfg.get("stagingBucket") or ""
    temp_bucket = (
        props.get("spark.datasource.bigquery.temporaryGcsBucket")
        or props.get("temporaryGcsBucket")
        or ""
    )

  effective_sa = configured_sa
  default_sa_inferred = False
  if (
      not effective_sa
      and auth_type != "END_USER_CREDENTIALS"
      and (workload_kind != "job" or cluster is not None)
  ):
    proj_info = _run_gcloud_json(
        runner,
        ["projects", "describe", project],
        warnings,
        f"projects describe '{project}'",
    )
    proj_num = (proj_info or {}).get("projectNumber")
    if proj_num:
      effective_sa = f"{proj_num}-compute@developer.gserviceaccount.com"
      default_sa_inferred = True

  project_iam_roles: List[str] = []
  if effective_sa:
    policy = _run_gcloud_json(
        runner,
        ["projects", "get-iam-policy", project],
        warnings,
        f"projects get-iam-policy '{project}'",
    )
    member_key = f"serviceAccount:{effective_sa}"
    for binding in (policy or {}).get("bindings") or []:
      members = binding.get("members") or []
      if member_key in members:
        role = binding.get("role") or ""
        cond = (binding.get("condition") or {}).get("title")
        label = f"{role} (condition: {cond})" if cond else role
        project_iam_roles.append(label)

  auth_related_props: Dict[str, Any] = {}
  for k in sorted(props):
    lk = k.lower()
    if any(
        tok in lk
        for tok in (
            "auth",
            "credential",
            "service.account",
            "token",
            "kms",
            "encryption",
            "secret",
            "ssl",
            "catalog",
            "warehouse",
        )
    ):
      auth_related_props[k] = redact_value(k, props[k])

  secret_info: Optional[Dict[str, Any]] = None
  if secret_id:
    sec_project, sec_name = _parse_secret_ref(project, secret_id)
    versions_raw = _run_gcloud_json(
        runner,
        ["secrets", "versions", "list", sec_name, f"--project={sec_project}"],
        warnings,
        f"secrets versions list '{sec_name}'",
    )
    versions_summary: List[Dict[str, str]] = []
    if isinstance(versions_raw, list):
      for v in versions_raw:
        raw_name = str(v.get("name") or "")
        ver_id = raw_name.rsplit("/", 1)[-1] if "/" in raw_name else raw_name
        versions_summary.append({
            "version": ver_id,
            "state": str(v.get("state") or ""),
            "create_time": str(v.get("createTime") or ""),
        })
    sec_policy = _run_gcloud_json(
        runner,
        ["secrets", "get-iam-policy", sec_name, f"--project={sec_project}"],
        warnings,
        f"secrets get-iam-policy '{sec_name}'",
    )
    sec_bindings: List[Dict[str, Any]] = []
    sa_secret_roles: List[str] = []
    member_key = f"serviceAccount:{effective_sa}" if effective_sa else ""
    for b in (sec_policy or {}).get("bindings") or []:
      role = str(b.get("role") or "")
      members = list(b.get("members") or [])
      sec_bindings.append({"role": role, "members": members})
      if member_key and member_key in members:
        sa_secret_roles.append(role)
    secret_info = {
        "secret_project": sec_project,
        "secret_id": sec_name,
        "versions": versions_summary,
        "iam_bindings": sec_bindings,
        "effective_sa_roles_on_secret": sorted(sa_secret_roles),
    }

  return {
      **header,
      "action": "identity",
      "configured_service_account": configured_sa,
      "effective_service_account": effective_sa,
      "default_service_account_inferred": default_sa_inferred,
      "user_workload_authentication_type": auth_type,
      "service_account_scopes": sa_scopes,
      "kms_key": kms_key,
      "staging_bucket": staging_bucket,
      "temp_bucket": temp_bucket,
      "project_iam_roles": sorted(project_iam_roles),
      "auth_related_properties": auth_related_props,
      "secret_inspection": secret_info,
      "warnings": warnings,
  }


def _parse_subnetwork_uri(
    uri: str, default_project: str, default_region: str
) -> Tuple[str, str, str]:
  """Extracts (host_project, subnet_region, subnet_name) from a subnet URI."""
  if not uri:
    return default_project, default_region, ""
  full_match = re.search(
      r"projects/([^/]+)/regions/([^/]+)/subnetworks/([^/?#]+)", uri
  )
  if full_match:
    return full_match.group(1), full_match.group(2), full_match.group(3)
  short_match = re.search(r"regions/([^/]+)/subnetworks/([^/?#]+)", uri)
  if short_match:
    return default_project, short_match.group(1), short_match.group(2)
  return default_project, default_region, uri.rsplit("/", 1)[-1]


def _parse_network_uri(uri: str, default_project: str) -> Tuple[str, str]:
  """Extracts (host_project, network_name) from a network URI."""
  if not uri:
    return default_project, ""
  full_match = re.search(r"projects/([^/]+)/global/networks/([^/?#]+)", uri)
  if full_match:
    return full_match.group(1), full_match.group(2)
  return default_project, uri.rsplit("/", 1)[-1]


def _cidr_usable_hosts(cidr: str) -> Optional[int]:
  if not cidr:
    return None
  try:
    net = ipaddress.ip_network(cidr, strict=False)
  except ValueError:
    return None
  # Google Cloud VPC subnets reserve 4 IP addresses (network, gateway,
  # second-to-last, and broadcast).
  return max(0, int(net.num_addresses) - 4)


def _port_matches_specs(
    specs: List[Dict[str, Any]], target_port: int
) -> bool:
  """Checks whether a GCE firewall allowed or denied spec covers a TCP port."""
  for spec in specs or []:
    proto = str(spec.get("IPProtocol") or "").lower()
    if proto not in ("all", "tcp", "6"):
      continue
    ports = spec.get("ports") or []
    if not ports:
      return True
    for p in ports:
      p_str = str(p).strip()
      if "-" in p_str:
        lo_s, hi_s = p_str.split("-", 1)
        if lo_s.isdigit() and hi_s.isdigit():
          if int(lo_s) <= target_port <= int(hi_s):
            return True
      elif p_str.isdigit() and int(p_str) == target_port:
        return True
  return False


def inspect_network(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
    target_port: Optional[int] = None,
) -> Dict[str, Any]:
  """Collects subnet PGA/CIDR, Cloud NAT, firewall, and private DNS facts."""
  warnings: List[str] = []
  workload, cluster = _fetch_workload(
      project, region, workload_kind, workload_id, runner, warnings
  )
  header = _extract_common_header(
      project, region, workload_kind, workload_id, workload, cluster
  )

  if workload_kind == "job":
    cluster_cfg = (cluster or {}).get("config") or {}
    gce_cfg = cluster_cfg.get("gceClusterConfig") or {}
    configured_subnet_uri = gce_cfg.get("subnetworkUri") or ""
    configured_network_uri = gce_cfg.get("networkUri") or ""
    network_tags = list(gce_cfg.get("tags") or [])
    workload_sa = str(gce_cfg.get("serviceAccount") or "")
    internal_ip_only = bool(gce_cfg.get("internalIpOnly", False))
  else:
    exec_cfg = (
        (workload.get("environmentConfig") or {}).get("executionConfig") or {}
    )
    configured_subnet_uri = exec_cfg.get("subnetworkUri") or ""
    configured_network_uri = exec_cfg.get("networkUri") or ""
    network_tags = list(exec_cfg.get("networkTags") or [])
    workload_sa = str(exec_cfg.get("serviceAccount") or "")
    # Dataproc Serverless never assigns external IPs to driver/executor VMs.
    internal_ip_only = True

  default_network_inferred = False
  if configured_subnet_uri:
    host_project, subnet_region, subnet_name = _parse_subnetwork_uri(
        configured_subnet_uri, project, region
    )
    _, network_name = _parse_network_uri(configured_network_uri, host_project)
  elif configured_network_uri:
    host_project, network_name = _parse_network_uri(
        configured_network_uri, project
    )
    subnet_region = region
    subnet_name = network_name
  else:
    host_project = project
    subnet_region = region
    subnet_name = "default"
    network_name = "default"
    default_network_inferred = True

  subnet_details: Optional[Dict[str, Any]] = None
  if subnet_name and (workload_kind != "job" or cluster is not None):
    raw_subnet = _run_gcloud_json(
        runner,
        [
            "compute",
            "networks",
            "subnets",
            "describe",
            subnet_name,
            f"--project={host_project}",
            f"--region={subnet_region}",
        ],
        warnings,
        f"compute networks subnets describe '{subnet_name}'",
    )
    if isinstance(raw_subnet, dict) and raw_subnet:
      net_from_subnet = str(raw_subnet.get("network") or "")
      if net_from_subnet:
        host_project, network_name = _parse_network_uri(
            net_from_subnet, host_project
        )
      cidr = str(raw_subnet.get("ipCidrRange") or "")
      subnet_details = {
          "name": str(raw_subnet.get("name") or subnet_name),
          "host_project": host_project,
          "region": subnet_region,
          "network": network_name,
          "ip_cidr_range": cidr,
          "usable_hosts_estimate": _cidr_usable_hosts(cidr),
          "private_ip_google_access": bool(
              raw_subnet.get("privateIpGoogleAccess", False)
          ),
          "purpose": str(raw_subnet.get("purpose") or ""),
          "stack_type": str(raw_subnet.get("stackType") or ""),
      }

  cloud_nats: List[Dict[str, Any]] = []
  if network_name and (workload_kind != "job" or cluster is not None):
    routers = _run_gcloud_json(
        runner,
        [
            "compute",
            "routers",
            "list",
            f"--project={host_project}",
            f"--regions={subnet_region}",
        ],
        warnings,
        f"compute routers list ({subnet_region})",
    )
    if isinstance(routers, list):
      for router in routers:
        r_net = str(router.get("network") or "")
        _, r_net_name = _parse_network_uri(r_net, host_project)
        if r_net_name != network_name:
          continue
        r_name = str(router.get("name") or "")
        if not r_name:
          continue
        nats = _run_gcloud_json(
            runner,
            [
                "compute",
                "routers",
                "nats",
                "list",
                f"--router={r_name}",
                f"--region={subnet_region}",
                f"--project={host_project}",
            ],
            warnings,
            f"compute routers nats list (router='{r_name}')",
        )
        if isinstance(nats, list):
          for nat in nats:
            nat_name = str(nat.get("name") or "")
            nat_type = str(nat.get("type") or "PUBLIC")
            source_mode = str(
                nat.get("sourceSubnetworkIpRangesToNat") or ""
            )
            nat_subnets: List[str] = []
            primary_covered_subnets: List[str] = []
            for s in nat.get("subnetworks") or []:
              if not isinstance(s, dict):
                continue
              sub_short = _parse_subnetwork_uri(
                  str(s.get("name") or ""), host_project, subnet_region
              )[2]
              nat_subnets.append(sub_short)
              ip_ranges = list(s.get("sourceIpRangesToNat") or [])
              if (
                  not ip_ranges
                  or "ALL_IP_RANGES" in ip_ranges
                  or "PRIMARY_IP_RANGE" in ip_ranges
              ):
                primary_covered_subnets.append(sub_short)
            covers_subnet = nat_type != "PRIVATE" and (
                source_mode.startswith("ALL_SUBNETWORKS")
                or subnet_name in primary_covered_subnets
            )
            cloud_nats.append({
                "router": r_name,
                "name": nat_name,
                "nat_type": nat_type,
                "source_subnetwork_ip_ranges_to_nat": source_mode,
                "subnetworks": nat_subnets,
                "covers_workload_subnet": covers_subnet,
            })

  firewall_rules: List[Dict[str, Any]] = []
  if network_name and (workload_kind != "job" or cluster is not None):
    raw_fws = _run_gcloud_json(
        runner,
        ["compute", "firewall-rules", "list", f"--project={host_project}"],
        warnings,
        f"compute firewall-rules list '{host_project}'",
    )
    if isinstance(raw_fws, list):
      matched_fws: List[Dict[str, Any]] = []
      for fw in raw_fws:
        if fw.get("disabled"):
          continue
        _, fw_net = _parse_network_uri(
            str(fw.get("network") or ""), host_project
        )
        if fw_net != network_name:
          continue
        direction = str(fw.get("direction") or "INGRESS")
        allowed = fw.get("allowed") or []
        denied = fw.get("denied") or []
        action = "DENY" if denied else "ALLOW"
        specs = denied if denied else allowed
        target_tags = list(fw.get("targetTags") or [])
        target_sas = list(fw.get("targetServiceAccounts") or [])
        if target_tags:
          tag_applies = bool(set(target_tags).intersection(network_tags))
        elif target_sas:
          tag_applies = bool(workload_sa and workload_sa in target_sas)
        else:
          tag_applies = True
        port_matches = (
            _port_matches_specs(specs, target_port)
            if target_port is not None
            else None
        )
        # Keep all EGRESS rules, any DENY rules, or rules matching target_port.
        if direction == "EGRESS" or action == "DENY" or bool(port_matches):
          matched_fws.append({
              "name": str(fw.get("name") or ""),
              "direction": direction,
              "priority": int(fw.get("priority", 1000)),
              "action": action,
              "destination_ranges": list(fw.get("destinationRanges") or []),
              "source_ranges": list(fw.get("sourceRanges") or []),
              "target_tags": target_tags,
              "target_service_accounts": target_sas,
              "applies_to_workload_tags": tag_applies,
              "rules": specs,
              "matches_target_port": port_matches,
          })
      matched_fws.sort(key=lambda item: (item["priority"], item["name"]))
      firewall_rules = matched_fws

  private_dns_zones: List[Dict[str, Any]] = []
  if network_name and (workload_kind != "job" or cluster is not None):
    raw_zones = _run_gcloud_json(
        runner,
        ["dns", "managed-zones", "list", f"--project={host_project}"],
        warnings,
        f"dns managed-zones list '{host_project}'",
    )
    if isinstance(raw_zones, list):
      for zone in raw_zones:
        if str(zone.get("visibility") or "").lower() != "private":
          continue
        vis_cfg = zone.get("privateVisibilityConfig") or {}
        bound_nets = [
            _parse_network_uri(str(n.get("networkUrl") or ""), host_project)[1]
            for n in (vis_cfg.get("networks") or [])
            if isinstance(n, dict)
        ]
        private_dns_zones.append({
            "name": str(zone.get("name") or ""),
            "dns_name": str(zone.get("dnsName") or ""),
            "bound_networks": bound_nets,
            "bound_to_workload_network": network_name in bound_nets,
        })

  return {
      **header,
      "action": "network",
      "configured_network_uri": configured_network_uri,
      "configured_subnetwork_uri": configured_subnet_uri,
      "default_network_inferred": default_network_inferred,
      "effective_host_project": host_project,
      "effective_network": network_name,
      "effective_subnetwork": subnet_name,
      "internal_ip_only": internal_ip_only,
      "network_tags": network_tags,
      "target_port": target_port,
      "subnet": subnet_details,
      "cloud_nats": cloud_nats,
      "firewall_rules": firewall_rules,
      "private_dns_zones": private_dns_zones,
      "warnings": warnings,
  }


def _map_runtime_versions(
    workload_kind: str, runtime_version: str
) -> Tuple[str, str]:
  """Maps a Dataproc runtime or image version to (spark_ver, scala_binary)."""
  if not runtime_version:
    return "unknown", "unknown"
  match = re.match(r"^(\d+\.\d+)", runtime_version.strip())
  prefix = match.group(1) if match else runtime_version.strip()
  table = (
      _CLUSTER_IMAGE_MAP if workload_kind == "job" else _SERVERLESS_RUNTIME_MAP
  )
  return table.get(prefix, ("unknown", "unknown"))


def _detect_scala_suffix(uri_or_coord: str) -> Optional[str]:
  basename = uri_or_coord.rsplit("/", 1)[-1]
  match = _SCALA_SUFFIX_RE.search(basename)
  return match.group(1) if match else None


def _split_csv_uris(raw: str) -> List[str]:
  if not raw:
    return []
  return [part.strip() for part in raw.split(",") if part.strip()]


def inspect_classpath(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
) -> Dict[str, Any]:
  """Collects runtime Spark/Scala ABI, JARs, files, and catalog properties."""
  warnings: List[str] = []
  workload, cluster = _fetch_workload(
      project, region, workload_kind, workload_id, runner, warnings
  )
  header = _extract_common_header(
      project, region, workload_kind, workload_id, workload, cluster
  )
  props = _merged_properties(workload_kind, workload, cluster)
  spark_ver, scala_ver = _map_runtime_versions(
      workload_kind, header["runtime_version"]
  )

  subtype = ""
  spec: Dict[str, Any] = {}
  if workload_kind == "job":
    candidate_keys = (
        "pysparkJob",
        "sparkJob",
        "sparkSqlJob",
        "sparkRJob",
        "hadoopJob",
    )
  else:
    candidate_keys = (
        "pysparkBatch",
        "sparkBatch",
        "sparkSqlBatch",
        "sparkRBatch",
        "jupyterSession",
        "sparkConnectSession",
    )
  for key in candidate_keys:
    if isinstance(workload.get(key), dict):
      subtype = key
      spec = workload[key]
      break

  jar_uris: List[str] = list(spec.get("jarFileUris") or [])
  for extra_jar in _split_csv_uris(props.get("spark.jars", "")):
    if extra_jar not in jar_uris:
      jar_uris.append(extra_jar)

  maven_packages = _split_csv_uris(props.get("spark.jars.packages", ""))
  file_uris: List[str] = list(spec.get("fileUris") or [])
  for extra_file in _split_csv_uris(props.get("spark.files", "")):
    if extra_file not in file_uris:
      file_uris.append(extra_file)

  python_file_uris: List[str] = list(spec.get("pythonFileUris") or [])
  for extra_py in _split_csv_uris(props.get("spark.submit.pyFiles", "")):
    if extra_py not in python_file_uris:
      python_file_uris.append(extra_py)

  archive_uris: List[str] = list(spec.get("archiveUris") or [])
  for extra_arch in _split_csv_uris(props.get("spark.archives", "")):
    if extra_arch not in archive_uris:
      archive_uris.append(extra_arch)

  classified_jars = [
      {
          "artifact": item,
          "scala_binary_version": _detect_scala_suffix(item),
      }
      for item in [*jar_uris, *maven_packages]
  ]

  optional_components: List[str] = []
  container_image = ""
  if workload_kind == "job":
    sw_cfg = ((cluster or {}).get("config") or {}).get("softwareConfig") or {}
    optional_components = list(sw_cfg.get("optionalComponents") or [])
  else:
    container_image = (
        (workload.get("runtimeConfig") or {}).get("containerImage") or ""
    )

  relevant_props: Dict[str, Any] = {}
  for k in sorted(props):
    lk = k.lower()
    if any(
        tok in lk
        for tok in (
            "classpath",
            "jars",
            "files",
            "archives",
            "pyfiles",
            "extrajavaoptions",
            "sql.extensions",
            "sql.catalog",
            "sql.defaultcatalog",
            "sql.ansi",
            "adaptive",
            "partition",
            "broadcast",
            "corrupt",
            "badrecords",
            "viewsenabled",
            "materialization",
            "biglake",
            "iceberg",
            "bigquery",
            "spanner",
            "jdbc",
            "fs.s3",
            "fs.gs",
            "fs.azure",
        )
    ):
      relevant_props[k] = redact_value(k, props[k])

  return {
      **header,
      "action": "classpath",
      "workload_subtype": subtype,
      "runtime_spark_version": spark_ver,
      "runtime_scala_binary_version": scala_ver,
      "container_image": container_image,
      "optional_components": optional_components,
      "main_python_file_uri": str(spec.get("mainPythonFileUri") or ""),
      "main_jar_file_uri": str(spec.get("mainJarFileUri") or ""),
      "main_class": str(spec.get("mainClass") or ""),
      "query_file_uri": str(spec.get("queryFileUri") or ""),
      "args": redact_args([str(a) for a in (spec.get("args") or [])]),
      "jar_file_uris": jar_uris,
      "spark_jars_packages": maven_packages,
      "classified_jars": classified_jars,
      "file_uris": file_uris,
      "python_file_uris": python_file_uris,
      "archive_uris": archive_uris,
      "classpath_and_catalog_properties": relevant_props,
      "warnings": warnings,
  }


def format_markdown(report: Dict[str, Any]) -> str:
  """Renders an inspection dictionary into concise key-value Markdown."""
  lines: List[str] = [
      (
          f"# Spark Environment Inspection (`{report['action']}`):"
          f" `{report['workload_id']}`"
      ),
      "",
      f"- workload_type: `{report['workload_type']}`",
      f"- project: `{report['project']}`",
      f"- region: `{report['region']}`",
  ]
  if report.get("cluster_name"):
    lines.append(f"- cluster_name: `{report['cluster_name']}`")
  lines.extend([
      f"- state: `{report['state'] or 'UNKNOWN'}`",
      f"- runtime_version: `{report['runtime_version'] or 'default'}`",
  ])
  if report.get("state_message"):
    lines.append(f"- state_message: {report['state_message']}")

  action = report["action"]
  if action == "identity":
    auth_mode = (
        report["user_workload_authentication_type"] or "SERVICE_ACCOUNT"
    )
    lines.extend([
        "",
        "## Identity & Encryption",
        (
            "- configured_service_account:"
            f" `{report['configured_service_account'] or '(unset)'}`"
        ),
        (
            "- effective_service_account:"
            f" `{report['effective_service_account'] or '(unresolved)'}`"
            + (
                " (inferred Compute Engine default SA)"
                if report["default_service_account_inferred"]
                else ""
            )
        ),
        f"- user_workload_authentication_type: `{auth_mode}`",
        f"- kms_key: `{report['kms_key'] or '(none)'}`",
        f"- staging_bucket: `{report['staging_bucket'] or '(auto)'}`",
        f"- temp_bucket: `{report['temp_bucket'] or '(unset)'}`",
    ])
    if report["service_account_scopes"]:
      lines.append(
          "- service_account_scopes:"
          f" {', '.join(f'`{s}`' for s in report['service_account_scopes'])}"
      )
    lines.append("")
    lines.append("## Project IAM Roles on Effective Service Account")
    if report["project_iam_roles"]:
      for role in report["project_iam_roles"]:
        lines.append(f"- `{role}`")
    else:
      lines.append("- (none found or IAM policy unreadable)")
    if report["auth_related_properties"]:
      lines.append("")
      lines.append("## Auth & Catalog Properties")
      for k, v in report["auth_related_properties"].items():
        lines.append(f"- `{k}`: `{v}`")
    sec = report.get("secret_inspection")
    if sec:
      lines.extend([
          "",
          f"## Secret Manager (`{sec['secret_project']}/{sec['secret_id']}`)",
          (
              "- effective_sa_roles_on_secret:"
              f" {sec['effective_sa_roles_on_secret'] or '(none)'}"
          ),
      ])
      for v in sec["versions"]:
        lines.append(
            f"- version `{v['version']}`: state=`{v['state']}`"
            f" (created `{v['create_time']}`)"
        )

  elif action == "network":
    lines.extend([
        "",
        "## Network Topology",
        f"- effective_host_project: `{report['effective_host_project']}`",
        f"- effective_network: `{report['effective_network']}`",
        f"- effective_subnetwork: `{report['effective_subnetwork']}`",
        f"- internal_ip_only: `{report['internal_ip_only']}`",
        f"- network_tags: {report['network_tags'] or '[]'}",
    ])
    sub = report.get("subnet")
    if sub:
      lines.extend([
          "",
          "## Subnetwork Details",
          f"- ip_cidr_range: `{sub['ip_cidr_range']}`",
          f"- usable_hosts_estimate: `{sub['usable_hosts_estimate']}`",
          (
              "- private_ip_google_access:"
              f" `{sub['private_ip_google_access']}`"
          ),
      ])
    lines.append("")
    lines.append("## Cloud NAT Gateways")
    if report["cloud_nats"]:
      for nat in report["cloud_nats"]:
        lines.append(
            f"- router=`{nat['router']}` nat=`{nat['name']}`"
            f" mode=`{nat['source_subnetwork_ip_ranges_to_nat']}`"
            f" covers_workload_subnet=`{nat['covers_workload_subnet']}`"
        )
    else:
      lines.append("- (no Cloud NAT gateways on workload network/region)")
    lines.append("")
    lines.append("## Applicable VPC Firewall Rules")
    if report["firewall_rules"]:
      for fw in report["firewall_rules"]:
        port_val = fw["matches_target_port"]
        port_note = (
            f" matches_port_{report['target_port']}=`{port_val}`"
            if port_val is not None
            else ""
        )
        range_label = "src" if fw["direction"] == "INGRESS" else "dest"
        ranges_val = (
            fw["source_ranges"]
            if fw["direction"] == "INGRESS"
            else fw["destination_ranges"]
        )
        lines.append(
            f"- `{fw['name']}`: {fw['direction']} {fw['action']}"
            f" priority=`{fw['priority']}`"
            f" {range_label}={ranges_val}"
            f" applies_to_tags=`{fw['applies_to_workload_tags']}`"
            f" rules=`{json.dumps(fw['rules'])}`{port_note}"
        )
    else:
      lines.append("- (no matching egress/deny firewall rules returned)")
    lines.append("")
    lines.append("## Private Cloud DNS Zones")
    if report["private_dns_zones"]:
      for z in report["private_dns_zones"]:
        lines.append(
            f"- `{z['name']}` (`{z['dns_name']}`):"
            f" bound_to_workload_network=`{z['bound_to_workload_network']}`"
            f" bound_networks={z['bound_networks']}"
        )
    else:
      lines.append("- (no private Cloud DNS zones found)")

  elif action == "classpath":
    lines.extend([
        "",
        "## Runtime & Entrypoint",
        f"- workload_subtype: `{report['workload_subtype'] or 'unknown'}`",
        f"- runtime_spark_version: `{report['runtime_spark_version']}`",
        (
            "- runtime_scala_binary_version:"
            f" `{report['runtime_scala_binary_version']}`"
        ),
        (
            "- optional_components:"
            f" {report['optional_components'] or '[]'}"
        ),
        (
            "- container_image:"
            f" `{report['container_image'] or '(default image)'}`"
        ),
    ])
    for field_name in (
        "main_python_file_uri",
        "main_jar_file_uri",
        "main_class",
        "query_file_uri",
    ):
      if report.get(field_name):
        lines.append(f"- {field_name}: `{report[field_name]}`")
    if report["args"]:
      lines.append(f"- args: `{json.dumps(report['args'])}`")
    lines.append("")
    lines.append("## Attached JARs & Packages")
    if report["classified_jars"]:
      for j in report["classified_jars"]:
        lines.append(
            f"- `{j['artifact']}`"
            f" (scala_binary=`{j['scala_binary_version'] or 'unversioned'}`)"
        )
    else:
      lines.append("- (no custom JARs or spark.jars.packages attached)")
    lines.append("")
    lines.append("## Distributed Files, PyFiles & Archives")
    lines.append(f"- file_uris: {report['file_uris'] or '[]'}")
    lines.append(f"- python_file_uris: {report['python_file_uris'] or '[]'}")
    lines.append(f"- archive_uris: {report['archive_uris'] or '[]'}")
    if report["classpath_and_catalog_properties"]:
      lines.append("")
      lines.append("## Classpath, SQL & Catalog Properties")
      for k, v in report["classpath_and_catalog_properties"].items():
        lines.append(f"- `{k}`: `{v}`")

  if report.get("warnings"):
    lines.append("")
    lines.append("## Warnings (Partial Visibility)")
    for w in report["warnings"]:
      lines.append(f"- {w}")

  return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
  """Builds the CLI argument parser."""
  parser = argparse.ArgumentParser(
      description=(
          "Inspects Google Cloud identity/KMS/secrets, VPC/PGA/NAT/DNS/firewall"
          " topology, or Spark/Scala classpath metadata for a Dataproc"
          " Serverless batch, interactive session, or cluster job."
      )
  )
  target = parser.add_mutually_exclusive_group(required=True)
  target.add_argument("--batch_id", help="Dataproc Serverless batch ID")
  target.add_argument("--session_id", help="Dataproc interactive session ID")
  target.add_argument("--job_id", help="Dataproc cluster job ID")

  parser.add_argument(
      "--project", help="GCP project ID (default: active gcloud project)"
  )
  parser.add_argument(
      "--region",
      "--location",
      dest="region",
      default=DEFAULT_REGION,
      help="GCP region / location (default: %(default)s)",
  )
  parser.add_argument(
      "--action",
      required=True,
      choices=["identity", "network", "classpath"],
      help="Environment plane to inspect",
  )
  parser.add_argument(
      "--secret_id",
      help=(
          "Optional Secret Manager secret ID or resource path to inspect"
          " version states and IAM bindings (--action=identity)"
      ),
  )
  parser.add_argument(
      "--target_port",
      type=int,
      help=(
          "Optional TCP port (e.g. 5432, 3306, 443) to match against VPC"
          " firewall rules (--action=network)"
      ),
  )
  parser.add_argument(
      "--format",
      choices=["markdown", "json"],
      default="markdown",
      help="Output format (default: %(default)s)",
  )
  return parser


def main(
    argv: Optional[List[str]] = None,
    runner: CommandRunner = _default_gcloud_runner,
) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)

  if args.target_port is not None and not (1 <= args.target_port <= 65535):
    parser.error("--target_port must be between 1 and 65535")

  project = args.project or resolve_default_project(runner)
  if not project:
    print(
        "Error: No project given and no active gcloud project; pass --project.",
        file=sys.stderr,
    )
    return 1

  if args.batch_id:
    workload_kind, workload_id = "batch", args.batch_id
  elif args.session_id:
    workload_kind, workload_id = "session", args.session_id
  else:
    workload_kind, workload_id = "job", args.job_id

  try:
    if args.action == "identity":
      report = inspect_identity(
          project,
          args.region,
          workload_kind,
          workload_id,
          runner,
          secret_id=args.secret_id,
      )
    elif args.action == "network":
      report = inspect_network(
          project,
          args.region,
          workload_kind,
          workload_id,
          runner,
          target_port=args.target_port,
      )
    else:
      report = inspect_classpath(
          project, args.region, workload_kind, workload_id, runner
      )
  except InspectorError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    return 1

  if args.format == "json":
    print(json.dumps(report, indent=2, sort_keys=True))
  else:
    print(format_markdown(report))
  return 0


if __name__ == "__main__":
  sys.exit(main())
