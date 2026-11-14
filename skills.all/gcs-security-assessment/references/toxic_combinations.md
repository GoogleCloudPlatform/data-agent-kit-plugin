# Toxic Combination Archetypes

These are the core risk archetypes your assessment evaluates. Each defines a
specific "toxic combination" — a set of individually low-risk configurations
that together create a critical security exposure.

> [!IMPORTANT]
> The detailed reasoning below is for YOUR understanding of the
> toxic combinations. When presenting findings to the user, condense each
> reasoning to 2-3 sentences. The user is a Storage Admin, not a security
> researcher.

> [!IMPORTANT]
> Your value is in connecting the dots. Do NOT just list individual
> misconfigurations. For each matching archetype, explain the **attack path** or
> **failure mode** that the combination enables. This is what separates you from
> a config checker.

## How to Match Archetypes

For each bucket, compare its telemetry against each archetype below. A bucket
matches an archetype when it exhibits the majority of the telemetry signals
listed. Not every signal needs to match — use judgment about which combinations
are dangerous in context.

> [!IMPORTANT]
> **Baseline-only failures do NOT match any archetype.** If a
> bucket's only deviations are baseline controls — UBLA disabled, object
> versioning off, soft delete off, Data Access audit logs disabled, and/or
> default GMEK encryption — it must NOT be labeled with any toxic-combination
> archetype. These are common defaults across most projects; an archetype
> requires at least one **additional risk factor** beyond baselines.
>
> Additional risk factors that qualify a bucket for archetype matching:
>
> -   **Over-permissioned IAM** — service accounts or users holding
>     `roles/storage.admin` or `roles/storage.objectAdmin` where a viewer-tier
>     role would suffice.
> -   **Public access enabled** — `allUsers` or `allAuthenticatedUsers` holds a
>     role on the bucket or its objects.
> -   **Data-residency mismatch** — bucket location is a multi-region (or
>     non-compliant region) containing data subject to regional regulations, AND
>     no org policy constrains resource locations.
> -   **AI-agent workload context** — Model Armor API enabled in the project
>     (signaling Vertex AI Agent Engine / Agent Builder usage), combined with
>     agent-side configuration like a service account holding broad storage
>     roles.
>
> A bucket failing only baseline controls is reported in the Section 2 baseline
> rollups and labeled "Baseline failures" in per-bucket cards — not with any
> archetype name.

A single bucket may match multiple archetypes. Report all matches.

--------------------------------------------------------------------------------

## Public Data Pipeline

**Base Severity:** Critical

**Telemetry Pattern:**

-   Bucket/Object classified as sensitive (or unclassified)
-   Bucket is publicly accessible (has public read or public write objects)
-   UBLA disabled (ACLs active alongside IAM)
-   Object encryption is managed with Google-default (GMEK), no CMEK
-   No VPC-SC perimeter
-   Data Access audit logs disabled

**Required Reasoning:** UBLA being disabled means ACLs operate alongside IAM,
creating a shadow access path. The allUsers ACL grants public read access to
training data even if IAM appears locked down. Without CMEK, the organization
cannot revoke encryption keys to cut off access in an emergency. No VPC-SC
perimeter means data can be copied to any external project with no exfiltration
boundary. Data Access audit logs being disabled means there is no record of who
accessed the data — ongoing exfiltration is undetectable.

The key insight: each gap amplifies the others. Publicly accessible data + no
key control + no network boundary + no audit trail = total exposure.

**SAIF Risks:** Unauthorized Training Data, Data Poisoning, Model Exfiltration,
Sensitive Data Disclosure

**Remediation:**

-   Enforce Uniform Bucket-Level Access: `gcloud storage buckets update
    gs://BUCKET --uniform-bucket-level-access`
-   Block public access: `gcloud storage buckets update gs://BUCKET
    --public-access-prevention`
-   Enable CMEK: See GCS CMEK documentation —
    https://cloud.google.com/storage/docs/encryption/customer-managed-keys
    -   Rewrite existing objects with CMEK key to update encryption of existing
        objects
-   Create VPC-SC perimeter: `gcloud access-context-manager perimeters create
    PERIMETER_NAME --title='AI Assets Perimeter'
    --resources=projects/PROJECT_NUMBER
    --restricted-services=storage.googleapis.com --policy=POLICY_ID`
-   Enable Data Access audit logs: Update project audit config for
    `storage.googleapis.com` with DATA_READ and DATA_WRITE

--------------------------------------------------------------------------------

## Silent Data Theft

**Base Severity:** Critical

**Telemetry Pattern:**

-   Over-permissioned service account (e.g., `roles/storage.admin` when
    `roles/storage.objectViewer` suffices)
-   No VPC-SC perimeter
-   Data Access audit logs disabled
-   Bucket is private (no public read or public write objects) — this is a
    positive signal that creates false confidence
-   CMEK configured for objects in the bucket — another positive signal that
    creates false confidence

