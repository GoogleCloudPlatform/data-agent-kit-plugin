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

"""Evaluates the security posture of a subset of GCS project level settings."""

from __future__ import annotations

import argparse
from collections.abc import Collection, Mapping, MutableMapping
import enum
import json
from typing import Any, TypedDict

import cloud_rest_helpers_nodeps

_TIMEOUT_SECONDS = 5
_STORAGE_API = "storage.googleapis.com"
_ALL_SERVICES = "allServices"
_DATA_READ = "DATA_READ"
_DATA_WRITE = "DATA_WRITE"
_VPC_SC_WILDCARD = "*"

_ORG_POLICY_API = "https://orgpolicy.googleapis.com/v2/projects"
_CLOUD_RESOURCE_MANAGER_API = "https://cloudresourcemanager.googleapis.com/v3"
_ACCESS_CONTEXT_MANAGER_API = "https://accesscontextmanager.googleapis.com/v1"
_MODEL_ARMOR_API = "https://modelarmor.googleapis.com/v1/projects"
# The aggregated `locations/-/templates` call fans out to every regional control
# plane, so it needs a longer timeout than per-region/global Model Armor calls.
_MODEL_ARMOR_TEMPLATES_TIMEOUT_SECONDS = 30

_SKILL = "gcs-security-assessment"
_SCRIPT = "evaluate-project-security-posture"


class OrgPolicySecureTypeEnum(enum.Enum):
  """The condition for a secure org policy.

  Attributes:
    ENFORCED: The 'enforce' rule is set to True.
    NO_ALLOW_ALL: The 'allowAll' is not present in the rules.
    RESTRICT_AUTH_TYPES: The HMAC signed-request auth types are denied.
  """

  ENFORCED = 1
  NO_ALLOW_ALL = 2
  RESTRICT_AUTH_TYPES = 3


_HMAC_AUTH_TYPES = frozenset({
    "USER_ACCOUNT_HMAC_SIGNED_REQUESTS",
    "SERVICE_ACCOUNT_HMAC_SIGNED_REQUESTS",
})
_HMAC_AUTH_GROUPS = frozenset({
    "in:ALL_HMAC_SIGNED_REQUESTS",
    "in:ALL_SIGNED_REQUESTS",
})


class _NoAllowAllOrgPolicyRuleValue(TypedDict, total=False):
  """OrgPolicy rule values for NO_ALLOW_ALL policies.

  These names are based on the response received from the JSON payload response
  returned from the OrgPolicy API.

  Attributes:
    allowedValues: The specific list of values that are allowed for this policy.
    deniedValues: The specific list of values that are denied for this policy.
  """

  allowedValues: Collection[str]  # pylint: disable=invalid-name
  deniedValues: Collection[str]  # pylint: disable=invalid-name


class _NoAllowAllOrgPolicyRule(TypedDict, total=False):
  """OrgPolicy rule types for NO_ALLOW_ALL policies.

  These names are based on the response received from the JSON payload response
  returned from the OrgPolicy API.

  Attributes:
    values: Specific list of allow/deny values for this rule (these will
      override the allowAll/denyAll values).
    allowAll: Whether the policy rule allows all values.
    denyAll: Whether the policy rule denies all values.
  """

  values: _NoAllowAllOrgPolicyRuleValue
  allowAll: bool  # pylint: disable=invalid-name
  denyAll: bool  # pylint: disable=invalid-name


class _EnforcedOrgPolicyRule(TypedDict, total=False):
  """OrgPolicy rule types for ENFORCED policies."""

  enforce: bool


def _check_no_allow_all_org_policy(
    rules: (
        Collection[_NoAllowAllOrgPolicyRule]
        | Collection[_EnforcedOrgPolicyRule]
    ),
) -> bool:
  """Checks if the provided OrgPolicy rules enforce at least one restriction.

  A "no allowAll" OrgPolicy is considered secure if:
  - Any rule has "denyAll" set to True.
  - Any rule contains "deniedValues".
  - There is at least one rule present and "allowAll" is not set to True at all.

  Args:
    rules: A list of rules for a specific OrgPolicy.

  Returns:
    True if the rules are securely configured (i.e., no "allowAll" without
    denial), False otherwise.
  """
  if any(rule.get("denyAll", False) for rule in rules):
    # Deny rules always override allow rules.
    return True

  for rule in rules:
    values = rule.get("values") or {}
    if values.get("deniedValues", []) or values.get("allowedValues", []):  # pyrefly: ignore[missing-attribute]
      # Deny rules always override allow rules.
      return True
  # If a rule is empty or only has allowAll enabled with no overrides, it is
  # considered insecure.
  return bool(rules and not any(rule.get("allowAll") for rule in rules))


