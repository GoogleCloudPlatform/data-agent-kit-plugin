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

"""Spark UI telemetry for Dataproc Serverless batches and sessions.

Dataproc exposes Spark UI data (jobs, stages, tasks, executors, SQL queries and
the Spark environment) through the public v1 REST resource
`projects.locations.{batches,sessions}.sparkApplications`. The data is served
by Dataproc itself, so no Persistent History Server and no `spark.eventLog.dir`
are needed. `gcloud` has no command for this resource, so this script calls the
REST API directly with a token minted by the Google Cloud CLI.

Written against the Python standard library only.

Verified server behavior that callers should know about:
  * `searchStageAttemptTasks` rejects both `sortRuntime` and `taskStatus`
    ("not supported yet"), so the `tasks` action sorts and filters locally.
  * int64 fields arrive as JSON strings and zero-valued fields are omitted
    (proto3 JSON). Responses are normalized so int64 fields become ints; an
    omitted numeric field means 0.
  * The `name` returned by `sparkApplications:search` is the application's
    display name, not a resource name. The application ID lives in
    `application.applicationId`.
"""

import argparse
import datetime
import functools
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENDPOINT = "https://dataproc.googleapis.com"
DEFAULT_REGION = "us-central1"
MAX_PAGE_SIZE = 100

_USER_AGENT = (
    "data-agent-kit/gcp-spark-troubleshooting"
    " (script:spark_application_telemetry)"
)
_HTTP_TIMEOUT_SECONDS = 60
_GCLOUD_TIMEOUT_SECONDS = 60
_RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 1.0
_TEXT_LIMIT = 600

# int64 fields that the REST API serializes as JSON strings, derived from the
# Dataproc v1 discovery document for every schema reachable from a
# sparkApplications response. None of these names is used for a string-typed
# field anywhere in those schemas, so converting by name is unambiguous.
_INT64_FIELDS = frozenset({
    "accumulatorId",
    "accumullableInfoId",
    "amount",
    "bytesRead",
    "bytesWritten",
    "corruptMergedBlockChunks",
    "count",
    "diskBytesSpilled",
    "diskUsed",
    "durationMillis",
    "executionId",
    "executorCpuTimeNanos",
    "executorDeserializeCpuTimeNanos",
    "executorDeserializeTimeMillis",
    "executorRunTimeMillis",
    "fetchWaitTimeMillis",
    "fromId",
    "gettingResultTimeMillis",
    "inputBytes",
    "inputRecords",
    "jobId",
    "jvmGcTimeMillis",
    "localBlocksFetched",
    "localBytesRead",
    "localMergedBlocksFetched",
    "localMergedBytesRead",
    "localMergedChunksFetched",
    "maxMemory",
    "maximum",
    "memoryBytesSpilled",
    "memoryUsed",
    "mergedFetchFallbackCount",
    "minimum",
    "outputBytes",
    "outputRecords",
    "peakExecutionMemoryBytes",
    "percentile25",
    "percentile50",
    "percentile75",
    "recordsRead",
    "recordsWritten",
    "remoteBlocksFetched",
    "remoteBytesRead",
    "remoteBytesReadToDisk",
    "remoteMergedBlocksFetched",
    "remoteMergedBytesRead",
    "remoteMergedChunksFetched",
    "remoteMergedReqsDuration",
    "remoteReqsDuration",
    "resultSerializationTimeMillis",
    "resultSize",
    "rootExecutionId",
    "schedulerDelayMillis",
    "shuffleRead",
    "shuffleReadRecords",
    "shuffleWrite",
    "shuffleWriteRecords",
    "sparkPlanGraphClusterId",
    "sparkPlanGraphNodeId",
    "sqlExecutionId",
    "stageId",
    "sum",
    "taskId",
    "taskTimeMillis",
    "toId",
    "totalDurationMillis",
    "totalGcTimeMillis",
    "totalInputBytes",
    "totalOffHeapStorageMemory",
    "totalOnHeapStorageMemory",
    "totalShuffleRead",
    "totalShuffleWrite",
    "usedOffHeapStorageMemory",
    "usedOnHeapStorageMemory",
    "writeTimeNanos",
})
# Repeated int64 fields and map<string, int64> fields.
_INT64_LIST_FIELDS = frozenset({
    "excludedInStages",
    "jobIds",
    "parentStageIds",
    "rddIds",
    "stageIds",
    "stages",
})
_INT64_MAP_FIELDS = frozenset({"locality", "metrics"})
_INT_STRING = re.compile(r"-?\d+\Z")

STAGE_STATUSES = ("ACTIVE", "COMPLETE", "FAILED", "PENDING", "SKIPPED")
TASK_STATUSES = ("RUNNING", "SUCCESS", "FAILED", "KILLED", "PENDING")
JOB_STATUSES = ("RUNNING", "SUCCEEDED", "FAILED", "UNKNOWN")
EXECUTOR_STATUSES = ("ACTIVE", "DEAD")


class DataprocApiError(RuntimeError):
  """A Dataproc REST call failed.

  Attributes:
    status: HTTP status code, or 0 when no HTTP response was received.
    reason: The `google.rpc.ErrorInfo` reason, when the server sent one.
  """

  def __init__(self, message: str, status: int = 0, reason: str = ""):
    super().__init__(message)
    self.status = status
    self.reason = reason


# ------------------------------------------------------------------------------
# Normalization helpers
# ------------------------------------------------------------------------------


def _snake_to_camel(name: str) -> str:
  head, *rest = name.split("_")
  return head + "".join(word.capitalize() for word in rest)


def _to_int(value: Any) -> Any:
  if isinstance(value, str) and _INT_STRING.match(value):
    return int(value)
  return value


def normalize_int64(value: Any, field_name: Optional[str] = None) -> Any:
  """Returns a copy of an API payload with int64 strings converted to ints.

  Accepts both camelCase (REST) and snake_case (proto / gcloud) field names.
  Only fields that are int64 in the Dataproc schema are converted, so string
  fields that merely look numeric (executor IDs, for example) are untouched.

  Args:
    value: A decoded JSON value.
    field_name: The name of the field holding `value`, if any.

  Returns:
    The normalized value.
  """
  camel = _snake_to_camel(field_name) if field_name else None
  if isinstance(value, dict):
    if camel in _INT64_MAP_FIELDS:
      return {
          k: normalize_int64(v) if isinstance(v, (dict, list)) else _to_int(v)
          for k, v in value.items()
      }
    return {k: normalize_int64(v, k) for k, v in value.items()}
  if isinstance(value, list):
    if camel in _INT64_LIST_FIELDS:
      return [
          normalize_int64(v) if isinstance(v, (dict, list)) else _to_int(v)
          for v in value
      ]
    return [normalize_int64(v) for v in value]
  if camel in _INT64_FIELDS:
    return _to_int(value)
  return value