**Required Reasoning:** While some controls are properly configured (no public
access, CMEK enabled), the combination of missing controls creates an invisible
exfiltration path. The over-permissioned service account can read, write,
delete, and modify IAM on every bucket. If compromised or behaving as a rogue
agent, it has full control. Without VPC-SC, nothing prevents copying data to an
external project. Without Data Access audit logs, these operations leave no
trace.

The key insight: the bucket being private and encrypted creates a **false sense
of security**. The exfiltration path through the service account is wide open
and completely invisible.

**SAIF Risks:** Model Exfiltration, Model Source Tampering, Rogue Actions

**Remediation:**

-   Reduce service account to least privilege: `gcloud projects
    add-iam-policy-binding PROJECT_ID --member='serviceAccount:SA_EMAIL'
    --role='roles/storage.objectViewer'` then `gcloud projects
    remove-iam-policy-binding PROJECT_ID --member='serviceAccount:SA_EMAIL'
    --role='roles/storage.admin'`
-   Create VPC-SC perimeter: `gcloud access-context-manager perimeters create
    PERIMETER_NAME --title='AI Assets Perimeter'
    --resources=projects/PROJECT_NUMBER
    --restricted-services=storage.googleapis.com --policy=POLICY_ID`
-   Enable Data Access audit logs: Update project audit config for
    `storage.googleapis.com` with DATA_READ and DATA_WRITE. Scope to high-value
    buckets.

--------------------------------------------------------------------------------

## Irreversible Data Corruption

**Base Severity:** High

**Telemetry Pattern:**

-   Object versioning disabled
-   Soft delete disabled (0-day retention)
-   Over-permissioned IAM (multiple users with `roles/storage.objectAdmin`)
-   Encryption is Google-default (GMEK), no CMEK
-   Data Access audit logs disabled

**Required Reasoning:** Without object versioning, any modification overwrites
the original with no rollback. Without soft delete, deletion is permanent and
immediate. Combined with multiple users having objectAdmin (write + delete), any
user could poison data or corrupt files. Without Data Access audit logs, the
organization cannot determine who modified what. Without CMEK, they cannot
revoke access at the key level in an emergency.

The key insight: no versioning + no soft delete + broad write access + no audit
trail = **undetectable and unrecoverable** data tampering.

**SAIF Risks:** Data Poisoning, Model Source Tampering

**Remediation:**

-   Enable object versioning: `gcloud storage buckets update gs://BUCKET
    --versioning`
-   Enable soft delete: `gcloud storage buckets update gs://BUCKET
    --soft-delete-duration=7d`
-   Enable CMEK: See GCS CMEK documentation —
    https://cloud.google.com/storage/docs/encryption/customer-managed-keys
-   Reduce write permissions: Grant `roles/storage.objectViewer` or
    `roles/storage.objectCreator` instead of `roles/storage.objectAdmin`.
    `gcloud storage buckets add-iam-policy-binding gs://BUCKET
    --member='user:USER_EMAIL' --role='roles/storage.objectViewer'` then `gcloud
    storage buckets remove-iam-policy-binding gs://BUCKET
    --member='user:USER_EMAIL' --role='roles/storage.objectAdmin'`
-   Enable Data Access audit logs: Update project audit config for
    `storage.googleapis.com` with DATA_READ and DATA_WRITE.

--------------------------------------------------------------------------------

## Intentional Public Data

**Base Severity:** Low

**Telemetry Pattern:**

-   Bucket classified as non-sensitive (via tags, labels, or naming heuristics)
-   Public access enabled — **intentional and expected**
-   UBLA enabled
-   Object versioning disabled
-   Soft delete disabled
-   Data Access audit logs disabled

> [!CAUTION]
> This archetype ONLY applies when the bucket is classified as
> non-sensitive or the context clearly indicates public data (marketing assets,
> public docs, open datasets). If the bucket is classified as high-sensitivity
> and public, that is a **classification mismatch** — see
> `bucket_classification.md`.

**Required Reasoning:** Public access is intentional and must NOT be recommended
for removal. However, intentionally public data still has integrity and
availability risks. Without versioning, content can be silently overwritten
(defacement). Without soft delete, content can be permanently deleted. Without
audit logging, unauthorized modifications go undetected.

The key insight: the skill must **respect the intended use case** while still
flagging integrity/availability gaps.

**SAIF Risks:** Model Source Tampering (if public data feeds downstream
pipelines)

**Remediation:**

-   Enable object versioning for defacement protection: `gcloud storage buckets
    update gs://BUCKET --versioning`
-   Enable soft delete for deletion recovery: `gcloud storage buckets update
    gs://BUCKET --soft-delete-duration=7d`
-   Enable Data Access audit logs for write operations: Update project audit
    config for `storage.googleapis.com` with DATA_WRITE.
-   **NOTE: Public access is recognized as intentional. No changes to access
    controls are recommended.**

--------------------------------------------------------------------------------

## Compliance Without Proof

**Base Severity:** High

**Telemetry Pattern:**

-   No data residency org policy
-   Bucket location is multi-region containing data subject to regional
    regulations (e.g., EU data in US multi-region)
-   Encryption is Google-default (GMEK), no CMEK
-   Data Access audit logs disabled
-   Bucket is private (public access prevention enforced) — positive signal
-   UBLA enabled — positive signal

