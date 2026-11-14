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

"""Script to fetch telemetry from a Storage Insights bucket."""

import argparse
from collections.abc import Mapping, Sequence
import json
import textwrap
from typing import Any

import cloud_rest_helpers_nodeps
import validation

_SKILL = "gcs-security-assessment"
_SCRIPT = "fetch-bucket-telemetry"


# TODO: Update scoring logic to be more robust.
def _calculate_risk_score(telemetry: Sequence[Mapping[str, Any]]) -> str:
  """Calculates the risk score for a list of telemetry data.

  Args:
    telemetry: List of telemetry data to calculate the risk score.

  Returns:
    The risk score as a string in the format "X/100".
  """
  risky_missing_fields = [
      "ubla_enabled",
      "soft_delete_retention_seconds",
      "enforced_encryption_types",
      "versioning",
  ]

  bucket_risk_score_total = 0
  for bucket in telemetry:
    for risky_missing_field in risky_missing_fields:
      if not bucket[risky_missing_field]:
        bucket_risk_score_total += 1

  bucket_risk_score_average = int(
      (
          bucket_risk_score_total
          / (len(risky_missing_fields) * (len(telemetry) or 1))
      )
      * 100
  )
  return f"{bucket_risk_score_average}/100"


def fetch_bucket_telemetry(
    *,
    project_id: str,
    dataset_name: str,
    bucket_names: Sequence[str] | None = None,
) -> tuple[str, Sequence[Mapping[str, Any]]]:
  """Fetches bucket telemetry signals from BigQuery.

  Queries the latest snapshot from the Storage Insights bucket_attributes
  table. Results are always restricted to buckets owned by project_id, since
  the dataset may be org- or folder-scoped and contain buckets from other
  projects. If bucket_names is provided, only those buckets are returned;
  otherwise all of the project's buckets in the dataset are returned.

  Args:
    project_id: The GCP project ID.
    dataset_name: The linked dataset name.
    bucket_names: Optional list of bucket names to filter on.

  Returns:
    A tuple containing the overall risk score and the telemetry data.

  Raises:
    cloud_rest_helpers_nodeps.CloudRestError: If the REST query fails.
    RuntimeError: If the query job does not complete in time.
  """
  validation.validate_inputs(project_id, dataset_name, bucket_names)  # pyrefly: ignore[bad-argument-type]

  if not bucket_names:
    bucket_filter = ""
    bucket_parameters = []
  else:
    bucket_filter = "AND name IN UNNEST(@bucket_names)"
    bucket_parameters = [{
        "name": "bucket_names",
        "parameterType": {
            "type": "ARRAY",
            "arrayType": {"type": "STRING"},
        },
        "parameterValue": {
            "arrayValues": [
                {"value": bucket_name} for bucket_name in bucket_names
            ]
        },
    }]

  # Sometimes regional jobs are ingested with the new snapshotTime before others
  # are finished. This means it's possible to have two snapshots that are both
  # latest for different buckets. We partition to find this latest snapshot per
  # bucket.
  query = textwrap.dedent(f"""
      SELECT
        name AS bucket_name,
        versioning,
        iamConfiguration.uniformBucketLevelAccess.enabled AS ubla_enabled,
        softDeletePolicy.retentionDurationSeconds
            AS soft_delete_retention_seconds,
        enforcedEncryptionAllowedTypes,
        resourceTags
      FROM
        (
          SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY name ORDER BY snapshotTime DESC) as rn
          FROM
            `{project_id}.{dataset_name}.bucket_attributes_view`
          WHERE
            snapshotTime >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 DAY)
            AND project = @project_number
            {bucket_filter}
        )
      WHERE
        rn = 1;
  """).strip()

  with cloud_rest_helpers_nodeps.get_authorized_session(
      skill=_SKILL, script=_SCRIPT, project_id=project_id
  ) as session:
    # The dataset may be org- or folder-scoped and contain buckets from other
    # projects; the views identify the owning project by project number only.
    project_number = cloud_rest_helpers_nodeps.get_project_number(
        project_id=project_id, session=session
    )
    payload = {
        "query": query,
        "useLegacySql": False,
        "parameterMode": "NAMED",
        "queryParameters": [
            {
                "name": "project_number",
                "parameterType": {"type": "INT64"},
                "parameterValue": {"value": str(project_number)},
            },
            *bucket_parameters,
        ],
    }
    schema_fields, rows = cloud_rest_helpers_nodeps.execute_bigquery_query(
        project_id=project_id,
        payload=payload,
        session=session,
        skill=_SKILL,
        script=_SCRIPT,
    )

  telemetry = []
  for r in rows:
    r_f = r.get("f", [])
    row_dict = {
        f["name"]: cloud_rest_helpers_nodeps.parse_bq_value(
            r_f[i].get("v") if i < len(r_f) else None, f
        )
        for i, f in enumerate(schema_fields)
    }
    telemetry.append({
        "bucket": row_dict.get("bucket_name"),
        "ubla_enabled": bool(row_dict.get("ubla_enabled")),
        "soft_delete_retention_seconds": row_dict.get(
            "soft_delete_retention_seconds"
        ),
        "enforced_encryption_types": list(
            row_dict.get("enforcedEncryptionAllowedTypes") or []
        ),
        "versioning": row_dict.get("versioning"),
        "tags": row_dict.get("resourceTags") or [],
    })

  return _calculate_risk_score(telemetry), telemetry


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Script to fetch telemetry from a Storage Insights bucket."
  )
  parser.add_argument(
      "--project_id", type=str, required=True, help="The GCP project ID."
  )
  parser.add_argument(
      "--dataset_name", type=str, required=True, help="The linked dataset name."
  )
  parser.add_argument(
      "--bucket_names",
      type=str,
      help=(
          "Comma-separated list of bucket names to query. If not provided, all"
          " buckets in the dataset are analyzed."
      ),
  )
  args = parser.parse_args()

  bucket_names = (
      [b.strip() for b in args.bucket_names.split(",")]
      if args.bucket_names
      else None
  )

  try:
    risk_score, telemetry = fetch_bucket_telemetry(
        project_id=args.project_id,
        dataset_name=args.dataset_name,
        bucket_names=bucket_names,
    )
    print(
        json.dumps({"risk_score": risk_score, "telemetry": telemetry}, indent=2)
    )
  except (
      cloud_rest_helpers_nodeps.CloudRestError,
      RuntimeError,
      TypeError,
      ValueError,
  ) as e:
    print(json.dumps({"error": repr(e)}))


if __name__ == "__main__":
  main()