def _check_restrict_auth_types_org_policy(
    rules: Collection[_NoAllowAllOrgPolicyRule],
) -> bool:
  """Checks if the provided OrgPolicy rules restrict HMAC authentication.

  A storage.restrictAuthTypes OrgPolicy is considered secure if:
  - Any rule has "denyAll" set to True.
  - Any rule denies all HMAC requests via a group (e.g.,
    "in:ALL_HMAC_SIGNED_REQUESTS" or "in:ALL_SIGNED_REQUESTS").
  - The denied values across rules include both user and service account HMAC
    signed requests.

  Args:
    rules: A list of rules for a specific OrgPolicy.

  Returns:
    True if HMAC authentication is restricted, False otherwise.
  """
  if any(rule.get("denyAll", False) for rule in rules):
    return True

  denied_values: set[str] = set()
  for rule in rules:
    values = rule.get("values") or {}
    for denied in values.get("deniedValues", []):
      if denied in _HMAC_AUTH_GROUPS:
        return True
      denied_values.add(denied)

  return _HMAC_AUTH_TYPES.issubset(denied_values)


def check_secure_org_policies_enforced(
    *,
    project_id: str,
    authorized_session: Any,
) -> Mapping[str, bool | Mapping[str, str]]:
  """Determines if a subset of org policies are set to a secure value for the project.

  Args:
      project_id: The GCP project ID to check.
      authorized_session: The AuthorizedSession to use for API requests.

  Returns:
      A dictionary mapping each policy name to a bool
      indicating whether the policy is securely configured. Errors are
      propagated to the dictionary as a string under the key "error" for each
      org policy.
  """
  org_policies: dict[str, OrgPolicySecureTypeEnum] = {
      "gcp.resourceLocations": OrgPolicySecureTypeEnum.NO_ALLOW_ALL,
      "gcp.restrictTLSVersion": OrgPolicySecureTypeEnum.NO_ALLOW_ALL,
      "storage.restrictAuthTypes": OrgPolicySecureTypeEnum.RESTRICT_AUTH_TYPES,
      "storage.secureHttpTransport": OrgPolicySecureTypeEnum.ENFORCED,
  }

  org_policy_results: MutableMapping[str, bool | MutableMapping[str, str]] = {}

  for policy_name, policy_type in org_policies.items():
    try:
      with authorized_session.request(
          method="GET",
          url=f"{_ORG_POLICY_API}/{project_id}/policies/{policy_name}:getEffectivePolicy",
          timeout=_TIMEOUT_SECONDS,
      ) as policy_response:
        policy_response.raise_for_status()
        policy = policy_response.json()
    except cloud_rest_helpers_nodeps.CloudRestError as e:
      org_policy_results[policy_name] = {"error": str(e)}
      continue

    rules = policy.get("spec", {}).get("rules", [])
    # These conditions expect to compare with the default values for the
    # policy, so if the rules are not configured, we consider the policy
    # to be set to its default value, which is insecure.
    if policy_type is OrgPolicySecureTypeEnum.ENFORCED:
      # Any enforced rule would be considered secure. A potential case where
      # there might be multiple rules is if a condition is bound to the
      # enforcement through tags.
      secure = any(rule.get("enforce", False) for rule in rules)
    elif policy_type is OrgPolicySecureTypeEnum.NO_ALLOW_ALL:
      secure = _check_no_allow_all_org_policy(rules)
    elif policy_type is OrgPolicySecureTypeEnum.RESTRICT_AUTH_TYPES:
      secure = _check_restrict_auth_types_org_policy(rules)
    else:
      org_policy_results[policy_name] = {"error": "Unable to evaluate policy."}
      continue
    org_policy_results[policy_name] = secure

  return org_policy_results