def field(data: Any, *path: str, default: Any = 0) -> Any:
  """Reads a nested field, accepting snake_case or camelCase at each step.

  Proto3 JSON omits zero values, so an absent numeric field reads as
  `default` (0 unless overridden).

  Args:
    data: The mapping to read from.
    *path: Field names, outermost first, in snake_case.
    default: Returned when any step is absent.

  Returns:
    The field value, or `default`.
  """
  for name in path:
    if not isinstance(data, dict):
      return default
    if name in data:
      data = data[name]
    else:
      camel = _snake_to_camel(name)
      if camel not in data:
        return default
      data = data[camel]
  return data


def parse_timestamp(value: Any) -> Optional[datetime.datetime]:
  """Parses an RFC 3339 timestamp; epoch-or-earlier placeholders mean unset."""
  if not isinstance(value, str) or not value:
    return None
  match = re.fullmatch(
      r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})?",
      value,
  )
  if not match:
    return None
  base, fraction, zone = match.groups()
  micros = int((fraction or "0")[:6].ljust(6, "0"))
  offset = "+00:00" if zone in (None, "Z") else zone
  try:
    parsed = datetime.datetime.fromisoformat(base + offset).replace(
        microsecond=micros
    )
  except ValueError:
    return None
  if parsed.timestamp() <= 0:
    return None
  return parsed


def duration_millis(start: Any, end: Any) -> Optional[int]:
  begin, finish = parse_timestamp(start), parse_timestamp(end)
  if begin is None or finish is None:
    return None
  return int((finish - begin).total_seconds() * 1000)


def human_bytes(num: Any) -> str:
  """Formats a byte count; negative (unavailable) values render as n/a."""
  try:
    value = float(num or 0)
  except (TypeError, ValueError):
    return str(num)
  if value < 0:
    # Spark reports -1 when a metric is unavailable (e.g. a failed task).
    return "n/a"
  for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
    if value < 1024 or unit == "TiB":
      return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
    value /= 1024
  return f"{value:.1f} TiB"


def human_millis(ms: Any) -> str:
  """Formats milliseconds; None or negative (unavailable) render as n/a."""
  if ms is None:
    return "n/a"
  try:
    value = float(ms)
  except (TypeError, ValueError):
    return str(ms)
  if value < 0:
    return "n/a"
  if value < 1000:
    return f"{value:.0f} ms"
  if value < 60_000:
    return f"{value / 1000:.1f} s"
  return f"{value / 60_000:.1f} min"


def truncate(text: Any, limit: int = _TEXT_LIMIT) -> str:
  text = str(text or "")
  return text if len(text) <= limit else text[:limit] + " ...[truncated]"


_FRAMEWORK_FRAME = re.compile(
    r"at (org\.apache\.(spark|hadoop)|scala\.|java\.|javax\.|jdk\.|sun\."
    r"|py4j\.|com\.google\.cloud\.hadoop)"
)
_PYTHON_EXCEPTION = re.compile(r"[A-Za-z_][\w.]*(Error|Exception|Exit)\b")


def summarize_error(text: Any, limit: int = _TEXT_LIMIT) -> str:
  """Condenses a stack trace to the lines that identify the root cause.

  Keeps the headline, the first frame of user code (JVM traces), the innermost
  `Caused by:` and, for Python tracebacks, the last user `File` frame and the
  final exception line.

  Args:
    text: A failure reason or task error message.
    limit: Maximum length of the result.

  Returns:
    A single-line summary joined with " | ".
  """
  lines = [line.strip() for line in str(text or "").splitlines()]
  lines = [line for line in lines if line]
  if not lines:
    return ""
  picked = [lines[0]]
  rest = lines[1:]
  user_frame = next(
      (
          line
          for line in rest
          if line.startswith("at ") and not _FRAMEWORK_FRAME.match(line)
      ),
      None,
  )
  causes = [line for line in rest if line.startswith("Caused by:")]
  py_frames = [
      line
      for line in rest
      if line.startswith('File "')
      and "/pyspark/" not in line
      and "py4j" not in line
  ]
  py_exceptions = [line for line in rest if _PYTHON_EXCEPTION.match(line)]
  for candidate in (
      user_frame,
      causes[-1] if causes else None,
      py_frames[-1] if py_frames else None,
      py_exceptions[-1] if py_exceptions else None,
  ):
    if candidate and candidate not in picked:
      picked.append(candidate)
  return truncate(" | ".join(picked), limit)


# ------------------------------------------------------------------------------
# Authentication and transport
# ------------------------------------------------------------------------------


class GcloudTokenProvider:
  """Mints OAuth access tokens with the Google Cloud CLI.

  Tries the active gcloud account first and falls back to Application Default
  Credentials. The fallback matters in environments that enforce context-aware
  access: there the gcloud user token is certificate-bound and the API rejects
  it on a plain HTTPS call with ACCESS_TOKEN_TYPE_UNSUPPORTED.
  """

  _COMMANDS = (
      ("auth", "print-access-token"),
      ("auth", "application-default", "print-access-token"),
  )

  def __init__(self):
    self._index = 0
    self._token: Optional[str] = None
    self._errors: List[str] = []

  def token(self) -> str:
    """Returns a cached token, minting one from the current source if needed."""
    while self._token is None:
      try:
        self._token = _fetch_gcloud_token(self._COMMANDS[self._index])
      except DataprocApiError as e:
        self._errors.append(str(e))
        if not self.fallback():
          raise DataprocApiError(
              "Could not obtain a Google Cloud access token. "
              + " | ".join(self._errors)
              + " Run 'gcloud auth login' (or 'gcloud auth application-default"
              " login')."
          ) from e
    return self._token

  def fallback(self) -> bool:
    """Switches to the next credential source; False when none is left."""
    if self._index + 1 >= len(self._COMMANDS):
      return False
    self._index += 1
    self._token = None
    return True


