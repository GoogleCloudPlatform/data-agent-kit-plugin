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
    and system firewall policy rules, Cloud DNS private zone bindings, and,
    with `--target_port`, a first-match firewall verdict for one connection
    that reports `INDETERMINATE` when a rule cannot be evaluated.
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
import itertools
import json
import math
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

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
# First-match firewall verdict for one connection (`--target_port`).
_VERDICT_ALLOWED = "ALLOWED"
_VERDICT_DENIED = "DENIED"
_VERDICT_INDETERMINATE = "INDETERMINATE"
# Terminal outcome of a matching rule whose effect the inspector cannot
# evaluate, such as `apply_security_profile_group` (L7 inspection decides).
_OUTCOME_UNEVALUATED = "UNEVALUATED"
# Per-rule match states for the connection.
_MATCH = "match"
_NO_MATCH = "no_match"
_UNKNOWN = "unknown"
_IMPLIED_RULE_PRIORITY = 65535
# Upper bound on the policy orders evaluated when the API does not report the
# order (several hierarchical or system policies, unknown enforcement order).
_MAX_FIREWALL_ORDERINGS = 720
_MAX_UNEVALUATED_RULES_SHOWN = 10
_PROTOCOL_NUMBERS = {"tcp": "6", "udp": "17"}
_HIERARCHY_POLICY_TYPES = ("HIERARCHY",)
_SYSTEM_POLICY_TYPES = ("SYSTEM", "SYSTEM_GLOBAL", "SYSTEM_REGIONAL")
_GLOBAL_NETWORK_POLICY_TYPES = ("NETWORK",)
_REGIONAL_NETWORK_POLICY_TYPES = ("NETWORK_REGIONAL",)
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
    specs: List[Dict[str, Any]], target_port: int, protocol: str = "tcp"
) -> bool:
  """Checks whether firewall rule protocol/port specs cover a port.

  Accepts VPC firewall rule specs (`IPProtocol`/`ports`) and firewall policy
  `layer4Configs` entries (`ipProtocol`/`ports`).

  Args:
    specs: Protocol and port specs of one rule.
    target_port: Port to match.
    protocol: Protocol of the connection (`tcp` or `udp`).

  Returns:
    Whether any spec covers `protocol` traffic to `target_port`.
  """
  wanted = {"all", protocol, _PROTOCOL_NUMBERS.get(protocol, protocol)}
  for spec in specs:
    proto = _str_field(
        spec, "IPProtocol", _str_field(spec, "ipProtocol")
    ).lower()
    if proto not in wanted:
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
) -> Tuple[List[Dict[str, Any]], str, bool]:
  """Returns (peerings, policy enforcement order, readable) of a network."""
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
  readable = isinstance(raw_net, dict) and bool(raw_net)
  return peerings, enforcement_order, readable


def _inspect_firewall_policies(
    network_name: str,
    host_project: str,
    region: str,
    runner: CommandRunner,
    warnings: List[str],
    network_tags: List[Any],
    workload_sa: str,
    target_port: Optional[int],
    target_protocol: str = "tcp",
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
  """Summarizes effective hierarchical, network, and system policy rules.

  Args:
    network_name: VPC network of the workload.
    host_project: Project that owns the network.
    region: Region of the workload subnet.
    runner: gcloud command runner.
    warnings: Partial-visibility warnings to append to.
    network_tags: Network tags on the workload VMs.
    workload_sa: Service account of the workload VMs ("" when unknown).
    target_port: Optional port to mark matching rules for.
    target_protocol: Protocol for `target_port`.

  Returns:
    (policy summaries, raw effective policies or None when unreadable).
  """
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
  raw_policies = (
      None
      if raw is None
      else [
          p for p in _list_field(raw, "firewallPolicys") if isinstance(p, dict)
      ]
  )
  policies: List[Dict[str, Any]] = []
  total_rules = 0
  truncated = False
  for policy in raw_policies or []:
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
              _port_matches_specs(layer4, target_port, target_protocol)
              if target_port is not None
              else None
          ),
      })
      total_rules += 1
    policies.append({
        "name": _policy_display_name(policy),
        "type": _str_field(policy, "type"),
        "rules": rules,
    })
  if truncated:
    warnings.append(
        f"firewall policies: only the first {_MAX_POLICY_RULES} rules are"
        " listed"
    )
  return policies, raw_policies


