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
"""A script to create and monitor Dataplex data profile scans.

This script takes a list of BigQuery tables, initiates Dataplex data profile
scans for each table, and polls the scan status until results are available.
The results are saved as JSON files in a specified output directory.
"""

import argparse
import asyncio
import json
import logging
import os
import uuid

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def run_command_async(cmd: str) -> str:
  """Runs a shell command asynchronously and returns the stdout."""
  process = await asyncio.create_subprocess_shell(
      cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
  )
  stdout, stderr = await process.communicate()

  if process.returncode != 0:
    raise RuntimeError(
        f"Command failed: {cmd}\nError: {stderr.decode('utf-8')}"
    )

  return stdout.decode("utf-8")


async def get_table_row_count(table_ref: str) -> int:
  """Gets the row count of a BigQuery table using count(*)."""
  cmd = (
      "bq query --quiet --nouse_legacy_sql --format=json "
      f"'SELECT count(*) as count FROM `{table_ref}`'"
  )
  output = await run_command_async(cmd)
  try:
    results = json.loads(output)
    return int(results[0]["count"])
  except Exception as e:
    raise RuntimeError(
        f"Failed to get row count for {table_ref}\nOutput: {output}"
    ) from e


async def create_and_wait_for_scan(
    table_id: str,
    location: str,
    output_dir: str,
):
  """Creates a DataPlex data-profile scan for a table and waits for results.

  Args:
      table_id: BigQuery table in `project.dataset.table` format.
      location: Google Cloud region (e.g., 'us-central1').
      output_dir: Directory to save the resulting JSON profile.
  """
  parts = table_id.split(".")
  if len(parts) == 3:
    project, dataset, table = parts
    data_source_resource = f"//bigquery.googleapis.com/projects/{project}/datasets/{dataset}/tables/{table}"
    bq_table_ref = f"{project}.{dataset}.{table}"
  elif len(parts) == 4:
    project, catalog, namespace, table = parts
    data_source_resource = f"//biglake.googleapis.com/iceberg/v1/restcatalog/v1/projects/{project}/catalogs/{catalog}/namespaces/{namespace}/tables/{table}"
    bq_table_ref = f"{project}.{catalog}.{namespace}.{table}"
  else:
    logging.error(
        "[%s] Invalid format. Expected 'project.dataset.table' or"
        " 'project.catalog.namespace.table'. Skipping.",
        table_id,
    )
    return

  profile_name = f"data-profile-{uuid.uuid4().hex[:8]}"

  try:
    row_count = await get_table_row_count(bq_table_ref)
    logging.info("[%s] Row count: %s", table_id, row_count)
  except Exception as e:  # pylint: disable=broad-exception-caught
    logging.exception("[%s] Error getting row count: %s", table_id, e)
    return

  if row_count == 0:
    logging.info("[%s] Table is empty (0 records). Returning early.", table_id)
    return

  sampling_percent = None
  if row_count > 1000000:
    sampling_percent = round((1000000 / row_count) * 100.0, 2)
    sampling_percent = max(0.01, min(sampling_percent, 100.0))
    logging.info(
        "[%s] Large table (%s rows). Calculated sampling percent: %s%%",
        table_id,
        row_count,
        sampling_percent,
    )

  # Construct the base create command
  create_cmd_parts = [
      f"gcloud dataplex datascans create data-profile {profile_name}",
      f"--location={location}",
      f'--data-source-resource="{data_source_resource}"',
      f"--project={project}",
      "--one-time",
      '--ttl-after-scan-completion="2400s"',
      "--format=json",
  ]

  if sampling_percent is not None:
    create_cmd_parts.append(f"--sampling-percent={sampling_percent}")

  create_cmd = " ".join(create_cmd_parts)

  logging.info("[%s] Creating Dataplex profile: %s", table_id, profile_name)
  try:
    await run_command_async(create_cmd)
    logging.info(
        "[%s] Profile %s successfully initiated.", table_id, profile_name
    )
  except Exception as e:  # pylint: disable=broad-exception-caught
    logging.exception("[%s] Failed to create scan: %s", table_id, e)
    return

  # Construct the describe command to poll for results
  describe_cmd = (
      f"gcloud dataplex datascans describe {profile_name} "
      f"--location={location} "
      f"--project={project} "
      "--view=full "
      "--format=json"
  )

  logging.info("[%s] Waiting for profile results...", table_id)
  max_retries = 50
  sleep_seconds = 5  # Poll every 5 seconds

  for attempt in range(1, max_retries + 1):
    try:
      output = await run_command_async(describe_cmd)
      result = json.loads(output)

      # Check if scan results are populated
      if "dataProfileResult" in result and result["dataProfileResult"]:
        result_data = result["dataProfileResult"]
        # Also ensure the profile internals are populated
        if "profile" in result_data:
          logging.info(
              "[%s] Profile results ready after %s attempt(s)!",
              table_id,
              attempt,
          )

          output_file = os.path.join(output_dir, f"{table}_{profile_name}.json")
          with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

          logging.info("[%s] Results saved to %s", table_id, output_file)
          return

    except Exception as e:  # pylint: disable=broad-exception-caught
      logging.warning(
          "[%s] Error describing scan on attempt %s: %s", table_id, attempt, e
      )

    logging.info(
        "[%s] Results not ready yet, waiting %ss... (Attempt %s/%s)",
        table_id,
        sleep_seconds,
        attempt,
        max_retries,
    )
    await asyncio.sleep(sleep_seconds)

  logging.error(
      "[%s] Timeout waiting for results after %ss.",
      table_id,
      max_retries * sleep_seconds,
  )


async def main():
  parser = argparse.ArgumentParser(
      description="Create and wait for Dataplex datascans concurrently."
  )
  parser.add_argument(
      "--tables",
      nargs="+",
      required=True,
      help="List of BigQuery tables in project.dataset.table format",
  )
  parser.add_argument(
      "--location",
      required=True,
      help=(
          "Google Cloud location/region (e.g., us-central1). DO NOT use"
          " multi-regions."
      ),
  )
  parser.add_argument(
      "--output-dir",
      required=True,
      help="Directory to save the resulting JSON profiles",
  )
  args = parser.parse_args()

  # Create the output directory upfront
  os.makedirs(args.output_dir, exist_ok=True)

  logging.info("Starting %s scan(s) in %s", len(args.tables), args.location)

  # Run all table scans concurrently
  tasks = [
      create_and_wait_for_scan(table, args.location, args.output_dir)
      for table in args.tables
  ]

  await asyncio.gather(*tasks)
  logging.info("All scan tasks completed.")


if __name__ == "__main__":
  asyncio.run(main())
