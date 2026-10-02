# Terraform Google Provider Cloud Storage Reference

> [!IMPORTANT]
>
> **DO NOT APPLY THESE CONFIGURATIONS AUTOMATICALLY.** The purpose of this guide
> is to define the mapping and translation rules to generate the correct snippet
> structure. These generated snippets must be presented to the user for
> confirmation.

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the corresponding Terraform configuration.

## Official Documentation Reference

*   [Terraform Registry: `google_storage_bucket`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket)
*   [Terraform Registry: `google_storage_bucket_object`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_object)
*   [Terraform Registry: `google_storage_notification`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_notification)
*   [Terraform Registry: `google_storage_anywhere_cache`](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_anywhere_cache)

--------------------------------------------------------------------------------

## Translation Mapping Table

Draft Plan Field / Setting         | Terraform Resource & Attribute                                        | Notes / Action
:--------------------------------- | :-------------------------------------------------------------------- | :-------------
**Bucket Name**                    | `google_storage_bucket.name`                                          | Required string. Must be globally unique.
**Project**                        | `google_storage_bucket.project`                                       | Optional. Defaults to provider project.
**Location**                       | `google_storage_bucket.location`                                      | Required. E.g., `"us-central1"`, `"us"`. Zonal buckets (using the Rapid storage class) require setting this to the region (e.g., `"us-east1"`).
**Placement**                      | `google_storage_bucket.custom_placement_config.data_locations`        | List of strings. E.g., `["us-east1", "us-west1"]` (for custom dual-regions), or `["us-east1-b"]` (for zonal buckets).
**Replication Speed (RPO)**        | `google_storage_bucket.rpo`                                           | String. E.g., `"ASYNC_TURBO"` (for dual-region buckets).
**Storage Class**                  | `google_storage_bucket.storage_class`                                 | String. E.g., `"STANDARD"`, `"NEARLINE"`, `"COLDLINE"`, `"ARCHIVE"`, `"RAPID"`. Zonal locations require `"RAPID"`. Note: If Autoclass is enabled, do not set storage_class to anything other than `"STANDARD"`.
**UBLA**                           | `google_storage_bucket.uniform_bucket_level_access`                   | Boolean. Always set to `true`.
**Public Access Prevention**       | `google_storage_bucket.public_access_prevention`                      | String. `"enforced"` or `"inherited"`.
**Soft Delete**                    | `google_storage_bucket.soft_delete_policy.retention_duration_seconds` | Number (seconds). E.g. `604800` (7 days). Set to `0` to disable. Zonal buckets do not support Soft Delete (the field can be left unset or explicitly set to 0). Note: Omitting this block leaves it enabled at Cloud Storage default (7 days). Min: `604800` (7 days), Max: `7776000` (90 days).
**Object Versioning**              | `google_storage_bucket.versioning.enabled`                            | Boolean. Enables/disables versioning.
**Encryption (CMEK)**              | `google_storage_bucket.encryption.default_kms_key_name`               | String. Full key ID: `projects/.../cryptoKeys/...` Note: Requires Cloud Storage Service Agent (`service-PROJECT_NUM@gs-project-accounts.iam.gserviceaccount.com`) to have `roles/cloudkms.cryptoKeyEncrypterDecrypter` role on the key.
**Restrict Encryption (CSEK)**     | `google_storage_bucket` encryption enforcement blocks                 | Configures encryption restrictions. See below.
**Autoclass**                      | `google_storage_bucket.autoclass.enabled`                             | Boolean. Set to `true` to enable. Note: Incompatible with zonal buckets.
**Hierarchical Namespace**         | `google_storage_bucket.hierarchical_namespace.enabled`                | Boolean. Set to `true` to enable. Note: Incompatible with Bucket Lock (retention policy), object versioning, and object retention. Must be enabled at bucket creation (irreversible).
**Labels**                         | `google_storage_bucket.labels`                                        | Map of strings.
**IP Filtering**                   | `google_storage_bucket.ip_filter`                                     | Block. Defines IP restriction rules. See below.
**Lifecycle Policies (OLM)**       | `google_storage_bucket.lifecycle_rule`                                | One or more blocks. See template below.
**CORS**                           | `google_storage_bucket.cors`                                          | One or more blocks.
**Website Configuration**          | `google_storage_bucket.website`                                       | Block with `main_page_suffix` and `not_found_page`.
**Public IAM Policy**              | `google_storage_bucket_iam_member`                                    | Separate resource to grant `roles/storage.objectViewer` to `allUsers`.
**Pub/Sub Notifications**          | `google_storage_notification`                                         | Separate resource linking bucket and Pub/Sub topic. Note: The Cloud Storage service agent (via `google_storage_project_service_account` data source) must have `roles/pubsub.publisher` on the topic (typically via `google_pubsub_topic_iam_binding`), and the notification resource should have a `depends_on` targeting this IAM binding.
**Bucket Retention Period**        | `google_storage_bucket.retention_policy.retention_period`             | Number in seconds. E.g. `7776000` (90 days).
**Lock Bucket Retention Policy**   | `google_storage_bucket.retention_policy.is_locked`                    | Boolean. Setting to `true` permanently locks policy. **Irreversible.**
**Object Retention (Object Lock)** | `google_storage_bucket.enable_object_retention`                       | Boolean. Enables object-level retention.
**Set Object Retention**           | `google_storage_bucket_object.retention`                              | Block with `mode` and `retain_until_time` inside bucket object resource.
**Rapid Cache**                    | `google_storage_anywhere_cache`                                       | Separate resource linking bucket to Rapid Cache zone.