def _rule_priority(rule: Dict[str, Any], default: int) -> int:
  try:
    return int(rule.get("priority", default))
  except (TypeError, ValueError):
    return default


def _policy_display_name(policy: Dict[str, Any]) -> str:
  return (
      _str_field(policy, "displayName")
      or _str_field(policy, "shortName")
      or _str_field(policy, "name")
  )


def _parse_ip_networks(ranges: List[Any]) -> Tuple[List[Any], bool]:
  """Parses IP ranges into networks and reports unparseable entries."""
  nets: List[Any] = []
  unparseable = False
  for item in ranges:
    try:
      nets.append(ipaddress.ip_network(str(item).strip(), strict=False))
    except ValueError:
      unparseable = True
  return nets, unparseable


def _remote_ranges_state(
    ranges: List[Any], remote_ip: Optional[Any], ip_version: Optional[int]
) -> str:
  """Matches the remote end of the connection against a rule's IP ranges.

  Args:
    ranges: IP ranges for the remote end (destination for egress, source for
      ingress).
    remote_ip: Remote address, or None when `--target_ip` is not given.
    ip_version: IP version of the connection, or None when unknown.

  Returns:
    _MATCH, _NO_MATCH, or _UNKNOWN.
  """
  nets, unparseable = _parse_ip_networks(ranges)
  if remote_ip is not None:
    if any(n.version == remote_ip.version and remote_ip in n for n in nets):
      return _MATCH
    return _UNKNOWN if unparseable else _NO_MATCH
  if ip_version is None:
    if {n.version for n in nets if n.prefixlen == 0} == {4, 6}:
      return _MATCH
    return _UNKNOWN if nets or unparseable else _NO_MATCH
  same_version = [n for n in nets if n.version == ip_version]
  if any(n.prefixlen == 0 for n in same_version):
    return _MATCH
  return _UNKNOWN if same_version or unparseable else _NO_MATCH


def _local_ranges_state(ranges: List[Any], local_nets: List[Any]) -> str:
  """Matches the workload end of the connection against a rule's IP ranges.

  The workload end can be any address of the workload subnet, so the rule
  matches only if its ranges cover the subnet and misses only if they do not
  overlap it.

  Args:
    ranges: IP ranges for the workload end (source for egress, destination for
      ingress).
    local_nets: Workload subnet ranges of the connection's IP version.

  Returns:
    _MATCH, _NO_MATCH, or _UNKNOWN.
  """
  if not local_nets:
    return _UNKNOWN
  nets, unparseable = _parse_ip_networks(ranges)
  if all(
      any(ln.version == n.version and ln.subnet_of(n) for n in nets)
      for ln in local_nets
  ):
    return _MATCH
  overlaps = any(
      ln.version == n.version and ln.overlaps(n)
      for ln in local_nets
      for n in nets
  )
  return _UNKNOWN if overlaps or unparseable else _NO_MATCH


def _combine_states(states: List[str]) -> str:
  if _NO_MATCH in states:
    return _NO_MATCH
  if _UNKNOWN in states:
    return _UNKNOWN
  return _MATCH


def _new_rule_record(name: str, priority: int, action: str) -> Dict[str, Any]:
  return {
      "rule": name,
      "priority": priority,
      "action": action,
      "state": _NO_MATCH,
      "remote_ranges": [],
      "reasons": [],
  }


def _finish_rule_record(
    record: Dict[str, Any], states: List[str], reasons: List[str]
) -> Dict[str, Any]:
  record["state"] = _combine_states(states)
  record["reasons"] = reasons if record["state"] == _UNKNOWN else []
  return record


def _remote_range_reason(conn: Dict[str, Any]) -> str:
  end = "destination" if conn["direction"] == "EGRESS" else "source"
  if conn["remote_ip"] is None:
    return f"matches only some {end} addresses; pass --target_ip to evaluate it"
  return f"has {end} ranges that could not be parsed"


def _local_range_reason(conn: Dict[str, Any]) -> str:
  if not conn["local_nets"]:
    return "limits workload addresses, and the workload subnet range is unknown"
  return "limits workload addresses to ranges that partly cover the subnet"