def _fetch_gcloud_token(args: Tuple[str, ...]) -> str:
  """Runs one `gcloud` token command and returns its output."""
  gcloud = shutil.which("gcloud")
  if not gcloud:
    raise DataprocApiError(
        "The Google Cloud CLI ('gcloud') is not installed or not on PATH."
    )
  command = [gcloud, *args]
  try:
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=_GCLOUD_TIMEOUT_SECONDS,
        # Never block on an interactive reauthentication prompt.
        stdin=subprocess.DEVNULL,
    )
  except (OSError, subprocess.SubprocessError) as e:
    raise DataprocApiError(f"'gcloud {' '.join(args)}' failed: {e}") from e
  token = (proc.stdout or "").strip()
  if proc.returncode != 0 or not token:
    detail = (proc.stderr or "").strip().splitlines()
    raise DataprocApiError(
        f"'gcloud {' '.join(args)}' failed: "
        + (detail[-1] if detail else f"exit code {proc.returncode}")
    )
  return token


# CA bundles maintained by the operating system, in lookup order.
_SYSTEM_CA_BUNDLES = (
    "/etc/ssl/cert.pem",  # macOS, Alpine, BSDs
    "/etc/ssl/certs/ca-certificates.crt",  # Debian, Ubuntu, Arch
    "/etc/pki/tls/certs/ca-bundle.crt",  # Fedora, RHEL, CentOS
    "/etc/ssl/ca-bundle.pem",  # openSUSE
)
_CERTIFICATE_HINT = (
    " If a proxy on your network inspects TLS traffic, set SSL_CERT_FILE to a"
    " CA bundle that includes its root certificate (for example the file set"
    " as gcloud's core/custom_ca_certs_file)."
)


@functools.lru_cache(maxsize=None)
def ssl_context() -> ssl.SSLContext:
  """Returns a certificate-verifying TLS context that needs no extra packages.

  `ssl.create_default_context()` trusts the CA certificates that Python's
  OpenSSL build is configured to read. The python.org installer for macOS
  ships an OpenSSL whose trust store stays empty until the user runs its
  "Install Certificates.command" (which pip-installs certifi), so every HTTPS
  call fails with CERTIFICATE_VERIFY_FAILED while `gcloud`, which carries its
  own CA bundle, keeps working. When the default trust store is empty and
  SSL_CERT_FILE / SSL_CERT_DIR are unset, this loads the operating system's
  CA bundle, or failing that the one shipped inside the Google Cloud CLI.
  Certificate and hostname verification are never disabled.
  """
  context = ssl.create_default_context()
  if context.cert_store_stats()["x509_ca"] or any(
      os.environ.get(name) for name in ("SSL_CERT_FILE", "SSL_CERT_DIR")
  ):
    return context
  for bundle in (*_SYSTEM_CA_BUNDLES, _gcloud_ca_bundle()):
    if not bundle or not os.path.isfile(bundle):
      continue
    try:
      context.load_verify_locations(cafile=bundle)
    except OSError:  # Includes ssl.SSLError for a file without certificates.
      continue
    break
  return context


def _gcloud_ca_bundle() -> Optional[str]:
  """Returns the CA bundle inside the Google Cloud CLI installation, if any."""
  gcloud = shutil.which("gcloud")
  if not gcloud:
    return None
  sdk_root = os.path.dirname(os.path.dirname(os.path.realpath(gcloud)))
  return os.path.join(sdk_root, "lib", "third_party", "certifi", "cacert.pem")


def _certificate_error(
    error: BaseException,
) -> Optional[ssl.SSLCertVerificationError]:
  """Returns the failed TLS certificate check behind a transport error."""
  if isinstance(error, urllib.error.URLError):
    error = error.reason
  return error if isinstance(error, ssl.SSLCertVerificationError) else None


Transport = Callable[[urllib.request.Request, float], Tuple[int, bytes]]


def _urllib_transport(
    request: urllib.request.Request, timeout: float
) -> Tuple[int, bytes]:
  try:
    with urllib.request.urlopen(
        request, timeout=timeout, context=ssl_context()
    ) as resp:
      return resp.status, resp.read()
  except urllib.error.HTTPError as e:
    return e.code, e.read()


_DEBUG_CAUSE = re.compile(r"(?:Exception|Error): ([^;]+)")
_STATUS_SUFFIX = re.compile(r"(\s*\([A-Z_]+\))+\s*$")


def _backend_cause(debug: str) -> str:
  """Extracts the innermost rejection from a DebugInfo detail string.

  INTERNAL responses wrap the real backend error, e.g. "...RpcClientException:
  <eye3 ...> APPLICATION_ERROR;...;BadRequestException: Filtering by task
  status is not supported yet.;AppErrorCode=3;...". Only the first line is
  considered (the rest is a suppressed-exception trailer) and the last
  exception segment wins.

  Args:
    debug: The `detail` field of a google.rpc.DebugInfo.

  Returns:
    The cause without status suffixes, or "" if none was found.
  """
  causes = _DEBUG_CAUSE.findall(debug.split("\n", 1)[0])
  if not causes:
    return ""
  cause = causes[-1].split(" [google.rpc", 1)[0]
  return _STATUS_SUFFIX.sub("", cause).strip()


def _describe_error(status: int, body: bytes) -> Tuple[str, str]:
  """Extracts a readable message and ErrorInfo reason from an error body."""
  try:
    error = json.loads(body.decode("utf-8", "replace")).get("error", {})
  except (ValueError, AttributeError):
    return truncate(body.decode("utf-8", "replace"), 300), ""
  message = error.get("message") or f"HTTP {status}"
  reason = ""
  for detail in error.get("details") or []:
    if not isinstance(detail, dict):
      continue
    reason = reason or detail.get("reason", "")
    debug = detail.get("detail")
    # INTERNAL responses can wrap a precise backend rejection; surface it.
    if isinstance(debug, str) and "Exception:" in debug:
      cause = _backend_cause(debug)
      if cause and cause not in message:
        message = f"{message} ({cause})"
  return message, reason


def _hint(status: int, reason: str, message: str = "") -> str:
  """Returns remediation advice for a failed call, or ""."""
  if status == 401:
    if reason == "ACCESS_TOKEN_TYPE_UNSUPPORTED":
      return (
          " The token is bound to a client certificate (context-aware access)."
          " Run 'gcloud auth application-default login' and retry."
      )
    return " Run 'gcloud auth login' and retry."
  if status == 403:
    return (
        " Check that the caller can read Dataproc batches/sessions in this"
        " project (for example roles/dataproc.viewer) and that the Dataproc"
        " API is enabled."
    )
  if status == 404:
    return (
        " Check the project, region and batch/session ID. Spark UI data only"
        " exists once the Spark driver has started."
    )
  if status == 500 and "not found" in message.lower():
    return (
        " The requested stage, attempt or task does not exist; list them with"
        " --action=stages."
    )
  return ""


