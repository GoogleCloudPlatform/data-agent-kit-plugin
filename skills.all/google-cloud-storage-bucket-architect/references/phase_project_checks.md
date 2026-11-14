# Phase 1: Project-Level Security Checks

> [!IMPORTANT]
> This phase is critical for establishing a secure baseline. Always
> verify project-level settings (TLS, HTTPS, HMAC, Liens) before drafting any
> Cloud Storage bucket configuration. If a project is insecure, warn the user
> and recommend remediation.

This phase focuses on assessing baseline project-level security settings before
designing a new Cloud Storage bucket. These checks are non-blocking, but missing
permissions will limit the scope of the assessment.

## Step 1: Execute Project Verification Commands

If the user explicitly instructs not to run any `gcloud` commands (or not to
execute any commands at all), the agent MUST NOT run the `gcloud` commands
below. Instead, skip Step 1 and proceed to Step 2, reporting the status for all
checks as Undetermined (⚠️) due to user constraints. (An instruction not to
execute bucket creation or mutating commands does NOT skip these read-only
project checks.)

Otherwise, the agent must execute the following `gcloud` commands (always
including the inline `CLOUDSDK_METRICS_ENVIRONMENT` prefix) to gather
project-level configurations. Before executing, tell the user that a secure
bucket configuration also relies on secure project settings:

### 1. Verification of Org Policies

Run the following command for each constraint
(`constraints/gcp.restrictTLSVersion`,
`constraints/storage.secureHttpTransport`,
`constraints/storage.restrictAuthTypes`):

```bash
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
gcloud org-policies describe <CONSTRAINT> --project=<PROJECT_ID> --effective --format=json
```

*   **For `storage.secureHttpTransport`**: Secure if `spec.rules[0].enforce` is
    `true`.
*   **For `gcp.restrictTLSVersion`**: Secure if the policy is enforced and
    denies older TLS versions.
*   **For `storage.restrictAuthTypes`**: Secure if the policy is enforced and
    restricts insecure auth types.
*   *If the command returns a permission denied error for a missing permission,
    report status as `⚠️` and specify that `orgpolicy.policy.get` is required
    (or indicate a potential VPC-SC restriction).*
*   *If the command returns a permission denied error because the Organization
    Policy API has not been used in project, then it should be marked as
    insecure ❌*.

### 2. Verification of Project Liens

Run the following command:

```bash
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
gcloud alpha resource-manager liens list --project=<PROJECT_ID> --format=json
```

*   **Secure (✅)**: The output contains a list with at least one lien.
*   **Insecure (❌)**: The output is an empty list `[]`.
*   *If the command returns a permission denied error, report status as `⚠️` and
    specify that `resourcemanager.projects.get` is required (or indicate a
    potential VPC-SC restriction).*

## Step 2: Interpret and Present Results

The agent MUST interpret the results of the commands executed in Step 1 and
present a summary to the user using the following status indicators:

*   ✅ **Secure**: The constraint/setting is securely configured.
*   ❌ **Insecure**: The constraint/setting is NOT securely configured (insecure
    default or explicitly disabled). If any "Insecure" results are present, the
    agent MUST warn the user and recommend remediation for each insecure setting
    (e.g., enforcing the corresponding Org Policy or creating project liens).
*   ⚠️ **Undetermined**: The status could not be determined due to lack of
    permissions or VPC-SC restrictions. The agent must explicitly state the
    reason (e.g. missing permission or VPC-SC denial). If any "Undetermined"
    results are present, the agent MUST append a note recommending the user
    contact their system administrator for help with setting these values if
    they don't have a method of setting them.

### Status Mapping Table

Check             | Target / Constraint                       | Secure Condition                                 | Status: ✅   | Status: ❌              | Status: ⚠️ (Undetermined)
:---------------- | :---------------------------------------- | :----------------------------------------------- | :---------: | :--------------------: | :------------------------
**TLS 1.2**       | `constraints/gcp.restrictTLSVersion`      | Policy is enforced and denies TLS versions < 1.2 | Enforced    | Not Enforced / Allowed | Requires `orgpolicy.policy.get`
**HTTPS Only**    | `constraints/storage.secureHttpTransport` | Policy is enforced                               | Enforced    | Not Enforced           | Requires `orgpolicy.policy.get`
**Restrict HMAC** | `constraints/storage.restrictAuthTypes`   | Policy is enforced and restricts HMAC keys       | Enforced    | Not Enforced           | Requires `orgpolicy.policy.get`
**Project Liens** | Liens                                     | At least one active lien exists on the project   | Lien exists | No Liens               | Requires `resourcemanager.projects.get`

### Example Output Presentation

```markdown
### Project-Level Security Posture Assessment

*   ❌ **TLS 1.2 Enforcement**: Insecure (Older TLS versions allowed).
*   ❌ **HTTPS Only**: Insecure (Non-secure HTTP transport allowed).
*   ❌ **Restrict HMAC Keys**: Insecure (HMAC key creation is not restricted).
*   ❌ **Project Liens**: Insecure (No active liens protect project from accidental deletion).

**Remediation Recommendations:**
*   **TLS 1.2 Enforcement**: Enforce the Organization Policy `constraints/gcp.restrictTLSVersion` to deny TLS versions older than 1.2.
*   **HTTPS Only**: Enforce the Organization Policy `constraints/storage.secureHttpTransport` to require secure HTTPS transport for all Cloud Storage operations.
*   **Restrict HMAC Keys**: Enforce the Organization Policy `constraints/storage.restrictAuthTypes` to restrict HMAC key creation.
*   **Project Liens**: Create at least one project lien using `gcloud alpha resource-manager liens create` to protect the project from accidental deletion.
```