def _evaluate_vpc_rule(
    fw: Dict[str, Any], conn: Dict[str, Any]
) -> Dict[str, Any]:
  """Matches one VPC firewall rule against the connection."""
  denied = _list_field(fw, "denied")
  specs = denied or _list_field(fw, "allowed")
  record = _new_rule_record(
      _str_field(fw, "name"),
      _rule_priority(fw, 1000),
      "deny" if denied else "allow",
  )
  direction = _str_field(fw, "direction", "INGRESS").upper()
  if direction != conn["direction"] or not _port_matches_specs(
      specs, conn["port"], conn["protocol"]
  ):
    return record
  states: List[str] = []
  reasons: List[str] = []
  applies = _target_applies(
      _list_field(fw, "targetTags"),
      _list_field(fw, "targetServiceAccounts"),
      conn["network_tags"],
      conn["workload_sa"],
  )
  if applies is None:
    states.append(_UNKNOWN)
    reasons.append(
        "targets service accounts, and the workload service account is unknown"
    )
  elif not applies:
    return record
  if direction == "EGRESS":
    # Egress rules without destination ranges apply to 0.0.0.0/0.
    remote = _list_field(fw, "destinationRanges") or ["0.0.0.0/0"]
    remote_other: List[str] = []
    local = _list_field(fw, "sourceRanges")
  else:
    remote = _list_field(fw, "sourceRanges")
    remote_other = [
        label
        for label, key in (
            ("source tags", "sourceTags"),
            ("source service accounts", "sourceServiceAccounts"),
        )
        if _list_field(fw, key)
    ]
    # Ingress rules without any source apply to 0.0.0.0/0.
    if not remote and not remote_other:
      remote = ["0.0.0.0/0"]
    local = _list_field(fw, "destinationRanges")
  record["remote_ranges"] = _summarize_ranges(remote)
  remote_state = (
      _remote_ranges_state(remote, conn["remote_ip"], conn["ip_version"])
      if remote
      else _NO_MATCH
  )
  if remote_state == _UNKNOWN:
    reasons.append(_remote_range_reason(conn))
  if remote_state != _MATCH and remote_other:
    # A VPC rule matches a source range OR a source tag or service account.
    remote_state = _UNKNOWN
    reasons.append(
        f"matches {' and '.join(remote_other)}, which are not resolved"
    )
  states.append(remote_state)
  if local:
    local_state = _local_ranges_state(local, conn["local_nets"])
    if local_state == _UNKNOWN:
      reasons.append(_local_range_reason(conn))
    states.append(local_state)
  return _finish_rule_record(record, states, reasons)


def _policy_target_state(
    rule: Dict[str, Any], conn: Dict[str, Any], reasons: List[str]
) -> str:
  """Returns whether a firewall policy rule targets the workload VMs."""
  states: List[str] = []
  resources = _list_field(rule, "targetResources")
  if resources:
    in_scope = any(
        _parse_network_uri(str(r), conn["network"][0]) == conn["network"]
        for r in resources
    )
    states.append(_MATCH if in_scope else _NO_MATCH)
  target_sas = _list_field(rule, "targetServiceAccounts")
  if target_sas:
    if not conn["workload_sa"]:
      states.append(_UNKNOWN)
      reasons.append(
          "targets service accounts, and the workload service account is"
          " unknown"
      )
    else:
      states.append(_MATCH if conn["workload_sa"] in target_sas else _NO_MATCH)
  if _list_field(rule, "targetSecureTags"):
    states.append(_UNKNOWN)
    reasons.append("targets secure tags, which are not resolved")
  return _combine_states(states)