class SparkApplicationsClient:
  """Minimal client for `{batches,sessions}.sparkApplications` methods."""

  def __init__(
      self,
      project: str,
      region: str,
      batch_id: Optional[str] = None,
      session_id: Optional[str] = None,
      endpoint: str = DEFAULT_ENDPOINT,
      token_provider: Optional[GcloudTokenProvider] = None,
      transport: Optional[Transport] = None,
      sleep: Callable[[float], None] = time.sleep,
  ):
    if bool(batch_id) == bool(session_id):
      raise ValueError("Specify exactly one of batch_id or session_id.")
    kind, workload = (
        ("batches", batch_id) if batch_id else ("sessions", session_id)
    )
    self.parent = f"projects/{project}/locations/{region}/{kind}/{workload}"
    self.workload_id = workload
    self._endpoint = endpoint.rstrip("/")
    self._tokens = token_provider or GcloudTokenProvider()
    self._transport = transport or _urllib_transport
    self._sleep = sleep

  def app_name(self, app_id: str) -> str:
    return f"{self.parent}/sparkApplications/{app_id}"

  def call(
      self,
      method: str,
      app_id: Optional[str] = None,
      params: Optional[Dict[str, Any]] = None,
  ) -> Dict[str, Any]:
    """Calls one sparkApplications method and returns the normalized JSON.

    Args:
      method: The REST method, e.g. "searchStages". "search" lists the
        applications of the batch or session.
      app_id: The Spark application ID; required for every method except
        "search".
      params: Query parameters. `parent` is added automatically.

    Returns:
      The decoded, int64-normalized response.

    Raises:
      DataprocApiError: On any transport, authentication or API failure.
    """
    query: Dict[str, Any] = {}
    if method == "search":
      path = f"{self.parent}/sparkApplications:search"
    else:
      if not app_id:
        raise ValueError(f"{method} requires a Spark application ID.")
      path = f"{self.app_name(app_id)}:{method}"
      query["parent"] = self.parent
    for key, value in (params or {}).items():
      if value is None or (isinstance(value, str) and not value):
        continue
      query[key] = str(value).lower() if isinstance(value, bool) else value
    url = f"{self._endpoint}/v1/{path}?{urllib.parse.urlencode(query)}"

    refreshed = False
    attempt = 0
    while True:
      attempt += 1
      request = urllib.request.Request(
          url,
          headers={
              "Authorization": f"Bearer {self._tokens.token()}",
              "Accept": "application/json",
              "User-Agent": _USER_AGENT,
          },
      )
      try:
        status, body = self._transport(request, _HTTP_TIMEOUT_SECONDS)
      except (urllib.error.URLError, OSError) as e:
        certificate_error = _certificate_error(e)
        if certificate_error is not None:
          # Retrying cannot fix an untrusted certificate chain.
          raise DataprocApiError(
              f"{method}: TLS certificate verification failed:"
              f" {certificate_error}."
              + _CERTIFICATE_HINT
          ) from e
        if attempt < _MAX_ATTEMPTS:
          self._sleep(_BACKOFF_SECONDS * attempt)
          continue
        raise DataprocApiError(f"{method}: network error: {e}") from e

      if 200 <= status < 300:
        try:
          return normalize_int64(json.loads(body.decode("utf-8") or "{}"))
        except ValueError as e:
          raise DataprocApiError(
              f"{method}: response was not valid JSON: {e}", status
          ) from e

      message, reason = _describe_error(status, body)
      if status == 401 and not refreshed and self._tokens.fallback():
        refreshed = True
        continue
      if status in _RETRYABLE_STATUS and attempt < _MAX_ATTEMPTS:
        self._sleep(_BACKOFF_SECONDS * attempt)
        continue
      raise DataprocApiError(
          f"{method} failed with HTTP {status}"
          + (f" [{reason}]" if reason else "")
          + f": {message.rstrip('.')}."
          + _hint(status, reason, message),
          status,
          reason,
      )

  def paginate(
      self,
      method: str,
      items_key: str,
      app_id: Optional[str] = None,
      params: Optional[Dict[str, Any]] = None,
      max_items: Optional[int] = None,
  ) -> List[Dict[str, Any]]:
    """Follows `nextPageToken` and returns the concatenated items."""
    query = dict(params or {})
    query.setdefault("pageSize", MAX_PAGE_SIZE)
    items: List[Dict[str, Any]] = []
    while True:
      response = self.call(method, app_id, query)
      items.extend(response.get(items_key) or [])
      token = response.get("nextPageToken")
      if not token or (max_items is not None and len(items) >= max_items):
        break
      query["pageToken"] = token
    return items if max_items is None else items[:max_items]

  def search_applications(self) -> List[Dict[str, Any]]:
    return self.paginate("search", "sparkApplications", params={"pageSize": 10})

  def resolve_application(
      self, app_id: Optional[str] = None
  ) -> Tuple[str, Dict[str, Any], int]:
    """Finds the Spark application to inspect.

    Mirrors the Dataproc agent: take `application.applicationId` of the first
    application, falling back to the trailing segment of `name`.

    Args:
      app_id: An explicit application ID; skips the lookup when given.

    Returns:
      (application ID, ApplicationInfo dict, number of applications found).

    Raises:
      DataprocApiError: If the workload has no Spark application yet.
    """
    if app_id:
      return app_id, {}, 1
    apps = self.search_applications()
    if not apps:
      raise DataprocApiError(
          f"No Spark application found for {self.parent}. The workload may"
          " still be pending, or it failed before the Spark driver started"
          " (check the batch stateMessage and driver logs instead).",
          404,
      )
    info = apps[0].get("application") or {}
    resolved = info.get("applicationId") or ""
    if not resolved:
      raw = apps[0].get("name") or ""
      resolved = raw.rsplit("/", 1)[-1] if "/sparkApplications/" in raw else raw
    return resolved, info, len(apps)


# ------------------------------------------------------------------------------
# Derived views
# ------------------------------------------------------------------------------


