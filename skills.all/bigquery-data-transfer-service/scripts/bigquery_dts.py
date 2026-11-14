#!/usr/bin/env python3
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
"""BigQuery Data Transfer Service REST API - Data Source Parameter Discovery."""

import argparse
import json
import os
import subprocess
import sys
from typing import Optional
import urllib.error
import urllib.parse
import urllib.request


def _run_gcloud(*args: str) -> Optional[str]:
  """Executes a gcloud command and returns the stripped stdout, or None."""
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
  return None


def get_project_id() -> str:
  """Retrieves the active Google Cloud project ID."""
  project_id = os.environ.get("PROJECT_ID")
  if project_id:
    return project_id

  val = _run_gcloud("config", "get-value", "project")
  if val and "(unset)" not in val:
    return val

  print("Error: Could not determine PROJECT_ID.", file=sys.stderr)
  sys.exit(1)


def get_token() -> str:
  """Retrieves the access token using the gcloud CLI."""
  token = _run_gcloud("auth", "print-access-token")
  if token:
    return token

  print(
      "Error: Could not obtain access token. Are you logged in?",
      file=sys.stderr,
  )
  sys.exit(1)


def get_region() -> str:
  """Retrieves the default compute region from gcloud config."""
  val = _run_gcloud("config", "get-value", "compute/region")
  if val and "(unset)" not in val:
    return val

  return "us"


def main() -> None:
  """Main entry point for the script."""
  parser = argparse.ArgumentParser(
      description=(
          "BigQuery Data Transfer Service REST API - "
          "Data Source Parameter Discovery"
      )
  )
  parser.add_argument("--project_id", help="The GCP project ID to use")
  parser.add_argument(
      "data_source_id", nargs="?", help="The DATA_SOURCE_ID to inspect"
  )
  parser.add_argument(
      "region", nargs="?", help="The GCP region (default: derived or us)"
  )
  args = parser.parse_args()

  project_id = args.project_id or get_project_id()
  if not project_id:
    print(
        "Error: PROJECT_ID not set and could not be determined.",
        file=sys.stderr,
    )
    sys.exit(1)

  region = args.region or get_region() or "us"

  if args.data_source_id:
    print(
        f"Retrieving Data Source parameters for: {args.data_source_id} "
        f"in {region}..."
    )
    url = (
        "https://bigquerydatatransfer.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/dataSources/"
        f"{args.data_source_id}"
    )
  else:
    print(
        f"Listing available Data Sources in {region} for project "
        f"{project_id}..."
    )
    url = (
        "https://bigquerydatatransfer.googleapis.com/v1/"
        f"projects/{project_id}/locations/{region}/dataSources"
    )

  token = get_token()

  req = urllib.request.Request(url)
  req.add_header("Authorization", f"Bearer {token}")
  req.add_header("Content-Type", "application/json")

  try:
    with urllib.request.urlopen(req, timeout=30) as response:
      data = json.loads(response.read().decode("utf-8"))
      print(json.dumps(data, indent=4))

      # Generate OAuth authorization URI for Google data sources
      client_id = data.get("clientId")
      scopes = data.get("scopes")
      if client_id and scopes:
        print("\n" + "=" * 40)
        print("MANDATORY OAUTH AUTHORIZATION STEP")
        print("=" * 40)
        print(
            "This Data Source requires user authorization. "
            "Please follow the URL below to authorize:"
        )
        params = {
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "response_type": "version_info",
            "client_id": client_id,
            "scope": " ".join(scopes),
        }
        query_string = urllib.parse.urlencode(params)
        auth_url = f"https://bigquery.cloud.google.com/datatransfer/oauthz/auth?{query_string}"
        print(f"\n{auth_url}\n")
        print("=" * 40 + "\n")
  except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}", file=sys.stderr)
    print(e.read().decode("utf-8"), file=sys.stderr)
    sys.exit(1)
  except Exception as e:  # pylint: disable=broad-exception-caught
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