def _evaluate_policy_rule(
    rule: Dict[str, Any], conn: Dict[str, Any]
) -> Dict[str, Any]:
  """Matches one firewall policy rule against the connection."""
  record = _new_rule_record(
      _str_field(rule, "ruleName"),
      _rule_priority(rule, 0),
      _str_field(rule, "action").lower(),
  )
  direction = _str_field(rule, "direction", "INGRESS").upper()
  match = _dict_field(rule, "match")
  layer4 = _list_field(match, "layer4Configs")
  if (
      rule.get("disabled")
      or direction != conn["direction"]
      or (
          layer4
          and not _port_matches_specs(layer4, conn["port"], conn["protocol"])
      )
  ):
    return record
  reasons: List[str] = []
  states = [_policy_target_state(rule, conn, reasons)]
  remote_key, local_key = (
      ("destIpRanges", "srcIpRanges")
      if direction == "EGRESS"
      else ("srcIpRanges", "destIpRanges")
  )
  remote_ranges = _list_field(match, remote_key)
  record["remote_ranges"] = _summarize_ranges(remote_ranges)
  # Selectors other than IP ranges (secure tags, address groups, FQDNs,
  # geolocations, threat intelligence lists, network context) are not
  # resolved, so a rule that uses one is indeterminate.
  selectors = sorted(
      key
      for key, value in match.items()
      if value and key not in ("layer4Configs", "srcIpRanges", "destIpRanges")
  )
  if selectors:
    states.append(_UNKNOWN)
    reasons.append(f"uses {', '.join(selectors)}, which are not resolved")
  else:
    if remote_ranges:
      remote_state = _remote_ranges_state(
          remote_ranges, conn["remote_ip"], conn["ip_version"]
      )
      if remote_state == _UNKNOWN:
        reasons.append(_remote_range_reason(conn))
      states.append(remote_state)
    local_ranges = _list_field(match, local_key)
    if local_ranges:
      local_state = _local_ranges_state(local_ranges, conn["local_nets"])
      if local_state == _UNKNOWN:
        reasons.append(_local_range_reason(conn))
      states.append(local_state)
  return _finish_rule_record(record, states, reasons)


def _implied_rule_record(direction: str) -> Dict[str, Any]:
  egress = direction == "EGRESS"
  record = _new_rule_record(
      "implied allow egress" if egress else "implied deny ingress",
      _IMPLIED_RULE_PRIORITY,
      "allow" if egress else "deny",
  )
  record["state"] = _MATCH
  return record


def _verdict_stage(
    name: str, records: Optional[List[Dict[str, Any]]]
) -> Dict[str, Any]:
  """Builds an evaluation stage; `records=None` marks it unreadable."""
  return {"name": name, "readable": records is not None, "records": records}


def _firewall_orderings(
    hierarchy: List[Dict[str, Any]],
    system: List[Dict[str, Any]],
    vpc_stage: Dict[str, Any],
    network: List[Dict[str, Any]],
    implied: Dict[str, Any],
    enforcement_order: str,
    enforcement_order_known: bool,
) -> Optional[List[List[Dict[str, Any]]]]:
  """Lists every stage order consistent with what the API reports.

  The API does not report the relative order of several hierarchical (or
  system) policies, and the enforcement order is unknown when the network
  cannot be read, so every consistent order is evaluated.

  Args:
    hierarchy: Hierarchical policy stages.
    system: System policy stages.
    vpc_stage: VPC firewall rules stage.
    network: Global, then regional, network policy stages.
    implied: Implied rules stage.
    enforcement_order: The network's firewall policy enforcement order.
    enforcement_order_known: Whether the network could be read.

  Returns:
    The candidate orders, or None when there are too many to evaluate.
  """
  after = [vpc_stage, *network]
  before = [*network, vpc_stage]
  if not enforcement_order_known:
    tails = [after, before] if network else [after]
  elif enforcement_order == "BEFORE_CLASSIC_FIREWALL":
    tails = [before]
  else:
    tails = [after]
  count = (
      math.factorial(len(hierarchy)) * math.factorial(len(system)) * len(tails)
  )
  if count > _MAX_FIREWALL_ORDERINGS:
    return None
  return [
      [*h, *s, *t, implied]
      for h in itertools.permutations(hierarchy)
      for s in itertools.permutations(system)
      for t in tails
  ]


def _ordering_outcomes(
    stages: List[Dict[str, Any]],
) -> Set[Tuple[str, Tuple[Any, ...]]]:
  """Returns every (outcome, deciding rule) that one stage order can produce.

  Walks the stages backward: a matching rule decides (or, for `goto_next`,
  passes to the next stage), and an indeterminate rule contributes the
  outcomes of both matching and not matching.

  Args:
    stages: Stages in evaluation order, ending with the implied rules.

  Returns:
    Pairs of outcome and deciding rule key.
  """
  entry: Set[Tuple[str, Tuple[Any, ...]]] = set()
  for stage in reversed(stages):
    passed = entry
    if not stage["readable"]:
      key = (stage["name"], None, "", "")
      entry = {(_VERDICT_ALLOWED, key), (_VERDICT_DENIED, key)} | passed
      continue
    acc = passed
    for rec in reversed(stage["records"]):
      if rec["state"] == _NO_MATCH:
        continue
      key = (stage["name"], rec["priority"], rec["rule"], rec["action"])
      if rec["action"] == "allow":
        matched = {(_VERDICT_ALLOWED, key)}
      elif rec["action"] == "deny":
        matched = {(_VERDICT_DENIED, key)}
      elif rec["action"] == "goto_next":
        matched = passed
      else:
        matched = {(_OUTCOME_UNEVALUATED, key)}
      acc = matched if rec["state"] == _MATCH else matched | acc
    entry = acc
  return entry