# TODO: Check org-level API as well for inherited policies.
def check_project_data_access_audit_logs_enabled(
    project_id: str,
    authorized_session: Any,
) -> Mapping[str, bool | str]:
  """Checks if DATA_ACCESS audit logs are enabled for the project.

  Args:
      project_id: GCP project ID
      authorized_session: AuthorizedSession to use for API requests

  Returns:
      A mapping of "DATA_READ" and "DATA_WRITE" to a boolean indicating if the
      respective audit log type is enabled. Returns a mapping of "error" to a
      string if one occurs during the API request.
  """
  try:
    with authorized_session.request(
        method="POST",
        url=f"{_CLOUD_RESOURCE_MANAGER_API}/projects/{project_id}:getIamPolicy",
        timeout=_TIMEOUT_SECONDS,
    ) as iam_response:
      iam_response.raise_for_status()
      iam_response_json = iam_response.json()
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    return {"error": str(e)}

  enabled_logs: MutableMapping[str, bool] = {
      _DATA_READ: False,
      _DATA_WRITE: False,
  }

  audit_configs = iam_response_json.get("auditConfigs") or []
  for config in audit_configs:
    service = config.get("service", "")
    if service not in (_STORAGE_API, _ALL_SERVICES):
      continue
    for audit_log_config in config.get("auditLogConfigs") or []:
      audit_log_type = audit_log_config.get("logType")
      if audit_log_type in enabled_logs:
        enabled_logs[audit_log_type] = True

      # Terminate early if all logs are enabled. Rules may be split across
      # storage and allServices.
      if all(enabled_logs.values()):
        return enabled_logs
  return enabled_logs


def _get_project_number_and_org_id(
    project_id: str,
    authorized_session: Any,
) -> tuple[str, str] | Mapping[str, str]:
  """Retrieves the project number and organization ID for a project ID.

  Traverses folders if necessary to get the organization ID.

  Args:
      project_id: GCP project ID.
      authorized_session: AuthorizedSession to use for API requests.

  Returns:
      A tuple of (project_number, org_id) or a mapping with "error" key.
  """
  try:
    with authorized_session.request(
        method="GET",
        url=f"{_CLOUD_RESOURCE_MANAGER_API}/projects/{project_id}",
        timeout=_TIMEOUT_SECONDS,
    ) as response:
      response.raise_for_status()
      project_data = response.json()
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    return {"error": f"Failed to get project data: {e}"}

  project_number_path = project_data.get("name", "")
  parent = project_data.get("parent", "")

  while parent and parent.startswith("folders/"):
    try:
      with authorized_session.request(
          method="GET",
          url=f"{_CLOUD_RESOURCE_MANAGER_API}/{parent}",
          timeout=_TIMEOUT_SECONDS,
      ) as response:
        response.raise_for_status()
        folder_data = response.json()
        parent = folder_data.get("parent", "")
    except cloud_rest_helpers_nodeps.CloudRestError as e:
      return {"error": f"Failed to get folder data for {parent}: {e}"}

  if not parent or not parent.startswith("organizations/"):
    return {"error": f"Could not find organization for project {project_id}."}

  return project_number_path, parent


# TODO: Add support for pagination in the API calls.
def check_vpc_sc_perimeter_enabled(
    *,
    project_id: str,
    authorized_session: Any,
) -> bool | Mapping[str, str]:
  """Checks if a VPC-SC perimeter restricting the storage API is enabled for the project.

  Args:
      project_id: GCP project ID.
      authorized_session: AuthorizedSession to use for API requests.

  Returns:
      True if a perimeter is enabled and secure, False otherwise.
      Returns a mapping with "error" key if an error occurs.
  """
  result = _get_project_number_and_org_id(project_id, authorized_session)
  if isinstance(result, Mapping) and "error" in result:
    return result

  if not isinstance(result, tuple):
    return {"error": "Failed to get project number and organization ID."}

  project_number_path, org_id_path = result

  try:
    with authorized_session.request(
        method="GET",
        url=(
            f"{_ACCESS_CONTEXT_MANAGER_API}/accessPolicies?parent={org_id_path}"
        ),
        timeout=_TIMEOUT_SECONDS,
    ) as response:
      response.raise_for_status()
      policies_data = response.json()
      policies = policies_data.get("accessPolicies") or []
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    return {"error": f"Failed to list access policies: {e}"}

  for policy in policies:
    policy_name = policy.get("name", "")
    try:
      with authorized_session.request(
          method="GET",
          url=f"{_ACCESS_CONTEXT_MANAGER_API}/{policy_name}/servicePerimeters",
          timeout=_TIMEOUT_SECONDS,
      ) as response:
        response.raise_for_status()
        perimeters_data = response.json()
        perimeters = perimeters_data.get("servicePerimeters") or []
    except cloud_rest_helpers_nodeps.CloudRestError as e:
      return {"error": f"Failed to list perimeters for {policy_name}: {e}"}

    for perimeter in perimeters:
      status = perimeter.get("status")
      if status is None:
        continue

      if perimeter.get("perimeterType") == "PERIMETER_TYPE_BRIDGE":
        continue

      resources = status.get("resources") or []
      if project_number_path not in resources:
        continue

      restricted_services = status.get("restrictedServices") or []
      if (
          "storage.googleapis.com" in restricted_services
          or _VPC_SC_WILDCARD in restricted_services
      ):
        return True

  return False