**Required Reasoning:** Despite good access controls (UBLA, private access), the
project has critical compliance gaps. Data stored in a non-compliant region with
no residency org policy may violate regulations like GDPR. Without CMEK, the
organization cannot demonstrate key sovereignty. Without Data Access audit logs,
they cannot prove who accessed data or fulfill data subject access requests.

The key insight: the data is technically secure from external threats but the
organization **cannot demonstrate compliance to regulators**. Infrastructure
that looks secure but cannot withstand a regulatory audit.

**SAIF Risks:** Sensitive Data Disclosure, Excessive Data Handling

**Remediation:**

-   Set org policy to restrict resource locations: `gcloud resource-manager
    org-policies set-policy --project=PROJECT_ID policy.yaml` (constrain to
    compliant regions)
-   Migrate bucket to compliant region: `gcloud storage buckets create
    gs://NEW_BUCKET --location=COMPLIANT_REGION` then `gcloud storage rsync
    gs://OLD_BUCKET gs://NEW_BUCKET --recursive`
-   Enable CMEK: See GCS CMEK documentation —
    https://cloud.google.com/storage/docs/encryption/customer-managed-keys
    -   Enable Data Access audit logs: Update project audit config for
        `storage.googleapis.com` with DATA_READ and DATA_WRITE.

--------------------------------------------------------------------------------

## Prompt Injection to Data Destruction

**Base Severity:** Critical

**Telemetry Pattern:**

-   Model Armor API enabled BUT Vertex AI integration NOT activated AND no
    templates created
-   Agent service account with `roles/storage.admin` at project level
-   No VPC-SC perimeter
-   Data Access audit logs disabled
-   Object versioning disabled
-   Soft delete disabled
-   Encryption is Google-default (GMEK), no CMEK
-   UBLA enabled — positive signal
-   Bucket is private — positive signal

> [!IMPORTANT]
> This archetype applies specifically to projects running AI agents
> (Vertex AI Agent Engine, Agent Builder). If the project has no AI agent
> workloads, this archetype does not apply. Look for Model Armor being enabled
> as a signal that the project has AI workloads.

**Required Reasoning:** Trace the full attack path from prompt to data
destruction. Model Armor floor settings exist and the API is enabled, but Vertex
AI integration is not activated — meaning Gemini calls from the agent bypass
Model Armor entirely. This is the most dangerous type of false signal: Model
Armor configuration suggests protections when they are not enforced.

A successful prompt injection reaches the model unscreened. The compromised
model instructs the agent to use its `roles/storage.admin` access to: read any
object (exfiltration), write/overwrite objects (poisoning), delete objects
(destruction), or modify IAM (escalation). Without VPC-SC, exfiltrated data
leaves freely. Without audit logs, actions leave no trace. Without versioning or
soft delete, damage is irrecoverable. Without CMEK, no emergency key revocation.

The key insight: every layer of defense is either absent or misconfigured. One
prompt injection **chains through the entire stack** unimpeded.

**SAIF Risks:** Prompt Injection, Rogue Actions, Sensitive Data Disclosure,
Model Exfiltration, Data Poisoning, Model Source Tampering

**Remediation:**

-   **URGENT** — Reduce agent service account to least privilege: `gcloud
    projects remove-iam-policy-binding PROJECT_ID
    --member='serviceAccount:AGENT_SA' --role='roles/storage.admin'` then
    `gcloud storage buckets add-iam-policy-binding gs://SPECIFIC_BUCKET
    --member='serviceAccount:AGENT_SA' --role='roles/storage.objectViewer'`
-   **URGENT** — Activate Model Armor Vertex AI integration: `gcloud model-armor
    floorsettings update
    --full-uri=projects/PROJECT_ID/locations/global/floorSetting
    --add-integrated-services=VERTEX_AI
    --vertex-ai-enforcement-type=INSPECT_AND_BLOCK`
-   Create Model Armor screening template: `gcloud model-armor templates create
    agent-protection --location=us-central1
    --rai-settings-filters='[{"filterType":"HATE_SPEECH","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"DANGEROUS","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"HARASSMENT","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"MEDIUM_AND_ABOVE"}]'
    --pi-and-jailbreak-filter-settings-enforcement=enabled
    --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above
    --malicious-uri-filter-settings-enforcement=enabled`
-   Enable object versioning: `gcloud storage buckets update gs://BUCKET
    --versioning`
-   Enable soft delete: `gcloud storage buckets update gs://BUCKET
    --soft-delete-duration=7d`
-   Enable CMEK: See GCS CMEK documentation —
    https://cloud.google.com/storage/docs/encryption/customer-managed-keys
    -   Create VPC-SC perimeter: `gcloud access-context-manager perimeters
        create agent-perimeter --title='Agent Workload Perimeter'
        --resources=projects/PROJECT_NUMBER
        --restricted-services=storage.googleapis.com,aiplatform.googleapis.com
        --policy=POLICY_ID`
-   Enable Data Access audit logs: Update project audit config for
    `storage.googleapis.com` with DATA_READ and DATA_WRITE.
