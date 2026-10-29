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
  * `identity`: effective principal (workload service account, or the
    creator/session user for end-user credentials), authentication mode,
    OAuth scopes, KMS key, direct project IAM roles, and optional Secret
    Manager version states/IAM (never accesses secret payloads).
  * `network`: VPC/subnet URIs, CIDR capacity, Private Google Access, Cloud
    NAT coverage, VPC peerings, VPC firewall rules that apply to the workload
    (with optional `--target_port` matching), effective hierarchical, network,
    and system firewall policy rules, and Cloud DNS private zone bindings.
  * `classpath`: Dataproc runtime/image version, mapped Spark and Scala binary
    versions, attached JARs/packages with detected Scala (`_2.12` / `_2.13`)
    and Spark (`spark-3.5`, `-3.5_2.13`) versions compared with the runtime,
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
# Spark minor version embedded in connector artifact names, for example
# `spark-3.5-bigquery`, `hudi-spark3.5-bundle`, or
# `iceberg-spark-runtime-3.5_2.13`.
_SPARK_MINOR_RES = (
    re.compile(r"spark[-_]?(\d+\.\d+)(?=[-_.:/]|$)", re.IGNORECASE),
    re.compile(r"[-_](\d+\.\d+)_2\.1[123](?=[-._/:]|$)"),
)
# Caps for list-valued network output so large enterprise VPCs stay readable.
_MAX_FIREWALL_RULES = 100
_MAX_POLICY_RULES = 80
_MAX_RANGES_SHOWN = 5
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
# Oracle thin/OCI URLs embed credentials as `user/password@host`.
_ORACLE_CREDENTIALS_RE = re.compile(
    r"(jdbc:oracle:[a-z0-9]+:[^/@\s:]+/)([^@\s]+)(@)", re.IGNORECASE
)
# Values after a sensitive flag that identify resources rather than carry
# credentials: URIs, absolute paths, and resource names.
_RESOURCE_VALUE_RE = re.compile(
    r"^(?:[a-z][a-z0-9+.-]*://|/|projects/)", re.IGNORECASE
)
_INLINE_SECRET_KV_RE = re.compile(
    r"((?:^|[?&;\s]|-D)[\w.-]*?(?:password|passwd|pwd|passphrase|secret|token|"
    r"credential|authorization|private[_.-]?key|access[_.-]?key|"
    r"account[_.-]?key|client[_.-]?secret|api[_.-]?key)\s*=\s*)([^&;\s\"']+)",
    re.IGNORECASE,
)


class InspectorError(RuntimeError):
  """Raised when the primary workload cannot be resolved or arguments fail."""


def _as_dict(value: Any) -> Dict[str, Any]:
  return value if isinstance(value, dict) else {}


def _dict_field(mapping: Any, key: str) -> Dict[str, Any]:
  if not isinstance(mapping, dict):
    return {}
  return _as_dict(mapping.get(key))


def _str_field(mapping: Any, key: str, default: str = "") -> str:
  if not isinstance(mapping, dict):
    return default
  val = mapping.get(key)
  if val is None:
    return default
  text = str(val)
  return text if text else default


def _list_field(mapping: Any, key: str) -> List[Any]:
  if not isinstance(mapping, dict):
    return []
  val = mapping.get(key)
  return list(val) if isinstance(val, list) else []


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
  out = "" if proc.stdout is None else proc.stdout
  err = "" if proc.stderr is None else proc.stderr
  return proc.returncode, out, err


def _concise_stderr(stderr: Optional[str], code: int) -> str:
  raw = "" if stderr is None else stderr
  lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
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
    parsed = json.loads(text)
  except ValueError as exc:
    msg = f"{label}: invalid JSON output ({exc})"
    if fatal:
      raise InspectorError(msg) from exc
    warnings.append(msg)
    return None
  return {} if parsed is None else parsed


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
  scrubbed = _ORACLE_CREDENTIALS_RE.sub(r"\1<REDACTED>\3", scrubbed)
  return _INLINE_SECRET_KV_RE.sub(r"\1<REDACTED>", scrubbed)