def health_indicators(executors_summary: Dict[str, Any]) -> Dict[str, float]:
  """Executor-level ratios, as computed by the Data Agent Kit MCP server.

  Only the measured percentages are returned. What counts as unhealthy is left
  to the caller.

  Args:
    executors_summary: A SummarizeSparkApplicationExecutorsResponse.

  Returns:
    GC overhead, dead-executor share and storage-memory saturation, in percent.
  """
  total = executors_summary.get("totalExecutorSummary") or {}
  dead = executors_summary.get("deadExecutorSummary") or {}
  active = executors_summary.get("activeExecutorSummary") or {}

  def pct(numerator: Any, denominator: Any) -> float:
    try:
      denominator = float(denominator or 0)
      return (
          round(100.0 * float(numerator or 0) / denominator, 2)
          if (denominator)
          else 0.0
      )
    except (TypeError, ValueError):
      return 0.0

  return {
      "gcOverheadPercentage": pct(
          total.get("totalGcTimeMillis"), total.get("totalDurationMillis")
      ),
      "executorMortalityRate": pct(dead.get("count"), total.get("count")),
      "memorySaturationPercentage": pct(
          active.get("memoryUsed"), active.get("maxMemory")
      ),
  }


def stage_row(stage: Dict[str, Any]) -> Dict[str, Any]:
  """Flattens a StageData into the fields worth showing an operator."""
  metrics = field(stage, "stage_metrics", default={})
  row = {
      "stageId": field(stage, "stage_id"),
      "attempt": field(stage, "stage_attempt_id"),
      "status": (
          str(field(stage, "status", default="")).replace("STAGE_STATUS_", "")
      ),
      "name": truncate(field(stage, "name", default=""), 80),
      "numTasks": field(stage, "num_tasks"),
      "numFailedTasks": field(stage, "num_failed_tasks"),
      "numKilledTasks": field(stage, "num_killed_tasks"),
      "durationMillis": duration_millis(
          field(stage, "submission_time", default=None),
          field(stage, "completion_time", default=None),
      ),
      "executorRunTimeMillis": field(metrics, "executor_run_time_millis"),
      "jvmGcTimeMillis": field(metrics, "jvm_gc_time_millis"),
      "inputBytes": field(metrics, "stage_input_metrics", "bytes_read"),
      "outputBytes": field(metrics, "stage_output_metrics", "bytes_written"),
      "shuffleReadBytes": field(
          metrics, "stage_shuffle_read_metrics", "bytes_read"
      ),
      "shuffleWriteBytes": field(
          metrics, "stage_shuffle_write_metrics", "bytes_written"
      ),
      "memoryBytesSpilled": field(metrics, "memory_bytes_spilled"),
      "diskBytesSpilled": field(metrics, "disk_bytes_spilled"),
  }
  reason = field(stage, "failure_reason", default="")
  if reason:
    row["failureReason"] = summarize_error(reason)
  return row


# ------------------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------------------


def _print_json(payload: Any) -> None:
  print(json.dumps(payload, indent=2, sort_keys=False))


def action_applications(client: SparkApplicationsClient, args) -> None:
  """Lists the Spark applications of the workload."""
  apps = client.search_applications()
  if args.format == "json":
    _print_json(apps)
    return
  print(f"# Spark applications for `{client.parent}`\n")
  if not apps:
    print(
        "No Spark application found. The workload may still be pending, or"
        " it failed before the Spark driver started."
    )
    return
  for app in apps:
    info = app.get("application") or {}
    print(
        f"- **{info.get('applicationId', app.get('name'))}**"
        f" (`{info.get('name', '')}`)"
    )
    for attempt in info.get("attempts") or []:
      print(
          f"  - Spark {attempt.get('appSparkVersion', '?')}, started"
          f" {attempt.get('startTime', '?')}, duration"
          f" {human_millis(attempt.get('durationMillis'))}, completed:"
          f" {bool(attempt.get('completed'))}"
      )
    print(
        "  - Context ingestion:"
        f" `{info.get('applicationContextIngestionStatus', 'UNSPECIFIED')}`,"
        f" quantile data: `{info.get('quantileDataStatus', 'UNSPECIFIED')}`"
    )


def _summaries(client, app_id) -> Dict[str, Any]:
  return {
      "jobs": client.call("summarizeJobs", app_id).get("jobsSummary") or {},
      "stages": (
          client.call("summarizeStages", app_id).get("stagesSummary") or {}
      ),
      "executors": client.call("summarizeExecutors", app_id),
  }


def action_summary(client: SparkApplicationsClient, args) -> None:
  """Prints job/stage/executor totals, health ratios and failed stages."""
  app_id, info, count = client.resolve_application(args.application_id)
  summaries = _summaries(client, app_id)
  indicators = health_indicators(summaries["executors"])
  failed_stages: List[Dict[str, Any]] = []
  if field(summaries["stages"], "num_failed_stages"):
    failed_stages = client.paginate(
        "searchStages",
        "sparkApplicationStages",
        app_id,
        {"stageStatus": "STAGE_STATUS_FAILED"},
        max_items=args.limit,
    )
  if args.format == "json":
    _print_json({
        "applicationId": app_id,
        "application": info,
        **summaries,
        "healthIndicators": indicators,
        "failedStages": failed_stages,
    })
    return

  jobs, stages = summaries["jobs"], summaries["stages"]
  total = summaries["executors"].get("totalExecutorSummary") or {}
  dead = summaries["executors"].get("deadExecutorSummary") or {}
  print(f"# Spark application summary: `{app_id}`\n")
  if count > 1:
    print(
        f"> {count} applications found; showing the first. Pass"
        " --application_id to pick another.\n"
    )
  if info.get("quantileDataStatus") not in (
      None,
      "QUANTILE_DATA_STATUS_COMPLETED",
  ):
    print(
        f"> Quantile data status is `{info.get('quantileDataStatus')}`;"
        " task quantile metrics may be incomplete.\n"
    )
  print("## Jobs")
  print(
      f"- Completed: {field(jobs, 'completed_jobs')}, failed:"
      f" {field(jobs, 'failed_jobs')}, active: {field(jobs, 'active_jobs')}"
  )
  print("## Stages")
  print(
      f"- Completed: {field(stages, 'num_completed_stages')}, failed:"
      f" {field(stages, 'num_failed_stages')}, active:"
      f" {field(stages, 'num_active_stages')}, pending:"
      f" {field(stages, 'num_pending_stages')}, skipped:"
      f" {field(stages, 'num_skipped_stages')}"
  )
  print("## Executors")
  print(
      f"- Executors: {field(total, 'count')} total, {field(dead, 'count')}"
      f" dead; cores: {field(total, 'total_cores')}"
  )
  print(
      f"- Tasks: {field(total, 'total_tasks')} total,"
      f" {field(total, 'completed_tasks')} completed,"
      f" {field(total, 'failed_tasks')} failed,"
      f" {field(total, 'active_tasks')} active"
  )
  print(
      f"- Task time: {human_millis(field(total, 'total_duration_millis'))},"
      f" GC: {human_millis(field(total, 'total_gc_time_millis'))}"
      f" ({indicators['gcOverheadPercentage']}%)"
  )
  print(
      f"- Input: {human_bytes(field(total, 'total_input_bytes'))}, shuffle"
      f" read: {human_bytes(field(total, 'total_shuffle_read'))}, shuffle"
      f" write: {human_bytes(field(total, 'total_shuffle_write'))}"
  )
  print(
      f"- Dead-executor share: {indicators['executorMortalityRate']}%, storage"
      f" memory used: {indicators['memorySaturationPercentage']}%"
  )
  if failed_stages:
    print(f"\n## Failed stages ({len(failed_stages)})")
    for stage in failed_stages:
      row = stage_row(stage)
      print(
          f"- **Stage {row['stageId']}.{row['attempt']}** `{row['name']}`:"
          f" {row['numFailedTasks']}/{row['numTasks']} tasks failed"
      )
      if row.get("failureReason"):
        print(f"  - Failure reason: `{row['failureReason']}`")
  if not any(
      field(stages, name)
      for name in (
          "num_completed_stages",
          "num_failed_stages",
          "num_active_stages",
          "num_pending_stages",
          "num_skipped_stages",
      )
  ):
    print(
        "\n> No stage ever ran. The application most likely failed before"
        " its first Spark action (argument parsing, imports, reading"
        " configuration); the root cause is in the driver log, not in"
        " Spark UI telemetry."
    )