def _firewall_connection(
    direction: str,
    protocol: str,
    port: int,
    target_ip: Optional[str],
    subnet: Optional[Dict[str, Any]],
    network: Tuple[str, str],
    network_tags: List[Any],
    workload_sa: str,
) -> Dict[str, Any]:
  """Describes the connection that the firewall verdict evaluates."""
  remote_ip = ipaddress.ip_address(target_ip) if target_ip else None
  stack = _str_field(subnet, "stack_type").upper()
  if remote_ip is not None:
    ip_version = remote_ip.version
  elif not subnet or stack not in ("", "IPV4_ONLY", "IPV6_ONLY"):
    ip_version = None
  else:
    ip_version = 6 if stack == "IPV6_ONLY" else 4
  local_nets: List[Any] = []
  if ip_version is not None and _str_field(subnet, "ip_cidr_range"):
    nets, _ = _parse_ip_networks([_str_field(subnet, "ip_cidr_range")])
    local_nets = [n for n in nets if n.version == ip_version]
  return {
      "direction": direction,
      "protocol": protocol,
      "port": port,
      "remote_ip": remote_ip,
      "ip_version": ip_version,
      "subnet_stack_type": stack if subnet else None,
      "local_nets": local_nets,
      "network": network,
      "network_tags": network_tags,
      "workload_sa": workload_sa,
  }


def _verdict_rule_view(rec: Dict[str, Any]) -> Dict[str, Any]:
  return {
      "rule": rec["rule"],
      "priority": rec["priority"],
      "action": rec["action"],
      "match": "match" if rec["state"] == _MATCH else "indeterminate",
      "remote_ranges": rec["remote_ranges"],
      "reasons": rec["reasons"],
  }


