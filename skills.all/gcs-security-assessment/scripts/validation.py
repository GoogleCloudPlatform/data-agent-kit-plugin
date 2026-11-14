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

"""Validation logic for telemetry scripts."""

import re


def validate_project_id(project_id: str) -> None:
  """Validates a GCP project ID for safe SQL/URL interpolation.

  Args:
    project_id: The GCP project ID.

  Raises:
    TypeError: If project_id is not a string.
    ValueError: If project_id contains a backtick.
  """
  if not isinstance(project_id, str):
    raise TypeError(f"project_id must be a string, got {type(project_id)}")

  # Legacy project IDs can violate modern format rules, so we only block
  # backticks which would break out of BigQuery's backtick-delimited
  # identifiers.
  if "`" in project_id:
    raise ValueError(
        "project_id contains backtick, which is not safe for SQL"
        f" interpolation: {project_id}"
    )


def validate_inputs(
    project_id: str,
    dataset_name: str,
    bucket_names: list[str] | None = None,
) -> None:
  """Validates project_id, dataset_name, and bucket_names.

  This function helps ensure that the calling agent passes correctly typed
  arguments and guards against SQL injection in interpolated strings
  (project_id and dataset_name).

  Args:
    project_id: The GCP project ID.
    dataset_name: The linked dataset name.
    bucket_names: Optional list of bucket names to filter on.

  Raises:
    TypeError: If any of the inputs have invalid types.
    ValueError: If any of the inputs are invalidly formatted.
  """
  validate_project_id(project_id)
  if not isinstance(dataset_name, str):
    raise TypeError(f"dataset_name must be a string, got {type(dataset_name)}")

  # Matches 1-1024 char BigQuery dataset names: alphanumeric and underscores.
  dataset_name_regex = re.compile(r"^[a-zA-Z0-9_]{1,1024}$")
  if not dataset_name_regex.match(dataset_name):
    raise ValueError(f"Invalid dataset_name format: {dataset_name}")

  if bucket_names is not None:
    if not isinstance(bucket_names, list):
      raise TypeError(f"bucket_names must be a list, got {type(bucket_names)}")

    # Matches 3-63 char GCS bucket names: alphanumeric start/end,
    # alphanumeric/dot/dash/underscore middle.
    bucket_name_regex = re.compile(r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$")
    for bucket_name in bucket_names:
      if not isinstance(bucket_name, str):
        raise TypeError(
            f"bucket name must be a string, got {type(bucket_name)}"
        )
      if not bucket_name_regex.match(bucket_name):
        raise ValueError(f"Invalid bucket_name format: {bucket_name}")
