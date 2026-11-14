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
"""Script to calculate disk usage of Managed Airflow components."""

import argparse
import collections
import datetime
import json

from lib import flagutils
from lib import monitoring

NUM_POINTS = 10


def main():
  parser = argparse.ArgumentParser(
      description="Calculate disk usage of Managed Airflow components."
  )
  parser.add_argument(
      "--project_id", type=str, required=True, help="GCP project ID"
  )
  parser.add_argument(
      "--location", type=str, required=True, help="GCP location"
  )
  parser.add_argument(
      "--environment_name",
      type=str,
      required=True,
      help="Managed Airflow environment name",
  )
  parser.add_argument(
      "--components",
      type=str,
      required=False,
      help=(
          "Comma-separated list of Managed Airflow components to query"
          " (default: all)"
      ),
  )
  parser.add_argument(
      "--query_duration_hours",
      type=int,
      required=True,
      help="Query duration in hours (minimum 1 hour)",
  )
  parser.add_argument(
      "--query_end_time",
      type=str,
      required=False,
      default=None,
      help="Query end time in ISO 8601 format (default: now)",
  )
  args = parser.parse_args()

  if args.query_duration_hours < 1:
    print("Error: Query duration must be at least 1 hour.")
    return

  components = flagutils.parse_components_flag(args.components)

  # Calculate step (duration / 10)
  step_seconds = (args.query_duration_hours * 3600) // NUM_POINTS
  common_filter = (
      'monitored_resource="cloud_composer_workload",'
      f'project_id="{args.project_id}",'
      f'environment_name="{args.environment_name}",'
      f'location="{args.location}",'
      f'type=~"{"|".join(components)}"'
  )

  query = f"""
label_replace(
  sum by (type)(avg_over_time({{__name__="composer.googleapis.com/workload/disk/quota",{common_filter}}}[{step_seconds}s])),
  "stat", "totalLimit", "", ""
)
or
label_replace(
  sum by (type)(avg_over_time({{__name__="composer.googleapis.com/workload/disk/bytes_used",{common_filter}}}[{step_seconds}s])),
  "stat", "totalUsage", "", ""
)
or
label_replace(
  max by (type)(avg_over_time({{__name__="composer.googleapis.com/workload/disk/bytes_used",{common_filter}}}[{step_seconds}s])),
  "stat", "maxUsage", "", ""
)
or
label_replace(
  avg by (type)(avg_over_time({{__name__="composer.googleapis.com/workload/disk/bytes_used",{common_filter}}}[{step_seconds}s])),
  "stat", "avgUsage", "", ""
)
"""

  end_time = datetime.datetime.now(datetime.timezone.utc).timestamp()
  if args.query_end_time:
    end_time = datetime.datetime.fromisoformat(args.query_end_time).timestamp()
  start_time = end_time - (args.query_duration_hours * 3600)

  params = {
      "query": query,
      "start": start_time,
      "end": end_time,
      "step": f"{step_seconds}s",
  }

  try:
    data = monitoring.fetch_time_series_promql(args.project_id, params)
  except Exception as e:
    print(f"Failed to fetch data: {e}")
    return

  output = collections.defaultdict(dict)

  for result in data.get("data", {}).get("result", []):
    component_upper = result["metric"].get("type")
    if not component_upper:
      continue
    component = component_upper.lower()

    stat = result["metric"].get("stat")

    for val in result["values"]:
      timestamp_sec = int(val[0])
      value_float = float(val[1]) / (1024 * 1024 * 1024)
      end_dt_str = datetime.datetime.fromtimestamp(
          timestamp_sec, datetime.timezone.utc
      ).isoformat()
      start_dt_str = datetime.datetime.fromtimestamp(
          timestamp_sec - step_seconds, datetime.timezone.utc
      ).isoformat()
      if timestamp_sec not in output[component]:
        output[component][timestamp_sec] = {
            "startTime": start_dt_str,
            "endTime": end_dt_str,
        }
      output[component][timestamp_sec][stat] = round(value_float, 3)

  final_output = {}
  for comp, points in output.items():
    sorted_points = [points[ts] for ts in sorted(points.keys())]
    final_output[comp] = sorted_points

  print("Workload disk usage (in GiB):")
  print(json.dumps(final_output, indent=2))


if __name__ == "__main__":
  main()
