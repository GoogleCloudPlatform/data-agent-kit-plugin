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

"""BigQuery and Spark (Dataproc) job monitoring, cost analysis, and inspection.

Supports the core Data Cloud Admin & Practitioner job-monitoring CUJs:
  1. List recent BigQuery jobs (`bq_list`)
  2. Find top most expensive BigQuery jobs (`bq_top_cost`)
  3. Find slowest / longest-running BigQuery jobs (`bq_slowest`)
  4. Inspect details of a specific BigQuery job (`bq_describe`)
  5. List recent Spark jobs across Serverless Batches, Sessions, and Cluster
     Jobs (`spark_list`)
  6. Find slowest / longest-running Spark jobs (`spark_slowest`)
  7. Inspect details of a specific Spark batch or cluster job (`spark_describe`)

Why this script uses the BigQuery `jobs.list` (`projection=full`) & `jobs.get`
and Dataproc REST APIs directly:
  * Querying `INFORMATION_SCHEMA.JOBS_BY_PROJECT` requires
    `bigquery.jobs.listAll` and `JOBS_BY_USER` requires `bigquery.jobs.list` at
    the project level. On projects where the user only has
    `roles/bigquery.jobUser`, both `INFORMATION_SCHEMA` views fail with 403
    Access Denied, whereas `jobs.list?projection=full` succeeds for the user's
    own jobs, costs $0 (metadata call, no query job billed), and spans all
    regions in a single request.
  * Under Context-Aware Access (CAA), `gcloud auth print-access-token` can fail
    or return a certificate-bound token rejected on standard HTTPS calls; this
    script automatically falls back to Application Default Credentials
    (`gcloud auth application-default print-access-token`).

Written against the Python standard library only.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import urllib.error
import urllib.parse
import urllib.request

BQ_ENDPOINT = "https://bigquery.googleapis.com"
BQ_RESERVATION_ENDPOINT = "https://bigqueryreservation.googleapis.com"
DATAPROC_ENDPOINT = "https://dataproc.googleapis.com"
DEFAULT_REGION = "us-central1"
ON_DEMAND_USD_PER_TIB = 6.25
TIB_BYTES = 1024**4

_HTTP_TIMEOUT_SECONDS = 60
_GCLOUD_TIMEOUT_SECONDS = 30
_USER_AGENT = "data-agent-kit/gcp-job-monitoring (script:gcp_job_monitor)"


class JobMonitorError(Exception):
  """Raised when a GCP CLI or REST API operation fails."""

  def __init__(self, message: str, status: int = 0):
    super().__init__(message)
    self.status = status


# ------------------------------------------------------------------------------
# Formatting & time helpers
# ------------------------------------------------------------------------------


def human_bytes(num: Any) -> str:
  """Formats a byte count in binary units (B, KiB, MiB, GiB, TiB)."""
  try:
    value = float(num or 0)
  except (TypeError, ValueError):
    return "0 B"
  if value <= 0:
    return "0 B"
  for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
    if value < 1024 or unit == "TiB":
      return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
    value /= 1024
  return f"{value:.2f} TiB"


def human_millis(ms: Any) -> str:
  """Formats milliseconds into human-readable ms, s, min, or hr."""
  if ms is None:
    return "n/a"
  try:
    value = float(ms)
  except (TypeError, ValueError):
    return "n/a"
  if value < 0:
    return "n/a"
  if value < 1000:
    return f"{value:.0f} ms"
  if value < 60_000:
    return f"{value / 1000:.1f} s"
  if value < 3_600_000:
    return f"{value / 60_000:.1f} min"
  return f"{value / 3_600_000:.2f} hr"


def estimate_on_demand_usd(bytes_billed: int) -> float:
  """Estimates BigQuery on-demand query cost in USD ($6.25 per TiB)."""
  if bytes_billed <= 0:
    return 0.0
  return (bytes_billed / TIB_BYTES) * ON_DEMAND_USD_PER_TIB


def format_usd(amount: float) -> str:
  """Formats a USD estimate cleanly, showing sub-cent precision when small."""
  if amount <= 0:
    return "$0.00"
  if amount < 0.01:
    return f"${amount:.6f}"
  return f"${amount:.4f}" if amount < 1.0 else f"${amount:.2f}"


def epoch_ms_to_iso(ms: Any) -> str:
  """Converts epoch milliseconds (int or string) to an ISO-8601 UTC string."""
  try:
    val = int(ms)
  except (TypeError, ValueError):
    return "n/a"
  if val <= 0:
    return "n/a"
  dt = datetime.datetime.fromtimestamp(val / 1000.0, tz=datetime.timezone.utc)
  return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def parse_rfc3339(value: Any) -> Optional[datetime.datetime]:
  """Parses an RFC-3339 timestamp string into a UTC datetime."""
  if not isinstance(value, str) or not value:
    return None
  cleaned = value.rstrip("Z")
  if "+" not in cleaned[10:] and "-" not in cleaned[10:]:
    cleaned += "+00:00"
  try:
    return datetime.datetime.fromisoformat(cleaned)
  except ValueError:
    return None


def truncate_one_line(text: Any, limit: int = 100) -> str:
  """Collapses whitespace to a single line and truncates to `limit` chars."""
  collapsed = " ".join(str(text or "").split())
  if len(collapsed) <= limit:
    return collapsed
  return collapsed[: limit - 3] + "..."


# ------------------------------------------------------------------------------
# Authentication & HTTP Client
# ------------------------------------------------------------------------------


class GcloudTokenProvider:
  """Mints OAuth access tokens via gcloud with ADC fallback for CAA."""

  _COMMANDS = (
      ("auth", "application-default", "print-access-token"),
      ("auth", "print-access-token"),
  )

  def __init__(self):
    self._index = 0
    self._token: Optional[str] = None
    self._errors: List[str] = []

  def token(self) -> str:
    while self._token is None:
      try:
        self._token = _run_gcloud(self._COMMANDS[self._index])
      except JobMonitorError as e:
        self._errors.append(str(e))
        if not self.fallback():
          raise JobMonitorError(
              "Could not obtain a Google Cloud access token. "
              + " | ".join(self._errors)
              + " Run 'gcloud auth login' and 'gcloud auth"
              " application-default login'."
          ) from e
    return self._token

  def fallback(self) -> bool:
    if self._index + 1 >= len(self._COMMANDS):
      return False
    self._index += 1
    self._token = None
    return True


def _run_gcloud(args: Sequence[str]) -> str:
  gcloud = shutil.which("gcloud")
  if not gcloud:
    raise JobMonitorError("gcloud CLI is not installed or not on PATH.")
  try:
    proc = subprocess.run(
        [gcloud, "--quiet", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=_GCLOUD_TIMEOUT_SECONDS,
        stdin=subprocess.DEVNULL,
    )
  except (OSError, subprocess.SubprocessError) as e:
    raise JobMonitorError(f"gcloud {' '.join(args)} failed: {e}") from e
  out = (proc.stdout or "").strip()
  if proc.returncode != 0 or not out:
    err_lines = (proc.stderr or "").strip().splitlines()
    detail = err_lines[-1] if err_lines else f"exit code {proc.returncode}"
    raise JobMonitorError(f"gcloud {' '.join(args)} failed: {detail}")
  return out


def resolve_default_project(explicit: Optional[str] = None) -> str:
  if explicit:
    return explicit
  for env_key in (
      "GCP_MCP_QUOTA_PROJECT",
      "GOOGLE_CLOUD_PROJECT",
      "CLOUDSDK_CORE_PROJECT",
  ):
    env_val = os.environ.get(env_key, "").strip()
    if env_val and env_val != "(unset)":
      return env_val
  try:
    val = _run_gcloud(("config", "get-value", "project"))
  except JobMonitorError:
    val = ""
  if not val or val == "(unset)":
    raise JobMonitorError(
        "No GCP project specified and gcloud default project is unset. "
        "Pass --project=<PROJECT_ID>."
    )
  return val


def resolve_default_account() -> str:
  try:
    val = _run_gcloud(("config", "get-value", "account"))
    return "" if val == "(unset)" else val
  except JobMonitorError:
    return ""


class RemoteCliMcpClient:
  """Sobi VMaaS / ACE sandbox client that routes API calls via `remote_cli mcp`.

  In the Gemini Enterprise (GE) + Sobi VMaaS sandbox architecture, Python and
  local `gcloud`/`bq` have no direct GCP credentials; authenticated egress to
  BigQuery and Dataproc goes through `/usr/local/bin/remote_cli mcp`
  (`bigquery`,
  `google-managed-apache-spark`, and optionally `google-cloud-cli`). This client
  implements the same `get_json(url, params)` interface as `RestClient` so all
  job normalization, aggregation, and rendering functions work unchanged.
  """

  def __init__(
      self,
      runner: Optional[Callable[[Sequence[str]], Tuple[int, str, str]]] = None,
      billing_project: Optional[str] = None,
  ):
    self._runner = runner or self._default_runner
    self._billing_project = (
        billing_project
        or os.environ.get("GCP_MCP_QUOTA_PROJECT", "").strip()
        or os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    )

  @staticmethod
  def is_available() -> bool:
    return bool(
        shutil.which("remote_cli")
        or os.path.exists("/usr/local/bin/remote_cli")
    )

  @staticmethod
  def _default_runner(cmd: Sequence[str]) -> Tuple[int, str, str]:
    try:
      proc = subprocess.run(
          list(cmd),
          capture_output=True,
          text=True,
          check=False,
          timeout=_HTTP_TIMEOUT_SECONDS,
          stdin=subprocess.DEVNULL,
      )
      return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (OSError, subprocess.SubprocessError) as e:
      raise JobMonitorError(f"remote_cli execution failed: {e}") from e

  def call_tool(
      self,
      server: str,
      tool: str,
      args: Dict[str, Any],
      endpoint: Optional[str] = None,
  ) -> Dict[str, Any]:
    """Invokes `remote_cli mcp <server> <tool> --json <args>` and returns JSON."""
    remote_cli = shutil.which("remote_cli") or "/usr/local/bin/remote_cli"
    filtered = {k: v for k, v in args.items() if v is not None and v != ""}
    effective_endpoint = endpoint or (
        "https://cloudcli.googleapis.com/mcp/readonly"
        if server == "google-cloud-cli"
        else None
    )
    cmd = [remote_cli, "mcp", server, tool]
    if effective_endpoint:
      cmd.extend(["--endpoint", effective_endpoint])
    cmd.extend(["--json", json.dumps(filtered)])
    rc, stdout, stderr = self._runner(cmd)
    combined = f"{stdout}\n{stderr}".strip()
    for line in combined.splitlines():
      if line.startswith("remote_cli:"):
        status = 500
        if "Unauthorized" in line or "UNAUTHENTICATED" in line:
          status = 401
        elif "PERMISSION_DENIED" in line or "Access Denied" in line:
          status = 403
        elif "NOT_FOUND" in line or "404" in line:
          status = 404
        raise JobMonitorError(line, status=status)
    if rc != 0 and not stdout.strip():
      raise JobMonitorError(
          f"remote_cli mcp {server} {tool} failed (exit {rc}): {combined}",
          status=500,
      )
    return self._unwrap_mcp_payload(stdout.strip() or "{}")

  def _unwrap_mcp_payload(self, raw_text: str) -> Dict[str, Any]:
    try:
      payload = json.loads(raw_text)
    except ValueError as e:
      raise JobMonitorError(
          "Invalid JSON from remote_cli mcp:"
          f" {truncate_one_line(raw_text, 200)}"
      ) from e
    if isinstance(payload, list):
      return {"items": payload}
    if not isinstance(payload, dict):
      return {}
    if payload.get("isError"):
      res_val = payload.get("result")
      msg = (
          self._extract_mcp_text(payload)
          or (res_val if isinstance(res_val, str) else "")
          or str(payload.get("error") or "")
          or json.dumps(payload)
      )
      status = 400
      if "403" in msg or "Access Denied" in msg or "PERMISSION_DENIED" in msg:
        status = 403
      elif "404" in msg or "Not found" in msg or "NOT_FOUND" in msg:
        status = 404
      elif "401" in msg or "Unauthorized" in msg or "UNAUTHENTICATED" in msg:
        status = 401
      raise JobMonitorError(msg, status=status)
    if isinstance(payload.get("result"), dict):
      inner_res = payload["result"]
      if isinstance(inner_res.get("structuredContent"), dict):
        return inner_res["structuredContent"]
      return inner_res
    if isinstance(payload.get("result"), list):
      return {"items": payload["result"]}
    if isinstance(payload.get("structuredContent"), dict):
      return payload["structuredContent"]
    inner_text = self._extract_mcp_text(payload)
    if inner_text:
      try:
        parsed_inner = json.loads(inner_text)
        if isinstance(parsed_inner, dict):
          return parsed_inner
        if isinstance(parsed_inner, list):
          return {"items": parsed_inner}
      except ValueError:
        pass
    return payload

  @staticmethod
  def _extract_mcp_text(payload: Dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, list):
      texts = [
          str(item.get("text") or "")
          for item in content
          if isinstance(item, dict) and item.get("text")
      ]
      return "\n".join(texts).strip()
    return ""

  def get_json(
      self, url: str, params: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
    """Routes REST URLs to the corresponding `remote_cli mcp` connector tools."""
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    merged_params: Dict[str, Any] = {}
    for k, v in urllib.parse.parse_qsl(parsed.query):
      merged_params[k] = v
    if params:
      for k, v in params.items():
        if v is not None and v != "":
          merged_params[k] = v

    # 1. Dataproc Serverless Batches / Sessions (`locations/{region}/...`)
    m = re.match(
        r"^/v1/projects/([^/]+)/locations/([^/]+)/(batches|sessions)(?:/([^/]+))?$",
        path,
    )
    if m:
      project, region, resource, item_id = m.groups()
      if resource == "batches" and item_id:
        return self.call_tool(
            "google-managed-apache-spark",
            "get_batch",
            {"project_id": project, "region": region, "batch_id": item_id},
        )
      if resource == "batches":
        args: Dict[str, Any] = {"project_id": project, "region": region}
        if merged_params.get("pageSize"):
          args["page_size"] = int(merged_params["pageSize"])
        return self.call_tool(
            "google-managed-apache-spark", "list_batches", args
        )
      if resource == "sessions":
        return self.call_tool(
            "google-managed-apache-spark",
            "list_sessions",
            {"project_id": project, "region": region},
        )

    # 2. Dataproc Cluster Jobs / Clusters (`regions/{region}/...`)
    m = re.match(
        r"^/v1/projects/([^/]+)/regions/([^/]+)/(jobs|clusters)(?:/([^/]+))?$",
        path,
    )
    if m:
      project, region, resource, item_id = m.groups()
      if resource == "jobs" and item_id:
        return self.call_tool(
            "google-managed-apache-spark",
            "get_job",
            {"project_id": project, "region": region, "job_id": item_id},
        )
      if resource == "jobs":
        args = {"project_id": project, "region": region}
        if merged_params.get("pageSize"):
          args["page_size"] = int(merged_params["pageSize"])
        return self.call_tool("google-managed-apache-spark", "list_jobs", args)
      if resource == "clusters":
        return self.call_tool(
            "google-managed-apache-spark",
            "list_clusters",
            {"project_id": project, "region": region},
        )

    # 3. BigQuery Job Detail (`/bigquery/v2/projects/{project}/jobs/{job_id}`)
    m = re.match(r"^/bigquery/v2/projects/([^/]+)/jobs/([^/]+)$", path)
    if m:
      project, job_id = m.groups()
      loc = str(merged_params.get("location") or "US")
      try:
        return self.call_tool(
            "bigquery",
            "get_job",
            {"project_id": project, "job_id": job_id, "location": loc},
        )
      except JobMonitorError as first_err:
        if not merged_params.get("location") and first_err.status == 404:
          for alt_loc in ("us-central1", "EU", "us-east1", "us-west1"):
            try:
              return self.call_tool(
                  "bigquery",
                  "get_job",
                  {
                      "project_id": project,
                      "job_id": job_id,
                      "location": alt_loc,
                  },
              )
            except JobMonitorError:
              continue
        if first_err.status in (403, 404):
          sql_job = self._bq_get_job_via_sql(project, job_id, loc)
          if sql_job is not None:
            return sql_job
        raise

    # 4. BigQuery Jobs List (`/bigquery/v2/projects/{project}/jobs`)
    m = re.match(r"^/bigquery/v2/projects/([^/]+)/jobs$", path)
    if m:
      project = m.group(1)
      return self._bq_list_jobs(project, merged_params)

    # 5. BigQuery Reservations (`/v1/projects/{project}/locations/{loc}/...`)
    m = re.match(
        r"^/v1/projects/([^/]+)/locations/([^/]+)/(reservations|capacityCommitments|reservations/-/assignments)$",
        path,
    )
    if m:
      project, loc, resource = m.groups()
      return self._bq_reservations(project, loc, resource)

    raise JobMonitorError(
        f"Unsupported URL for RemoteCliMcpClient: {url}", status=400
    )

  def _bq_get_job_via_sql(
      self, project: str, job_id: str, loc: str = "US"
  ) -> Optional[Dict[str, Any]]:
    """Fetches a single BigQuery job via `execute_sql_readonly` using `_billing_project`."""
    billing_project = self._billing_project or project
    safe_job_id = job_id.replace("'", "''")
    regions = [loc] + [
        r for r in ("US", "us-central1", "EU") if r.lower() != loc.lower()
    ]
    for reg in regions:
      for view_name in ("JOBS_BY_PROJECT", "JOBS_BY_USER"):
        sql = (
            "SELECT job_id, project_id, user_email, job_type, statement_type,"
            " state, priority, reservation_id, edition,"
            " CAST(UNIX_MILLIS(creation_time) AS STRING) AS creation_ms,"
            " CAST(UNIX_MILLIS(start_time) AS STRING) AS start_ms,"
            " CAST(UNIX_MILLIS(end_time) AS STRING) AS end_ms,"
            " CAST(total_bytes_billed AS STRING) AS total_bytes_billed,"
            " CAST(total_bytes_processed AS STRING) AS total_bytes_processed,"
            " CAST(total_slot_ms AS STRING) AS total_slot_ms, cache_hit,"
            " query, error_result.reason AS error_reason, error_result.message"
            " AS error_message, TO_JSON_STRING(referenced_tables) AS"
            " referenced_tables_json, TO_JSON_STRING(labels) AS labels_json,"
            " TO_JSON_STRING(job_stages) AS job_stages_json FROM"
            f" `{project}`.`region-{reg.lower()}`.INFORMATION_SCHEMA.{view_name}"
            f" WHERE job_id = '{safe_job_id}' LIMIT 1"
        )
        try:
          resp = self.call_tool(
              "bigquery",
              "execute_sql_readonly",
              {"project_id": billing_project, "query": sql},
          )
          jobs = self._rows_to_bq_jobs(resp, project=project, location=reg)
          if jobs:
            return jobs[0]
          break
        except JobMonitorError as e:
          if e.status == 403 and view_name == "JOBS_BY_PROJECT":
            continue
          break
    return None

  def _bq_list_jobs(
      self, project: str, params: Dict[str, Any]
  ) -> Dict[str, Any]:
    """Lists BigQuery jobs via `bigquery` MCP SQL or `google-cloud-cli` `bq ls -j`."""
    max_results = int(params.get("maxResults") or 100)
    all_users = str(params.get("allUsers") or "").lower() == "true"
    min_creation_ms = int(params.get("minCreationTime") or 0)
    state_filter = str(params.get("stateFilter") or "").strip().upper()
    view_name = "JOBS_BY_PROJECT" if all_users else "JOBS_BY_USER"

    where_clauses = []
    if min_creation_ms > 0:
      where_clauses.append(
          f"creation_time >= TIMESTAMP_MILLIS({min_creation_ms})"
      )
    else:
      where_clauses.append(
          "creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
      )
    if state_filter:
      where_clauses.append(f"state = '{state_filter}'")
    where_sql = " AND ".join(where_clauses)

    sql = (
        "SELECT "
        "job_id, project_id, user_email, job_type, statement_type, state, "
        "priority, reservation_id, edition, "
        "CAST(UNIX_MILLIS(creation_time) AS STRING) AS creation_ms, "
        "CAST(UNIX_MILLIS(start_time) AS STRING) AS start_ms, "
        "CAST(UNIX_MILLIS(end_time) AS STRING) AS end_ms, "
        "CAST(total_bytes_billed AS STRING) AS total_bytes_billed, "
        "CAST(total_bytes_processed AS STRING) AS total_bytes_processed, "
        "CAST(total_slot_ms AS STRING) AS total_slot_ms, "
        "cache_hit, query, "
        "error_result.reason AS error_reason, "
        "error_result.message AS error_message, "
        "TO_JSON_STRING(referenced_tables) AS referenced_tables_json, "
        "TO_JSON_STRING(labels) AS labels_json "
        f"FROM `{project}`.`region-us`.INFORMATION_SCHEMA.{view_name} "
        f"WHERE {where_sql} "
        f"ORDER BY creation_time DESC LIMIT {max_results}"
    )
    billing_project = self._billing_project or project
    try:
      resp = self.call_tool(
          "bigquery",
          "execute_sql_readonly",
          {"project_id": billing_project, "query": sql},
      )
      return {
          "jobs": self._rows_to_bq_jobs(resp, project=project, location="US")
      }
    except JobMonitorError as sql_err:
      if sql_err.status == 403 and all_users:
        raise
      # Fallback to google-cloud-cli `bq ls -j` if available
      try:
        all_flag = " -a" if all_users else ""
        cmd_str = (
            f"bq --format=prettyjson ls -j{all_flag} -n {max_results}"
            f" --project_id={project}"
        )
        cli_resp = self.call_tool(
            "google-cloud-cli",
            "run_bq_command",
            {"command": cmd_str, "project": f"projects/{billing_project}"},
        )
        return self._parse_bq_cli_jobs(cli_resp)
      except JobMonitorError:
        raise sql_err

  @staticmethod
  def _rows_to_bq_jobs(
      resp: Dict[str, Any], project: str, location: str = "US"
  ) -> List[Dict[str, Any]]:
    """Converts `execute_sql_readonly` rows into `jobs.list` Job resource dicts."""
    raw_rows: List[Dict[str, Any]] = []
    if isinstance(resp.get("rows"), list):
      schema_fields = (
          (resp.get("schema") or {}).get("fields") or resp.get("columns") or []
      )
      col_names = [
          str(f.get("name") if isinstance(f, dict) else f)
          for f in schema_fields
      ]
      for r in resp["rows"]:
        if isinstance(r, dict) and "f" in r and col_names:
          vals = [
              cell.get("v") if isinstance(cell, dict) else cell
              for cell in r["f"]
          ]
          raw_rows.append(dict(zip(col_names, vals)))
        elif isinstance(r, dict):
          raw_rows.append(r)
    elif isinstance(resp.get("items"), list):
      raw_rows = [r for r in resp["items"] if isinstance(r, dict)]

    jobs: List[Dict[str, Any]] = []
    for row in raw_rows:
      refs_raw: List[Dict[str, Any]] = []
      refs_json = row.get("referenced_tables_json")
      if isinstance(refs_json, str) and refs_json:
        try:
          parsed_refs = json.loads(refs_json)
          if isinstance(parsed_refs, list):
            for t in parsed_refs:
              if isinstance(t, dict):
                refs_raw.append({
                    "projectId": (
                        t.get("project_id") or t.get("projectId") or ""
                    ),
                    "datasetId": (
                        t.get("dataset_id") or t.get("datasetId") or ""
                    ),
                    "tableId": t.get("table_id") or t.get("tableId") or "",
                })
        except ValueError:
          pass
      labels_dict: Dict[str, str] = {}
      labels_json = row.get("labels_json")
      if isinstance(labels_json, str) and labels_json:
        try:
          parsed_lbls = json.loads(labels_json)
          if isinstance(parsed_lbls, list):
            for item in parsed_lbls:
              if isinstance(item, dict) and item.get("key"):
                labels_dict[str(item["key"])] = str(item.get("value") or "")
        except ValueError:
          pass
      stages_raw: List[Dict[str, Any]] = []
      stages_json = row.get("job_stages_json")
      if isinstance(stages_json, str) and stages_json:
        try:
          parsed_stages = json.loads(stages_json)
          if isinstance(parsed_stages, list):
            for s in parsed_stages:
              if isinstance(s, dict):
                stages_raw.append({
                    "id": str(s.get("id") or ""),
                    "name": str(s.get("name") or ""),
                    "status": str(s.get("status") or ""),
                    "recordsRead": str(
                        s.get("records_read") or s.get("recordsRead") or "0"
                    ),
                    "recordsWritten": str(
                        s.get("records_written")
                        or s.get("recordsWritten")
                        or "0"
                    ),
                    "slotMs": str(s.get("slot_ms") or s.get("slotMs") or "0"),
                    "waitMsMax": str(
                        s.get("wait_ms_max") or s.get("waitMsMax") or "0"
                    ),
                    "computeMsMax": str(
                        s.get("compute_ms_max") or s.get("computeMsMax") or "0"
                    ),
                    "shuffleOutputBytes": str(
                        s.get("shuffle_output_bytes")
                        or s.get("shuffleOutputBytes")
                        or "0"
                    ),
                    "shuffleOutputBytesSpilled": str(
                        s.get("shuffle_output_bytes_spilled")
                        or s.get("shuffleOutputBytesSpilled")
                        or "0"
                    ),
                })
        except ValueError:
          pass
      err_reason = str(row.get("error_reason") or "")
      err_msg = str(row.get("error_message") or "")
      err_result = (
          {"reason": err_reason, "message": err_msg}
          if (err_reason or err_msg)
          else {}
      )
      jobs.append({
          "jobReference": {
              "projectId": str(row.get("project_id") or project),
              "jobId": str(row.get("job_id") or ""),
              "location": location,
          },
          "user_email": str(row.get("user_email") or ""),
          "state": str(row.get("state") or "DONE"),
          "status": {
              "state": str(row.get("state") or "DONE"),
              "errorResult": err_result,
          },
          "configuration": {
              "jobType": str(row.get("job_type") or "QUERY"),
              "labels": labels_dict,
              "query": {
                  "query": str(row.get("query") or ""),
                  "priority": str(row.get("priority") or "INTERACTIVE"),
                  "statementType": str(row.get("statement_type") or ""),
              },
          },
          "statistics": {
              "creationTime": str(row.get("creation_ms") or "0"),
              "startTime": str(row.get("start_ms") or "0"),
              "endTime": str(row.get("end_ms") or "0"),
              "totalBytesProcessed": str(
                  row.get("total_bytes_processed") or "0"
              ),
              "totalSlotMs": str(row.get("total_slot_ms") or "0"),
              "reservation_id": str(row.get("reservation_id") or ""),
              "edition": str(row.get("edition") or ""),
              "query": {
                  "totalBytesBilled": str(row.get("total_bytes_billed") or "0"),
                  "totalBytesProcessed": str(
                      row.get("total_bytes_processed") or "0"
                  ),
                  "totalSlotMs": str(row.get("total_slot_ms") or "0"),
                  "cacheHit": (
                      str(row.get("cache_hit") or "").lower() in ("true", "1")
                  ),
                  "statementType": str(row.get("statement_type") or ""),
                  "referencedTables": refs_raw,
                  "queryPlan": stages_raw,
              },
          },
      })
    return jobs

  @staticmethod
  def _parse_bq_cli_jobs(cli_resp: Dict[str, Any]) -> Dict[str, Any]:
    stdout_text = str(cli_resp.get("stdout") or "")
    if stdout_text.strip():
      try:
        parsed = json.loads(stdout_text)
        if isinstance(parsed, list):
          return {"jobs": parsed}
      except ValueError:
        pass
    if isinstance(cli_resp.get("items"), list):
      return {"jobs": cli_resp["items"]}
    return {"jobs": []}

  def _bq_reservations(
      self, project: str, loc: str, resource: str
  ) -> Dict[str, Any]:
    """Queries BigQuery Reservation metadata via `INFORMATION_SCHEMA`."""
    billing_project = self._billing_project or project
    region_qualifier = f"`{project}`.`region-{loc.lower()}`"
    if resource == "reservations":
      sql = (
          "SELECT reservation_name, edition, slot_capacity, "
          "autoscale.current_slots AS current_slots, "
          "autoscale.max_slots AS max_slots, ignore_idle_slots, concurrency "
          f"FROM {region_qualifier}.INFORMATION_SCHEMA.RESERVATIONS"
      )
      resp = self.call_tool(
          "bigquery",
          "execute_sql_readonly",
          {"project_id": billing_project, "query": sql},
      )
      rows = self._extract_sql_dicts(resp)
      return {
          "reservations": [
              {
                  "name": str(r.get("reservation_name") or ""),
                  "edition": str(r.get("edition") or "STANDARD"),
                  "slotCapacity": int(r.get("slot_capacity") or 0),
                  "autoscale": {
                      "currentSlots": int(r.get("current_slots") or 0),
                      "maxSlots": int(r.get("max_slots") or 0),
                  },
                  "ignoreIdleSlots": (
                      str(r.get("ignore_idle_slots") or "").lower()
                      in ("true", "1")
                  ),
                  "concurrency": int(r.get("concurrency") or 0),
              }
              for r in rows
          ]
      }
    if resource == "capacityCommitments":
      sql = (
          "SELECT capacity_commitment_id, edition, slot_count, "
          "commitment_plan, state "
          f"FROM {region_qualifier}.INFORMATION_SCHEMA.CAPACITY_COMMITMENTS"
      )
      resp = self.call_tool(
          "bigquery",
          "execute_sql_readonly",
          {"project_id": billing_project, "query": sql},
      )
      rows = self._extract_sql_dicts(resp)
      return {
          "capacityCommitments": [
              {
                  "name": str(r.get("capacity_commitment_id") or ""),
                  "edition": str(r.get("edition") or ""),
                  "slotCount": int(r.get("slot_count") or 0),
                  "plan": str(r.get("commitment_plan") or ""),
                  "state": str(r.get("state") or ""),
              }
              for r in rows
          ]
      }
    sql = (
        "SELECT assignment_id, reservation_name, assignee_name, job_type "
        f"FROM {region_qualifier}.INFORMATION_SCHEMA.ASSIGNMENTS"
    )
    resp = self.call_tool(
        "bigquery",
        "execute_sql_readonly",
        {"project_id": billing_project, "query": sql},
    )
    rows = self._extract_sql_dicts(resp)
    return {
        "assignments": [
            {
                "name": (
                    f"reservations/{r.get('reservation_name', '')}/assignments/{r.get('assignment_id', '')}"
                ),
                "assignee": str(r.get("assignee_name") or ""),
                "jobType": str(r.get("job_type") or ""),
                "state": "ACTIVE",
            }
            for r in rows
        ]
    }

  @staticmethod
  def _extract_sql_dicts(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(resp.get("rows"), list):
      schema_fields = (
          (resp.get("schema") or {}).get("fields") or resp.get("columns") or []
      )
      col_names = [
          str(f.get("name") if isinstance(f, dict) else f)
          for f in schema_fields
      ]
      for r in resp["rows"]:
        if isinstance(r, dict) and "f" in r and col_names:
          vals = [
              cell.get("v") if isinstance(cell, dict) else cell
              for cell in r["f"]
          ]
          out.append(dict(zip(col_names, vals)))
        elif isinstance(r, dict):
          out.append(r)
    elif isinstance(resp.get("items"), list):
      out = [r for r in resp["items"] if isinstance(r, dict)]
    return out


class RestClient:
  """Minimal standard-library JSON REST client with auth and Sobi MCP fallback."""

  def __init__(
      self,
      token_provider: Optional[GcloudTokenProvider] = None,
      urlopen: Optional[Callable[..., Any]] = None,
      remote_cli_client: Optional[RemoteCliMcpClient] = None,
  ):
    self._explicit_tokens = token_provider is not None
    self._tokens = token_provider or GcloudTokenProvider()
    self._urlopen = urlopen or urllib.request.urlopen
    self._remote_cli = remote_cli_client

  def get_json(
      self, url: str, params: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
    """Performs an authenticated GET request and returns decoded JSON."""
    if self._remote_cli is not None:
      return self._remote_cli.get_json(url, params)
    req_url = url
    if params:
      filtered = {k: v for k, v in params.items() if v is not None and v != ""}
      if filtered:
        req_url = f"{url}?{urllib.parse.urlencode(filtered, doseq=True)}"
    while True:
      try:
        token = self._tokens.token()
      except JobMonitorError:
        if not self._explicit_tokens and RemoteCliMcpClient.is_available():
          self._remote_cli = RemoteCliMcpClient()
          return self._remote_cli.get_json(url, params)
        raise
      req = urllib.request.Request(
          req_url,
          headers={
              "Authorization": f"Bearer {token}",
              "Accept": "application/json",
              "User-Agent": _USER_AGENT,
          },
      )
      try:
        ctx = ssl.create_default_context()
        with self._urlopen(
            req, timeout=_HTTP_TIMEOUT_SECONDS, context=ctx
        ) as r:
          raw = r.read().decode("utf-8", errors="replace")
          return json.loads(raw) if raw.strip() else {}
      except urllib.error.HTTPError as e:
        body = ""
        try:
          body = e.read().decode("utf-8", errors="replace")
        except Exception:  # pylint: disable=broad-except
          pass
        if e.code == 401 and self._tokens.fallback():
          continue
        msg = _extract_api_error(body) or f"HTTP {e.code}: {e.reason}"
        raise JobMonitorError(msg, status=e.code) from e
      except urllib.error.URLError as e:
        raise JobMonitorError(f"Network error calling {req_url}: {e}") from e


def _extract_api_error(body: str) -> str:
  try:
    payload = json.loads(body)
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
      return str(payload["error"].get("message") or "")
  except ValueError:
    pass
  return ""


# ------------------------------------------------------------------------------
# BigQuery Job Normalization & Actions
# ------------------------------------------------------------------------------


def normalize_bq_job(raw: Dict[str, Any]) -> Dict[str, Any]:
  """Extracts a consistent summary dict from a BigQuery Job resource."""
  ref = raw.get("jobReference") or {}
  stats = raw.get("statistics") or {}
  qstats = stats.get("query") or {}
  config = raw.get("configuration") or {}
  qconfig = config.get("query") or {}
  status = raw.get("status") or {}
  err = status.get("errorResult") or raw.get("errorResult") or {}
  errors_list = status.get("errors") or []
  first_err = (
      errors_list[0]
      if (errors_list and isinstance(errors_list[0], dict))
      else {}
  )

  creation_ms = int(stats.get("creationTime") or 0)
  start_ms = int(stats.get("startTime") or 0)
  end_ms = int(stats.get("endTime") or 0)
  raw_state = str(status.get("state") or raw.get("state") or "UNKNOWN")
  if (
      raw_state in ("RUNNING", "PENDING")
      and end_ms == 0
      and (start_ms > 0 or creation_ms > 0)
  ):
    end_ms = int(time.time() * 1000)
    if start_ms == 0:
      start_ms = creation_ms
  duration_ms = (
      (end_ms - start_ms)
      if (end_ms > 0 and start_ms > 0 and end_ms >= start_ms)
      else 0
  )

  bytes_billed = int(qstats.get("totalBytesBilled") or 0)
  bytes_processed = int(
      qstats.get("totalBytesProcessed") or stats.get("totalBytesProcessed") or 0
  )
  slot_ms = int(qstats.get("totalSlotMs") or stats.get("totalSlotMs") or 0)
  cache_hit = bool(qstats.get("cacheHit", False))

  # Inspect queryPlan stages for spill or high wait ratio.
  stages = qstats.get("queryPlan") or []
  spilled_bytes = sum(
      int(s.get("shuffleOutputBytesSpilled") or 0) for s in stages
  )
  max_wait_ms = max((int(s.get("waitMsMax") or 0) for s in stages), default=0)

  bi_stats = qstats.get("biEngineStatistics") or {}
  bi_engine_mode = str(bi_stats.get("biEngineMode") or "")
  labels = (
      config.get("labels") if isinstance(config.get("labels"), dict) else {}
  )
  priority = str(qconfig.get("priority") or "INTERACTIVE")
  dest_tbl = qconfig.get("destinationTable") or {}
  dest_table_str = (
      f"{dest_tbl.get('projectId', '')}.{dest_tbl.get('datasetId', '')}.{dest_tbl.get('tableId', '')}"
      if isinstance(dest_tbl, dict) and dest_tbl.get("tableId")
      else ""
  )
  num_dml_affected = int(qstats.get("numDmlAffectedRows") or 0)
  transferred_bytes = int(qstats.get("transferredBytes") or 0)

  err_reason = str(err.get("reason") or first_err.get("reason") or "")
  err_msg = str(err.get("message") or first_err.get("message") or "")
  is_redacted = str(ref.get("jobId") or "") == "<REDACTED>"

  state = raw_state
  # Note: When BigQuery redacts another user's job (`jobId == '<REDACTED>'`),
  # it sets `errorResult.reason = 'unknown'` with no message on succeeded jobs
  # (including 0-byte cached/metadata queries).
  if (
      err_msg
      or (
          err_reason
          and not (is_redacted and err_reason == "unknown" and not err_msg)
      )
  ) and state == "DONE":
    state = "FAILED"

  return {
      "jobId": str(ref.get("jobId") or raw.get("id") or ""),
      "projectId": str(ref.get("projectId") or ""),
      "location": str(ref.get("location") or "US"),
      "userEmail": str(raw.get("user_email") or ""),
      "jobType": str(config.get("jobType") or "QUERY"),
      "statementType": str(
          qstats.get("statementType") or qconfig.get("statementType") or ""
      ),
      "edition": str(stats.get("edition") or ""),
      "reservationId": str(stats.get("reservation_id") or ""),
      "state": state,
      "creationTimeMs": creation_ms,
      "creationTime": epoch_ms_to_iso(creation_ms),
      "startTimeMs": start_ms,
      "endTimeMs": end_ms,
      "durationMs": duration_ms,
      "durationHuman": human_millis(duration_ms),
      "bytesBilled": bytes_billed,
      "bytesBilledHuman": human_bytes(bytes_billed),
      "bytesProcessed": bytes_processed,
      "bytesProcessedHuman": human_bytes(bytes_processed),
      "estimatedUsd": estimate_on_demand_usd(bytes_billed),
      "estimatedUsdHuman": format_usd(estimate_on_demand_usd(bytes_billed)),
      "slotMs": slot_ms,
      "slotTimeHuman": human_millis(slot_ms),
      "cacheHit": cache_hit,
      "spilledBytes": spilled_bytes,
      "maxWaitMs": max_wait_ms,
      "biEngineMode": bi_engine_mode,
      "priority": priority,
      "labels": labels,
      "destinationTable": dest_table_str,
      "numDmlAffectedRows": num_dml_affected,
      "transferredBytes": transferred_bytes,
      "query": str(qconfig.get("query") or ""),
      "errorMessage": err_msg,
      "errorReason": err_reason,
      "referencedTables": [
          f"{t.get('projectId', '')}.{t.get('datasetId', '')}.{t.get('tableId', '')}"
          for t in qstats.get("referencedTables") or []
          if isinstance(t, dict)
      ],
      "stages": [
          {
              "id": str(s.get("id") or ""),
              "name": str(s.get("name") or ""),
              "status": str(s.get("status") or ""),
              "recordsRead": int(s.get("recordsRead") or 0),
              "recordsWritten": int(s.get("recordsWritten") or 0),
              "slotMs": int(s.get("slotMs") or 0),
              "waitMsMax": int(s.get("waitMsMax") or 0),
              "computeMsMax": int(s.get("computeMsMax") or 0),
              "shuffleOutputBytes": int(s.get("shuffleOutputBytes") or 0),
              "shuffleOutputBytesSpilled": int(
                  s.get("shuffleOutputBytesSpilled") or 0
              ),
          }
          for s in stages
          if isinstance(s, dict)
      ],
  }


def fetch_bq_jobs(
    client: RestClient,
    project: str,
    max_results: int = 100,
    all_users: bool = True,
    user_filter: Optional[str] = None,
    days: Optional[float] = None,
    state_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
  """Fetches BigQuery jobs via `jobs.list` with automatic `allUsers` fallback.

  Tries `allUsers=true` first (when `all_users` is True); if the caller lacks
  `bigquery.jobs.listAll` (HTTP 403), automatically falls back to
  `allUsers=false` so developers with `roles/bigquery.jobUser` still get their
  own jobs.

  Args:
    client: Authenticated RestClient.
    project: GCP project ID.
    max_results: Max jobs to fetch.
    all_users: Whether to request all users' jobs first.
    user_filter: Optional substring or email filter on `user_email`.
    days: Optional lookback window in days (`minCreationTime`).
    state_filter: Optional state filter (`DONE`, `FAILED`, `RUNNING`,
      `PENDING`).

  Returns:
    Tuple of (normalized_jobs, fell_back_to_own_jobs).
  """
  url = f"{BQ_ENDPOINT}/bigquery/v2/projects/{urllib.parse.quote(project)}/jobs"
  fell_back = False
  params: Dict[str, Any] = {
      "projection": "full",
      "maxResults": min(max(max_results, 50), 200),
  }
  if days is not None and days > 0:
    min_ms = int((time.time() - float(days) * 86400.0) * 1000)
    params["minCreationTime"] = str(max(min_ms, 0))
  if state_filter and state_filter.strip().upper() in ("RUNNING", "PENDING"):
    params["stateFilter"] = state_filter.strip().upper()
  if all_users:
    params["allUsers"] = "true"

  raw_jobs: List[Dict[str, Any]] = []
  page_token: Optional[str] = None
  while len(raw_jobs) < max_results:
    page_params = dict(params)
    if page_token:
      page_params["pageToken"] = page_token
    try:
      payload = client.get_json(url, page_params)
    except JobMonitorError as e:
      if e.status == 403 and all_users:
        fell_back = True
        all_users = False
        params.pop("allUsers", None)
        page_params.pop("allUsers", None)
        payload = client.get_json(url, page_params)
      else:
        raise
    batch = payload.get("jobs") or []
    raw_jobs.extend(j for j in batch if isinstance(j, dict))
    page_token = payload.get("nextPageToken")
    if not page_token or not batch:
      break

  normalized = [normalize_bq_job(j) for j in raw_jobs]
  if user_filter:
    needle = user_filter.lower()
    normalized = [
        j for j in normalized if needle in j.get("userEmail", "").lower()
    ]
  if state_filter:
    target_state = state_filter.strip().upper()
    normalized = [
        j for j in normalized if j.get("state", "").upper() == target_state
    ]
  return normalized, fell_back


def fetch_bq_job_detail(
    client: RestClient,
    project: str,
    job_id: str,
    location: Optional[str] = None,
) -> Dict[str, Any]:
  """Fetches a single BigQuery job by ID (accepts `proj:loc.jobId` or `jobId`)."""
  clean_id = job_id.strip()
  if ":" in clean_id:
    proj_part, rest = clean_id.split(":", 1)
    if proj_part:
      project = proj_part
    clean_id = rest
  if "." in clean_id:
    loc_part, rest = clean_id.split(".", 1)
    if loc_part and not location:
      location = loc_part
    clean_id = rest

  url = (
      f"{BQ_ENDPOINT}/bigquery/v2/projects/{urllib.parse.quote(project)}"
      f"/jobs/{urllib.parse.quote(clean_id)}"
  )
  params = {"location": location} if location else None
  raw = client.get_json(url, params)
  return normalize_bq_job(raw)


def aggregate_bq_summary(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
  """Aggregates BigQuery jobs by user, edition/reservation, and error reason."""
  by_user: Dict[str, Dict[str, Any]] = {}
  by_reservation: Dict[str, Dict[str, Any]] = {}
  by_error: Dict[str, Dict[str, Any]] = {}

  for j in jobs:
    user = j.get("userEmail") or "<REDACTED>"
    u_rec = by_user.setdefault(
        user,
        {
            "userEmail": user,
            "totalJobs": 0,
            "succeededJobs": 0,
            "failedJobs": 0,
            "runningJobs": 0,
            "bytesBilled": 0,
            "onDemandBytesBilled": 0,
            "slotMs": 0,
        },
    )
    u_rec["totalJobs"] += 1
    state = j.get("state") or "UNKNOWN"
    if state == "FAILED":
      u_rec["failedJobs"] += 1
    elif state in ("RUNNING", "PENDING"):
      u_rec["runningJobs"] += 1
    else:
      u_rec["succeededJobs"] += 1
    u_rec["bytesBilled"] += int(j.get("bytesBilled") or 0)
    if not j.get("reservationId") and not j.get("edition"):
      u_rec["onDemandBytesBilled"] += int(j.get("bytesBilled") or 0)
    u_rec["slotMs"] += int(j.get("slotMs") or 0)

    edition = j.get("edition") or "ON_DEMAND"
    res_id = j.get("reservationId") or "(none - on-demand)"
    res_key = f"{edition}|{res_id}"
    r_rec = by_reservation.setdefault(
        res_key,
        {
            "edition": edition,
            "reservationId": res_id,
            "totalJobs": 0,
            "succeededJobs": 0,
            "failedJobs": 0,
            "bytesBilled": 0,
            "slotMs": 0,
        },
    )
    r_rec["totalJobs"] += 1
    if state == "FAILED":
      r_rec["failedJobs"] += 1
    else:
      r_rec["succeededJobs"] += 1
    r_rec["bytesBilled"] += int(j.get("bytesBilled") or 0)
    r_rec["slotMs"] += int(j.get("slotMs") or 0)

    if state == "FAILED":
      reason = j.get("errorReason") or "unknownError"
      msg = truncate_one_line(j.get("errorMessage") or "(no message)", 120)
      err_key = f"{reason}|{msg}"
      e_rec = by_error.setdefault(
          err_key,
          {
              "errorReason": reason,
              "sampleMessage": msg,
              "count": 0,
              "sampleJobId": j.get("jobId") or "",
          },
      )
      e_rec["count"] += 1

  users_list = sorted(
      by_user.values(),
      key=lambda r: (r["bytesBilled"], r["slotMs"], r["totalJobs"]),
      reverse=True,
  )
  for u in users_list:
    u["bytesBilledHuman"] = human_bytes(u["bytesBilled"])
    u["estimatedOnDemandUsd"] = estimate_on_demand_usd(u["onDemandBytesBilled"])
    u["estimatedOnDemandUsdHuman"] = format_usd(u["estimatedOnDemandUsd"])
    u["slotTimeHuman"] = human_millis(u["slotMs"])

  res_list = sorted(
      by_reservation.values(),
      key=lambda r: (r["bytesBilled"], r["slotMs"], r["totalJobs"]),
      reverse=True,
  )
  for r in res_list:
    r["bytesBilledHuman"] = human_bytes(r["bytesBilled"])
    r["slotTimeHuman"] = human_millis(r["slotMs"])

  err_list = sorted(by_error.values(), key=lambda e: e["count"], reverse=True)
  return {
      "totalJobsAnalyzed": len(jobs),
      "byUser": users_list,
      "byReservation": res_list,
      "topErrors": err_list,
  }


def aggregate_bq_hot_tables(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
  """Aggregates referenced BigQuery tables by total bytes billed and slot time."""
  tables: Dict[str, Dict[str, Any]] = {}
  redacted_count = 0
  for j in jobs:
    if j.get("jobId") == "<REDACTED>" and not j.get("referencedTables"):
      redacted_count += 1
    refs = j.get("referencedTables") or []
    for tbl in set(refs):
      if not tbl or tbl == "..":
        continue
      rec = tables.setdefault(
          tbl,
          {
              "table": tbl,
              "queryCount": 0,
              "totalBytesBilled": 0,
              "totalSlotMs": 0,
              "users": set(),
          },
      )
      rec["queryCount"] += 1
      rec["totalBytesBilled"] += int(j.get("bytesBilled") or 0)
      rec["totalSlotMs"] += int(j.get("slotMs") or 0)
      if j.get("userEmail"):
        rec["users"].add(j["userEmail"])

  ranked = sorted(
      tables.values(),
      key=lambda r: (
          r["totalBytesBilled"],
          r["totalSlotMs"],
          r["queryCount"],
      ),
      reverse=True,
  )
  out_tables = []
  for r in ranked:
    out_tables.append({
        "table": r["table"],
        "queryCount": r["queryCount"],
        "totalBytesBilled": r["totalBytesBilled"],
        "totalBytesBilledHuman": human_bytes(r["totalBytesBilled"]),
        "estimatedUsd": estimate_on_demand_usd(r["totalBytesBilled"]),
        "estimatedUsdHuman": format_usd(
            estimate_on_demand_usd(r["totalBytesBilled"])
        ),
        "totalSlotMs": r["totalSlotMs"],
        "totalSlotTimeHuman": human_millis(r["totalSlotMs"]),
        "distinctUsers": len(r["users"]),
    })
  return {
      "totalJobsAnalyzed": len(jobs),
      "redactedJobsWithoutTableRefs": redacted_count,
      "hotTables": out_tables,
  }


def fetch_bq_reservations(
    client: RestClient,
    project: str,
    location: str = "US",
) -> Dict[str, Any]:
  """Fetches BigQuery slot reservations, capacity commitments, and assignments."""
  loc = location or "US"
  base = (
      f"{BQ_RESERVATION_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
      f"/locations/{urllib.parse.quote(loc)}"
  )
  reservations: List[Dict[str, Any]] = []
  commitments: List[Dict[str, Any]] = []
  assignments: List[Dict[str, Any]] = []
  warnings: List[str] = []

  try:
    r_resp = client.get_json(f"{base}/reservations")
    for r in r_resp.get("reservations") or []:
      if isinstance(r, dict):
        autoscale = r.get("autoscale") or {}
        reservations.append({
            "name": str(r.get("name") or "").rsplit("/", 1)[-1],
            "edition": str(r.get("edition") or "STANDARD"),
            "baselineSlots": int(r.get("slotCapacity") or 0),
            "autoscaleCurrentSlots": int(autoscale.get("currentSlots") or 0),
            "autoscaleMaxSlots": int(autoscale.get("maxSlots") or 0),
            "ignoreIdleSlots": bool(r.get("ignoreIdleSlots", False)),
            "concurrency": int(r.get("concurrency") or 0),
        })
  except JobMonitorError as e:
    warnings.append(f"Reservations ({loc}): {e}")

  try:
    c_resp = client.get_json(f"{base}/capacityCommitments")
    for c in c_resp.get("capacityCommitments") or []:
      if isinstance(c, dict):
        commitments.append({
            "name": str(c.get("name") or "").rsplit("/", 1)[-1],
            "edition": str(c.get("edition") or ""),
            "slotCount": int(c.get("slotCount") or 0),
            "plan": str(c.get("plan") or ""),
            "state": str(c.get("state") or ""),
        })
  except JobMonitorError as e:
    warnings.append(f"Capacity commitments ({loc}): {e}")

  try:
    a_resp = client.get_json(f"{base}/reservations/-/assignments")
    for a in a_resp.get("assignments") or []:
      if isinstance(a, dict):
        full_name = str(a.get("name") or "")
        parts = full_name.split("/")
        res_name = (
            parts[parts.index("reservations") + 1]
            if "reservations" in parts
            else ""
        )
        assignments.append({
            "name": full_name.rsplit("/", 1)[-1],
            "reservation": res_name,
            "assignee": str(a.get("assignee") or ""),
            "jobType": str(a.get("jobType") or ""),
            "state": str(a.get("state") or ""),
        })
  except JobMonitorError as e:
    warnings.append(f"Assignments ({loc}): {e}")

  return {
      "project": project,
      "location": loc,
      "reservations": reservations,
      "capacityCommitments": commitments,
      "assignments": assignments,
      "warnings": warnings,
  }


# ------------------------------------------------------------------------------
# Spark (Dataproc Serverless Batches & Cluster Jobs) Normalization & Actions
# ------------------------------------------------------------------------------


def normalize_spark_batch(
    raw: Dict[str, Any], project: str, region: str
) -> Dict[str, Any]:
  """Normalizes a Dataproc Serverless Batch resource."""
  name = str(
      raw.get("name") or raw.get("batchName") or raw.get("batch_name") or ""
  )
  batch_id = name.rsplit("/", 1)[-1] if "/" in name else name
  create_str = str(raw.get("createTime") or raw.get("create_time") or "")
  state_str = str(raw.get("stateTime") or raw.get("state_time") or "")
  state = str(raw.get("state") or "UNKNOWN")

  create_dt = parse_rfc3339(create_str)
  end_dt = parse_rfc3339(state_str)
  if state in ("RUNNING", "PENDING", "CANCELLING") and create_dt is not None:
    end_dt = datetime.datetime.now(datetime.timezone.utc)
  duration_ms = (
      int((end_dt - create_dt).total_seconds() * 1000)
      if (create_dt and end_dt and end_dt >= create_dt)
      else 0
  )

  workload_type = "PYSPARK"
  main_uri = ""
  if isinstance(raw.get("pysparkBatch"), dict):
    workload_type = "PYSPARK"
    main_uri = str(raw["pysparkBatch"].get("mainPythonFileUri") or "")
  elif isinstance(raw.get("sparkBatch"), dict):
    workload_type = "SPARK_JAR"
    main_uri = str(
        raw["sparkBatch"].get("mainJarFileUri")
        or raw["sparkBatch"].get("mainClass")
        or ""
    )
  elif isinstance(raw.get("sparkSqlBatch"), dict):
    workload_type = "SPARK_SQL"
    main_uri = str(raw["sparkSqlBatch"].get("queryFileUri") or "")

  runtime_info = raw.get("runtimeInfo") or {}
  usage = runtime_info.get("approximateUsage") or {}
  milli_dcu_seconds = int(usage.get("milliDcuSeconds") or 0)

  return {
      "id": batch_id,
      "kind": "SERVERLESS_BATCH",
      "workloadType": workload_type,
      "projectId": project,
      "region": region,
      "creator": str(raw.get("creator") or ""),
      "clusterName": "(serverless)",
      "state": state,
      "createTime": create_str,
      "createTimeEpochMs": (
          int(create_dt.timestamp() * 1000) if create_dt else 0
      ),
      "endTime": state_str,
      "durationMs": duration_ms,
      "durationHuman": human_millis(duration_ms),
      "milliDcuSeconds": milli_dcu_seconds,
      "dcuHours": round(milli_dcu_seconds / (1000.0 * 3600.0), 4),
      "mainArtifact": main_uri,
      "driverOutputUri": str(runtime_info.get("outputUri") or ""),
      "stateMessage": str(raw.get("stateMessage") or ""),
  }


def normalize_spark_cluster_job(
    raw: Dict[str, Any], project: str, region: str
) -> Dict[str, Any]:
  """Normalizes a Dataproc Cluster Job resource."""
  ref = raw.get("reference") or {}
  job_id = str(ref.get("jobId") or "")
  placement = raw.get("placement") or {}
  status = raw.get("status") or {}
  history = raw.get("statusHistory") or []

  state = str(status.get("state") or "UNKNOWN")
  state_start = str(status.get("stateStartTime") or "")
  create_str = state_start
  for h in history:
    if isinstance(h, dict) and h.get("state") in ("PENDING", "RUNNING"):
      create_str = str(h.get("stateStartTime") or create_str)
      break

  create_dt = parse_rfc3339(create_str)
  end_dt = parse_rfc3339(state_start)
  if state in ("RUNNING", "PENDING", "SETUP_DONE") and create_dt is not None:
    end_dt = datetime.datetime.now(datetime.timezone.utc)
  duration_ms = (
      int((end_dt - create_dt).total_seconds() * 1000)
      if (create_dt and end_dt and end_dt >= create_dt)
      else 0
  )

  workload_type = "CLUSTER_JOB"
  main_uri = ""
  if isinstance(raw.get("pysparkJob"), dict):
    workload_type = "PYSPARK"
    main_uri = str(raw["pysparkJob"].get("mainPythonFileUri") or "")
  elif isinstance(raw.get("sparkJob"), dict):
    workload_type = "SPARK_JAR"
    main_uri = str(
        raw["sparkJob"].get("mainJarFileUri")
        or raw["sparkJob"].get("mainClass")
        or ""
    )
  elif isinstance(raw.get("sparkSqlJob"), dict):
    workload_type = "SPARK_SQL"
    main_uri = str(raw["sparkSqlJob"].get("queryFileUri") or "")

  return {
      "id": job_id,
      "kind": "CLUSTER_JOB",
      "workloadType": workload_type,
      "projectId": project,
      "region": region,
      "creator": str(raw.get("submittedBy") or ""),
      "clusterName": str(placement.get("clusterName") or ""),
      "state": state,
      "createTime": create_str,
      "createTimeEpochMs": (
          int(create_dt.timestamp() * 1000) if create_dt else 0
      ),
      "endTime": state_start,
      "durationMs": duration_ms,
      "durationHuman": human_millis(duration_ms),
      "milliDcuSeconds": 0,
      "dcuHours": 0.0,
      "mainArtifact": main_uri,
      "driverOutputUri": str(raw.get("driverOutputResourceUri") or ""),
      "stateMessage": str(status.get("details") or ""),
  }


def fetch_spark_workloads(
    client: RestClient,
    project: str,
    region: str = DEFAULT_REGION,
    max_results: int = 50,
    user_filter: Optional[str] = None,
    state_filter: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
  """Fetches both Dataproc Serverless Batches and Cluster Jobs across region(s)."""
  workloads: List[Dict[str, Any]] = []
  warnings: List[str] = []

  regions = [
      r.strip() for r in (region or DEFAULT_REGION).split(",") if r.strip()
  ] or [DEFAULT_REGION]

  for reg in regions:
    # 1. Dataproc Serverless Batches
    batches_url = (
        f"{DATAPROC_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
        f"/locations/{urllib.parse.quote(reg)}/batches"
    )
    try:
      b_payload = client.get_json(
          batches_url, {"pageSize": min(max_results, 100)}
      )
      for b in b_payload.get("batches") or []:
        if isinstance(b, dict):
          workloads.append(normalize_spark_batch(b, project, reg))
    except JobMonitorError as e:
      warnings.append(f"Serverless batches ({reg}): {e}")

    # 2. Dataproc Cluster Jobs
    jobs_url = (
        f"{DATAPROC_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
        f"/regions/{urllib.parse.quote(reg)}/jobs"
    )
    try:
      j_payload = client.get_json(jobs_url, {"pageSize": min(max_results, 100)})
      for j in j_payload.get("jobs") or []:
        if isinstance(j, dict):
          workloads.append(normalize_spark_cluster_job(j, project, reg))
    except JobMonitorError as e:
      warnings.append(f"Cluster jobs ({reg}): {e}")

  if user_filter:
    needle = user_filter.lower()
    workloads = [
        w
        for w in workloads
        if needle in w.get("creator", "").lower() or not w.get("creator")
    ]
  if state_filter:
    target_state = state_filter.strip().upper()
    workloads = [
        w for w in workloads if w.get("state", "").upper() == target_state
    ]

  workloads.sort(key=lambda w: w.get("createTimeEpochMs", 0), reverse=True)
  return workloads, warnings


def fetch_spark_workload_detail(
    client: RestClient,
    project: str,
    job_or_batch_id: str,
    region: str = DEFAULT_REGION,
    workload_type: str = "auto",
) -> Dict[str, Any]:
  """Fetches details for a Spark Serverless Batch or Cluster Job by ID."""
  clean_id = job_or_batch_id.strip().rsplit("/", 1)[-1]
  batch_url = (
      f"{DATAPROC_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
      f"/locations/{urllib.parse.quote(region)}/batches/{urllib.parse.quote(clean_id)}"
  )
  job_url = (
      f"{DATAPROC_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
      f"/regions/{urllib.parse.quote(region)}/jobs/{urllib.parse.quote(clean_id)}"
  )
  if workload_type == "cluster_job":
    raw_job = client.get_json(job_url)
    return normalize_spark_cluster_job(raw_job, project, region)
  if workload_type == "batch":
    raw_batch = client.get_json(batch_url)
    return normalize_spark_batch(raw_batch, project, region)
  try:
    raw_batch = client.get_json(batch_url)
    return normalize_spark_batch(raw_batch, project, region)
  except JobMonitorError as batch_err:
    try:
      raw_job = client.get_json(job_url)
      return normalize_spark_cluster_job(raw_job, project, region)
    except JobMonitorError:
      raise batch_err


def fetch_spark_fleet(
    client: RestClient,
    project: str,
    region: str = DEFAULT_REGION,
) -> Dict[str, Any]:
  """Fetches Dataproc Clusters and Serverless Interactive Sessions in region(s)."""
  clusters: List[Dict[str, Any]] = []
  sessions: List[Dict[str, Any]] = []
  warnings: List[str] = []

  regions = [
      r.strip() for r in (region or DEFAULT_REGION).split(",") if r.strip()
  ] or [DEFAULT_REGION]

  for reg in regions:
    # 1. Dataproc Clusters
    clusters_url = (
        f"{DATAPROC_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
        f"/regions/{urllib.parse.quote(reg)}/clusters"
    )
    try:
      c_payload = client.get_json(clusters_url)
      for c in c_payload.get("clusters") or []:
        if isinstance(c, dict):
          cfg = c.get("config") or {}
          master_cfg = cfg.get("masterConfig") or {}
          worker_cfg = cfg.get("workerConfig") or {}
          status = c.get("status") or {}
          clusters.append({
              "clusterName": str(
                  c.get("clusterName") or c.get("cluster_name") or ""
              ),
              "region": reg,
              "state": str(status.get("state") or "UNKNOWN"),
              "stateStartTime": str(
                  status.get("stateStartTime")
                  or status.get("state_start_time")
                  or ""
              ),
              "masterMachineType": (
                  str(master_cfg.get("machineTypeUri") or "").rsplit("/", 1)[-1]
              ),
              "workerCount": int(worker_cfg.get("numInstances") or 0),
              "workerMachineType": (
                  str(worker_cfg.get("machineTypeUri") or "").rsplit("/", 1)[-1]
              ),
          })
    except JobMonitorError as e:
      warnings.append(f"Clusters ({reg}): {e}")

    # 2. Dataproc Serverless Interactive Sessions
    sessions_url = (
        f"{DATAPROC_ENDPOINT}/v1/projects/{urllib.parse.quote(project)}"
        f"/locations/{urllib.parse.quote(reg)}/sessions"
    )
    try:
      s_payload = client.get_json(sessions_url)
      for s in s_payload.get("sessions") or []:
        if isinstance(s, dict):
          name = str(
              s.get("name")
              or s.get("sessionName")
              or s.get("session_name")
              or ""
          )
          sessions.append({
              "sessionId": name.rsplit("/", 1)[-1] if "/" in name else name,
              "region": reg,
              "state": str(s.get("state") or "UNKNOWN"),
              "createTime": str(
                  s.get("createTime") or s.get("create_time") or ""
              ),
              "creator": str(s.get("creator") or ""),
          })
    except JobMonitorError as e:
      warnings.append(f"Serverless sessions ({reg}): {e}")

  return {
      "project": project,
      "region": region,
      "clusters": clusters,
      "sessions": sessions,
      "warnings": warnings,
  }


# ------------------------------------------------------------------------------
# Markdown Rendering
# ------------------------------------------------------------------------------


def render_bq_jobs_markdown(
    jobs: List[Dict[str, Any]],
    title: str,
    limit: int = 10,
    fell_back: bool = False,
) -> str:
  """Renders a Markdown table of BigQuery jobs."""
  lines = [f"### {title}"]
  if fell_back:
    lines.append(
        "> **Note**: Caller lacks project-wide `bigquery.jobs.listAll`"
        " permission; showing jobs for the current user (`allUsers=false`)."
    )
  if any(j.get("jobId") == "<REDACTED>" for j in jobs[:limit]):
    lines.append(
        "> **Note**: `<REDACTED>` entries are jobs run by other principals"
        " where the caller has project/reservation statistics visibility"
        " (`bigquery.jobs.list`) but not full SQL text visibility"
        " (`bigquery.jobs.listAll`)."
    )
  if not jobs:
    lines.append("\nNo matching BigQuery jobs found.")
    return "\n".join(lines)

  lines.append(
      "\n| Job ID | Region | User | State | Duration | Bytes Billed | Est."
      " Cost (On-Demand) | Slot Time | Statement / Query |"
  )
  lines.append(
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
  )
  for j in jobs[:limit]:
    raw_summary = j.get("query")
    if not raw_summary:
      if j.get("errorMessage"):
        raw_summary = f"ERROR ({j.get('errorReason')}): {j.get('errorMessage')}"
      elif j.get("state") == "FAILED" and j.get("errorReason"):
        raw_summary = f"ERROR: {j.get('errorReason')}"
      elif j.get("reservationId"):
        raw_summary = (
            f"{j.get('jobType')} [{j.get('edition') or 'RES'}:"
            f" {j.get('reservationId')}] (SQL redacted)"
        )
      else:
        raw_summary = j.get("jobType")
    q_preview = truncate_one_line(raw_summary, 70).replace("|", "\\|")
    cache_tag = " *(cached)*" if j.get("cacheHit") else ""
    lines.append(
        f"| `{j['jobId']}` | {j['location']} | {j['userEmail'] or 'n/a'} |"
        f" {j['state']} | {j['durationHuman']} |"
        f" {j['bytesBilledHuman']}{cache_tag} | {j['estimatedUsdHuman']} |"
        f" {j['slotTimeHuman']} | `{q_preview}` |"
    )
  return "\n".join(lines)


def render_bq_detail_markdown(j: Dict[str, Any]) -> str:
  """Renders detailed Markdown for a single BigQuery job."""
  lines = [
      f"### BigQuery Job Details: `{j['jobId']}`",
      f"- **Project / Location**: `{j['projectId']}` (`{j['location']}`)",
      f"- **User**: `{j['userEmail'] or 'n/a'}`",
      (
          f"- **State**: **{j['state']}** (Job Type: `{j['jobType']}`,"
          f" Statement: `{j['statementType'] or 'n/a'}`)"
      ),
      f"- **Created**: {j['creationTime']}",
      f"- **Wall-Clock Duration**: **{j['durationHuman']}**",
      (
          f"- **Bytes Billed**: **{j['bytesBilledHuman']}** (Processed:"
          f" {j['bytesProcessedHuman']}, Cache Hit: `{j['cacheHit']}`)"
      ),
      (
          "- **Estimated Cost (On-Demand @ $6.25/TiB)**:"
          f" **{j['estimatedUsdHuman']}**"
      ),
      f"- **Total Slot Time**: **{j['slotTimeHuman']}** ({j['slotMs']} ms)",
  ]
  if j.get("spilledBytes", 0) > 0:
    lines.append(
        f"- **Shuffle Spill to Disk**: {human_bytes(j['spilledBytes'])}"
    )
  if j.get("referencedTables"):
    refs = ", ".join(f"`{t}`" for t in j["referencedTables"][:10])
    lines.append(f"- **Referenced Tables**: {refs}")
  if j.get("errorMessage"):
    lines.append(f"- **Error (`{j.get('errorReason')}`)**: {j['errorMessage']}")
  if j.get("query"):
    lines.extend(["\n#### SQL Query", "```sql", j["query"], "```"])
  if j.get("stages"):
    lines.extend([
        "\n#### Execution Stages (`queryPlan`)",
        (
            "| Stage | Status | Records Read | Records Written | Slot Time |"
            " Max Wait | Max Compute | Spill |"
        ),
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for s in j["stages"]:
      lines.append(
          f"| `{s['name']}` | {s['status']} | {s['recordsRead']:,} |"
          f" {s['recordsWritten']:,} | {human_millis(s['slotMs'])} |"
          f" {human_millis(s['waitMsMax'])} |"
          f" {human_millis(s['computeMsMax'])} |"
          f" {human_bytes(s['shuffleOutputBytesSpilled'])} |"
      )
  return "\n".join(lines)


def render_spark_workloads_markdown(
    workloads: List[Dict[str, Any]],
    title: str,
    limit: int = 10,
    warnings: Optional[List[str]] = None,
) -> str:
  """Renders a Markdown table of Spark Serverless Batches and Cluster Jobs."""
  lines = [f"### {title}"]
  for w in warnings or []:
    lines.append(f"> **Warning**: {w}")
  if not workloads:
    lines.append("\nNo matching Spark jobs or batches found.")
    return "\n".join(lines)

  lines.append(
      "\n| ID | Kind | Type | Cluster / Runtime | State | Duration | Created |"
      " Creator | Main Script / Artifact |"
  )
  lines.append(
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
  )
  for w in workloads[:limit]:
    artifact = truncate_one_line(w.get("mainArtifact") or "n/a", 60).replace(
        "|", "\\|"
    )
    lines.append(
        f"| `{w['id']}` | {w['kind']} | {w['workloadType']} |"
        f" {w['clusterName']} | {w['state']} | {w['durationHuman']} |"
        f" {w['createTime']} | {w['creator'] or 'n/a'} | `{artifact}` |"
    )
  return "\n".join(lines)


def render_spark_detail_markdown(w: Dict[str, Any]) -> str:
  """Renders detailed Markdown for a single Spark Batch or Cluster Job."""
  lines = [
      f"### Spark Workload Details: `{w['id']}`",
      f"- **Kind / Type**: `{w['kind']}` (`{w['workloadType']}`)",
      f"- **Project / Region**: `{w['projectId']}` (`{w['region']}`)",
      f"- **Cluster / Runtime**: `{w['clusterName']}`",
      f"- **Creator**: `{w['creator'] or 'n/a'}`",
      f"- **State**: **{w['state']}**",
      f"- **Created**: {w['createTime']}",
      f"- **Elapsed Duration**: **{w['durationHuman']}**",
  ]
  if w.get("dcuHours", 0) > 0:
    lines.append(
        f"- **Approximate Serverless Usage**: {w['dcuHours']} DCU-hours"
        f" ({w['milliDcuSeconds']:,} milli-DCU-seconds)"
    )
  if w.get("mainArtifact"):
    lines.append(f"- **Main Script / JAR**: `{w['mainArtifact']}`")
  if w.get("driverOutputUri"):
    lines.append(f"- **Driver Output URI**: `{w['driverOutputUri']}`")
  if w.get("stateMessage"):
    lines.append(f"- **State / Error Message**: {w['stateMessage']}")
  return "\n".join(lines)


def render_bq_summary_markdown(
    summary: Dict[str, Any],
    project: str,
    fell_back: bool = False,
    limit: int = 10,
) -> str:
  """Renders a multi-section admin summary of BigQuery usage, reservations, and errors."""
  lines = [
      f"### BigQuery Admin Usage & Error Summary: `{project}`"
      f" ({summary['totalJobsAnalyzed']} jobs analyzed)"
  ]
  if fell_back:
    lines.append(
        "> **Note**: Caller lacks project-wide `bigquery.jobs.listAll`"
        " permission; summarizing jobs for the current user (`allUsers=false`)."
    )

  lines.extend([
      "\n#### 1. Cost & Slot Attribution by User",
      (
          "| User | Total Jobs | Succeeded | Failed | Running | Bytes Billed |"
          " Est. On-Demand Cost | Slot Time |"
      ),
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
  ])
  for u in summary["byUser"][:limit]:
    lines.append(
        f"| `{u['userEmail']}` | {u['totalJobs']} | {u['succeededJobs']} |"
        f" {u['failedJobs']} | {u['runningJobs']} | {u['bytesBilledHuman']} |"
        f" {u['estimatedOnDemandUsdHuman']} | {u['slotTimeHuman']} |"
    )

  lines.extend([
      "\n#### 2. Usage by Edition & Slot Reservation",
      (
          "| Edition | Reservation ID | Total Jobs | Succeeded | Failed | Bytes"
          " Billed | Slot Time |"
      ),
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
  ])
  for r in summary["byReservation"][:limit]:
    lines.append(
        f"| `{r['edition']}` | `{r['reservationId']}` | {r['totalJobs']} |"
        f" {r['succeededJobs']} | {r['failedJobs']} | {r['bytesBilledHuman']} |"
        f" {r['slotTimeHuman']} |"
    )

  lines.append("\n#### 3. Top Error Reasons (Failed Jobs)")
  if not summary["topErrors"]:
    lines.append("No failed jobs in the analyzed window.")
  else:
    lines.extend([
        (
            "| Error Reason | Failure Count | Sample Job ID | Sample Error"
            " Message |"
        ),
        "| :--- | :--- | :--- | :--- |",
    ])
    for e in summary["topErrors"][:limit]:
      msg = e["sampleMessage"].replace("|", "\\|")
      lines.append(
          f"| `{e['errorReason']}` | {e['count']} | `{e['sampleJobId']}` |"
          f" `{msg}` |"
      )
  return "\n".join(lines)


def render_bq_hot_tables_markdown(
    report: Dict[str, Any], project: str, limit: int = 10
) -> str:
  """Renders a Markdown table of the most-queried / highest-billed BigQuery tables."""
  lines = [
      f"### Most Queried / Highest-Cost BigQuery Tables in `{project}`"
      f" ({report['totalJobsAnalyzed']} jobs analyzed)"
  ]
  if report.get("redactedJobsWithoutTableRefs", 0) > 0:
    lines.append(
        f"> **Note**: {report['redactedJobsWithoutTableRefs']} `<REDACTED>`"
        " jobs from other principals did not expose `referencedTables`"
        " metadata."
    )
  hot = report.get("hotTables") or []
  if not hot:
    lines.append("\nNo referenced tables found in the analyzed jobs.")
    return "\n".join(lines)

  lines.extend([
      (
          "\n| Table (`project.dataset.table`) | Query Count | Distinct Users |"
          " Total Bytes Billed | Est. On-Demand Cost | Total Slot Time |"
      ),
      "| :--- | :--- | :--- | :--- | :--- | :--- |",
  ])
  for t in hot[:limit]:
    lines.append(
        f"| `{t['table']}` | {t['queryCount']} | {t['distinctUsers']} |"
        f" {t['totalBytesBilledHuman']} | {t['estimatedUsdHuman']} |"
        f" {t['totalSlotTimeHuman']} |"
    )
  return "\n".join(lines)


def render_bq_reservations_markdown(data: Dict[str, Any]) -> str:
  """Renders BigQuery slot reservations, capacity commitments, and assignments."""
  lines = [
      f"### BigQuery Slot Reservations & Capacity in `{data['project']}`"
      f" (`{data['location']}`)"
  ]
  for w in data.get("warnings") or []:
    lines.append(f"> **Warning**: {w}")

  lines.append("\n#### 1. Slot Reservations")
  if not data.get("reservations"):
    lines.append("No reservations configured in this location.")
  else:
    lines.extend([
        (
            "| Reservation | Edition | Baseline Slots | Autoscale Current |"
            " Autoscale Max | Ignore Idle Slots |"
        ),
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for r in data["reservations"]:
      lines.append(
          f"| `{r['name']}` | `{r['edition']}` | {r['baselineSlots']} |"
          f" {r['autoscaleCurrentSlots']} | {r['autoscaleMaxSlots']} |"
          f" `{r['ignoreIdleSlots']}` |"
      )

  lines.append("\n#### 2. Capacity Commitments")
  if not data.get("capacityCommitments"):
    lines.append("No capacity commitments in this location.")
  else:
    lines.extend([
        "| Commitment ID | Edition | Slots | Plan | State |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for c in data["capacityCommitments"]:
      lines.append(
          f"| `{c['name']}` | `{c['edition']}` | {c['slotCount']} |"
          f" `{c['plan']}` | {c['state']} |"
      )

  lines.append("\n#### 3. Reservation Assignments")
  if not data.get("assignments"):
    lines.append("No active reservation assignments in this location.")
  else:
    lines.extend([
        "| Assignment ID | Reservation | Assignee | Job Type | State |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for a in data["assignments"]:
      lines.append(
          f"| `{a['name']}` | `{a['reservation']}` | `{a['assignee']}` |"
          f" `{a['jobType']}` | {a['state']} |"
      )
  return "\n".join(lines)


def render_spark_fleet_markdown(data: Dict[str, Any]) -> str:
  """Renders active Dataproc Clusters and Serverless Interactive Sessions."""
  lines = [
      "### Dataproc Clusters & Interactive Spark Sessions in"
      f" `{data['project']}` (`{data['region']}`)"
  ]
  for w in data.get("warnings") or []:
    lines.append(f"> **Warning**: {w}")

  lines.append("\n#### 1. Dataproc Clusters")
  if not data.get("clusters"):
    lines.append("No Dataproc clusters found.")
  else:
    lines.extend([
        (
            "| Cluster Name | Region | State | Master Type | Workers | Worker"
            " Type | State Start Time |"
        ),
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for c in data["clusters"]:
      lines.append(
          f"| `{c['clusterName']}` | {c['region']} | {c['state']} |"
          f" `{c['masterMachineType']}` | {c['workerCount']} |"
          f" `{c['workerMachineType']}` | {c['stateStartTime']} |"
      )

  lines.append("\n#### 2. Dataproc Serverless Interactive Sessions")
  if not data.get("sessions"):
    lines.append("No Dataproc Serverless interactive sessions found.")
  else:
    lines.extend([
        "| Session ID | Region | State | Creator | Created |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for s in data["sessions"]:
      lines.append(
          f"| `{s['sessionId']}` | {s['region']} | {s['state']} |"
          f" `{s['creator'] or 'n/a'}` | {s['createTime']} |"
      )
  return "\n".join(lines)


# ------------------------------------------------------------------------------
# CLI Entrypoint
# ------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
      description=(
          "Monitor BigQuery and Spark (Dataproc) jobs, costs, durations, and"
          " job details."
      )
  )
  parser.add_argument(
      "--action",
      required=True,
      choices=(
          "bq_list",
          "bq_top_cost",
          "bq_slowest",
          "bq_describe",
          "bq_summary",
          "bq_hot_tables",
          "bq_reservations",
          "spark_list",
          "spark_slowest",
          "spark_describe",
          "spark_clusters",
      ),
      help="Monitoring action to execute.",
  )
  parser.add_argument(
      "--project",
      "--project_id",
      dest="project",
      help="GCP project ID (defaults to gcloud).",
  )
  parser.add_argument(
      "--region",
      default=DEFAULT_REGION,
      help=(
          "Region (or comma-separated regions) for Spark/Dataproc lookup"
          f" (default: {DEFAULT_REGION})."
      ),
  )
  parser.add_argument(
      "--location",
      help="Optional BigQuery job location (e.g., US, EU, us-central1).",
  )
  parser.add_argument(
      "--job_id",
      help="Job ID or Batch ID for bq_describe or spark_describe.",
  )
  parser.add_argument(
      "--workload_type",
      choices=("auto", "batch", "cluster_job"),
      default="auto",
      help="Spark workload type for spark_describe (default: auto).",
  )
  parser.add_argument(
      "--user",
      help="Filter jobs by user email substring.",
  )
  parser.add_argument(
      "--mine",
      action="store_true",
      help="Filter to jobs submitted by the active gcloud account.",
  )
  parser.add_argument(
      "--state",
      help="Optional state filter (e.g., DONE, FAILED, RUNNING, PENDING).",
  )
  parser.add_argument(
      "--days",
      type=float,
      help="Optional lookback window in days (e.g., 7 or 30).",
  )
  parser.add_argument(
      "--limit",
      type=int,
      default=10,
      help="Maximum number of rows to display (default: 10).",
  )
  parser.add_argument(
      "--format",
      choices=("markdown", "json"),
      default="markdown",
      help="Output format (default: markdown).",
  )
  parser.add_argument(
      "--transport",
      choices=("auto", "rest", "remote_cli"),
      default="auto",
      help=(
          "API transport: 'auto' (default, REST with automatic Sobi VMaaS"
          " remote_cli mcp fallback), 'rest', or 'remote_cli'."
      ),
  )
  return parser


def main(
    argv: Optional[Sequence[str]] = None,
    client: Optional[Any] = None,
) -> int:
  parser = build_parser()
  args = parser.parse_args(argv)
  if client is None:
    if args.transport == "remote_cli":
      client = RestClient(remote_cli_client=RemoteCliMcpClient())
    else:
      client = RestClient()

  try:
    project = resolve_default_project(args.project)
    user_filter = args.user
    if args.mine and not user_filter:
      user_filter = resolve_default_account()

    if args.action in ("bq_list", "bq_top_cost", "bq_slowest"):
      jobs, fell_back = fetch_bq_jobs(
          client,
          project=project,
          max_results=max(args.limit * 5, 100),
          all_users=not args.mine,
          user_filter=user_filter,
          days=args.days,
          state_filter=args.state,
      )
      if args.action == "bq_top_cost":
        jobs.sort(
            key=lambda j: (j.get("bytesBilled", 0), j.get("slotMs", 0)),
            reverse=True,
        )
        title = f"Top Most Expensive BigQuery Jobs in `{project}`"
      elif args.action == "bq_slowest":
        jobs.sort(key=lambda j: j.get("durationMs", 0), reverse=True)
        title = f"Slowest / Longest-Running BigQuery Jobs in `{project}`"
      else:
        jobs.sort(key=lambda j: j.get("creationTimeMs", 0), reverse=True)
        title = f"Recent BigQuery Jobs in `{project}`"

      sliced = jobs[: args.limit]
      if args.format == "json":
        print(
            json.dumps(
                {
                    "project": project,
                    "fellBackToOwnJobs": fell_back,
                    "jobs": sliced,
                },
                indent=2,
            )
        )
      else:
        print(
            render_bq_jobs_markdown(
                sliced, title=title, limit=args.limit, fell_back=fell_back
            )
        )
      return 0

    if args.action == "bq_describe":
      if not args.job_id:
        raise JobMonitorError("--job_id is required for --action=bq_describe.")
      detail = fetch_bq_job_detail(
          client, project=project, job_id=args.job_id, location=args.location
      )
      if args.format == "json":
        print(json.dumps(detail, indent=2))
      else:
        print(render_bq_detail_markdown(detail))
      return 0

    if args.action == "bq_summary":
      jobs, fell_back = fetch_bq_jobs(
          client,
          project=project,
          max_results=max(args.limit * 20, 200),
          all_users=not args.mine,
          user_filter=user_filter,
          days=args.days,
          state_filter=args.state,
      )
      summary = aggregate_bq_summary(jobs)
      if args.format == "json":
        print(
            json.dumps(
                {
                    "project": project,
                    "fellBackToOwnJobs": fell_back,
                    **summary,
                },
                indent=2,
            )
        )
      else:
        print(
            render_bq_summary_markdown(
                summary,
                project=project,
                fell_back=fell_back,
                limit=args.limit,
            )
        )
      return 0

    if args.action == "bq_hot_tables":
      jobs, fell_back = fetch_bq_jobs(
          client,
          project=project,
          max_results=max(args.limit * 20, 200),
          all_users=not args.mine,
          user_filter=user_filter,
          days=args.days,
          state_filter=args.state,
      )
      report = aggregate_bq_hot_tables(jobs)
      if args.format == "json":
        print(
            json.dumps(
                {"project": project, "fellBackToOwnJobs": fell_back, **report},
                indent=2,
            )
        )
      else:
        print(
            render_bq_hot_tables_markdown(
                report, project=project, limit=args.limit
            )
        )
      return 0

    if args.action == "bq_reservations":
      res_data = fetch_bq_reservations(
          client, project=project, location=args.location or "US"
      )
      if args.format == "json":
        print(json.dumps(res_data, indent=2))
      else:
        print(render_bq_reservations_markdown(res_data))
      return 0

    if args.action == "spark_clusters":
      fleet_data = fetch_spark_fleet(
          client, project=project, region=args.region
      )
      if args.format == "json":
        print(json.dumps(fleet_data, indent=2))
      else:
        print(render_spark_fleet_markdown(fleet_data))
      return 0

    if args.action in ("spark_list", "spark_slowest"):
      workloads, warnings = fetch_spark_workloads(
          client,
          project=project,
          region=args.region,
          max_results=max(args.limit * 3, 50),
          user_filter=user_filter,
          state_filter=args.state,
      )
      if args.action == "spark_slowest":
        workloads.sort(key=lambda w: w.get("durationMs", 0), reverse=True)
        title = f"Slowest Spark Workloads in `{project}` (`{args.region}`)"
      else:
        title = f"Recent Spark Workloads in `{project}` (`{args.region}`)"

      sliced = workloads[: args.limit]
      if args.format == "json":
        print(
            json.dumps(
                {
                    "project": project,
                    "region": args.region,
                    "warnings": warnings,
                    "workloads": sliced,
                },
                indent=2,
            )
        )
      else:
        print(
            render_spark_workloads_markdown(
                sliced, title=title, limit=args.limit, warnings=warnings
            )
        )
      return 0

    if args.action == "spark_describe":
      if not args.job_id:
        raise JobMonitorError(
            "--job_id is required for --action=spark_describe."
        )
      detail = fetch_spark_workload_detail(
          client,
          project=project,
          job_or_batch_id=args.job_id,
          region=args.region,
          workload_type=args.workload_type,
      )
      if args.format == "json":
        print(json.dumps(detail, indent=2))
      else:
        print(render_spark_detail_markdown(detail))
      return 0

  except JobMonitorError as e:
    if args.format == "json":
      print(json.dumps({"status": "ERROR", "errorMessage": str(e)}, indent=2))
    else:
      print(f"ERROR: {e}", file=sys.stderr)
    return 1

  return 0


if __name__ == "__main__":
  sys.exit(main())
