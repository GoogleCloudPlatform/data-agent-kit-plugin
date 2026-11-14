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
"""Library for parsing and validating flags."""


def parse_components_flag(components_str: str) -> list[str]:
  """Parses a comma-separated string of components."""
  valid_components = [
      "CELERY_WORKER",
      "KUBERNETES_WORKER",
      "KUBERNETES_OPERATOR_POD",
      "SCHEDULER",
      "DAG_PROCESSOR",
      "TRIGGERER",
      "WEB_SERVER",
  ]
  if not components_str or components_str.upper() == "ALL":
    return valid_components
  components = [c.strip().upper() for c in components_str.split(",")]
  invalid_components = [c for c in components if c not in valid_components]
  if invalid_components:
    raise ValueError(
        f"Invalid components: {', '.join(invalid_components)}. Valid components"
        f" are: {', '.join(valid_components)} or 'all'."
    )
  return [c.upper() for c in components]