def action_stages(client: SparkApplicationsClient, args) -> None:
  """Prints one row per stage."""
  app_id, _, _ = client.resolve_application(args.application_id)
  params: Dict[str, Any] = {}
  if args.stage_status:
    params["stageStatus"] = f"STAGE_STATUS_{args.stage_status}"
  if args.quantiles:
    params["summaryMetricsMask"] = "task_quantile_metrics"
  stages = client.paginate(
      "searchStages",
      "sparkApplicationStages",
      app_id,
      params,
      max_items=args.limit,
  )
  if args.format == "json":
    _print_json(stages)
    return
  rows = [stage_row(s) for s in stages]
  if args.sort == "duration":
    rows.sort(key=lambda r: r["durationMillis"] or 0, reverse=True)
  elif args.sort == "run_time":
    rows.sort(key=lambda r: r["executorRunTimeMillis"] or 0, reverse=True)
  print(f"# Stages of `{app_id}` ({len(rows)} shown)\n")
  if not rows:
    print("No stages matched.")
    return
  print(
      "| Stage | Status | Tasks (failed/killed) | Duration | GC / run |"
      " Input | Shuffle R/W | Spill mem/disk | Name |"
  )
  print("|---|---|---|---|---|---|---|---|---|")
  for r in rows:
    print(
        f"| {r['stageId']}.{r['attempt']} | {r['status']} |"
        f" {r['numTasks']} ({r['numFailedTasks']}/{r['numKilledTasks']}) |"
        f" {human_millis(r['durationMillis'])} |"
        f" {human_millis(r['jvmGcTimeMillis'])} /"
        f" {human_millis(r['executorRunTimeMillis'])} |"
        f" {human_bytes(r['inputBytes'])} |"
        f" {human_bytes(r['shuffleReadBytes'])} /"
        f" {human_bytes(r['shuffleWriteBytes'])} |"
        f" {human_bytes(r['memoryBytesSpilled'])} /"
        f" {human_bytes(r['diskBytesSpilled'])} | {r['name']} |"
    )
  for r in rows:
    if r.get("failureReason"):
      print(
          f"\n**Stage {r['stageId']}.{r['attempt']} failure reason:**"
          f" `{r['failureReason']}`"
      )


_QUANTILE_ROWS = (
    ("Task duration", ("duration_millis",), human_millis),
    ("Executor run time", ("executor_run_time_millis",), human_millis),
    ("GC time", ("jvm_gc_time_millis",), human_millis),
    ("Scheduler delay", ("scheduler_delay_millis",), human_millis),
    ("Input bytes", ("input_metrics", "bytes_read"), human_bytes),
    ("Output bytes", ("output_metrics", "bytes_written"), human_bytes),
    ("Shuffle read bytes", ("shuffle_read_metrics", "read_bytes"), human_bytes),
    (
        "Shuffle write bytes",
        ("shuffle_write_metrics", "write_bytes"),
        human_bytes,
    ),
    ("Memory spilled", ("memory_bytes_spilled",), human_bytes),
    ("Disk spilled", ("disk_bytes_spilled",), human_bytes),
    ("Peak execution memory", ("peak_execution_memory_bytes",), human_bytes),
)


def action_stage(client: SparkApplicationsClient, args) -> None:
  """Prints one stage attempt with its task-quantile table."""
  if args.stage_id is None:
    raise ValueError("--stage_id is required for --action=stage")
  app_id, _, _ = client.resolve_application(args.application_id)
  response = client.call(
      "accessStageAttempt",
      app_id,
      {
          "stageId": args.stage_id,
          "stageAttemptId": args.stage_attempt_id,
          "summaryMetricsMask": "task_quantile_metrics",
      },
  )
  stage = response.get("stageData") or {}
  if args.format == "json":
    _print_json(stage)
    return
  row = stage_row(stage)
  print(f"# Stage {row['stageId']}.{row['attempt']} of `{app_id}`\n")
  print(f"- Name: `{row['name']}`")
  print(
      f"- Status: {row['status']}; tasks: {row['numTasks']} total,"
      f" {row['numFailedTasks']} failed, {row['numKilledTasks']} killed"
  )
  print(f"- Duration: {human_millis(row['durationMillis'])}")
  if row.get("failureReason"):
    print(f"- Failure reason: `{row['failureReason']}`")
  quantiles = field(stage, "task_quantile_metrics", default={})
  if not quantiles:
    print("\nNo task quantile metrics were returned for this stage.")
    return
  print("\n## Task quantiles\n")
  print("| Metric | Min | p25 | Median | p75 | Max |")
  print("|---|---|---|---|---|---|")
  for label, path, fmt in _QUANTILE_ROWS:
    q = field(quantiles, *path, default=None)
    if not isinstance(q, dict) or not field(q, "count"):
      continue
    print(
        f"| {label} | {fmt(field(q, 'minimum'))} |"
        f" {fmt(field(q, 'percentile_25'))} |"
        f" {fmt(field(q, 'percentile_50'))} |"
        f" {fmt(field(q, 'percentile_75'))} | {fmt(field(q, 'maximum'))} |"
    )


