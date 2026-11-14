# Python SDK Examples

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the Python SDK.

## Official Documentation Reference

*   [Cloud Storage Python Client Library](https://cloud.google.com/python/docs/reference/storage/latest)

## Version Requirements

> [!IMPORTANT]
> **Encryption Enforcement Config** requires the Python SDK version
> **3.10.0** or higher. If you are using a version below 3.10.0, you must
> configure this setting using the [REST API](rest.md), [gcloud](gcloud.md), or
> [Terraform](terraform.md) (the bucket can then be managed through the SDK).

--------------------------------------------------------------------------------

### Example 1: Standard Secure Bucket (Baseline)

#### Input Draft Plan

*   **Bucket Name**: `my-company-secure-bucket`
*   **Project**: `my-security-project`
*   **Location**: `us-east1`
*   **Storage Class**: `STANDARD`
*   **UBLA**: Enabled
*   **Public Access Prevention (PAP)**: Enforced
*   **Soft Delete**: Enabled (7 days)
*   **Encryption Enforcement**: CSEK Restricted

```python
from google.cloud import storage
from google.cloud.storage.bucket import EncryptionEnforcementConfig

def create_secure_bucket(project_id, bucket_name):
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    bucket.storage_class = "STANDARD"
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.iam_configuration.public_access_prevention = "enforced"
    bucket.soft_delete_policy.retention_duration_seconds = 604800 # 7 days
    bucket.encryption.customer_supplied_encryption_enforcement_config = EncryptionEnforcementConfig(restriction_mode="FullyRestricted")

    new_bucket = client.create_bucket(bucket, location="us-east1")
    return new_bucket
```

--------------------------------------------------------------------------------

### Example 2: Sensitive Data / Compliance

#### Input Draft Plan

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
    *   CMEK Key ID:
        `projects/my-kms-project/locations/us-central1/keyRings/my-keyring/cryptoKeys/my-key`
    *   Labels: `data-class=pii`, `owner=security-team`
    *   Lifecycle: Abort incomplete multipart uploads after 7 days
    *   IP Filtering: Restrict access to `192.0.2.0/24` (Corporate Range) and
        VPC networks (`10.0.0.0/16`) without cross-org VPCs.

```python
from google.cloud import storage
from google.cloud.storage.bucket import EncryptionEnforcementConfig
from google.cloud.storage.ip_filter import IPFilter, PublicNetworkSource, VpcNetworkSource

def create_compliance_bucket(project_id, bucket_name, kms_key_id):
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    bucket.storage_class = "STANDARD"
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.iam_configuration.public_access_prevention = "enforced"
    bucket.default_kms_key_name = kms_key_id
    bucket.soft_delete_policy.retention_duration_seconds = 604800 # 7 days
    bucket.retention_period = 7776000 # 90 days
    bucket.autoclass_enabled = True
    bucket.labels = {
        "data-class": "pii",
        "owner": "security-team"
    }
    bucket.lifecycle_rules = [
        {
            "action": {"type": "AbortIncompleteMultipartUpload"},
            "condition": {"age": 7}
        }
    ]

    bucket.encryption.customer_supplied_encryption_enforcement_config = EncryptionEnforcementConfig(restriction_mode="FullyRestricted")

    # Configure IP Filtering (including VPC Network Sources)
    ip_filter = IPFilter()
    ip_filter.mode = "Enabled"
    ip_filter.allow_all_service_agent_access = True
    ip_filter.allow_cross_org_vpcs = False
    ip_filter.public_network_source = PublicNetworkSource(
        allowed_ip_cidr_ranges=["192.0.2.0/24"]
    )
    ip_filter.vpc_network_sources = [
        VpcNetworkSource(
            network="projects/PROJECT_ID/global/networks/NETWORK_NAME",
            allowed_ip_cidr_ranges=["10.0.0.0/16"]
        )
    ]
    bucket.ip_filter = ip_filter

    new_bucket = client.create_bucket(bucket, location="us-central1")
    return new_bucket
```

*(Note: To lock the retention policy, call `bucket.lock_retention_policy()`.
Locking is permanent and irreversible).*

--------------------------------------------------------------------------------

### Example 3: Static Website Hosting

#### Input Draft Plan

*   **Bucket Name**: `www.my-company-site.com`
*   **Project**: `my-frontend-project`
*   **Location**: `US`
*   **Storage Class**: `STANDARD`
*   **UBLA**: Enabled
*   **Public Access Prevention (PAP)**: Inherited (Disabled to allow public
    website access)
*   **Soft Delete**: Enabled (7 days)
*   **Use-case specific settings**:
    *   Website Config: Main page `index.html`, Error page `404.html`
    *   Public Access: Required (allUsers -> storage.objectViewer)
    *   CORS: Allowed GET/HEAD/OPTIONS from any domain
    *   Versioning: Enabled

```python
from google.cloud import storage

def create_static_website_bucket(project_id, bucket_name):
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    bucket.storage_class = "STANDARD"
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.iam_configuration.public_access_prevention = "inherited" # allow public
    bucket.versioning_enabled = True
    bucket.soft_delete_policy.retention_duration_seconds = 604800 # 7 days

    bucket.configure_website(
        main_page_suffix="index.html",
        not_found_page="404.html"
    )
    bucket.cors = [{
        "origin": ["*"],
        "method": ["GET", "HEAD", "OPTIONS"],
        "responseHeader": ["Content-Type"],
        "maxAgeSeconds": 3600
    }]

    new_bucket = client.create_bucket(bucket, location="US")

    # Grant public access
    policy = new_bucket.get_iam_policy(requested_policy_version=3)
    policy.bindings.append({
        "role": "roles/storage.objectViewer",
        "members": {"allUsers"}
    })
    new_bucket.set_iam_policy(policy)
    return new_bucket
```

--------------------------------------------------------------------------------

### Example 4: AI/ML Checkpointing (Zonal Buckets)

#### Input Draft Plan

*   **Bucket Name**: `my-training-checkpoints-us-east1-b`
*   **Project**: `my-ai-project`
*   **Location**: `us-east1` (Region)
*   **Placement**: `us-east1-b` (Zone-level co-location for high performance)
*   **Storage Class**: `RAPID` (Must be explicitly specified for zonal buckets)
*   **UBLA**: Enabled (Required for Hierarchical Namespace)
*   **Public Access Prevention (PAP)**: Enforced
*   **Encryption**: Google-managed key
*   **Soft Delete**: Disabled (Not supported for zonal buckets)
*   **Use-case specific settings**:
    *   Hierarchical Namespace: Enabled (Required for Zonal buckets)
    *   Lifecycle: Delete checkpoint files older than 14 days

```python
from google.cloud import storage

def create_checkpoint_bucket(project_id, bucket_name):
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    bucket.storage_class = "RAPID"
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.iam_configuration.public_access_prevention = "enforced"
    bucket.hierarchical_namespace_enabled = True
    bucket.soft_delete_policy.retention_duration_seconds = 0
    bucket.lifecycle_rules = [
        {
            "action": {"type": "Delete"},
            "condition": {"age": 14}
        }
    ]

    # location must be the region, and data_locations must contain the zone
    new_bucket = client.create_bucket(bucket, location="us-east1", data_locations=["us-east1-b"])
    return new_bucket
```

--------------------------------------------------------------------------------

### Example 5: WORM Archive with Object Lock (Per-Object Retention)

#### Input Draft Plan

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
    *   CMEK Key ID:
        `projects/my-kms-project/locations/us-east1/keyRings/my-keyring/cryptoKeys/my-key`
    *   Labels: `compliance-type=regulatory`, `retention-period=7y` (Highly
        Recommended tags)
    *   Lifecycle: Delete objects older than 7 years (2555 days)

> [!CAUTION]
>
> Setting per-object retention mode to "Locked" is irreversible. Once set, the
> mode cannot be changed back and the retention date can only be extended.

```python
import datetime
from google.cloud import storage

def create_regulatory_worm_bucket(project_id, bucket_name, kms_key_id):
    client = storage.Client(project=project_id)

    # 1. Create bucket with Object Retention enabled
    bucket = client.create_bucket(
        bucket_or_name=bucket_name,
        location="us-east1",
        enable_object_retention=True
    )

    # 2. Configure bucket metadata
    bucket.storage_class = "ARCHIVE"
    bucket.iam_configuration.uniform_bucket_level_access_enabled = True
    bucket.iam_configuration.public_access_prevention = "enforced"
    bucket.default_kms_key_name = kms_key_id
    bucket.labels = {
        "compliance-type": "regulatory",
        "retention-period": "7y"
    }
    bucket.soft_delete_policy.retention_duration_seconds = 604800

    bucket.lifecycle_rules = [{
        "action": {"type": "Delete"},
        "condition": {"age": 2555}
    }]

    bucket.patch()
    return bucket

def upload_object_with_retention(bucket_name, source_file, destination_blob):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)

    # Configure retention on upload (Locked mode, retain until Dec 31, 2030)
    # The date can also be calculated dynamically as 7 years from now.
    retain_until = datetime.datetime(2030, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)

    blob.retention.mode = "Locked"
    blob.retention.retain_until_time = retain_until

    blob.upload_from_filename(source_file)
    return blob
```
