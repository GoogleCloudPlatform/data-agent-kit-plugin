# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""GCP REST helpers with no third-party Python dependencies.

Same surface as ``cloud_rest_helpers`` but uses only Python stdlib plus
two system binaries:

* ``gcloud auth application-default print-access-token`` for OAuth2 bearer
tokens.
* ``curl`` for HTTPS calls.
"""

from collections.abc import Mapping, Sequence
import json as json_lib
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any
import urllib.parse

_BIGQUERY_API = "https://bigquery.googleapis.com/bigquery/v2/projects"
_RESOURCE_MANAGER_API = (
    "https://cloudresourcemanager.googleapis.com/v3/projects"
)
_TIMEOUT_SECONDS = 60

_ATTRIBUTION_PREFIX = "gcs-skills"
_KIT_VERSION = "1.0"


def _user_agent(skill: str, script: str) -> str:
  return (
      f"{_ATTRIBUTION_PREFIX}/{_KIT_VERSION} (skill:{skill}; script:{script})"
  )


def sanitize_label(val: str) -> str:
  """Sanitizes a string to satisfy the BigQuery label charset requirements.

  Converts to lowercase, replaces underscores and invalid characters with
  hyphens, collapses consecutive hyphens, and strips leading/trailing hyphens.

  Args:
    val: The string to sanitize.

  Returns:
    The sanitized string.
  """
  val = val.replace("_", "-")
  val = re.sub(r"[^a-z0-9-]", "-", val.lower())
  val = re.sub(r"-+", "-", val)
  return val.strip("-")


def bigquery_labels(skill: str, script: str) -> dict[str, str]:
  """BigQuery job labels for kit attribution.

  Lowercase + hyphens only to satisfy the BigQuery label charset
  (https://cloud.google.com/bigquery/docs/labels-intro#requirements).

  Args:
    skill: Identifier for the calling skill (e.g., "gcs-security-assessment").
    script: Identifier for the calling script (e.g., "fetch-bucket-telemetry").

  Returns:
    A dictionary containing the aggregated kit labels.
  """
  return {
      _ATTRIBUTION_PREFIX: "true",
      f"{_ATTRIBUTION_PREFIX}-skill": sanitize_label(skill),
      f"{_ATTRIBUTION_PREFIX}-script": sanitize_label(script),
  }


class CloudRestError(Exception):
  """Base error for transport, auth, or HTTP failures from the kit."""


class CredentialsError(CloudRestError):
  """Raised when an access token cannot be obtained via gcloud."""


class HttpError(CloudRestError):
  """Raised on a 4xx/5xx HTTP response.

  Attributes:
    status_code: The HTTP status code.
    body: The response body decoded as UTF-8 (errors replaced).
    url: The URL that was requested.
  """

  def __init__(self, status_code: int, body: str, url: str):
    self.status_code = status_code
    self.body = body
    self.url = url
    super().__init__(f"HTTP {status_code} from {url}: {body[:500]}")


_SERVICE_DISABLED_REASON = "SERVICE_DISABLED"


def is_service_disabled_error(http_error: HttpError) -> bool:
  """Returns True if the HTTP error indicates the API is not enabled.

  GCP's API gateway returns 403 with errorInfo.reason="SERVICE_DISABLED"
  when an API has not been enabled on the project. Permission-denied errors
  use other reasons (e.g., IAM_PERMISSION_DENIED) and must not match here.

  Args:
    http_error: The HttpError raised by an HTTP request to a GCP service.

  Returns:
    True if the error body contains a SERVICE_DISABLED reason, False otherwise.
  """
  if http_error.status_code != 403:
    return False
  try:
    payload = json_lib.loads(http_error.body)
  except (ValueError, TypeError):
    return False
  details = (payload.get("error") or {}).get("details") or []
  return any(
      isinstance(d, Mapping) and d.get("reason") == _SERVICE_DISABLED_REASON
      for d in details
  )


def _fetch_access_token() -> str:
  """Fetches an OAuth2 access token via ``gcloud auth application-default print-access-token``.

  Returns:
    The bearer token string with surrounding whitespace stripped.

  Raises:
    CredentialsError: If ``gcloud`` is not on PATH, the subprocess fails,
      the call times out, or the returned token is empty.
  """
  gcloud = shutil.which("gcloud")
  if not gcloud:
    raise CredentialsError(
        "gcloud CLI not found on PATH. Install Google Cloud SDK and run "
        "'gcloud auth application-default login'."
    )
  try:
    result = subprocess.run(
        [gcloud, "auth", "application-default", "print-access-token"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_TIMEOUT_SECONDS,
        check=True,
    )
  except subprocess.CalledProcessError as e:
    stderr = (e.stderr or "").strip()
    raise CredentialsError(
        "'gcloud auth application-default print-access-token' failed:"
        f" {stderr}. Run 'gcloud auth application-default login'."
    ) from e
  except subprocess.TimeoutExpired as e:
    raise CredentialsError(
        "gcloud auth application-default print-access-token timed out."
    ) from e

  token = result.stdout.strip()
  if not token:
    raise CredentialsError(
        "gcloud auth application-default print-access-token returned an empty"
        " token."
    )
  return token


class Response:
  """Minimal Response-shaped wrapper used by AuthorizedSession.

  Supports context-manager use, ``raise_for_status()``, ``json()``,
  ``status_code``, and ``text``.
  """

  def __init__(self, status_code: int, body: bytes, url: str):
    self.status_code = status_code
    self._body = body
    self.url = url

  @property
  def text(self) -> str:
    """The response body decoded as UTF-8 string."""
    return self._body.decode("utf-8", errors="replace")

  def json(self) -> Any:
    """Returns the parsed JSON response body."""

    # `utf-8-sig` strips a leading BOM if present (some Cloud edge proxies
    # emit one), matching `requests.Response.json()` tolerance.
    return json_lib.loads(self._body.decode("utf-8-sig") or "null")

  def raise_for_status(self) -> None:
    """Raises HttpError if status_code is 4xx or 5xx."""
    if 400 <= self.status_code < 600:
      raise HttpError(self.status_code, self.text, self.url)

  def __enter__(self) -> "Response":
    return self

  def __exit__(self, *exc: Any) -> bool:
    return False


class AuthorizedSession:
  """Curl + gcloud-backed AuthorizedSession.

  Provides ``request(method, url, json=, timeout=)``, ``get(url, ...)``,
  and a mutable ``headers`` dict. On HTTP 401 the bearer token is
  refreshed once via gcloud and the request is retried; a second 401
  raises ``HttpError`` rather than returning the response, since a
  persistent 401 signals a broken credential rather than per-resource
  authorization.

  Not thread-safe: concurrent calls on a shared instance race on the
  ``_token`` field on 401-refresh paths. Construct one session per
  thread/task if you need concurrency.
  """

  def __init__(self) -> None:
    self._token = _fetch_access_token()
    self.headers: dict[str, str] = {}

  def __enter__(self) -> "AuthorizedSession":
    return self

  def __exit__(self, *exc: Any) -> bool:
    return False

  def _execute_request(
      self,
      method: str,
      url: str,
      body_bytes: bytes | None,
      headers: Mapping[str, str],
      timeout: float,
  ) -> Response:
    """Executes a single HTTP request using curl.

    Args:
      method: The HTTP method (e.g., "GET", "POST").
      url: The URL to request.
      body_bytes: The raw bytes to send as the request body, or None.
      headers: A mapping of header names to values.
      timeout: The timeout for the request in seconds.

    Returns:
      A Response object.

    Raises:
      CloudRestError: If curl fails or times out.
    """
    curl = shutil.which("curl")
    if not curl:
      raise CloudRestError(
          "curl not found on PATH. The kit shells out to curl for HTTPS"
          " calls; install curl and ensure it is on PATH"
          " (https://curl.se/download.html)."
      )
    cmd: list[str] = [
        curl,
        "-sS",  # silent (no progress meter), but still print errors.
        "-X",
        method,  # explicit HTTP method (GET, POST, ...).
        # Total operation timeout in seconds; guarded against 0/negative.
        "--max-time",
        str(max(1, int(timeout))),
        # Append the 3-digit HTTP status to stdout after the body so we can
        # recover it (curl doesn't expose status code any other way without
        # parsing response headers).
        "-w",
        "%{http_code}",
    ]
    if body_bytes is not None:
      # `@-` reads the request body from stdin (piped via subprocess.run
      # input=). `--data-binary` (vs `--data`) preserves bytes exactly --
      # no newline stripping or CRLF conversion, which would corrupt JSON.
      cmd.extend(["--data-binary", "@-"])

    # Headers are written to a 0600 temp file and read by curl via
    # `-H @<path>` so the bearer token is never visible in `ps`/argv.
    # We close the file before spawning curl so Windows (which forbids a
    # second open on a file already held by another handle) can also read
    # it; cleanup happens in `finally`.
    fd, headers_path = tempfile.mkstemp(prefix="curl-headers-")
    try:
      with os.fdopen(fd, "w", encoding="utf-8") as headers_file:
        for k, v in headers.items():
          # Reject CR/LF anywhere in header name/value. Otherwise an
          # attacker who controls a header value (e.g., via a label
          # interpolated into User-Agent) could smuggle additional
          # headers by injecting `\r\n`.
          if "\r" in k or "\n" in k or "\r" in v or "\n" in v:
            raise CloudRestError(
                f"Refusing to send header {k!r}: CR/LF in name or value."
            )
          headers_file.write(f"{k}: {v}\n")
      cmd.extend(["-H", f"@{headers_path}"])
      cmd.append(url)
      try:
        result = subprocess.run(
            cmd,
            input=body_bytes,
            capture_output=True,
            timeout=timeout + 5,
            check=False,
        )
      except subprocess.TimeoutExpired as e:
        raise CloudRestError(f"curl timed out contacting {url}.") from e
    finally:
      try:
        os.unlink(headers_path)
      except OSError:
        pass  # best-effort cleanup

    if result.returncode != 0:
      stderr = result.stderr.decode("utf-8", errors="replace").strip()
      raise CloudRestError(
          f"curl failed contacting {url} (exit {result.returncode}): {stderr}"
      )

    # `-w "%{http_code}"` appends the 3-digit HTTP status to stdout after
    # the body. HTTP status codes are always 3 digits, so split on length.
    stdout = result.stdout
    if len(stdout) < 3:
      raise CloudRestError(
          f"curl returned unexpectedly short output for {url}."
      )
    status_bytes = stdout[-3:]
    try:
      status_code = int(status_bytes.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as e:
      raise CloudRestError(
          f"curl returned non-numeric status for {url}: {status_bytes!r}"
      ) from e
    body = stdout[:-3]
    return Response(status_code, body, url)

  def request(
      self,
      method: str,
      url: str,
      *,
      json: Mapping[str, Any] | None = None,
      timeout: float = _TIMEOUT_SECONDS,
      headers: Mapping[str, str | None] | None = None,
  ) -> Response:
    """Issues an authenticated HTTP request, refreshing the token on 401.

    Args:
      method: The HTTP method (e.g., "GET", "POST").
      url: The URL to request.
      json: Optional JSON-serializable request body, sent with Content-Type:
        application/json.
      timeout: The timeout for the request in seconds.
      headers: Optional per-request headers, merged over the session headers. A
        header value of None removes that header from the request instead of
        sending it, matching requests.Session semantics.

    Returns:
      A Response object.

    Raises:
      HttpError: If the server returns 401 again after a token refresh.
      CloudRestError: If curl fails or times out.
      CredentialsError: If refreshing the token via gcloud fails.
    """
    request_headers: dict[str, str] = dict(self.headers)
    if headers:
      for name, value in headers.items():
        if value is None:
          request_headers.pop(name, None)
        else:
          request_headers[name] = value
    request_headers["Authorization"] = f"Bearer {self._token}"

    body_bytes: bytes | None = None
    if json is not None:
      body_bytes = json_lib.dumps(json).encode("utf-8")
      request_headers["Content-Type"] = "application/json"

    resp = self._execute_request(
        method, url, body_bytes, request_headers, timeout
    )
    if resp.status_code == 401:
      self._token = _fetch_access_token()
      request_headers["Authorization"] = f"Bearer {self._token}"
      resp = self._execute_request(
          method, url, body_bytes, request_headers, timeout
      )
      if resp.status_code == 401:
        raise HttpError(401, resp.text, url)
    return resp

  def get(
      self,
      url: str,
      *,
      timeout: float = _TIMEOUT_SECONDS,
      headers: Mapping[str, str | None] | None = None,
  ) -> Response:
    """Issues an authenticated HTTP GET request."""
    return self.request("GET", url, timeout=timeout, headers=headers)


def get_authorized_session(
    *, skill: str, script: str, project_id: str | None = None
) -> AuthorizedSession:
  """Returns an AuthorizedSession with the kit User-Agent stamped.

  Every outbound request is stamped with a gcs-skills User-Agent so
  the GCS team can measure aggregate kit usage from server-side request
  logs. If ``project_id`` is provided, the ``X-Goog-User-Project`` header is
  also stamped so requests are billed/quota-attributed to that project.

  Args:
    skill: Identifier for the calling skill (e.g., "gcs-security-assessment").
    script: Identifier for the calling script (e.g., "fetch-bucket-telemetry").
    project_id: Optional GCP project ID for billing/quota attribution. When set,
      stamped as the ``X-Goog-User-Project`` header on every request.

  Returns:
    AuthorizedSession with a freshly fetched access token.

  Raises:
    CredentialsError: If fetching the access token via gcloud fails.
  """
  session = AuthorizedSession()
  session.headers["User-Agent"] = _user_agent(skill, script)
  if project_id:
    session.headers["X-Goog-User-Project"] = project_id
  return session


def get_project_number(*, project_id: str, session: AuthorizedSession) -> int:
  """Resolves a GCP project ID to its project number.

  Storage Insights dataset views identify a bucket's owning project by
  project number, so callers filtering those views by project must resolve
  the user-facing project ID first. Requires the
  ``resourcemanager.projects.get`` permission on the project, which every
  predefined project-level role includes.

  Args:
    project_id: The GCP project ID (or project number, returned as-is).
    session: Authorized session for REST requests.

  Returns:
    The project number.

  Raises:
    CloudRestError: If the REST call fails or the response does not contain
      a project number.
  """
  # isascii() guards against non-ASCII digits (e.g. superscripts), which
  # isdigit() accepts but int() rejects.
  if project_id.isascii() and project_id.isdigit():
    return int(project_id)
  url = f"{_RESOURCE_MANAGER_API}/{urllib.parse.quote(project_id, safe='')}"
  # projects.get is free metadata, so it needs no billing attribution.
  # Sending X-Goog-User-Project would additionally require the Cloud
  # Resource Manager API to be enabled on that quota project, so the header
  # is omitted to keep resolution working on projects that have not
  # enabled it.
  with session.get(url, headers={"X-Goog-User-Project": None}) as response:
    response.raise_for_status()
    payload = response.json()
  # v3 projects.get returns the resource name "projects/<project number>".
  name = payload.get("name") if isinstance(payload, Mapping) else None
  prefix, _, project_number = (name or "").partition("/")
  if prefix != "projects" or not (
      project_number.isascii() and project_number.isdigit()
  ):
    raise CloudRestError(
        f"Could not resolve project number for {project_id!r}: unexpected"
        f" resource name {name!r} from Cloud Resource Manager."
    )
  return int(project_number)


def parse_bq_value(val: Any, field: Mapping[str, Any]) -> Any:
  """Recursively parses BigQuery REST JSON response row values.

  Args:
    val: The value to parse.
    field: The field definition from the BigQuery schema.

  Returns:
    The parsed value.
  """
  if val is None:
    return None
  ftype = field.get("type")
  fmode = field.get("mode")

  if fmode == "REPEATED":
    if not val:
      return []
    single_field = dict(field)
    single_field["mode"] = "NULLABLE"
    return [parse_bq_value(item.get("v"), single_field) for item in val]

  if ftype == "BOOLEAN":
    return val.lower() == "true"
  elif ftype == "INTEGER":
    return int(val)
  elif ftype == "RECORD":
    fields = field.get("fields", [])
    row_f = val.get("f", [])
    res = {}
    for i, subfield in enumerate(fields):
      subval = row_f[i].get("v") if i < len(row_f) else None
      res[subfield["name"]] = parse_bq_value(subval, subfield)
    return res
  else:
    return val


def execute_bigquery_query(
    *,
    project_id: str,
    payload: Mapping[str, Any],
    session: AuthorizedSession,
    skill: str,
    script: str,
) -> tuple[Sequence[Mapping[str, Any]], Sequence[Any]]:
  """Executes a BigQuery REST query, polls for completion, and paginates rows.

  Merges gcs-skills job labels into the request body so the kit's BigQuery
  traffic is queryable from `INFORMATION_SCHEMA.JOBS_BY_PROJECT` and Cloud
  Audit Logs. Caller-supplied labels in `payload` win on key collision.

  Args:
    project_id: The GCP project ID.
    payload: The JSON query payload.
    session: Authorized session for REST requests.
    skill: Identifier for the calling skill (e.g., "gcs-security-assessment").
    script: Identifier for the calling script (e.g., "fetch-bucket-telemetry").

  Returns:
    A tuple (schema_fields, rows) where schema_fields is a list of
    the BigQuery column schema fields and rows is a list of unparsed rows.

  Raises:
    CloudRestError: If the REST query fails.
    RuntimeError: If the query fails or doesn't complete.
  """

  enriched_payload = dict(payload)
  enriched_payload["labels"] = {
      **bigquery_labels(skill, script),
      **(payload.get("labels") or {}),
  }
  url = f"{_BIGQUERY_API}/{project_id}/queries"
  logging.debug("Executing REST query with payload: %s", enriched_payload)
  with session.request(
      method="POST",
      url=url,
      json=enriched_payload,
      timeout=_TIMEOUT_SECONDS,
  ) as response:
    response.raise_for_status()
    response_json = response.json()

  job_ref = response_json.get("jobReference", {})
  job_id = job_ref.get("jobId")
  job_complete = response_json.get("jobComplete")

  polling_attempts = 0
  while not job_complete and job_id and polling_attempts < 60:
    logging.debug("Query job not complete, polling job: %s", job_id)
    time.sleep(1)
    job_url = f"{_BIGQUERY_API}/{project_id}/queries/{job_id}"
    with session.request(
        method="GET",
        url=job_url,
        timeout=_TIMEOUT_SECONDS,
    ) as job_response:
      job_response.raise_for_status()
      response_json = job_response.json()
    job_complete = response_json.get("jobComplete")
    polling_attempts += 1

  if not job_complete:
    # Covers both "polling capped at 60 attempts and the job is still
    # running" and "server returned an incomplete-but-no-jobReference
    # response we can't poll" -- the latter would otherwise return an
    # empty ([], []) silently.
    raise RuntimeError(f"BigQuery query did not complete (job_id={job_id!r}).")

  error_result = response_json.get("errorResult") or response_json.get(
      "status", {}
  ).get("errorResult")
  if error_result:
    raise RuntimeError(
        f"BigQuery job failed: {error_result.get('message', 'Unknown error')}"
    )

  schema_fields = (response_json.get("schema") or {}).get("fields") or []
  rows = response_json.get("rows", [])

  job_ref = response_json.get("jobReference", {})
  job_id = job_ref.get("jobId")
  page_token = response_json.get("pageToken")

  while page_token and job_id:
    page_url = (
        f"{_BIGQUERY_API}/{project_id}/queries/{job_id}"
        f"?pageToken={urllib.parse.quote(page_token, safe='')}"
    )
    logging.debug("Fetching next page of results: %s", page_token)
    with session.request(
        method="GET",
        url=page_url,
        timeout=_TIMEOUT_SECONDS,
    ) as page_response:
      page_response.raise_for_status()
      page_json = page_response.json()
    rows.extend(page_json.get("rows", []))
    page_token = page_json.get("pageToken")

  return schema_fields, rows
