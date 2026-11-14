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

"""Script to list Storage Insights datasets.

This script lists all DatasetConfigs within a specified GCP project and location
using the Storage Insights API.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, MutableSequence, Sequence
import json
from typing import Any

import cloud_rest_helpers_nodeps

_TIMEOUT_SECONDS = 10
_SKILL = "gcs-security-assessment"
_SCRIPT = "list-datasets"

# Warnings attached to dataset entries whose config ingests resources beyond
# the assessed project. Keyed by the scope returned by _dataset_scope().
_NON_PROJECT_SCOPE_WARNINGS: Mapping[str, str] = {
    "organization": (
        "This dataset config is organization-scoped: it ingests metadata"
        " from every project in the organization, not just the assessed"
        " project. Bucket and object telemetry results are restricted to"
        " buckets owned by the target project."
    ),
    "folders": (
        "This dataset config is folder-scoped: it ingests metadata from"
        " every project under its source folders, not just the assessed"
        " project. Bucket and object telemetry results are restricted to"
        " buckets owned by the target project."
    ),
}

# Warning for a project-scoped config whose source projects include projects
# other than the assessed one.
_MULTI_PROJECT_WARNING = (
    "This dataset config ingests metadata from projects other than the"
    " assessed project. Bucket and object telemetry results are restricted"
    " to buckets owned by the target project."
)

# Warning for a project-scoped config whose source projects do not include
# the assessed project at all.
_NO_TARGET_PROJECT_WARNING = (
    "This dataset config does not ingest the assessed project: its source"
    " projects do not include it. Bucket and object telemetry will return"
    " no results for the target project."
)


def _dataset_scope(config: Mapping[str, Any]) -> str:
  """Returns the resource scope of a dataset config.

  A dataset config ingests metadata from an entire organization, a set of
  folders, or a set of projects. Anything broader than "projects" means the
  linked dataset contains buckets owned by projects other than the one being
  assessed.

  Args:
    config: A DatasetConfig resource from the Storage Insights API.

  Returns:
    One of "organization", "folders", or "projects".
  """
  if config.get("organizationScope"):
    return "organization"
  if config.get("sourceFolders"):
    return "folders"
  return "projects"


def list_datasets(
    *,
    project_id: str,
    location: str,
    session: Any,
) -> Sequence[Mapping[str, str]]:
  """Lists Storage Insights linked datasets using public HTTP REST endpoint.

  Args:
    project_id: The GCP project ID.
    location: The dataset location.
    session: The authorized session to make requests.

  Returns:
    A list of dictionaries mapping {"{LOCATION_NAME}": "{DATASET_ID}",
    "description": "{DESCRIPTION}", "scope": "{SCOPE}"} where each field is
    extracted from the SI dataset. Scope is "organization", "folders", or
    "projects" depending on which resources the dataset config ingests. An
    entry whose config spans resources beyond the assessed project — scope
    "organization" or "folders", or a project-scoped config whose source
    projects include others or omit the assessed project entirely — also
    carries a "warning" explaining that.

  Raises:
    RuntimeError: If the request fails.
  """
  url = f"https://storageinsights.googleapis.com/v1/projects/{project_id}/locations/{location}/datasetConfigs"
  try:
    response = session.get(url, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    raise RuntimeError(
        f"Failed to fetch dataset configs for '{location}':'{project_id}' with"
        f" error: {e!r}"
    ) from e
  else:
    data = response.json()
  configs = data.get("datasetConfigs") or []
  # sourceProjects lists project numbers, so comparing against the input
  # project ID requires resolving it once up front.
  target_project_number: str | None = None
  if any(config.get("sourceProjects") for config in configs):
    try:
      target_project_number = str(
          cloud_rest_helpers_nodeps.get_project_number(
              project_id=project_id, session=session
          )
      )
    except cloud_rest_helpers_nodeps.CloudRestError:
      target_project_number = None
  result: MutableSequence[Mapping[str, str]] = []
  for config in configs:
    name = config.get("name") or ""
    link = config.get("link") or {}
    description = config.get("description") or ""
    if link.get("linked") and link.get("dataset") and "/locations/" in name:
      # Config names look like projects/N/locations/LOC/datasetConfigs/ID.
      _, location_path = name.split("/locations/")
      loc, *_ = location_path.split("/")
      scope = _dataset_scope(config)
      entry = {
          loc: str(link.get("dataset")),
          "description": description,
          "scope": scope,
      }
      # Organization and folder-scoped configs always span beyond the
      # assessed project.
      warning = _NON_PROJECT_SCOPE_WARNINGS.get(scope)
      if scope == "projects" and target_project_number is not None:
        source_projects = config.get("sourceProjects") or {}
        source_numbers = {
            str(number)
            for number in source_projects.get("projectNumbers") or []
        }
        # A project-scoped config warns when it skips the assessed project
        # entirely, or additionally ingests other projects.
        if source_numbers and target_project_number not in source_numbers:
          warning = _NO_TARGET_PROJECT_WARNING
        elif source_numbers - {target_project_number}:
          warning = _MULTI_PROJECT_WARNING
      if warning is not None:
        entry["warning"] = warning
      result.append(entry)
  return result


def main() -> None:
  parser = argparse.ArgumentParser(
      description="List Storage Insights datasets for a project and location."
  )
  parser.add_argument(
      "--project_id", type=str, required=True, help="The GCP project ID."
  )
  parser.add_argument(
      "--location", type=str, default="-", help="The dataset location."
  )
  args = parser.parse_args()

  try:
    with cloud_rest_helpers_nodeps.get_authorized_session(
        skill=_SKILL, script=_SCRIPT, project_id=args.project_id
    ) as session:
      datasets = list_datasets(
          project_id=args.project_id,
          location=args.location,
          session=session,
      )
      print(json.dumps(datasets, indent=2))
  except (
      cloud_rest_helpers_nodeps.CredentialsError,
      RuntimeError,
  ) as e:
    print(json.dumps({"error": repr(e)}))


if __name__ == "__main__":
  main()
