# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Library for interacting with Cloud Monitoring API."""

import json
import subprocess
import sys
from typing import Any, Dict
import urllib.parse
import urllib.request


def _run_gcloud(*args: str) -> str:
  """Executes a gcloud command and returns the stripped stdout."""
  for cmd in ["gcloud", "gcloud.cmd"]:
    try:
      result = subprocess.run(
          [cmd, *args],
          capture_output=True,
          text=True,
          check=True,
      )
      return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
      continue
  print(f"Error: Command '{args}' failed.", file=sys.stderr)
  sys.exit(1)


def get_token() -> str:
  """Retrieves the access token using the gcloud CLI."""
  token = _run_gcloud("auth", "application-default", "print-access-token")
  if token:
    return token
  print(
      "Error: Could not obtain access token. Are you logged in?",
      file=sys.stderr,
  )
  sys.exit(1)


def fetch_time_series_promql(
    project_id: str, params: Dict[str, Any]
) -> Dict[str, Any]:
  """Fetches time series data from Cloud Monitoring using PromQL API."""
  token = get_token()
  url = f"https://monitoring.googleapis.com/v1/projects/{project_id}/location/global/prometheus/api/v1/query_range"

  data = urllib.parse.urlencode(params).encode("utf-8")
  req = urllib.request.Request(
      url, data=data, headers={"Authorization": f"Bearer {token}"}
  )

  try:
    with urllib.request.urlopen(req) as response:
      return json.loads(response.read().decode())
  except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}", file=sys.stderr)
    print(e.read().decode("utf-8"), file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
