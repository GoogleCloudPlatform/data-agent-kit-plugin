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
"""Script to calculate health percentage of Managed Airflow environment."""

import argparse
import collections
import datetime
import json

from lib import monitoring

NUM_POINTS = 10


def main():
  parser = argparse.ArgumentParser(
      description="Calculate health percentage of Managed Airflow environment."
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

  step_seconds = (args.query_duration_hours * 3600) // NUM_POINTS
  common_filter = (
      'monitored_resource="cloud_composer_environment",'
      f'project_id="{args.project_id}",'
      f'environment_name="{args.environment_name}",'
      f'location="{args.location}"'
  )

  query = f"""
label_replace(
  avg_over_time({{__name__="composer.googleapis.com/environment/healthy",{common_filter}}}[{step_seconds}s]),
  "stat", "envHealth", "", ""
)
or
label_replace(
  avg_over_time({{__name__="composer.googleapis.com/environment/database_health",{common_filter}}}[{step_seconds}s]),
  "stat", "databaseHealth", "", ""
)
or
label_replace(
  avg_over_time({{__name__="composer.googleapis.com/environment/web_server/health",{common_filter}}}[{step_seconds}s]),
  "stat", "webserverHealth", "", ""
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
    stat = result["metric"].get("stat")
    if not stat:
      continue

    for val in result["values"]:
      timestamp_sec = int(val[0])
      value_float = float(val[1])

      end_dt_str = datetime.datetime.fromtimestamp(
          timestamp_sec, datetime.timezone.utc
      ).isoformat()
      start_dt_str = datetime.datetime.fromtimestamp(
          timestamp_sec - step_seconds, datetime.timezone.utc
      ).isoformat()

      if timestamp_sec not in output:
        output[timestamp_sec] = {
            "startTime": start_dt_str,
            "endTime": end_dt_str,
        }

      percent_val = round(value_float * 100)
      output[timestamp_sec][stat] = f"{percent_val}%"

  final_list = [output[ts] for ts in sorted(output.keys())]

  # Ensure all expected stats are present in every point even if missing
  expected_stats = ["envHealth", "databaseHealth", "webserverHealth"]
  for point in final_list:
    for stat in expected_stats:
      if stat not in point:
        point[stat] = "N/A"

  final_output = {"environment_health": final_list}

  print(json.dumps(final_output, indent=2))


if __name__ == "__main__":
  main()