def action_tasks(client: SparkApplicationsClient, args) -> None:
  """Prints the tasks of one stage attempt, with deduplicated errors."""
  if args.stage_id is None:
    raise ValueError("--stage_id is required for --action=tasks")
  app_id, _, _ = client.resolve_application(args.application_id)
  # The server rejects sortRuntime and taskStatus, so fetch the attempt's
  # tasks and filter/sort locally.
  tasks = client.paginate(
      "searchStageAttemptTasks",
      "sparkApplicationStageAttemptTasks",
      app_id,
      {"stageId": args.stage_id, "stageAttemptId": args.stage_attempt_id},
      max_items=args.max_fetch,
  )
  fetched = len(tasks)
  if args.task_status:
    tasks = [
        t for t in tasks if str(t.get("status", "")).upper() == args.task_status
    ]
  if args.sort == "duration":
    tasks.sort(key=lambda t: field(t, "duration_millis"), reverse=True)
  elif args.sort == "run_time":
    tasks.sort(
        key=lambda t: field(t, "task_metrics", "executor_run_time_millis"),
        reverse=True,
    )
  tasks = tasks[: args.limit]
  if args.format == "json":
    _print_json(tasks)
    return
  print(
      f"# Tasks of stage {args.stage_id}.{args.stage_attempt_id}"
      f" (`{app_id}`): {len(tasks)} shown of {fetched} fetched\n"
  )
  if fetched >= args.max_fetch:
    print(
        f"> Stopped after {args.max_fetch} tasks; raise --max_fetch to scan"
        " more.\n"
    )
  if not tasks:
    print("No tasks matched.")
    return
  print(
      "| Task | Index.attempt | Status | Executor / host | Duration |"
      " GC | Input | Shuffle read | Spill mem/disk |"
  )
  print("|---|---|---|---|---|---|---|---|---|")
  for t in tasks:
    m = field(t, "task_metrics", default={})
    remote = field(m, "shuffle_read_metrics", "remote_bytes_read")
    local = field(m, "shuffle_read_metrics", "local_bytes_read")
    shuffle_read = remote + local if remote >= 0 and local >= 0 else -1
    print(
        f"| {field(t, 'task_id')} | {field(t, 'index')}.{field(t, 'attempt')}"
        f" | {t.get('status', '')} | {t.get('executorId', '')} /"
        f" {t.get('host', '')} | {human_millis(field(t, 'duration_millis'))} |"
        f" {human_millis(field(m, 'jvm_gc_time_millis'))} |"
        f" {human_bytes(field(m, 'input_metrics', 'bytes_read'))} |"
        f" {human_bytes(shuffle_read)} |"
        f" {human_bytes(field(m, 'memory_bytes_spilled'))} /"
        f" {human_bytes(field(m, 'disk_bytes_spilled'))} |"
    )
  errors: Dict[str, List[Any]] = {}
  for t in tasks:
    if t.get("errorMessage"):
      summary = summarize_error(t["errorMessage"])
      errors.setdefault(summary, []).append(field(t, "task_id"))
  if errors:
    print("\n## Task errors (deduplicated)")
    for summary, task_ids in errors.items():
      print(f"- Tasks {', '.join(str(i) for i in task_ids)}: `{summary}`")


def action_executors(client: SparkApplicationsClient, args) -> None:
  """Prints one row per executor, including removal reasons."""
  app_id, _, _ = client.resolve_application(args.application_id)
  params = {}
  if args.executor_status:
    params["executorStatus"] = f"EXECUTOR_STATUS_{args.executor_status}"
  executors = client.paginate(
      "searchExecutors",
      "sparkApplicationExecutors",
      app_id,
      params,
      max_items=args.limit,
  )
  if args.format == "json":
    _print_json(executors)
    return
  print(f"# Executors of `{app_id}` ({len(executors)} shown)\n")
  if not executors:
    print("No executors matched.")
    return
  print(
      "| Executor | Host | Active | Tasks (failed) | Task time | GC |"
      " Input | Shuffle R/W | Removed | Remove reason |"
  )
  print("|---|---|---|---|---|---|---|---|---|---|")
  for e in executors:
    removed = parse_timestamp(e.get("removeTime"))
    print(
        f"| {e.get('executorId', '')} | {e.get('hostPort', '')} |"
        f" {bool(e.get('isActive'))} | {field(e, 'total_tasks')}"
        f" ({field(e, 'failed_tasks')}) |"
        f" {human_millis(field(e, 'total_duration_millis'))} |"
        f" {human_millis(field(e, 'total_gc_time_millis'))} |"
        f" {human_bytes(field(e, 'total_input_bytes'))} |"
        f" {human_bytes(field(e, 'total_shuffle_read'))} /"
        f" {human_bytes(field(e, 'total_shuffle_write'))} |"
        f" {removed.isoformat() if removed else ''} |"
        f" {truncate(e.get('removeReason', ''), 200)} |"
    )


def action_jobs(client: SparkApplicationsClient, args) -> None:
  """Prints one row per Spark job."""
  app_id, _, _ = client.resolve_application(args.application_id)
  params = {}
  if args.job_status:
    params["jobStatus"] = f"JOB_EXECUTION_STATUS_{args.job_status}"
  jobs = client.paginate(
      "searchJobs",
      "sparkApplicationJobs",
      app_id,
      params,
      max_items=args.limit,
  )
  if args.format == "json":
    _print_json(jobs)
    return
  print(f"# Jobs of `{app_id}` ({len(jobs)} shown)\n")
  if not jobs:
    print("No jobs matched.")
    return
  print(
      "| Job | Status | Stages (failed) | Tasks (failed/killed) | Duration |"
      " Name |"
  )
  print("|---|---|---|---|---|---|")
  for j in jobs:
    print(
        f"| {field(j, 'job_id')} |"
        f" {str(j.get('status', '')).replace('JOB_EXECUTION_STATUS_', '')} |"
        f" {len(j.get('stageIds') or [])} ({field(j, 'num_failed_stages')}) |"
        f" {field(j, 'num_tasks')}"
        f" ({field(j, 'num_failed_tasks')}/{field(j, 'num_killed_tasks')}) |"
        f" {human_millis(duration_millis(j.get('submissionTime'), j.get('completionTime')))}"
        f" | {truncate(j.get('name', ''), 80)} |"
    )


