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

"""Script to fetch aggregated object-level telemetry for buckets in a Storage Insights dataset."""

import argparse
from collections.abc import Mapping, Sequence
import json
import textwrap
from typing import Any

import cloud_rest_helpers_nodeps
import validation

_SKILL = "gcs-security-assessment"
_SCRIPT = "fetch-object-telemetry"


def fetch_object_telemetry(
    project_id: str,
    dataset_name: str,
    bucket_names: Sequence[str] | None = None,
) -> Sequence[Mapping[str, Any]]:
  """Fetches object telemetry signals from BigQuery.

  Queries the latest snapshot from the Storage Insights
  object_attributes_latest_snapshot_view. Results are always restricted to
  buckets owned by project_id, since the dataset may be org- or folder-scoped
  and contain buckets from other projects.

  Args:
    project_id: The GCP project ID.
    dataset_name: The linked dataset name.
    bucket_names: Optional list of bucket names to filter on.

  Returns:
    A list of dictionaries containing telemetry signals per object.

  Raises:
    cloud_rest_helpers_nodeps.CloudRestError: If the REST query fails.
    RuntimeError: If the query job does not complete in time.
  """
  validation.validate_inputs(project_id, dataset_name, bucket_names)  # pyrefly: ignore[bad-argument-type]

  if not bucket_names:
    bucket_filter = ""
    bucket_parameters = []
  else:
    bucket_filter = "AND bucket IN UNNEST(@bucket_names)"
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

  query = textwrap.dedent(f"""
      SELECT
        bucket,
        COUNT(*) AS total_objects,
        COUNTIF(securityInsights.publicAccessInsight.readPublicAccess = 'PUBLIC') AS public_read_objects,
        COUNTIF(securityInsights.publicAccessInsight.writePublicAccess = 'PUBLIC') AS public_write_objects,
        COUNTIF(retentionExpirationTime IS NOT NULL) AS objects_with_retention,
        COUNTIF(encryptionType = 'CMEK') AS cmek_objects,
        COUNTIF(encryptionType = 'CSEK') AS csek_objects,
        COUNTIF(encryptionType = 'GMEK') AS gmek_objects
      FROM
        `{project_id}.{dataset_name}.object_attributes_latest_snapshot_view`
      WHERE
        project = @project_number
        {bucket_filter}
      GROUP BY
        bucket
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
        "bucket": row_dict.get("bucket"),
        "total_objects": row_dict.get("total_objects"),
        "public_read_objects": row_dict.get("public_read_objects"),
        "public_write_objects": row_dict.get("public_write_objects"),
        "objects_with_retention": row_dict.get("objects_with_retention"),
        "cmek_objects": row_dict.get("cmek_objects"),
        "csek_objects": row_dict.get("csek_objects"),
        "gmek_objects": row_dict.get("gmek_objects"),
    })

  return telemetry


def main() -> None:
  parser = argparse.ArgumentParser(
      description=(
          "Script to fetch aggregated object-level telemetry for buckets in a"
          " Storage Insights dataset."
      )
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

  telemetry = fetch_object_telemetry(
      project_id=args.project_id,
      dataset_name=args.dataset_name,
      bucket_names=bucket_names,
  )
  print(json.dumps(telemetry, indent=2))


if __name__ == "__main__":
  main()
