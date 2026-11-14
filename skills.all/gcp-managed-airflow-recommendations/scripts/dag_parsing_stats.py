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
"""Script to fetch DAG parsing stats for a Managed Airflow environment."""

import argparse
import collections
import datetime
import json

from lib import monitoring

NUM_POINTS = 10


def main():
  parser = argparse.ArgumentParser(
      description="Calculate DAG processing stats."
  )
  parser.add_argument("--project_id", type=str, required=True)
  parser.add_argument("--location", type=str, required=True)
  parser.add_argument("--environment_name", type=str, required=True)
  parser.add_argument("--query_duration_hours", type=int, required=True)
  parser.add_argument(
      "--query_end_time", type=str, required=False, default=None
  )

  args = parser.parse_args()

  step_seconds = (args.query_duration_hours * 3600) // NUM_POINTS

  common_filter = (
      'monitored_resource="cloud_composer_environment",'
      f'project_id="{args.project_id}",'
      f'environment_name="{args.environment_name}",'
      f'location="{args.location}"'
  )

  query = f"""
label_replace(
  sum(increase({{__name__="composer.googleapis.com/environment/dag_processing/parse_error_count",{common_filter}}}[{step_seconds}s])),
  "stat", "parseErrors", "", ""
)
or
label_replace(
  sum(increase({{__name__="composer.googleapis.com/environment/dag_processing/processor_timeout_count",{common_filter}}}[{step_seconds}s])),
  "stat", "processorTimeouts", "", ""
)
or
label_replace(
  avg(avg_over_time({{__name__="composer.googleapis.com/environment/dag_processing/total_parse_time",{common_filter}}}[{step_seconds}s])),
  "stat", "avgTotalParseTime", "", ""
)
or
label_replace(
  max(max_over_time({{__name__="composer.googleapis.com/environment/dag_processing/total_parse_time",{common_filter}}}[{step_seconds}s])),
  "stat", "maxTotalParseTime", "", ""
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

  data = monitoring.fetch_time_series_promql(args.project_id, params)

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
            "parseErrors": 0,
            "processorTimeouts": 0,
            "avgTotalParseTime": "0s",
            "maxTotalParseTime": "0s",
        }

      if stat == "parseErrors":
        output[timestamp_sec]["parseErrors"] = int(value_float)
      elif stat == "processorTimeouts":
        output[timestamp_sec]["processorTimeouts"] = int(value_float)
      elif stat == "avgTotalParseTime":
        output[timestamp_sec][
            "avgTotalParseTime"
        ] = f"{int(round(value_float))}s"
      elif stat == "maxTotalParseTime":
        output[timestamp_sec][
            "maxTotalParseTime"
        ] = f"{int(round(value_float))}s"

  sorted_points = [output[ts] for ts in sorted(output.keys())]
  print(json.dumps({"dag_parsing_stats": sorted_points}, indent=2))


if __name__ == "__main__":
  main()
