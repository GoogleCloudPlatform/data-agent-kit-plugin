# gcloud Command Generation Guide

> [!IMPORTANT]
>
> **DO NOT EXECUTE THESE COMMANDS AUTOMATICALLY.** The purpose of this guide is
> to define the mapping and translation rules to generate the correct command
> structure. These generated commands must be presented to the user for
> confirmation and are only executed in a subsequent phase if explicit
> confirmation is granted by the user.

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the corresponding `gcloud storage` commands.

## Official Documentation References

*   [gcloud storage buckets create](https://cloud.google.com/sdk/gcloud/reference/storage/buckets/create)
*   [gcloud storage buckets update](https://cloud.google.com/sdk/gcloud/reference/storage/buckets/update)
*   [gcloud storage buckets add-iam-policy-binding](https://cloud.google.com/sdk/gcloud/reference/storage/buckets/add-iam-policy-binding)
*   [gcloud storage objects update](https://cloud.google.com/sdk/gcloud/reference/storage/objects/update)
*   [gcloud storage cp](https://cloud.google.com/sdk/gcloud/reference/storage/cp)
*   [gcloud storage buckets notifications create](https://cloud.google.com/sdk/gcloud/reference/storage/buckets/notifications/create)
*   [gcloud storage buckets anywhere-caches create](https://cloud.google.com/sdk/gcloud/reference/storage/buckets/anywhere-caches/create)
*   [Create zonal buckets](https://cloud.google.com/storage/docs/rapid/create-zonal-buckets)
*   [Domain-named bucket verification](https://cloud.google.com/storage/docs/domain-name-verification)
*   [Host a static website](https://cloud.google.com/storage/docs/hosting-static-website)

--------------------------------------------------------------------------------

> [!CAUTION]
>
> **DO NOT HALLUCINATE GCLOUD FLAGS.** The `gcloud storage` CLI syntax and flags
> evolve. The agent MUST strictly ground all flags, settings, and argument
> formats in the provided reference and anything unclear should come from the
> `--help` flag. If it is still unclear, reference the official Google Cloud SDK
> documentation (linked above) before presenting them in the commands. Do not
> assume a flag exists or guess its name (e.g. do not guess
> `--enable-versioning` if it is `--versioning`). If unsure about a flag or its
> compatibility with other settings, the agent must perform a search or verify
> with official documentation first.

## Translation Mapping Table

Use this mapping table to translate draft configurations into `gcloud` flags or
secondary commands.

Draft Plan Field / Setting                | gcloud CLI Element / Flag                                                                                                                                               | Notes / Action
:---------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------
**Attribution**                           | `CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)"` | **CRITICAL: Required prefix for all gcloud commands.** Set inline.
**Bucket Name**                           | `gs://[bucket-name]`                                                                                                                                                    | Positional argument at the end of the `create` command. Must be globally unique.
**Project**                               | `--project=[project-id]`                                                                                                                                                | Global flag. Specify to ensure target project is correct.
**Location**                              | `--location=[location]`                                                                                                                                                 | E.g. `us-central1` (region), `US` (multi-region/custom dual-region), or `NAM4` (predefined dual-region). For zonal buckets (using the Rapid storage class), this must be the region (e.g. `us-east1`).
**Placement**                             | `--placement=[placement]`                                                                                                                                               | Used ONLY for custom dual-regions or zonal buckets. For custom dual-regions, set to a comma-separated list of regions (e.g., `us-east1,us-west1`) and `--location` to the geo area (e.g., `US`). For zonal buckets, set to the zone (e.g., `us-east1-b`) and `--location` to the region (e.g., `us-east1`).
**Replication Speed (RPO)**               | `--rpo=ASYNC_TURBO`                                                                                                                                                     | Optional. Enables Turbo Replication for dual-region buckets to guarantee replication within 15 minutes.
**Storage Class**                         | `--default-storage-class=[class]`                                                                                                                                       | Values: `STANDARD`, `NEARLINE`, `COLDLINE`, `ARCHIVE`, `RAPID`. Default is `STANDARD`. Must be explicitly set to `RAPID` for zonal buckets.
**UBLA**                                  | `--uniform-bucket-level-access`                                                                                                                                         | Boolean flag. Always enable this flag.
**Public Access Prevention**              | `--public-access-prevention` or `--no-public-access-prevention`                                                                                                         | A secure bucket should have this enabled. Only disable with clear use-case driven intent and explicit consent from the user.
**Soft Delete**                           | `--soft-delete-duration=[duration]`                                                                                                                                     | E.g., `7d` (7 days). Set to `0` to disable soft delete. Must be set to `0` (disabled) for zonal buckets.
**Object Versioning**                     | `gcloud storage buckets update gs://[bucket-name] --versioning` or `--no-versioning`                                                                                    | **Cannot be set during creation.** Enables/disables object versioning. Recommended as fallback if Soft Delete is disabled.
**Encryption (CMEK)**                     | `--default-encryption-key=[key-id]`                                                                                                                                     | Pass the full KMS key resource ID if CMEK is specified (format: `projects/[project-id]/locations/[location]/keyRings/[key-ring]/cryptoKeys/[my-key]`). Omit for GMEK.
**Restrict Encryption (CSEK)**            | `--encryption-enforcement-file=[file]`                                                                                                                                  | Uses a JSON file to set the encryption enforcement configuration. See **Helper Configuration Templates** below for an example.
**Autoclass**                             | `--enable-autoclass`                                                                                                                                                    | Boolean flag. *Incompatible with zonal buckets*.
**Hierarchical Namespace**                | `--enable-hierarchical-namespace`                                                                                                                                       | Boolean flag. Requires UBLA. Required for Zonal buckets.
**Labels**                                | `gcloud storage buckets update gs://[bucket-name] --update-labels=[key=value,...]`                                                                                      | **Cannot be set during creation.** Must be applied via a separate update command. The agent MUST explicitly state in the response or plan document that labels cannot be set during creation and explain why a separate update command is provided.
**IP Filtering**                          | `--ip-filter-file=[file]`                                                                                                                                               | JSON file defining IP access restrictions. See **Helper Configuration Templates** below.
**Cloud Logging (Usage Logs)**            | `gcloud storage buckets update gs://[bucket-name] --log-bucket=gs://[log-bucket] [--log-object-prefix=[prefix]]`                                                        | **Cannot be set during creation.** Enables usage and storage logging. The Google-managed group `cloud-storage-analytics@google.com` must be granted `roles/storage.objectCreator` on the log bucket.
**Lifecycle Policies (OLM)**              | `--lifecycle-file=[file]`                                                                                                                                               | JSON file defining OLM rules. See template below.
**CORS**                                  | `gcloud storage buckets update ... --cors-file=[file]`                                                                                                                  | **Cannot be set during creation.** Requires a separate `update` command. See **Helper Configuration Templates** below.
**Website Configuration**                 | `gcloud storage buckets update ... --web-main-page-suffix=[main] --web-error-page=[error]`                                                                              | **Cannot be set during creation.** Requires separate `update` command.
**Public IAM Policy**                     | `gcloud storage buckets add-iam-policy-binding ... --member=allUsers --role=roles/storage.objectViewer`                                                                 | **Cannot be set during creation.** Required to allow public read access for websites.
**Pub/Sub Notifications**                 | `gcloud storage buckets notifications create gs://[bucket-name] --topic=[topic-name]`                                                                                   | **Cannot be set during creation.** Creates a Pub/Sub notification configuration on the bucket to trigger events.
**Bucket Retention Period (Bucket Lock)** | `--retention-period=[duration]`                                                                                                                                         | Sets a default retention period for all objects. E.g. `1d43200s`. Supports standard durations (e.g. `90d`) or ISO 8601 (e.g. `P1Y1M1DT5S`).
**Lock Bucket Retention Policy**          | `gcloud storage buckets update gs://[bucket-name] --lock-retention-period`                                                                                              | Locks the retention policy. **Irreversible.**
**Object Retention (Object Lock)**        | `--enable-per-object-retention`                                                                                                                                         | Enables per-object retention. **Can only be set during bucket creation via gcloud.**
**Set Object Retention**                  | `gcloud storage objects update gs://[bucket]/[object] --retain-until=[timestamp] --retention-mode=[Locked/Unlocked]`                                                    | Sets retention on a specific object. Can also be set during upload.
**Rapid Cache**                           | `gcloud storage buckets anywhere-caches create gs://[bucket-name] [zone] --ttl=[duration]`                                                                              | **Cannot be set during creation.** Creates Rapid Cache instance for the bucket in the specified zone.

--------------------------------------------------------------------------------

## Helper Configuration Templates

When the plan requires complex configurations (CORS, Lifecycles, Encryption
Enforcement, IP Filters), you must write them to temporary JSON files in the
workspace before running `gcloud`.

### 1. Encryption Enforcement (`encryption_enforcement.json`)

Used to restrict CSEK:

```json
{
  "gmekEnforcement": {"restrictionMode": "NotRestricted"},
  "cmekEnforcement": {"restrictionMode": "NotRestricted"},
  "csekEnforcement": {"restrictionMode": "FullyRestricted"}
}
```

You must allow at least one encryption type. If you omit the enforcement
configuration for a specific encryption type, then that encryption type is
allowed by default on create.

### 2. CORS Template (`cors.json`)

Configure allowed domains and methods:

```json
[
  {
    "origin": ["https://my-website.appspot.com"],
    "method": ["GET", "POST", "PUT"],
    "responseHeader": ["Content-Type", "x-goog-resumable"],
    "maxAgeSeconds": 3600
  }
]
```

### 3. Lifecycle OLM Template (`lifecycle.json`)

Configure object deletion or transitions. e.g. aborting incomplete uploads and
deleting files after 365 days:

```json
{
  "rule": [
    {
      "action": {"type": "AbortIncompleteMultipartUpload"},
      "condition": {"age": 7}
    },
    {
      "action": {"type": "Delete"},
      "condition": {"age": 365}
    }
  ]
}
```

> [!WARNING]
> **Autoclass Restrictions**: If Autoclass is enabled on the bucket,
> the Object Lifecycle Management (OLM) configuration **MUST NOT** contain rules
> that use the `SetStorageClass` action or the `matchesStorageClass` condition.
> Combining Autoclass with these rules will cause the bucket creation or update
> to fail.

### 4. IP Filtering Template (`ip_filter.json`)

Configure allowed IP ranges and VPC networks:

```json
{
  "mode": "Enabled",
  "allowAllServiceAgentAccess": true,
  "allowCrossOrgVpcs": false,
  "publicNetworkSource": {
    "allowedIpCidrRanges": ["192.0.2.0/24", "198.51.100.0/32"]
  },
  "vpcNetworkSources": [
    {
      "network": "projects/PROJECT_ID/global/networks/NETWORK_NAME",
      "allowedIpCidrRanges": ["10.0.0.0/16"]
    }
  ]
}
```

--------------------------------------------------------------------------------

## Conversion Examples

### Example 1: Standard Secure Bucket (Baseline)

#### Input Draft Plan

```markdown
*   **Bucket Name**: `my-company-secure-bucket`
*   **Project**: `my-security-project`
*   **Location**: `us-east1`
*   **Storage Class**: `STANDARD`
*   **UBLA**: Enabled
*   **Public Access Prevention (PAP)**: Enforced
*   **Soft Delete**: Enabled (7 days)
*   **Encryption Enforcement**: CSEK Restricted
```

#### Output Commands

Create `encryption_enforcement.json` with CSEK restricted:

```json
{
  "gmekEnforcement": {"restrictionMode": "NotRestricted"},
  "cmekEnforcement": {"restrictionMode": "NotRestricted"},
  "csekEnforcement": {"restrictionMode": "FullyRestricted"}
}
```

gcloud Command:

```bash
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
gcloud storage buckets create gs://my-company-secure-bucket \
    --project=my-security-project \
    --location=us-east1 \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access \
    --public-access-prevention \
    --soft-delete-duration=7d \
    --encryption-enforcement-file=encryption_enforcement.json
```

--------------------------------------------------------------------------------

### Example 2: Sensitive Data / Compliance

#### Input Draft Plan

```markdown
*   **Bucket Name**: `my-compliance-pii-bucket`
*   **Project**: `my-compliance-project`
*   **Location**: `us-central1`
*   **Storage Class**: `STANDARD` (Autoclass will handle transitions)
*   **UBLA**: Enabled
*   **Public Access Prevention (PAP)**: Enforced
*   **Encryption Enforcement**: Restrict CSEK
*   **Encryption**: Customer-Managed Key (CMEK)
*   **Soft Delete**: Enabled (7 days)
*   **Bucket Lock (Retention Policy)**: Enabled (90 days, Unlocked)
*   **Use-case specific settings**:
    *   Autoclass: Enabled
    *   CMEK Key ID: `projects/my-kms-project/locations/us-central1/keyRings/my-keyring/cryptoKeys/my-key`
    *   Labels: `data-class=pii`, `owner=security-team`
    *   Lifecycle: Abort incomplete multipart uploads after 7 days
    *   IP Filtering: Restrict access to `192.0.2.0/24` (Corporate Range)
```

#### Output Commands

1.  Create `encryption_enforcement.json` (CSEK restricted):

    ```json
    {
      "gmekEnforcement": {"restrictionMode": "NotRestricted"},
      "cmekEnforcement": {"restrictionMode": "NotRestricted"},
      "csekEnforcement": {"restrictionMode": "FullyRestricted"}
    }
    ```

2.  Create `lifecycle_abort.json`:

    ```json
    {
      "rule": [
        {
          "action": {"type": "AbortIncompleteMultipartUpload"},
          "condition": {"age": 7}
        }
      ]
    }
    ```

3.  Create `ip_filter.json` (allowing corporate IP range):

    ```json
    {
      "mode": "Enabled",
      "allowAllServiceAgentAccess": true,
      "publicNetworkSource": {
        "allowedIpCidrRanges": ["192.0.2.0/24"]
      },
    }
    ```

4.  Run:

    ```bash
    # 1. Create the bucket
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets create gs://my-compliance-pii-bucket \
        --project=my-compliance-project \
        --location=us-central1 \
        --uniform-bucket-level-access \
        --public-access-prevention \
        --soft-delete-duration=7d \
        --retention-period=90d \
        --encryption-enforcement-file=encryption_enforcement.json \
        --enable-autoclass \
        --default-encryption-key=projects/my-kms-project/locations/us-central1/keyRings/my-keyring/cryptoKeys/my-key \
        --lifecycle-file=lifecycle_abort.json \
        --ip-filter-file=ip_filter.json

    # 2. Add labels (cannot be set during create)
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets update gs://my-compliance-pii-bucket \
        --project=my-compliance-project \
        --update-labels=data-class=pii,owner=security-team
    ```

    *Note: The retention policy is created unlocked. To lock it (making it
    permanent and irreversible), run:*

    ```bash
    # WARNING: Locking is irreversible. Neither an administrator nor Cloud
    # Support can reduce or remove the retention period on a locked bucket.
    # CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    # gcloud storage buckets update gs://my-compliance-pii-bucket --lock-retention-period
    ```

--------------------------------------------------------------------------------

### Example 3: Static Website Hosting

#### Input Draft Plan

```markdown
*   **Bucket Name**: `www.my-company-site.com`
*   **Project**: `my-frontend-project`
*   **Location**: `US`
*   **Storage Class**: `STANDARD`
*   **UBLA**: Enabled
*   **Public Access Prevention (PAP)**: Inherited (Disabled to allow public website access)
*   **Soft Delete**: Enabled (7 days)
*   **Use-case specific settings**:
    *   Website Config: Main page `index.html`, Error page `404.html`
    *   Public Access: Required (allUsers -> storage.objectViewer)
    *   CORS: Allowed GET/HEAD from any domain
```

#### Output Commands

1.  Create `cors_web.json` (allowing GET/HEAD from `*`).
2.  Run:

    ```bash
    # 1. Create the bucket with PAP inherited (allowing public access)
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets create gs://www.my-company-site.com \
        --project=my-frontend-project \
        --location=US \
        --default-storage-class=STANDARD \
        --uniform-bucket-level-access \
        --no-public-access-prevention \
        --soft-delete-duration=7d

    # 2. Configure Website settings (cannot be set during create)
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets update gs://www.my-company-site.com \
        --web-main-page-suffix=index.html \
        --web-error-page=404.html

    # 3. Apply CORS configuration (cannot be set during create)
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets update gs://www.my-company-site.com --cors-file=cors_web.json

    # 4. Grant public read access to website files
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets add-iam-policy-binding gs://www.my-company-site.com \
        --member=allUsers \
        --role=roles/storage.objectViewer
    ```

--------------------------------------------------------------------------------

### Example 4: AI/ML Checkpointing (Zonal Buckets)

#### Input Draft Plan

```markdown
*   **Bucket Name**: `my-training-checkpoints-us-east1-b`
*   **Project**: `my-ai-project`
*   **Location**: `us-east1-b` (Zone-level co-location for high performance)
*   **Storage Class**: `RAPID` (Must be explicitly specified for zonal buckets)
*   **UBLA**: Enabled (Required for Hierarchical Namespace)
*   **Public Access Prevention (PAP)**: Enforced
*   **Encryption**: Google-managed key
*   **Soft Delete**: Disabled (0 days) (Soft delete is not supported for zonal buckets)
*   **Use-case specific settings**:
    *   Hierarchical Namespace: Enabled (Required for Zonal buckets)
    *   Lifecycle: Delete checkpoint files older than 14 days
```

#### Output Commands

1.  Create `lifecycle_checkpoint.json`:

    ```json
    {
      "rule": [
        {
          "action": {"type": "Delete"},
          "condition": {"age": 14}
        }
      ]
    }
    ```

2.  Run:

    ```bash
    # Specifying a zone (e.g. us-east1-b) and RAPID storage class sets up a zonal bucket.
    # Zonal buckets require enabling Hierarchical Namespace and UBLA.
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets create gs://my-training-checkpoints-us-east1-b \
        --project=my-ai-project \
        --location=us-east1 \
        --placement=us-east1-b \
        --default-storage-class=RAPID \
        --uniform-bucket-level-access \
        --enable-hierarchical-namespace \
        --public-access-prevention \
        --soft-delete-duration=0 \
        --lifecycle-file=lifecycle_checkpoint.json
    ```

--------------------------------------------------------------------------------

### Example 5: WORM Archive with Object Lock (Per-Object Retention)

#### Input Draft Plan

```markdown
*   **Bucket Name**: `my-legal-archive-bucket`
*   **Project**: `my-legal-project`
*   **Location**: `us-east1`
*   **UBLA**: Enabled
*   **Public Access Prevention (PAP)**: Enforced
*   **Soft Delete**: Enabled (7 days)
*   **Encryption**: Customer-Managed Key (CMEK) (Highly Recommended)
*   **Use-case specific settings**:
    *   Storage Class: `ARCHIVE`
    *   Object Lock (Per-Object Retention): Enabled
    *   CMEK Key ID: `projects/my-kms-project/locations/us-east1/keyRings/my-keyring/cryptoKeys/my-key`
    *   Labels: `compliance-type=regulatory`, `retention-period=7y` (Highly Recommended tags)
    *   Lifecycle: Delete objects older than 7 years (2555 days) (Highly Recommended OLM)
```

#### Output Commands

1.  Create `lifecycle_archive.json` to purge objects after 7 years:

    ```json
    {
      "rule": [
        {
          "action": {"type": "Delete"},
          "condition": {"age": 2555}
        }
      ]
    }
    ```

2.  Create the bucket and apply labels:

    ```bash
    # 1. Create the bucket (object retention must be enabled at bucket creation time)
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets create gs://my-legal-archive-bucket \
        --project=my-legal-project \
        --location=us-east1 \
        --default-storage-class=ARCHIVE \
        --uniform-bucket-level-access \
        --public-access-prevention \
        --soft-delete-duration=7d \
        --enable-per-object-retention \
        --default-encryption-key=projects/my-kms-project/locations/us-east1/keyRings/my-keyring/cryptoKeys/my-key \
        --lifecycle-file=lifecycle_archive.json

    # 2. Add labels (cannot be set during create)
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage buckets update gs://my-legal-archive-bucket \
        --project=my-legal-project \
        --update-labels=compliance-type=regulatory,retention-period=7y
    ```

3.  Upload an object with a specific retention period (e.g., retain until
    December 31, 2030, in `Locked` mode):

    ```bash
    # Uploading and setting retention in one command:
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage cp case_file_abc.pdf gs://my-legal-archive-bucket/case_file_abc.pdf \
        --retain-until=2030-12-31T23:59:59Z \
        --retention-mode=Locked
    ```

4.  Alternatively, set or update retention on an existing object in the bucket:

    ```bash
    # Update retention on an existing object:
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
    gcloud storage objects update gs://my-legal-archive-bucket/case_file_abc.pdf \
        --retain-until=2030-12-31T23:59:59Z \
        --retention-mode=Locked \
        --override-unlocked-retention
    ```

    *Note: Setting the retention mode to `Locked` is permanent and irreversible.
    Once locked, the retention period cannot be shortened or removed, and the
    object cannot be deleted or overwritten by anyone (including administrators)
    until the retention period expires.*

    > [!IMPORTANT]
    > If you are modifying an existing `Unlocked` retention
    > configuration on an object, you must include the
    > `--override-unlocked-retention` flag if you want to:
    >
    > *   Change the mode to `Locked` (`--retention-mode=Locked`).
    > *   Reduce the retention time (`--retain-until`).
    > *   Clear the retention settings (`--clear-retention`).
    >
    > Failing to include this flag when performing these actions on an object
    > with existing `Unlocked` retention will cause the command to fail.