--------------------------------------------------------------------------------

## Helper Configuration Templates

### Encryption Enforcement (CSEK Restriction)

```tf
resource "google_storage_bucket" "secure_bucket" {
  name                        = "my-secure-bucket"
  location                    = "us-central1"
  uniform_bucket_level_access = true

  encryption {
    customer_supplied_encryption_enforcement_config {
      restriction_mode = "FullyRestricted"
    }
    customer_managed_encryption_enforcement_config {
      restriction_mode = "NotRestricted"
    }
    google_managed_encryption_enforcement_config {
      restriction_mode = "NotRestricted"
    }
  }
}
```

### IP Filtering

```tf
resource "google_storage_bucket" "ip_filtered_bucket" {
  name                        = "my-ip-filtered-bucket"
  location                    = "us-central1"
  uniform_bucket_level_access = true

  ip_filter {
    mode                           = "Enabled"
    allow_all_service_agent_access = true
    allow_cross_org_vpcs           = false

    public_network_source {
      allowed_ip_cidr_ranges = [
        "192.0.2.0/24"
      ]
    }

    vpc_network_sources {
      network                = "projects/PROJECT_ID/global/networks/NETWORK_NAME"
      allowed_ip_cidr_ranges = [
        "10.0.0.0/16"
      ]
    }
  }
}
```

### Lifecycle Policy (OLM)

```tf
resource "google_storage_bucket" "lifecycle_bucket" {
  name     = "my-lifecycle-bucket"
  location = "us-central1"

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }
}
```

### CORS Configuration

```tf
resource "google_storage_bucket" "cors_bucket" {
  name     = "my-cors-bucket"
  location = "us-central1"

  cors {
    origin          = ["http://example.com"]
    method          = ["GET", "PUT", "POST", "DELETE"]
    response_header = ["Content-Type", "Authorization"]
    max_age_seconds = 3600
  }
}
```

--------------------------------------------------------------------------------

## Terraform Examples

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

#### Output Terraform Configuration

```tf
resource "google_storage_bucket" "secure_bucket" {
  name                        = "my-company-secure-bucket"
  location                    = "us-east1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  encryption {
    customer_supplied_encryption_enforcement_config {
      restriction_mode = "FullyRestricted"
    }
  }

  soft_delete_policy {
    retention_duration_seconds = 604800 # 7 days
  }
}
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
    *   IP Filtering: Restrict access to `192.0.2.0/24` (Corporate Range) and VPC networks (`10.0.0.0/16`) without cross-org VPCs.
```

#### Output Terraform Configuration

