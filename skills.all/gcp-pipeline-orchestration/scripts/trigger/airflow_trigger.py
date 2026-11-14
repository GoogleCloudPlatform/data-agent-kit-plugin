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
import time
from typing import Any

import google.auth
import google.auth.transport.requests
import requests


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
    """Gets the Airflow URI for a Composer environment."""
    url = f'https://composer.googleapis.com/v1/projects/{project}/locations/{location}/environments/{environment}'
    response = requests.get(url, headers=self._get_headers())
    response.raise_for_status()
    env_data = response.json()
    airflow_uri = env_data.get('config', {}).get('airflowUri')
    if not airflow_uri:
      raise RuntimeError(f'Airflow URI not found for environment {environment}')
    return airflow_uri.rstrip('/')

  def trigger_dag_run(
      self, project: str, location: str, environment: str, dag_id: str
  ) -> dict[str, Any]:
    """Triggers a DAG run in the specified Composer environment."""
    airflow_uri = self.get_airflow_uri(project, location, environment)
    url = f'{airflow_uri}/api/v1/dags/{dag_id}/dagRuns'
    response = requests.post(url, headers=self._get_headers(), json={})
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
    JSON string with the trigger response or error message.
  """
  client = ComposerClient()
  try:
    logging.info('Waiting 2 minutes for deployment to complete...')
    time.sleep(120)
    result = client.trigger_dag_run(project, location, environment, dag_id)
    return json.dumps(result, indent=2)
  except Exception as e:  # pylint: disable=broad-except
    logging.error('Failed to trigger DAG.', exc_info=True)
    return f'Failed to trigger DAG: {e}'


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
  print(trigger_dag(args.project, args.location, args.environment, args.dag_id))


if __name__ == '__main__':
  main()
