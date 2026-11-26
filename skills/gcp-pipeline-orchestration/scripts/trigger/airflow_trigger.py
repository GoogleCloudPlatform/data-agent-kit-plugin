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
"""Script to trigger an Airflow DAG in a Cloud Composer environment."""

import argparse
import json
import logging
import re
import sys
import time
from typing import Any
import urllib.parse

import google.auth
import google.auth.transport.requests
import requests

_SAFE_PATH_SEGMENT_RE = re.compile(r'^[A-Za-z0-9._-]+$')
_DNS_HOSTNAME_RE = re.compile(
    r'^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$'
)
_ALLOWED_AIRFLOW_HOST_SUFFIXES = (
    '.composer.googleusercontent.com',
    '.composer.byoid.googleusercontent.com',
)


def _validate_path_segment(value: str, param_name: str) -> str:
  """Validates and URL-encodes a single URL path segment."""
  if (
      not value
      or value in ('.', '..')
      or not _SAFE_PATH_SEGMENT_RE.fullmatch(value)
  ):
    raise ValueError(
        f'Invalid {param_name!r}: must match ^[A-Za-z0-9._-]+$ and not be '
        "'.' or '..'."
    )
  return urllib.parse.quote(value, safe='')


def _validate_airflow_uri(airflow_uri: Any) -> str:
  """Validates that airflowUri is HTTPS on a Cloud Composer proxy host."""
  if not isinstance(airflow_uri, str):
    raise ValueError(
        'Untrusted airflowUri: expected a string, got '
        f'{type(airflow_uri).__name__}.'
    )
  uri = airflow_uri.strip()
  parsed = urllib.parse.urlparse(uri)
  hostname = (parsed.hostname or '').lower()

  if parsed.scheme != 'https':
    raise ValueError(f'Untrusted airflowUri scheme: {parsed.scheme!r}')
  if (
      parsed.username is not None
      or parsed.password is not None
      or parsed.port is not None
      or parsed.netloc.lower() != hostname
      or parsed.path not in ('', '/')
      or parsed.params
      or parsed.query
      or parsed.fragment
  ):
    raise ValueError(
        'Untrusted airflowUri: userinfo, custom port, non-root path, params, '
        'query, and fragment are not allowed.'
    )
  is_allowed_host = _DNS_HOSTNAME_RE.fullmatch(hostname) is not None and any(
      hostname.endswith(suffix) and len(hostname) > len(suffix)
      for suffix in _ALLOWED_AIRFLOW_HOST_SUFFIXES
  )
  if not is_allowed_host:
    raise ValueError(f'Untrusted airflowUri host: {hostname!r}')
  return f'https://{hostname}'


class ComposerClient:
  """Client for interacting with Cloud Composer and Airflow."""

  def __init__(self, token: str = '', creds: Any | None = None) -> None:
    self.token = token
    self.creds = creds
    self.token_expiration_time = 0

    if not self.token and not self.creds:
      try:
        logging.info('Attempting to get default credentials...')
        self.creds, _ = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
      except Exception:  # pylint: disable=broad-except
        logging.error('Failed to get default credentials.', exc_info=True)

    if self.creds:
      self._refresh_access_token()

  def _refresh_access_token(self) -> None:
    """Refreshes the access token."""
    request = google.auth.transport.requests.Request()
    self.creds.refresh(request)
    self.token = self.creds.token
    # Tokens typically expire after 3600 seconds. Refresh a bit earlier.
    self.token_expiration_time = time.time() + 3500

  def _get_headers(self) -> dict[str, str]:
    if self.creds and time.time() >= self.token_expiration_time:
      logging.info('Access token expired, refreshing...')
      self._refresh_access_token()

    headers = {'Content-Type': 'application/json'}
    if self.token:
      headers['Authorization'] = f'Bearer {self.token}'
    return headers

  def get_airflow_uri(
      self, project: str, location: str, environment: str
  ) -> str:
    """Gets and validates the Airflow URI for a Composer environment."""
    safe_project = _validate_path_segment(project, 'project')
    safe_location = _validate_path_segment(location, 'location')
    safe_environment = _validate_path_segment(environment, 'environment')
    url = (
        'https://composer.googleapis.com/v1/'
        f'projects/{safe_project}/locations/{safe_location}/'
        f'environments/{safe_environment}'
    )
    response = requests.get(
        url, headers=self._get_headers(), allow_redirects=False
    )
    if 300 <= response.status_code < 400:
      raise RuntimeError(
          f'Unexpected redirect ({response.status_code}) from Composer API.'
      )
    response.raise_for_status()
    env_data = response.json()
    config = env_data.get('config') if isinstance(env_data, dict) else None
    if not isinstance(config, dict):
      raise RuntimeError(f'Config not found for environment {environment}')
    airflow_uri = config.get('airflowUri')
    if not airflow_uri:
      raise RuntimeError(f'Airflow URI not found for environment {environment}')
    return _validate_airflow_uri(airflow_uri)

  def trigger_dag_run(
      self, project: str, location: str, environment: str, dag_id: str
  ) -> dict[str, Any]:
    """Triggers a DAG run in the specified Composer environment."""
    safe_dag_id = _validate_path_segment(dag_id, 'dag_id')
    airflow_uri = self.get_airflow_uri(project, location, environment)
    url = f'{airflow_uri}/api/v1/dags/{safe_dag_id}/dagRuns'
    response = requests.post(
        url, headers=self._get_headers(), json={}, allow_redirects=False
    )
    if 300 <= response.status_code < 400:
      raise RuntimeError(
          f'Unexpected redirect ({response.status_code}) from Airflow API.'
      )
    response.raise_for_status()
    return response.json()


def trigger_dag(
    project: str, location: str, environment: str, dag_id: str
) -> str:
  """Triggers an Airflow DAG in a Cloud Composer environment.

  Args:
    project: GCP Project ID.
    location: GCP Region (e.g., us-central1).
    environment: Composer environment name.
    dag_id: ID of the DAG to trigger.

  Returns:
    JSON string with the trigger response.

  Raises:
    ValueError: If an identifier argument or the returned airflowUri is
      invalid.
    RuntimeError: If the Composer or Airflow API returns an unexpected
      response.
    requests.HTTPError: If the Composer or Airflow API returns an HTTP error.
  """
  # Validate all identifiers before acquiring credentials or waiting.
  _validate_path_segment(project, 'project')
  _validate_path_segment(location, 'location')
  _validate_path_segment(environment, 'environment')
  _validate_path_segment(dag_id, 'dag_id')

  client = ComposerClient()
  logging.info('Waiting 2 minutes for deployment to complete...')
  time.sleep(120)
  result = client.trigger_dag_run(project, location, environment, dag_id)
  return json.dumps(result, indent=2)


def main() -> None:
  parser = argparse.ArgumentParser(description='Trigger an Airflow DAG.')
  parser.add_argument('--project', required=True, help='GCP Project ID')
  parser.add_argument('--location', required=True, help='GCP Location')
  parser.add_argument(
      '--environment', required=True, help='Composer Environment'
  )
  parser.add_argument('--dag_id', required=True, help='Airflow DAG ID')

  args = parser.parse_args()

  logging.basicConfig(level=logging.INFO)
  try:
    print(
        trigger_dag(args.project, args.location, args.environment, args.dag_id)
    )
  except Exception as e:  # pylint: disable=broad-except
    logging.error('Failed to trigger DAG.', exc_info=True)
    print(f'Failed to trigger DAG: {e}', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
  main()