def _firewall_verdict(
    conn: Dict[str, Any],
    policies: Optional[List[Dict[str, Any]]],
    vpc_rules: Optional[List[Dict[str, Any]]],
    enforcement_order: str,
    enforcement_order_known: bool,
) -> Dict[str, Any]:
  """Evaluates one connection through the Cloud NGFW first-match order.

  Args:
    conn: The connection (see `_firewall_connection`).
    policies: Raw effective firewall policies, or None when unreadable.
    vpc_rules: Enabled VPC firewall rules of the network, or None when
      unreadable.
    enforcement_order: The network's firewall policy enforcement order.
    enforcement_order_known: Whether the network could be read.

  Returns:
    The verdict, the deciding rule, the first match of each policy, the rules
    that could not be evaluated, and notes on assumptions.
  """
  notes: List[str] = []
  hierarchy: List[Dict[str, Any]] = []
  system: List[Dict[str, Any]] = []
  network: List[Dict[str, Any]] = []
  regional: List[Dict[str, Any]] = []
  unplaced: List[Dict[str, Any]] = []
  if policies is None:
    hierarchy.append(_verdict_stage("firewall policies", None))
  for policy in policies or []:
    records = sorted(
        (
            _evaluate_policy_rule(r, conn)
            for r in _list_field(policy, "rules")
            if isinstance(r, dict)
        ),
        key=lambda r: r["priority"],
    )
    name = _policy_display_name(policy)
    policy_type = _str_field(policy, "type").upper()
    if policy_type in _HIERARCHY_POLICY_TYPES:
      hierarchy.append(_verdict_stage(f"hierarchical policy `{name}`", records))
    elif policy_type in _SYSTEM_POLICY_TYPES:
      system.append(_verdict_stage(f"system policy `{name}`", records))
    elif policy_type in _GLOBAL_NETWORK_POLICY_TYPES:
      network.append(_verdict_stage(f"global network policy `{name}`", records))
    elif policy_type in _REGIONAL_NETWORK_POLICY_TYPES:
      regional.append(
          _verdict_stage(f"regional network policy `{name}`", records)
      )
    else:
      unplaced.append(
          _verdict_stage(
              f"policy `{name}` ({policy_type or 'no type'})", records
          )
      )
  vpc_records = None
  if vpc_rules is not None:
    # Lower priority numbers win; at equal priority a deny beats an allow.
    vpc_records = sorted(
        (_evaluate_vpc_rule(fw, conn) for fw in vpc_rules),
        key=lambda r: (r["priority"], r["action"] != "deny", r["rule"]),
    )
  vpc_stage = _verdict_stage("VPC firewall rules", vpc_records)
  implied = _verdict_stage(
      "implied rules", [_implied_rule_record(conn["direction"])]
  )
  network.extend(regional)
  orderings = _firewall_orderings(
      hierarchy,
      system,
      vpc_stage,
      network,
      implied,
      enforcement_order,
      enforcement_order_known,
  )

  if policies is not None and len(hierarchy) > 1:
    notes.append(
        f"The API does not report the order of the {len(hierarchy)}"
        " hierarchical policies, so every order was evaluated."
    )
  if len(system) > 1:
    notes.append(
        f"The API does not report the order of the {len(system)} system"
        " policies, so every order was evaluated."
    )
  if not enforcement_order_known and network:
    notes.append(
        "The network could not be read, so both network firewall policy"
        " enforcement orders were evaluated."
    )
  if conn["ip_version"] is None:
    notes.append(
        "The connection's IP version is unknown (dual-stack or unreadable"
        " subnet); pass --target_ip."
    )
  elif conn["remote_ip"] is not None and conn["subnet_stack_type"] in (
      "",
      "IPV4_ONLY",
      "IPV6_ONLY",
  ):
    subnet_version = 6 if conn["subnet_stack_type"] == "IPV6_ONLY" else 4
    if subnet_version != conn["ip_version"]:
      notes.append(
          f"The workload subnet is IPv{subnet_version}-only, so the workload"
          f" cannot use IPv{conn['ip_version']}."
      )

  outcomes: Set[Tuple[str, Tuple[Any, ...]]] = set()
  per_ordering: List[Set[str]] = []
  if orderings is None:
    outcomes.add((_OUTCOME_UNEVALUATED, ("policy order", None, "", "")))
    notes.append("Too many unordered policies to evaluate every order.")
  else:
    for ordering in orderings:
      result = _ordering_outcomes(ordering)
      per_ordering.append({outcome for outcome, _ in result})
      outcomes |= result
  for stage in unplaced:
    if any(r["state"] != _NO_MATCH for r in stage["records"]):
      outcomes.add((_OUTCOME_UNEVALUATED, (stage["name"], None, "", "")))
      notes.append(
          f"{stage['name']} has an unrecognized type, so its place in the"
          " evaluation order is unknown."
      )
  kinds = {outcome for outcome, _ in outcomes}
  if kinds == {_VERDICT_ALLOWED}:
    verdict = _VERDICT_ALLOWED
  elif kinds == {_VERDICT_DENIED}:
    verdict = _VERDICT_DENIED
  else:
    verdict = _VERDICT_INDETERMINATE
  if (
      verdict == _VERDICT_INDETERMINATE
      and all(len(kinds_of) == 1 for kinds_of in per_ordering)
      and len(set().union(*per_ordering)) > 1
  ):
    notes.append(
        "Each policy order gives a definite result, but the results differ."
    )
  decided_by = None
  deciders = {key for _, key in outcomes}
  if verdict != _VERDICT_INDETERMINATE and len(deciders) == 1:
    stage_name, priority, rule_name, action = next(iter(deciders))
    decided_by = {
        "stage": stage_name,
        "priority": priority,
        "rule": rule_name,
        "action": action,
    }

  listed = (
      orderings[0]
      if orderings
      else [*hierarchy, *system, vpc_stage, *network, implied]
  )
  stages: List[Dict[str, Any]] = []
  unevaluated: List[Dict[str, Any]] = []
  for stage in [*listed, *unplaced]:
    if not stage["readable"]:
      stages.append(
          {"stage": stage["name"], "readable": False, "first_match": None}
      )
      continue
    first = next((r for r in stage["records"] if r["state"] != _NO_MATCH), None)
    stages.append({
        "stage": stage["name"],
        "readable": True,
        "first_match": None if first is None else _verdict_rule_view(first),
    })
    for rec in stage["records"]:
      if rec["state"] == _MATCH:
        break
      if rec["state"] == _UNKNOWN:
        unevaluated.append({"stage": stage["name"], **_verdict_rule_view(rec)})

  return {
      "direction": conn["direction"],
      "protocol": conn["protocol"],
      "port": conn["port"],
      "remote_ip": (
          None if conn["remote_ip"] is None else str(conn["remote_ip"])
      ),
      "ip_version": conn["ip_version"],
      "verdict": verdict,
      "decided_by": decided_by,
      "possible_outcomes": sorted(kinds),
      "evaluation_order": [stage["name"] for stage in listed],
      "stages": stages,
      "unevaluated_rules": unevaluated[:_MAX_UNEVALUATED_RULES_SHOWN],
      "unevaluated_rules_omitted": max(
          0, len(unevaluated) - _MAX_UNEVALUATED_RULES_SHOWN
      ),
      "notes": notes,
  }