def check_model_armor_status(
    *,
    project_id: str,
    authorized_session: Any,
) -> Mapping[str, Any]:
  """Checks Model Armor enablement, floor settings, Vertex AI integration, and templates.

  Uses the Model Armor API itself as the enablement probe to avoid requiring
  Service Usage permissions. The floor settings GET is the lightest possible
  call (single global resource, single permission). A SERVICE_DISABLED error
  from this call unambiguously means the API is not enabled on the project; a
  generic 403 means the caller lacks `modelarmor.floorsettings.get` and the
  signals are reported as unknown via an error mapping.

  Args:
    project_id: The GCP project ID to check.
    authorized_session: The AuthorizedSession to use for API requests.

  Returns:
    A mapping containing Model Armor signals: `api_enabled` (always present),
    plus `floor_settings_configured`, `vertex_ai_integration`, and
    `templates` (a sub-mapping with `count` or `error`) when the API is
    enabled. Returns `{"error": str}` if the caller lacks permissions or
    another transport failure occurs.
  """
  floor_setting_url = (
      f"{_MODEL_ARMOR_API}/{project_id}/locations/global/floorSetting"
  )
  try:
    with authorized_session.request(
        method="GET",
        url=floor_setting_url,
        timeout=_TIMEOUT_SECONDS,
    ) as response:
      if response.status_code == 404:
        # API enabled but no FloorSetting resource has been created yet.
        floor_setting: Mapping[str, Any] = {}
      else:
        response.raise_for_status()
        floor_setting = response.json()
  except cloud_rest_helpers_nodeps.HttpError as e:
    if cloud_rest_helpers_nodeps.is_service_disabled_error(e):
      return {"api_enabled": False}
    return {"error": str(e)}
  # CloudRestError covers transport-layer failures (no HTTP response received).
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    return {"error": str(e)}

  filter_config = floor_setting.get("filterConfig") or {}
  integrated_services = floor_setting.get("integratedServices") or []
  result: dict[str, Any] = {
      "api_enabled": True,
      "floor_settings_configured": bool(filter_config),
      "vertex_ai_integration": "VERTEX_AI" in integrated_services,
  }

  # Use the `-` location wildcard to list templates across all regions.
  templates_url = f"{_MODEL_ARMOR_API}/{project_id}/locations/-/templates"
  try:
    with authorized_session.request(
        method="GET",
        url=templates_url,
        timeout=_MODEL_ARMOR_TEMPLATES_TIMEOUT_SECONDS,
    ) as response:
      response.raise_for_status()
      templates_data = response.json()
  except cloud_rest_helpers_nodeps.CloudRestError as e:
    result["templates"] = {"error": str(e)}
    return result

  templates = templates_data.get("templates") or []
  result["templates"] = {"count": len(templates)}
  return result


def main() -> None:
  parser = argparse.ArgumentParser(
      description=(
          "Evaluates the security posture of a subset of GCP project level"
          " settings."
      )
  )
  parser.add_argument(
      "--project_id", type=str, required=True, help="The GCP project ID."
  )
  args = parser.parse_args()

  try:
    authorized_session = cloud_rest_helpers_nodeps.get_authorized_session(
        skill=_SKILL, script=_SCRIPT, project_id=args.project_id
    )
  except cloud_rest_helpers_nodeps.CredentialsError as e:
    print(f"Failed to get authorized session using credentials: {e}")
    return

  print(
      json.dumps(
          {
              "project_id": args.project_id,
              "details": {
                  "org_policy": check_secure_org_policies_enforced(
                      project_id=args.project_id,
                      authorized_session=authorized_session,
                  ),
                  "audit_logs": check_project_data_access_audit_logs_enabled(
                      project_id=args.project_id,
                      authorized_session=authorized_session,
                  ),
                  "vpc_sc_perimeter": check_vpc_sc_perimeter_enabled(
                      project_id=args.project_id,
                      authorized_session=authorized_session,
                  ),
                  "model_armor": check_model_armor_status(
                      project_id=args.project_id,
                      authorized_session=authorized_session,
                  ),
              },
          },
          indent=2,
      )
  )


if __name__ == "__main__":
  main()
