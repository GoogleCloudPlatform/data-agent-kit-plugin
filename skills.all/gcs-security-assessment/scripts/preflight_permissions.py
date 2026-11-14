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

"""Preflight permission check for the GCS security assessment skill.

Probes prerequisites the assessment depends on and emits a structured report.
Required checks gate the assessment; recommended checks downgrade it to a
partial assessment with surfaced gaps.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
import sys
from typing import Any

import cloud_rest_helpers_nodeps
import validation

_BIGQUERY_API = "https://bigquery.googleapis.com/bigquery/v2/projects"
_STORAGE_INSIGHTS_API = "https://storageinsights.googleapis.com/v1/projects"
_SKILL = "gcs-security-assessment"
_SCRIPT = "preflight-permissions"


def _bq_failure(*, impact: str, fix: str, error: str) -> Mapping[str, Any]:
  return {
      "check": "bigquery_dataset_access",
      "status": "missing",
      "impact": impact,
      "fix": fix,
      "error": error,
  }


def _si_failure(*, impact: str, fix: str, error: str) -> Mapping[str, Any]:
  return {
      "check": "storage_insights_enabled",
      "status": "missing",
      "impact": impact,
      "fix": fix,
      "error": error,
  }


def _check_storage_insights_enabled(
    *,
    project_id: str,
    session: Any,
) -> Mapping[str, Any]:
  """Probes whether the Storage Insights API is enabled on the project.

  Storage Insights unlocks the bucket- and object-level telemetry that the
  full assessment depends on. It is a *recommended* prerequisite, not a hard
  gate: when it is unavailable the assessment degrades to a project-level
  posture report (IAM, VPC-SC, audit logs, org policies, Model Armor) and
  recommends enabling SI to unlock the full bucket- and object-level
  assessment. The downstream bigquery_dataset_access check covers the case
  where SI is enabled but no linked dataset exists yet (or the wrong dataset
  name was supplied).

  Args:
    project_id: GCP project ID to probe.
    session: Authorized session for REST requests.

  Returns:
    Mapping with keys `check`, `status`, and on failure `impact`, `fix`,
    `error`.
  """
  try:
    validation.validate_project_id(project_id)
  except (TypeError, ValueError) as e:
    return _si_failure(
        impact=f"Input validation failed: {e}",
        fix="Provide a valid GCP project ID.",
        error=str(e),
    )

  url = f"{_STORAGE_INSIGHTS_API}/{project_id}/locations/-/datasetConfigs"
  try:
    response = session.get(url, timeout=10)
    response.raise_for_status()
  except cloud_rest_helpers_nodeps.HttpError as e:
    error = str(e)
    status_code = e.status_code
    body = (e.body or "").lower()

    if status_code == 403 and "has not been used" in body:
      return _si_failure(
          impact=(
              "Storage Insights is not enabled on the project, so bucket- and"
              " object-level telemetry is unavailable. The assessment will"
              " cover project-level posture only."
          ),
          fix=(
              "To unlock the full bucket- and object-level assessment, enable"
              " Storage Insights: `gcloud services enable"
              f" storageinsights.googleapis.com --project {project_id}`."
          ),
          error=error,
      )
    elif status_code == 403:
      return _si_failure(
          impact=(
              "Caller lacks permission to list Storage Insights dataset"
              " configs, so bucket- and object-level telemetry is"
              " unavailable. The assessment will cover project-level posture"
              " only."
          ),
          fix=(
              "To unlock the full assessment, grant"
              " roles/storageinsights.viewer (or a role containing"
              " storageinsights.datasetConfigs.list) on the project."
          ),
          error=error,
      )

    return _si_failure(
        impact=f"Unexpected HTTP {status_code} from Storage Insights API.",
        fix=(
            "Retry the preflight check. If the failure persists, see"
            " https://status.cloud.google.com for ongoing GCP incidents."
        ),
        error=error,
    )
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    return _si_failure(
        impact="Network or transport failure contacting Storage Insights.",
        fix="Check network connectivity and GCP reachability.",
        error=str(e),
    )

  return {"check": "storage_insights_enabled", "status": "ok"}


def _check_adc() -> Mapping[str, Any]:
  try:
    # Constructing the session fetches a token via gcloud, which validates
    # that the user has working credentials.
    cloud_rest_helpers_nodeps.get_authorized_session(
        skill=_SKILL, script=_SCRIPT
    )
    return {"check": "adc", "status": "ok"}
  except cloud_rest_helpers_nodeps.CredentialsError as e:
    return {
        "check": "adc",
        "status": "missing",
        "impact": "Cannot make any authenticated GCP API calls.",
        "fix": "Run: gcloud auth application-default login",
        "error": str(e),
    }


def _check_bigquery_dataset_access(
    *,
    project_id: str,
    dataset_name: str,
    session: Any,
) -> Mapping[str, Any]:
  """Probes BigQuery dataset accessibility via a zero-cost dry-run query.

  Validates inputs, then issues a `dryRun: true` query against the Storage
  Insights `bucket_attributes_view`. Distinguishes the common failure modes
  (API not enabled, dataset/view not found, missing dataset permissions,
  network/transport error) and returns a structured result with a
  user-actionable fix per case.

  Args:
    project_id: GCP project ID hosting the Storage Insights dataset.
    dataset_name: BigQuery dataset name to probe.
    session: Authorized session for REST requests.

  Returns:
    Mapping with keys `check`, `status`, and on failure `impact`, `fix`,
    `error`.
  """
  try:
    validation.validate_inputs(project_id, dataset_name, None)
  except (TypeError, ValueError) as e:
    return {
        "check": "bigquery_dataset_access",
        "status": "missing",
        "impact": f"Input validation failed: {e}",
        "fix": (
            "project_id must not contain backticks; dataset_name must match"
            " ^[a-zA-Z0-9_]{1,1024}$"
        ),
        "error": str(e),
    }

  try:
    with session.request(
        method="POST",
        url=f"{_BIGQUERY_API}/{project_id}/queries",
        json={
            "query": (
                "SELECT 1 FROM"
                f" `{project_id}.{dataset_name}.bucket_attributes_view` LIMIT 0"
            ),
            "useLegacySql": False,
            "dryRun": True,
            "labels": cloud_rest_helpers_nodeps.bigquery_labels(
                _SKILL, _SCRIPT
            ),
        },
        timeout=10,
    ) as response:
      response.raise_for_status()
    return {"check": "bigquery_dataset_access", "status": "ok"}
  except cloud_rest_helpers_nodeps.HttpError as e:
    error = str(e)
    status_code = e.status_code
    body = e.body or ""

    if status_code == 403 and "has not been used" in body.lower():
      return _bq_failure(
          impact="BigQuery API is not enabled on the project.",
          fix=(
              "Run: gcloud services enable bigquery.googleapis.com --project"
              f" {project_id}"
          ),
          error=error,
      )
    elif status_code == 404:
      return _bq_failure(
          impact="Dataset or view not found.",
          fix=(
              "Run scripts/list_datasets.py to see available datasets. If"
              " none exist, create a Storage Insights dataset config in the"
              " Cloud Console: Cloud Storage > Insights > Datasets > Create."
          ),
          error=error,
      )
    elif status_code == 403:
      return _bq_failure(
          impact="Caller lacks BigQuery permissions to query the dataset.",
          fix=(
              "Grant roles/bigquery.dataViewer on the dataset and"
              " roles/bigquery.jobUser on the project."
          ),
          error=error,
      )

    return _bq_failure(
        impact=f"Unexpected HTTP {status_code} from BigQuery.",
        fix=(
            "Retry the preflight check. If the failure persists, see"
            " https://status.cloud.google.com for ongoing GCP incidents."
        ),
        error=error,
    )
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    return _bq_failure(
        impact="Network or transport failure contacting BigQuery.",
        fix="Check network connectivity and GCP reachability.",
        error=str(e),
    )


def run_preflight(*, project_id: str, dataset_name: str) -> Mapping[str, Any]:
  """Runs all preflight checks and aggregates them into a readiness report.

  Only the ADC check is *required*: without working credentials no GCP API
  call can be made and the assessment cannot run at all. The Storage Insights
  enablement and BigQuery dataset access checks are *recommended* — when they
  fail the assessment does not stop; it degrades to a project-level posture
  report (IAM, VPC-SC, audit logs, org policies, Model Armor) and recommends
  enabling Storage Insights / creating a linked dataset to unlock the full
  bucket- and object-level assessment.

  The returned `analysis_scope` tells the skill which mode to run:
    * "full"         — SI enabled and the linked dataset is queryable.
    * "project_only" — ADC works but SI and/or the dataset are unavailable.
    * "none"         — ADC failed; the assessment cannot run.

  Args:
    project_id: GCP project ID for downstream checks.
    dataset_name: Storage Insights linked dataset name.

  Returns:
    Mapping with `ready_to_proceed` (bool), `analysis_scope` (str), `required`
    (list of check results), `recommended` (list of check results), and a
    human-readable `summary`.
  """
  adc = _check_adc()
  if adc["status"] != "ok":
    return {
        "ready_to_proceed": False,
        "analysis_scope": "none",
        "required": [adc],
        "recommended": [],
        "summary": (
            "ADC check failed — cannot authenticate to GCP, so the assessment"
            " cannot run. Address the required check below and re-run"
            " preflight."
        ),
    }

  with cloud_rest_helpers_nodeps.get_authorized_session(
      skill=_SKILL, script=_SCRIPT, project_id=project_id
  ) as session:
    si_check = _check_storage_insights_enabled(
        project_id=project_id, session=session
    )
    if si_check["status"] == "ok":
      bq_check = _check_bigquery_dataset_access(
          project_id=project_id,
          dataset_name=dataset_name,
          session=session,
      )
    else:
      bq_check = {
          "check": "bigquery_dataset_access",
          "status": "skipped",
          "impact": (
              "Skipped because Storage Insights is not enabled on the project."
          ),
      }

  recommended = [si_check, bq_check]
  full = si_check["status"] == "ok" and bq_check["status"] == "ok"
  if full:
    analysis_scope = "full"
    summary = "All checks passed — running the full assessment."
  else:
    analysis_scope = "project_only"
    summary = (
        "Storage Insights telemetry is unavailable — running a project-level"
        " assessment only. See the recommended check(s) below to unlock the"
        " full bucket- and object-level assessment."
    )

  return {
      "ready_to_proceed": True,
      "analysis_scope": analysis_scope,
      "required": [adc],
      "recommended": recommended,
      "summary": summary,
  }


def main() -> None:
  parser = argparse.ArgumentParser(
      description=(
          "Preflight permission check for the GCS security assessment skill."
      )
  )
  parser.add_argument("--project_id", required=True, help="GCP project ID")
  parser.add_argument(
      "--dataset_name",
      required=True,
      help="Storage Insights linked BigQuery dataset name",
  )
  args = parser.parse_args()

  result = run_preflight(
      project_id=args.project_id, dataset_name=args.dataset_name
  )
  print(json.dumps(result, indent=2))
  sys.exit(0)


if __name__ == "__main__":
  main()