def redact_value(key: str, value: Any) -> Any:
  """Redacts sensitive credential values while preserving safe metadata keys."""
  str_val = str(value)
  if _is_safe_key(key):
    return value
  if _SENSITIVE_KEY_RE.search(key) and str_val:
    return "<REDACTED>"
  if isinstance(value, str):
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
        # Keep resource values (for example the input path after
        # `--use-secret-manager`); inline URI credentials are still scrubbed.
        sanitized.append(
            _scrub_inline_secrets(item)
            if _RESOURCE_VALUE_RE.match(item)
            else "<REDACTED>"
        )
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
    return _as_dict(batch), None

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
      return _as_dict(session), None
    err_msg = beta_warnings[0]
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
      return _as_dict(ga_session), None
    raise InspectorError(err_msg)

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
    job_dict = _as_dict(job)
    cluster_name = _str_field(_dict_field(job_dict, "placement"), "clusterName")
    cluster_dict = None
    if cluster_name:
      raw_cluster = _run_gcloud_json(
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
      if raw_cluster is not None:
        cluster_dict = _as_dict(raw_cluster)
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
    status = _dict_field(workload, "status")
    state = _str_field(status, "state")
    state_message = _str_field(status, "details")
    cluster_name = _str_field(_dict_field(workload, "placement"), "clusterName")
    sw_cfg = _dict_field(_dict_field(cluster, "config"), "softwareConfig")
    runtime_version = _str_field(sw_cfg, "imageVersion")
  else:
    state = _str_field(workload, "state")
    state_message = _str_field(workload, "stateMessage")
    cluster_name = ""
    runtime_version = _str_field(
        _dict_field(workload, "runtimeConfig"), "version"
    )
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
    sw_cfg = _dict_field(_dict_field(cluster, "config"), "softwareConfig")
    for k, v in _dict_field(sw_cfg, "properties").items():
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
        for k, v in _dict_field(sub, "properties").items():
          merged[_normalize_prop_key(k)] = str(v)
  else:
    rt_props = _dict_field(_dict_field(workload, "runtimeConfig"), "properties")
    for k, v in rt_props.items():
      merged[str(k)] = str(v)
    # Properties the autotuning engine set (`ValueInfo` objects); explicitly
    # configured properties take precedence.
    autotuned = _dict_field(
        _dict_field(_dict_field(workload, "runtimeInfo"), "propertiesInfo"),
        "autotuningProperties",
    )
    for k, v in autotuned.items():
      value = v.get("value") if isinstance(v, dict) else v
      if value is not None:
        merged.setdefault(str(k), str(value))
  return merged


def _parse_secret_ref(default_project: str, raw_secret: str) -> Tuple[str, str]:
  """Parses `projects/<p>/secrets/<s>[/versions/<v>]` or bare `<s>`."""
  match = re.fullmatch(
      r"projects/([^/]+)/secrets/([^/]+)(?:/versions/[^/]+)?",
      raw_secret.strip(),
  )
  if match:
    return match.group(1), match.group(2)
  return default_project, raw_secret.strip()


def _member_for_email(email: str) -> str:
  """Returns the IAM member string for a user or service account email."""
  if email.endswith(".gserviceaccount.com"):
    return f"serviceAccount:{email}"
  return f"user:{email}"


def _serverless_auth_type(
    workload: Dict[str, Any], runtime_version: str
) -> str:
  """Resolves the user workload authentication type of a batch or session.

  Serverless runtime 3.0+ uses end-user credentials by default when no
  service account is configured; older runtimes use a service account.

  Args:
    workload: Batch or session resource.
    runtime_version: Runtime version string from `runtimeConfig.version`.

  Returns:
    `SERVICE_ACCOUNT` or `END_USER_CREDENTIALS`.
  """
  exec_cfg = _dict_field(
      _dict_field(workload, "environmentConfig"), "executionConfig"
  )
  raw_auth_type = _str_field(
      _dict_field(exec_cfg, "authenticationConfig"),
      "userWorkloadAuthenticationType",
  )
  if raw_auth_type and raw_auth_type != "AUTHENTICATION_TYPE_UNSPECIFIED":
    return raw_auth_type
  ver_match = re.search(r"^(\d+)\.", runtime_version.strip())
  is_serverless_3_plus = bool(ver_match and int(ver_match.group(1)) >= 3)
  if not _str_field(exec_cfg, "serviceAccount") and is_serverless_3_plus:
    return "END_USER_CREDENTIALS"
  return "SERVICE_ACCOUNT"


def _default_compute_sa(
    project: str, runner: CommandRunner, warnings: List[str]
) -> str:
  """Returns the Compute Engine default service account of a project."""
  proj_info = _run_gcloud_json(
      runner,
      ["projects", "describe", project],
      warnings,
      f"projects describe '{project}'",
  )
  proj_num = _str_field(proj_info, "projectNumber")
  if not proj_num:
    return ""
  return f"{proj_num}-compute@developer.gserviceaccount.com"


def inspect_identity(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
    secret_id: Optional[str] = None,
) -> Dict[str, Any]:
  """Collects principal, KMS, IAM, and optional Secret Manager facts."""
  warnings: List[str] = []
  workload, cluster = _fetch_workload(
      project, region, workload_kind, workload_id, runner, warnings
  )
  header = _extract_common_header(
      project, region, workload_kind, workload_id, workload, cluster
  )
  props = _merged_properties(workload_kind, workload, cluster)

  creator = ""
  session_user = ""
  if workload_kind == "job":
    cluster_cfg = _dict_field(cluster, "config")
    gce_cfg = _dict_field(cluster_cfg, "gceClusterConfig")
    enc_cfg = _dict_field(cluster_cfg, "encryptionConfig")
    configured_sa = _str_field(gce_cfg, "serviceAccount")
    auth_type = "SERVICE_ACCOUNT"
    sa_scopes = _list_field(gce_cfg, "serviceAccountScopes")
    kms_key = _str_field(
        enc_cfg, "gcePdKmsKeyName", _str_field(enc_cfg, "kmsKey")
    )
    staging_bucket = _str_field(cluster_cfg, "configBucket")
    temp_bucket = _str_field(cluster_cfg, "tempBucket")
    # Multi-tenant and personal-auth clusters run jobs as other principals.
    user_sa_mapping = _dict_field(
        _dict_field(
            _dict_field(cluster_cfg, "securityConfig"), "identityConfig"
        ),
        "userServiceAccountMapping",
    )
    if user_sa_mapping:
      warnings.append(
          "cluster uses secure multi-tenancy"
          f" ({len(user_sa_mapping)} user mappings): jobs run as the service"
          " account mapped to the submitting user, not as the VM service"
          " account"
      )
    personal_auth_user = _str_field(
        _dict_field(_dict_field(cluster_cfg, "softwareConfig"), "properties"),
        "dataproc:dataproc.personal-auth.user",
    )
    if personal_auth_user:
      warnings.append(
          "cluster uses personal cluster authentication: jobs call Google"
          f" APIs with the credentials of '{personal_auth_user}'"
      )
  else:
    exec_cfg = _dict_field(
        _dict_field(workload, "environmentConfig"), "executionConfig"
    )
    configured_sa = _str_field(exec_cfg, "serviceAccount")
    auth_type = _serverless_auth_type(workload, str(header["runtime_version"]))
    creator = _str_field(workload, "creator")
    session_user = _str_field(workload, "user")
    sa_scopes = []
    kms_key = _str_field(exec_cfg, "kmsKey")
    staging_bucket = _str_field(exec_cfg, "stagingBucket")
    temp_bucket = _str_field(
        props,
        "spark.datasource.bigquery.temporaryGcsBucket",
        _str_field(props, "temporaryGcsBucket"),
    )

  effective_sa = configured_sa
  default_sa_inferred = False
  if (
      not effective_sa
      and auth_type != "END_USER_CREDENTIALS"
      and (workload_kind != "job" or cluster is not None)
  ):
    effective_sa = _default_compute_sa(project, runner, warnings)
    default_sa_inferred = bool(effective_sa)

  # With end-user credentials the workload acts as the session owner or the
  # user who created the batch, not as a service account.
  if auth_type == "END_USER_CREDENTIALS":
    principal_email = session_user or creator
  else:
    principal_email = effective_sa
  effective_principal = (
      _member_for_email(principal_email) if principal_email else ""
  )

  project_iam_roles: List[str] = []
  if effective_principal:
    policy = _run_gcloud_json(
        runner,
        ["projects", "get-iam-policy", project],
        warnings,
        f"projects get-iam-policy '{project}'",
    )
    for binding in _list_field(policy, "bindings"):
      members = _list_field(binding, "members")
      if effective_principal in members:
        role = _str_field(binding, "role")
        cond = _str_field(_dict_field(binding, "condition"), "title")
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
        raw_name = _str_field(v, "name")
        versions_summary.append({
            "version": raw_name.split("/")[-1],
            "state": _str_field(v, "state"),
            "create_time": _str_field(v, "createTime"),
        })
    sec_policy = _run_gcloud_json(
        runner,
        ["secrets", "get-iam-policy", sec_name, f"--project={sec_project}"],
        warnings,
        f"secrets get-iam-policy '{sec_name}'",
    )
    sec_bindings: List[Dict[str, Any]] = []
    principal_secret_roles: List[str] = []
    for b in _list_field(sec_policy, "bindings"):
      role = _str_field(b, "role")
      members = _list_field(b, "members")
      sec_bindings.append({"role": role, "members": members})
      if effective_principal and effective_principal in members:
        principal_secret_roles.append(role)
    secret_info = {
        "secret_project": sec_project,
        "secret_id": sec_name,
        "versions": versions_summary,
        "iam_bindings": sec_bindings,
        "principal_roles_on_secret": sorted(principal_secret_roles),
    }

  return {
      **header,
      "action": "identity",
      "configured_service_account": configured_sa,
      "effective_service_account": effective_sa,
      "default_service_account_inferred": default_sa_inferred,
      "user_workload_authentication_type": auth_type,
      "creator": creator,
      "session_user": session_user,
      "effective_principal": effective_principal,
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
  full_match = re.search(
      r"projects/([^/]+)/regions/([^/]+)/subnetworks/([^/?#]+)", uri
  )
  if full_match:
    return full_match.group(1), full_match.group(2), full_match.group(3)
  short_match = re.search(r"regions/([^/]+)/subnetworks/([^/?#]+)", uri)
  if short_match:
    return default_project, short_match.group(1), short_match.group(2)
  return default_project, default_region, uri.split("/")[-1]


def _parse_network_uri(uri: str, default_project: str) -> Tuple[str, str]:
  """Extracts (host_project, network_name) from a network URI."""
  full_match = re.search(r"projects/([^/]+)/global/networks/([^/?#]+)", uri)
  if full_match:
    return full_match.group(1), full_match.group(2)
  return default_project, uri.split("/")[-1]


def _cidr_usable_hosts(cidr: str) -> Optional[int]:
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
  """Checks whether firewall rule protocol/port specs cover a TCP port.

  Accepts VPC firewall rule specs (`IPProtocol`/`ports`) and firewall policy
  `layer4Configs` entries (`ipProtocol`/`ports`).

  Args:
    specs: Protocol and port specs of one rule.
    target_port: TCP port to match.

  Returns:
    Whether any spec covers TCP `target_port`.
  """
  for spec in specs:
    proto = _str_field(
        spec, "IPProtocol", _str_field(spec, "ipProtocol")
    ).lower()
    if proto not in ("all", "tcp", "6"):
      continue
    ports = _list_field(spec, "ports")
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


def _target_applies(
    target_tags: List[Any],
    target_sas: List[Any],
    network_tags: List[Any],
    workload_sa: str,
) -> Optional[bool]:
  """Returns whether a tag/SA-scoped rule targets the workload VMs.

  Args:
    target_tags: Network tags the rule targets.
    target_sas: Service accounts the rule targets.
    network_tags: Network tags on the workload VMs.
    workload_sa: Service account of the workload VMs ("" when unknown).

  Returns:
    True or False, or None when the rule targets service accounts and the
    workload VM service account is unknown.
  """
  if target_tags:
    return bool(set(target_tags).intersection(network_tags))
  if target_sas:
    if not workload_sa:
      return None
    return workload_sa in target_sas
  return True


def _summarize_ranges(ranges: List[Any]) -> List[str]:
  """Truncates long IP range lists, noting how many were omitted."""
  shown = [str(r) for r in ranges[:_MAX_RANGES_SHOWN]]
  if len(ranges) > _MAX_RANGES_SHOWN:
    shown.append(f"... (+{len(ranges) - _MAX_RANGES_SHOWN} more)")
  return shown


def _inspect_vpc_network(
    network_name: str,
    host_project: str,
    runner: CommandRunner,
    warnings: List[str],
) -> Tuple[List[Dict[str, Any]], str]:
  """Returns (VPC peerings, firewall policy enforcement order) of a network."""
  raw_net = _run_gcloud_json(
      runner,
      [
          "compute",
          "networks",
          "describe",
          network_name,
          f"--project={host_project}",
      ],
      warnings,
      f"compute networks describe '{network_name}'",
  )
  peerings: List[Dict[str, Any]] = []
  for peer in _list_field(raw_net, "peerings"):
    if not isinstance(peer, dict):
      continue
    peer_project, peer_network = _parse_network_uri(
        _str_field(peer, "network"), host_project
    )
    peerings.append({
        "name": _str_field(peer, "name"),
        "peer_project": peer_project,
        "peer_network": peer_network,
        "state": _str_field(peer, "state"),
        "state_details": _str_field(peer, "stateDetails"),
        "import_custom_routes": bool(peer.get("importCustomRoutes", False)),
        "export_custom_routes": bool(peer.get("exportCustomRoutes", False)),
    })
  enforcement_order = _str_field(
      raw_net, "networkFirewallPolicyEnforcementOrder"
  )
  return peerings, enforcement_order


def _inspect_firewall_policies(
    network_name: str,
    host_project: str,
    region: str,
    runner: CommandRunner,
    warnings: List[str],
    network_tags: List[Any],
    workload_sa: str,
    target_port: Optional[int],
) -> List[Dict[str, Any]]:
  """Summarizes effective hierarchical, network, and system policy rules."""
  raw = _run_gcloud_json(
      runner,
      [
          "compute",
          "network-firewall-policies",
          "get-effective-firewalls",
          f"--network={network_name}",
          f"--region={region}",
          f"--project={host_project}",
      ],
      warnings,
      f"compute network-firewall-policies get-effective-firewalls ({region})",
  )
  policies: List[Dict[str, Any]] = []
  total_rules = 0
  truncated = False
  for policy in _list_field(raw, "firewallPolicys"):
    if not isinstance(policy, dict):
      continue
    rules: List[Dict[str, Any]] = []
    raw_rules = [r for r in _list_field(policy, "rules") if isinstance(r, dict)]
    raw_rules.sort(key=lambda r: int(r.get("priority", 0)))
    for rule in raw_rules:
      if rule.get("disabled"):
        continue
      if total_rules >= _MAX_POLICY_RULES:
        truncated = True
        break
      match = _dict_field(rule, "match")
      layer4 = _list_field(match, "layer4Configs")
      target_sas = _list_field(rule, "targetServiceAccounts")
      secure_tags = [
          _str_field(t, "name")
          for t in _list_field(rule, "targetSecureTags")
          if isinstance(t, dict)
      ]
      # Secure tags (for example the per-subnet tag that Serverless runtime
      # 3.0+ system policies use) cannot be resolved here.
      applies = (
          None
          if secure_tags
          else _target_applies([], target_sas, network_tags, workload_sa)
      )
      rules.append({
          "priority": int(rule.get("priority", 0)),
          "direction": _str_field(rule, "direction"),
          "action": _str_field(rule, "action"),
          "layer4_configs": layer4,
          "source_ranges": _summarize_ranges(
              _list_field(match, "srcIpRanges")
          ),
          "destination_ranges": _summarize_ranges(
              _list_field(match, "destIpRanges")
          ),
          "target_service_accounts": target_sas,
          "target_secure_tags": secure_tags,
          "applies_to_workload": applies,
          "matches_target_port": (
              _port_matches_specs(layer4, target_port)
              if target_port is not None
              else None
          ),
      })
      total_rules += 1
    policy_name = (
        _str_field(policy, "displayName")
        or _str_field(policy, "shortName")
        or _str_field(policy, "name")
    )
    policies.append({
        "name": policy_name,
        "type": _str_field(policy, "type"),
        "rules": rules,
    })
  if truncated:
    warnings.append(
        f"firewall policies: only the first {_MAX_POLICY_RULES} rules are"
        " listed"
    )
  return policies


def inspect_network(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
    target_port: Optional[int] = None,
) -> Dict[str, Any]:
  """Collects subnet, NAT, peering, firewall, and private DNS facts."""
  warnings: List[str] = []
  workload, cluster = _fetch_workload(
      project, region, workload_kind, workload_id, runner, warnings
  )
  header = _extract_common_header(
      project, region, workload_kind, workload_id, workload, cluster
  )
  can_inspect_vpc = workload_kind != "job" or cluster is not None

  if workload_kind == "job":
    cluster_cfg = _dict_field(cluster, "config")
    gce_cfg = _dict_field(cluster_cfg, "gceClusterConfig")
    configured_subnet_uri = _str_field(gce_cfg, "subnetworkUri")
    configured_network_uri = _str_field(gce_cfg, "networkUri")
    network_tags = _list_field(gce_cfg, "tags")
    workload_sa = _str_field(gce_cfg, "serviceAccount")
    uses_service_account = True
    internal_ip_only = bool(gce_cfg.get("internalIpOnly", False))
  else:
    exec_cfg = _dict_field(
        _dict_field(workload, "environmentConfig"), "executionConfig"
    )
    configured_subnet_uri = _str_field(exec_cfg, "subnetworkUri")
    configured_network_uri = _str_field(exec_cfg, "networkUri")
    network_tags = _list_field(exec_cfg, "networkTags")
    workload_sa = _str_field(exec_cfg, "serviceAccount")
    uses_service_account = (
        _serverless_auth_type(workload, str(header["runtime_version"]))
        != "END_USER_CREDENTIALS"
    )
    # Dataproc Serverless never assigns external IPs to driver/executor VMs.
    internal_ip_only = True

  # Firewall rules can target the Compute Engine default service account,
  # which workloads use when no service account is configured.
  workload_sa_inferred = False
  if not workload_sa and uses_service_account and can_inspect_vpc:
    workload_sa = _default_compute_sa(project, runner, warnings)
    workload_sa_inferred = bool(workload_sa)

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
  cloud_nats: List[Dict[str, Any]] = []
  vpc_peerings: List[Dict[str, Any]] = []
  enforcement_order = ""
  firewall_rules: List[Dict[str, Any]] = []
  firewall_policies: List[Dict[str, Any]] = []
  private_dns_zones: List[Dict[str, Any]] = []

  if can_inspect_vpc:
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
      net_from_subnet = _str_field(raw_subnet, "network")
      if net_from_subnet:
        host_project, network_name = _parse_network_uri(
            net_from_subnet, host_project
        )
      cidr = _str_field(raw_subnet, "ipCidrRange")
      subnet_details = {
          "name": _str_field(raw_subnet, "name", subnet_name),
          "host_project": host_project,
          "region": subnet_region,
          "network": network_name,
          "ip_cidr_range": cidr,
          "usable_hosts_estimate": _cidr_usable_hosts(cidr),
          "private_ip_google_access": bool(
              raw_subnet.get("privateIpGoogleAccess", False)
          ),
          "purpose": _str_field(raw_subnet, "purpose"),
          "stack_type": _str_field(raw_subnet, "stackType"),
      }

  if can_inspect_vpc and network_name:
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
        r_net = _str_field(router, "network")
        _, r_net_name = _parse_network_uri(r_net, host_project)
        if r_net_name != network_name:
          continue
        r_name = _str_field(router, "name")
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
            nat_name = _str_field(nat, "name")
            nat_type = _str_field(nat, "type", "PUBLIC")
            source_mode = _str_field(nat, "sourceSubnetworkIpRangesToNat")
            nat_subnets: List[str] = []
            primary_covered_subnets: List[str] = []
            for s in _list_field(nat, "subnetworks"):
              if not isinstance(s, dict):
                continue
              sub_short = _parse_subnetwork_uri(
                  _str_field(s, "name"), host_project, subnet_region
              )[2]
              nat_subnets.append(sub_short)
              ip_ranges = _list_field(s, "sourceIpRangesToNat")
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

    vpc_peerings, enforcement_order = _inspect_vpc_network(
        network_name, host_project, runner, warnings
    )

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
            _str_field(fw, "network"), host_project
        )
        if fw_net != network_name:
          continue
        direction = _str_field(fw, "direction", "INGRESS")
        allowed = _list_field(fw, "allowed")
        denied = _list_field(fw, "denied")
        action = "DENY" if denied else "ALLOW"
        specs = denied if denied else allowed
        target_tags = _list_field(fw, "targetTags")
        target_sas = _list_field(fw, "targetServiceAccounts")
        applies = _target_applies(
            target_tags, target_sas, network_tags, workload_sa
        )
        port_matches = (
            _port_matches_specs(specs, target_port)
            if target_port is not None
            else None
        )
        # Keep every rule that (may) apply to the workload VMs, plus DENY and
        # port-matching rules scoped elsewhere so near misses stay visible.
        may_apply = applies is None or applies
        if may_apply or action == "DENY" or bool(port_matches):
          matched_fws.append({
              "name": _str_field(fw, "name"),
              "direction": direction,
              "priority": int(fw.get("priority", 1000)),
              "action": action,
              "destination_ranges": _list_field(fw, "destinationRanges"),
              "source_ranges": _list_field(fw, "sourceRanges"),
              "source_tags": _list_field(fw, "sourceTags"),
              "target_tags": target_tags,
              "target_service_accounts": target_sas,
              "applies_to_workload": applies,
              "rules": specs,
              "matches_target_port": port_matches,
          })
      # Lower priority numbers win; at equal priority DENY beats ALLOW.
      matched_fws.sort(
          key=lambda item: (
              item["priority"],
              0 if item["action"] == "DENY" else 1,
              item["name"],
          )
      )
      if len(matched_fws) > _MAX_FIREWALL_RULES:
        warnings.append(
            f"firewall rules: only the first {_MAX_FIREWALL_RULES} of"
            f" {len(matched_fws)} matching VPC rules are listed"
        )
      firewall_rules = matched_fws[:_MAX_FIREWALL_RULES]

    firewall_policies = _inspect_firewall_policies(
        network_name,
        host_project,
        subnet_region,
        runner,
        warnings,
        network_tags,
        workload_sa,
        target_port,
    )

    raw_zones = _run_gcloud_json(
        runner,
        ["dns", "managed-zones", "list", f"--project={host_project}"],
        warnings,
        f"dns managed-zones list '{host_project}'",
    )
    if isinstance(raw_zones, list):
      for zone in raw_zones:
        if _str_field(zone, "visibility").lower() != "private":
          continue
        vis_cfg = _dict_field(zone, "privateVisibilityConfig")
        bound_nets = [
            _parse_network_uri(_str_field(n, "networkUrl"), host_project)[1]
            for n in _list_field(vis_cfg, "networks")
            if isinstance(n, dict)
        ]
        private_dns_zones.append({
            "name": _str_field(zone, "name"),
            "dns_name": _str_field(zone, "dnsName"),
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
      "workload_service_account": workload_sa,
      "workload_service_account_inferred": workload_sa_inferred,
      "target_port": target_port,
      "subnet": subnet_details,
      "cloud_nats": cloud_nats,
      "vpc_peerings": vpc_peerings,
      "firewall_policy_enforcement_order": enforcement_order,
      "firewall_rules": firewall_rules,
      "firewall_policies": firewall_policies,
      "private_dns_zones": private_dns_zones,
      "warnings": warnings,
  }


def _map_runtime_versions(
    workload_kind: str, runtime_version: str
) -> Tuple[str, str]:
  """Maps a Dataproc runtime or image version to (spark_ver, scala_binary)."""
  match = re.search(r"^(\d+\.\d+)", runtime_version.strip())
  prefix = match.group(1) if match else runtime_version.strip()
  table = (
      _CLUSTER_IMAGE_MAP if workload_kind == "job" else _SERVERLESS_RUNTIME_MAP
  )
  return table.get(prefix, ("unknown", "unknown"))


def _detect_scala_suffix(uri_or_coord: str) -> Optional[str]:
  basename = uri_or_coord.split("/")[-1]
  match = _SCALA_SUFFIX_RE.search(basename)
  return match.group(1) if match else None


def _detect_spark_minor(uri_or_coord: str) -> Optional[str]:
  """Returns the Spark minor version a connector artifact targets, if any."""
  basename = uri_or_coord.split("/")[-1]
  for pattern in _SPARK_MINOR_RES:
    match = pattern.search(basename)
    if match:
      return match.group(1)
  return None


def _matches_runtime(artifact_ver: Optional[str], runtime_ver: str) -> Any:
  """Compares an artifact version with the runtime's (None if unknown)."""
  if not artifact_ver or runtime_ver == "unknown":
    return None
  return artifact_ver == runtime_ver


def _split_csv_uris(raw: str) -> List[str]:
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
        "pysparkNotebookBatch",
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

  jar_uris = _list_field(spec, "jarFileUris")
  for extra_jar in _split_csv_uris(props.get("spark.jars", "")):
    if extra_jar not in jar_uris:
      jar_uris.append(extra_jar)

  maven_packages = _split_csv_uris(props.get("spark.jars.packages", ""))
  file_uris = _list_field(spec, "fileUris")
  for extra_file in _split_csv_uris(props.get("spark.files", "")):
    if extra_file not in file_uris:
      file_uris.append(extra_file)

  python_file_uris = _list_field(spec, "pythonFileUris")
  for extra_py in _split_csv_uris(props.get("spark.submit.pyFiles", "")):
    if extra_py not in python_file_uris:
      python_file_uris.append(extra_py)

  archive_uris = _list_field(spec, "archiveUris")
  for extra_arch in _split_csv_uris(props.get("spark.archives", "")):
    if extra_arch not in archive_uris:
      archive_uris.append(extra_arch)

  main_jar = _str_field(spec, "mainJarFileUri")
  all_jars = (
      [main_jar, *jar_uris]
      if main_jar and main_jar not in jar_uris
      else jar_uris
  )
  classified_jars = []
  for item in [*all_jars, *maven_packages]:
    scala_bin = _detect_scala_suffix(item)
    spark_minor = _detect_spark_minor(item)
    classified_jars.append({
        "artifact": item,
        "scala_binary_version": scala_bin,
        "spark_minor_version": spark_minor,
        "scala_matches_runtime": _matches_runtime(scala_bin, scala_ver),
        "spark_matches_runtime": _matches_runtime(spark_minor, spark_ver),
    })

  optional_components: List[str] = []
  container_image = ""
  if workload_kind == "job":
    sw_cfg = _dict_field(_dict_field(cluster, "config"), "softwareConfig")
    optional_components = _list_field(sw_cfg, "optionalComponents")
  else:
    container_image = _str_field(
        _dict_field(workload, "runtimeConfig"), "containerImage"
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
      "main_python_file_uri": _str_field(spec, "mainPythonFileUri"),
      "notebook_file_uri": _str_field(spec, "notebookFileUri"),
      "main_jar_file_uri": main_jar,
      "main_class": _str_field(spec, "mainClass"),
      "query_file_uri": _str_field(spec, "queryFileUri"),
      "args": redact_args([str(a) for a in _list_field(spec, "args")]),
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
  state_disp = _str_field(report, "state", "UNKNOWN")
  ver_disp = _str_field(report, "runtime_version", "default")
  lines.extend([
      f"- state: `{state_disp}`",
      f"- runtime_version: `{ver_disp}`",
  ])
  if report.get("state_message"):
    lines.append(f"- state_message: {report['state_message']}")

  action = report["action"]
  if action == "identity":
    auth_mode = _str_field(
        report, "user_workload_authentication_type", "SERVICE_ACCOUNT"
    )
    principal_disp = _str_field(report, "effective_principal", "(unresolved)")
    cfg_sa = _str_field(report, "configured_service_account", "(unset)")
    eff_sa = _str_field(report, "effective_service_account", "(unresolved)")
    sa_suffix = (
        " (inferred Compute Engine default SA)"
        if report["default_service_account_inferred"]
        else ""
    )
    kms_disp = _str_field(report, "kms_key", "(none)")
    stg_disp = _str_field(report, "staging_bucket", "(unset)")
    tmp_disp = _str_field(report, "temp_bucket", "(unset)")
    lines.extend([
        "",
        "## Identity & Encryption",
        f"- user_workload_authentication_type: `{auth_mode}`",
        f"- effective_principal: `{principal_disp}`",
        f"- configured_service_account: `{cfg_sa}`",
        f"- effective_service_account: `{eff_sa}`{sa_suffix}",
    ])
    for field_name in ("creator", "session_user"):
      if report.get(field_name):
        lines.append(f"- {field_name}: `{report[field_name]}`")
    lines.extend([
        f"- kms_key: `{kms_disp}`",
        f"- staging_bucket: `{stg_disp}`",
        f"- temp_bucket: `{tmp_disp}`",
    ])
    if report["service_account_scopes"]:
      lines.append(
          "- service_account_scopes:"
          f" {', '.join(f'`{s}`' for s in report['service_account_scopes'])}"
      )
    lines.append("")
    lines.append("## Direct Project IAM Roles on Effective Principal")
    if report["project_iam_roles"]:
      for role in report["project_iam_roles"]:
        lines.append(f"- `{role}`")
    else:
      lines.append("- (none found, or IAM policy unreadable)")
    lines.append(
        "- note: folder/organization inheritance, group membership, and"
        " resource-level bindings (buckets, datasets, KMS keys, service"
        " accounts) are not evaluated"
    )
    if report["auth_related_properties"]:
      lines.append("")
      lines.append("## Auth & Catalog Properties")
      for k, v in report["auth_related_properties"].items():
        lines.append(f"- `{k}`: `{v}`")
    sec = report.get("secret_inspection")
    if sec:
      roles_disp = (
          sec["principal_roles_on_secret"]
          if sec["principal_roles_on_secret"]
          else "(none)"
      )
      lines.extend([
          "",
          f"## Secret Manager (`{sec['secret_project']}/{sec['secret_id']}`)",
          f"- principal_roles_on_secret: {roles_disp}",
      ])
      for v in sec["versions"]:
        lines.append(
            f"- version `{v['version']}`: state=`{v['state']}`"
            f" (created `{v['create_time']}`)"
        )

  elif action == "network":
    wsa_disp = _str_field(report, "workload_service_account", "(unknown)")
    wsa_suffix = (
        " (inferred Compute Engine default SA)"
        if report.get("workload_service_account_inferred")
        else ""
    )
    lines.extend([
        "",
        "## Network Topology",
        f"- effective_host_project: `{report['effective_host_project']}`",
        f"- effective_network: `{report['effective_network']}`",
        f"- effective_subnetwork: `{report['effective_subnetwork']}`",
        f"- internal_ip_only: `{report['internal_ip_only']}`",
        f"- network_tags: {report['network_tags']}",
        f"- workload_service_account: `{wsa_disp}`{wsa_suffix}",
    ])
    sub = report.get("subnet")
    if sub:
      lines.extend([
          "",
          "## Subnetwork Details",
          f"- ip_cidr_range: `{sub['ip_cidr_range']}`",
          (
              f"- usable_hosts_estimate: `{sub['usable_hosts_estimate']}`"
              " (total capacity, not free IPs)"
          ),
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
    lines.append("## VPC Peerings")
    if report.get("vpc_peerings"):
      for peer in report["vpc_peerings"]:
        lines.append(
            f"- `{peer['name']}` -> `{peer['peer_project']}/"
            f"{peer['peer_network']}` state=`{peer['state']}`"
        )
    else:
      lines.append("- (no VPC peerings on workload network)")
    port_label = f"matches_port_{report['target_port']}"
    lines.append("")
    lines.append("## Applicable VPC Firewall Rules")
    if report["firewall_rules"]:
      for fw in report["firewall_rules"]:
        port_val = fw["matches_target_port"]
        port_note = (
            f" {port_label}=`{port_val}`" if port_val is not None else ""
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
            f" applies_to_workload=`{fw['applies_to_workload']}`"
            f" rules=`{json.dumps(fw['rules'])}`{port_note}"
        )
    else:
      lines.append("- (no matching VPC firewall rules returned)")
    lines.append("")
    lines.append("## Firewall Policies")
    if report.get("firewall_policy_enforcement_order"):
      lines.append(
          "- network_firewall_policy_enforcement_order:"
          f" `{report['firewall_policy_enforcement_order']}`"
      )
    if report.get("firewall_policies"):
      for policy in report["firewall_policies"]:
        lines.append(f"- policy `{policy['name']}` ({policy['type']}):")
        for rule in policy["rules"]:
          port_val = rule["matches_target_port"]
          port_note = (
              f" {port_label}=`{port_val}`" if port_val is not None else ""
          )
          range_label = "src" if rule["direction"] == "INGRESS" else "dest"
          ranges_val = (
              rule["source_ranges"]
              if rule["direction"] == "INGRESS"
              else rule["destination_ranges"]
          )
          lines.append(
              f"  - priority=`{rule['priority']}` {rule['direction']}"
              f" {rule['action']} {range_label}={ranges_val}"
              f" l4=`{json.dumps(rule['layer4_configs'])}`"
              f" applies_to_workload=`{rule['applies_to_workload']}`"
              f"{port_note}"
          )
    else:
      lines.append(
          "- (no hierarchical, network, or system firewall policies returned)"
      )
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

  else:
    subtype_disp = _str_field(report, "workload_subtype", "unknown")
    img_disp = _str_field(report, "container_image", "(default image)")
    lines.extend([
        "",
        "## Runtime & Entrypoint",
        f"- workload_subtype: `{subtype_disp}`",
        f"- runtime_spark_version: `{report['runtime_spark_version']}`",
        (
            "- runtime_scala_binary_version:"
            f" `{report['runtime_scala_binary_version']}`"
        ),
        f"- optional_components: {report['optional_components']}",
        f"- container_image: `{img_disp}`",
    ])
    for field_name in (
        "main_python_file_uri",
        "notebook_file_uri",
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
        scala_disp = _str_field(j, "scala_binary_version", "unversioned")
        spark_disp = _str_field(j, "spark_minor_version", "n/a")
        lines.append(
            f"- `{j['artifact']}` (scala_binary=`{scala_disp}`"
            f" scala_matches_runtime=`{j.get('scala_matches_runtime')}`"
            f" spark_minor=`{spark_disp}`"
            f" spark_matches_runtime=`{j.get('spark_matches_runtime')}`)"
        )
    else:
      lines.append("- (no custom JARs or spark.jars.packages attached)")
    lines.append("")
    lines.append("## Distributed Files, PyFiles & Archives")
    lines.append(f"- file_uris: {report['file_uris']}")
    lines.append(f"- python_file_uris: {report['python_file_uris']}")
    lines.append(f"- archive_uris: {report['archive_uris']}")
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
          "Inspects Google Cloud identity/KMS/secrets, VPC topology (PGA,"
          " Cloud NAT, peering, DNS, firewall rules and policies), or"
          " Spark/Scala classpath metadata for a Dataproc Serverless batch,"
          " interactive session, or cluster job. Read-only."
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

  try:
    project = args.project or resolve_default_project(runner)
  except InspectorError as exc:
    print(f"Error: {exc}", file=sys.stderr)
    return 1
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