def inspect_network(
    project: str,
    region: str,
    workload_kind: str,
    workload_id: str,
    runner: CommandRunner,
    target_port: Optional[int] = None,
    target_protocol: str = "tcp",
    target_ip: Optional[str] = None,
    target_direction: str = "egress",
) -> Dict[str, Any]:
  """Collects subnet, NAT, peering, firewall, and private DNS facts.

  Args:
    project: Workload project.
    region: Workload region.
    workload_kind: `batch`, `session`, or `job`.
    workload_id: Workload ID.
    runner: gcloud command runner.
    target_port: Optional port of one connection to mark matching rules for and
      to compute a first-match firewall verdict for.
    target_protocol: `tcp` or `udp`.
    target_ip: Optional remote address of the connection (destination for
      egress, source for ingress).
    target_direction: `egress` (from the workload) or `ingress` (to it).

  Returns:
    The network report.
  """
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
  enforcement_order_known = False
  firewall_rules: List[Dict[str, Any]] = []
  firewall_policies: List[Dict[str, Any]] = []
  # Unfiltered inputs of the firewall verdict (None while unreadable).
  network_vpc_rules: Optional[List[Dict[str, Any]]] = None
  raw_policies: Optional[List[Dict[str, Any]]] = None
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

    vpc_peerings, enforcement_order, enforcement_order_known = (
        _inspect_vpc_network(network_name, host_project, runner, warnings)
    )

    raw_fws = _run_gcloud_json(
        runner,
        ["compute", "firewall-rules", "list", f"--project={host_project}"],
        warnings,
        f"compute firewall-rules list '{host_project}'",
    )
    if isinstance(raw_fws, list):
      network_vpc_rules = []
      matched_fws: List[Dict[str, Any]] = []
      for fw in raw_fws:
        if not isinstance(fw, dict) or fw.get("disabled"):
          continue
        _, fw_net = _parse_network_uri(
            _str_field(fw, "network"), host_project
        )
        if fw_net != network_name:
          continue
        network_vpc_rules.append(fw)
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
            _port_matches_specs(specs, target_port, target_protocol)
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

    firewall_policies, raw_policies = _inspect_firewall_policies(
        network_name,
        host_project,
        subnet_region,
        runner,
        warnings,
        network_tags,
        workload_sa,
        target_port,
        target_protocol,
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

  firewall_verdict: Optional[Dict[str, Any]] = None
  if target_port is not None:
    firewall_verdict = _firewall_verdict(
        _firewall_connection(
            target_direction.upper(),
            target_protocol,
            target_port,
            target_ip,
            subnet_details,
            (host_project, network_name),
            network_tags,
            workload_sa,
        ),
        raw_policies,
        network_vpc_rules,
        enforcement_order,
        enforcement_order_known,
    )
    if not can_inspect_vpc:
      firewall_verdict["notes"].append(
          "The cluster could not be read, so its network is unknown."
      )

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
      "firewall_verdict": firewall_verdict,
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


def _format_verdict_rule(rule: Dict[str, Any]) -> str:
  name = f" `{rule['rule']}`" if rule.get("rule") else ""
  return f"priority=`{rule['priority']}` `{rule['action']}`{name}"


def _format_firewall_verdict(verdict: Dict[str, Any]) -> List[str]:
  """Formats the first-match firewall verdict as Markdown lines."""
  remote = verdict["remote_ip"] or {
      4: "any IPv4 address",
      6: "any IPv6 address",
  }.get(verdict["ip_version"], "any address")
  egress = verdict["direction"] == "EGRESS"
  lines = [
      f"## Firewall Verdict (`{verdict['direction']}"
      f" {verdict['protocol']}:{verdict['port']}`"
      f" {'to' if egress else 'from'} `{remote}`)"
  ]
  summary = f"- verdict: `{verdict['verdict']}`"
  if verdict.get("decided_by"):
    decided = verdict["decided_by"]
    summary += (
        f", decided by {decided['stage']} {_format_verdict_rule(decided)}"
    )
  elif verdict["verdict"] == _VERDICT_INDETERMINATE:
    summary += (
        f" (possible outcomes: {', '.join(verdict['possible_outcomes'])})"
    )
  lines.append(summary)
  lines.append(
      "- evaluation order: " + " -> ".join(verdict["evaluation_order"])
  )
  for stage in verdict["stages"]:
    first = stage["first_match"]
    if not stage["readable"]:
      detail = "not readable (see warnings)"
    elif first is None:
      detail = "no matching rule"
    else:
      ranges = (
          f" {'dest' if egress else 'src'}={first['remote_ranges']}"
          if first["remote_ranges"]
          else ""
      )
      detail = f"first match {_format_verdict_rule(first)}{ranges}"
      if first["match"] != "match":
        detail += " (indeterminate)"
    lines.append(f"- {stage['stage']}: {detail}")
  if verdict["unevaluated_rules"]:
    lines.append("- unevaluated rules (check by hand):")
    for rule in verdict["unevaluated_rules"]:
      lines.append(
          f"  - {rule['stage']} {_format_verdict_rule(rule)}:"
          f" {'; '.join(rule['reasons'])}"
      )
    if verdict.get("unevaluated_rules_omitted"):
      lines.append(f"  - ... (+{verdict['unevaluated_rules_omitted']} more)")
  for note in verdict["notes"]:
    lines.append(f"- note: {note}")
  return lines


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
    if report.get("target_port") is None and (
        report.get("firewall_rules") or report.get("firewall_policies")
    ):
      lines.append(
          "- note: The first matching rule in evaluation order decides, and"
          " `goto_next` hands off to the next level, so a lower-priority"
          " `deny` may never apply. Re-run with `--target_port=<PORT>` (and"
          " `--target_ip=<IP>`) for a first-match verdict."
      )
    if report.get("firewall_verdict"):
      lines.append("")
      lines.extend(_format_firewall_verdict(report["firewall_verdict"]))
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
          " interactive session, or cluster job. Read-only. For a failed"
          " connection, add --target_port (and --target_ip) to"
          " --action=network for a first-match firewall verdict."
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
          "Port of a failed connection (e.g. 5432, 3306, 443) for"
          " --action=network. Pass it for connection timeouts or refusals:"
          " it marks matching VPC firewall and firewall policy rules and"
          " computes a first-match firewall verdict that accounts for rule"
          " order and goto_next"
      ),
  )
  parser.add_argument(
      "--target_protocol",
      choices=["tcp", "udp"],
      default="tcp",
      help="Protocol for --target_port (default: %(default)s)",
  )
  parser.add_argument(
      "--target_ip",
      help=(
          "Optional remote IP address for the firewall verdict: the"
          " destination for egress, the source for ingress. Without it,"
          " rules that match only some remote addresses are indeterminate"
      ),
  )
  parser.add_argument(
      "--target_direction",
      choices=["egress", "ingress"],
      default="egress",
      help=(
          "Connection direction for the firewall verdict, relative to the"
          " workload VMs (default: %(default)s)"
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
  if args.target_ip is not None:
    if args.target_port is None:
      parser.error("--target_ip requires --target_port")
    try:
      ipaddress.ip_address(args.target_ip)
    except ValueError:
      parser.error("--target_ip must be an IPv4 or IPv6 address")

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
          target_protocol=args.target_protocol,
          target_ip=args.target_ip,
          target_direction=args.target_direction,
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