```tf
resource "google_storage_bucket" "compliance_bucket" {
  name                        = "my-compliance-pii-bucket"
  location                    = "us-central1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  encryption {
    default_kms_key_name = "projects/my-kms-project/locations/us-central1/keyRings/my-keyring/cryptoKeys/my-key"

    customer_supplied_encryption_enforcement_config {
      restriction_mode = "FullyRestricted"
    }
    customer_managed_encryption_enforcement_config {
      restriction_mode = "NotRestricted"
    }
    google_managed_encryption_enforcement_config {
      restriction_mode = "NotRestricted"
    }
  }

  retention_policy {
    retention_period = 7776000 # 90 days in seconds
    is_locked        = false # Unlocked by default
  }

  autoclass {
    enabled = true
  }

  labels = {
    data-class = "pii"
    owner      = "security-team"
  }

  lifecycle_rule {
    action {
      type = "AbortIncompleteMultipartUpload"
    }
    condition {
      age = 7
    }
  }

  ip_filter {
    mode                           = "Enabled"
    allow_all_service_agent_access = true
    allow_cross_org_vpcs           = false

    public_network_source {
      allowed_ip_cidr_ranges = ["192.0.2.0/24"]
    }

    vpc_network_sources {
      network                = "projects/PROJECT_ID/global/networks/NETWORK_NAME"
      allowed_ip_cidr_ranges = ["10.0.0.0/16"]
    }
  }

  soft_delete_policy {
    retention_duration_seconds = 604800 # 7 days
  }
}
```

*(Note: To lock the retention policy, set `is_locked = true` inside the
`retention_policy` block. Locking is permanent and irreversible).*

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
    *   Versioning: Enabled
```

#### Output Terraform Configuration

```tf
resource "google_storage_bucket" "static_website" {
  name                        = "www.my-company-site.com"
  location                    = "US"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "inherited"

  website {
    main_page_suffix = "index.html"
    not_found_page   = "404.html"
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800 # 7 days
  }
}

resource "google_storage_bucket_iam_member" "public_viewer" {
  bucket = google_storage_bucket.static_website.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
```

--------------------------------------------------------------------------------

### Example 4: AI/ML Checkpointing (Zonal Buckets)

#### Input Draft Plan

```markdown
*   **Bucket Name**: `my-training-checkpoints-us-east1-b`
*   **Project**: `my-ai-project`
*   **Location**: `us-east1` (Region)
*   **Placement**: `us-east1-b` (Zone-level co-location for high performance)
*   **Storage Class**: `RAPID` (Must be explicitly specified for zonal buckets)
*   **UBLA**: Enabled (Required for Hierarchical Namespace)
*   **Public Access Prevention (PAP)**: Enforced
*   **Encryption**: Google-managed key
*   **Soft Delete**: Disabled (0 days) (Soft delete is not supported for zonal buckets)
*   **Use-case specific settings**:
    *   Hierarchical Namespace: Enabled (Required for Zonal buckets)
    *   Lifecycle: Delete checkpoint files older than 14 days
```

#### Output Terraform Configuration

```tf
resource "google_storage_bucket" "checkpoint_bucket" {
  name                        = "my-training-checkpoints-us-east1-b"
  location                    = "us-east1"
  storage_class               = "RAPID"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  custom_placement_config {
    data_locations = ["us-east1-b"]
  }

  hierarchical_namespace {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 0
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 14
    }
  }
}
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

#### Output Terraform Configuration

```tf
resource "google_storage_bucket" "legal_archive" {
  name                        = "my-legal-archive-bucket"
  location                    = "us-east1"
  storage_class               = "ARCHIVE"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  enable_object_retention     = true

  encryption {
    default_kms_key_name = "projects/my-kms-project/locations/us-east1/keyRings/my-keyring/cryptoKeys/my-key"
  }

  labels = {
    compliance-type  = "regulatory"
    retention-period = "7y"
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 2555
    }
  }

  soft_delete_policy {
    retention_duration_seconds = 604800 # 7 days
  }
}
```

--------------------------------------------------------------------------------

## Object-Level Retention Configurations

### Create Object with Specific Retention Policy

Applying Object Lock on individual objects.

> [!CAUTION]
>
> Setting `mode = "Locked"` in Terraform will permanently lock the object's
> retention policy. Once locked, this policy cannot be removed, and the
> retention period can only be increased, not reduced.

```tf
resource "google_storage_bucket_object" "case_file" {
  name   = "case_file_abc.pdf"
  bucket = google_storage_bucket.legal_archive.name
  source = "path/to/local/file.pdf"

  retention {
    mode              = "Locked"
    retain_until_time = "2030-12-31T23:59:59Z"
  }
}
```