def action_environment(client: SparkApplicationsClient, args) -> None:
  """Prints the runtime versions and effective Spark properties."""
  app_id, _, _ = client.resolve_application(args.application_id)
  env = (
      client.call("accessEnvironmentInfo", app_id).get(
          "applicationEnvironmentInfo"
      )
      or {}
  )
  props = env.get("sparkProperties") or {}
  if args.grep:
    needle = args.grep.lower()
    props = {k: v for k, v in props.items() if needle in k.lower()}
  if args.format == "json":
    _print_json({"runtime": env.get("runtime") or {}, "sparkProperties": props})
    return
  runtime = env.get("runtime") or {}
  print(f"# Spark environment of `{app_id}`\n")
  print(
      f"- Java {runtime.get('javaVersion', '?')}, Scala"
      f" {runtime.get('scalaVersion', '?')}\n"
  )
  print(f"## Spark properties ({len(props)})")
  for key in sorted(props):
    print(f"- `{key}` = `{truncate(props[key], 200)}`")


def action_sql(client: SparkApplicationsClient, args) -> None:
  """Prints one row per SQL execution."""
  app_id, _, _ = client.resolve_application(args.application_id)
  queries = client.paginate(
      "searchSqlQueries",
      "sparkApplicationSqlQueries",
      app_id,
      {"details": False, "planDescription": False},
      max_items=args.limit,
  )
  if args.format == "json":
    _print_json(queries)
    return
  print(f"# SQL executions of `{app_id}` ({len(queries)} shown)\n")
  if not queries:
    print("No SQL executions recorded.")
    return
  print("| Execution | Duration | Jobs | Error | Description |")
  print("|---|---|---|---|---|")
  for q in queries:
    print(
        f"| {field(q, 'execution_id')} |"
        f" {human_millis(duration_millis(q.get('submissionTime'), q.get('completionTime')))}"
        f" | {len(q.get('jobs') or {})} |"
        f" {truncate(q.get('errorMessage', ''), 200)} |"
        f" {truncate(q.get('description', ''), 100)} |"
    )


ACTIONS = {
    "applications": action_applications,
    "summary": action_summary,
    "stages": action_stages,
    "stage": action_stage,
    "tasks": action_tasks,
    "executors": action_executors,
    "jobs": action_jobs,
    "environment": action_environment,
    "sql": action_sql,
}


def default_project() -> Optional[str]:
  """Returns the active gcloud project, or None if unset."""
  gcloud = shutil.which("gcloud")
  if not gcloud:
    return None
  try:
    proc = subprocess.run(
        [gcloud, "config", "get-value", "project"],
        capture_output=True,
        text=True,
        check=False,
        timeout=_GCLOUD_TIMEOUT_SECONDS,
        stdin=subprocess.DEVNULL,
    )
  except (OSError, subprocess.SubprocessError):
    return None
  value = (proc.stdout or "").strip()
  return (
      value if proc.returncode == 0 and value and value != "(unset)" else None
  )


def add_workload_arguments(parser: argparse.ArgumentParser) -> None:
  """Adds the flags that identify a batch or session; shared with siblings."""
  target = parser.add_mutually_exclusive_group()
  target.add_argument("--batch_id", help="Dataproc Serverless batch ID")
  target.add_argument("--session_id", help="Dataproc interactive session ID")
  parser.add_argument(
      "--project", help="GCP project ID (default: active gcloud project)"
  )
  parser.add_argument("--region", default=DEFAULT_REGION, help="GCP region")
  parser.add_argument(
      "--application_id",
      help="Spark application ID (default: the first one the workload has)",
  )
  parser.add_argument(
      "--endpoint",
      default=DEFAULT_ENDPOINT,
      help="Dataproc API endpoint (default: %(default)s)",
  )


def build_client(args) -> SparkApplicationsClient:
  project = args.project or default_project()
  if not project:
    raise ValueError(
        "No project given and no active gcloud project; pass --project."
    )
  return SparkApplicationsClient(
      project=project,
      region=args.region,
      batch_id=args.batch_id,
      session_id=args.session_id,
      endpoint=args.endpoint,
  )


def main(argv: Optional[List[str]] = None) -> int:
  parser = argparse.ArgumentParser(
      description=(
          "Reads Spark UI telemetry (jobs, stages, tasks, executors, SQL,"
          " environment) for a Dataproc Serverless batch or session through"
          " the Dataproc sparkApplications REST API."
      )
  )
  add_workload_arguments(parser)
  parser.add_argument("--action", choices=sorted(ACTIONS), default="summary")
  parser.add_argument(
      "--format", choices=["markdown", "json"], default="markdown"
  )
  parser.add_argument("--stage_id", type=int, help="Stage ID (stage, tasks)")
  parser.add_argument(
      "--stage_attempt_id",
      type=int,
      default=0,
      help="Stage attempt ID (default: 0)",
  )
  parser.add_argument(
      "--stage_status",
      choices=STAGE_STATUSES,
      help="Only stages in this state (stages)",
  )
  parser.add_argument(
      "--task_status",
      choices=TASK_STATUSES,
      help="Only tasks in this state (tasks; filtered locally)",
  )
  parser.add_argument(
      "--job_status",
      choices=JOB_STATUSES,
      help="Only jobs in this state (jobs)",
  )
  parser.add_argument(
      "--executor_status",
      choices=EXECUTOR_STATUSES,
      help="Only active or dead executors (executors)",
  )
  parser.add_argument(
      "--quantiles",
      action="store_true",
      help="Include task quantile metrics (stages)",
  )
  parser.add_argument(
      "--sort",
      choices=["none", "duration", "run_time"],
      default="none",
      help="Sort stages or tasks, longest first",
  )
  parser.add_argument(
      "--grep", help="Only Spark properties containing this text (environment)"
  )
  parser.add_argument(
      "--limit",
      type=int,
      default=50,
      help="Maximum rows to return (default: %(default)s)",
  )
  parser.add_argument(
      "--max_fetch",
      type=int,
      default=2000,
      help="Maximum tasks to scan for --action=tasks (default: %(default)s)",
  )
  args = parser.parse_args(argv)

  if not (args.batch_id or args.session_id):
    parser.error("one of --batch_id or --session_id is required")
  if args.limit <= 0 or args.max_fetch <= 0:
    parser.error("--limit and --max_fetch must be positive")
  try:
    ACTIONS[args.action](build_client(args), args)
  except (DataprocApiError, ValueError) as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
