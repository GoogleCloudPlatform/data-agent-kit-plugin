# C++ SDK Examples

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the C++ SDK.

## Official Documentation Reference

*   [Cloud Storage C++ Client Library](https://cloud.google.com/cpp/docs/reference/storage/latest)

## Client Initialization

```cpp
#include "google/cloud/storage/client.h"

namespace gcs = ::google::cloud::storage;
auto client = gcs::Client();
```

## Version Requirements

> [!IMPORTANT]
> **Encryption Enforcement Config** requires the C++ Cloud Storage
> SDK version **2.46.0** or higher. If you are using a version below 2.46.0, you
> must configure this setting using the [REST API](rest.md),
> [gcloud](gcloud.md), or [Terraform](terraform.md) (the bucket can then be
> managed through the SDK).

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

```cpp
#include "google/cloud/storage/client.h"
#include <chrono>
#include <string>
#include <utility>

namespace gcs = ::google::cloud::storage;
using ::google::cloud::StatusOr;

StatusOr<gcs::BucketMetadata> CreateSecureBucket(gcs::Client client,
                                                 std::string const& project_id,
                                                 std::string const& bucket_name) {
  gcs::BucketIamConfiguration iam_config;
  iam_config.uniform_bucket_level_access = gcs::UniformBucketLevelAccess{true, {}};
  iam_config.public_access_prevention = gcs::PublicAccessPreventionEnforced();

  gcs::BucketEncryption encryption;
  encryption.customer_supplied_encryption_enforcement_config.restriction_mode = "FullyRestricted";

  gcs::BucketMetadata metadata = gcs::BucketMetadata()
      .set_storage_class(gcs::storage_class::Standard())
      .set_location("us-east1")
      .set_iam_configuration(iam_config)
      .set_encryption(encryption)
      .set_soft_delete_policy(std::chrono::seconds(7 * 24 * 3600)); // 7 days

  return client.CreateBucket(bucket_name, std::move(metadata),
                             gcs::OverrideDefaultProject(project_id));
}
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

```cpp
#include "google/cloud/storage/client.h"
#include <chrono>
#include <string>
#include <utility>

namespace gcs = ::google::cloud::storage;
using ::google::cloud::StatusOr;

StatusOr<gcs::BucketMetadata> CreateComplianceBucket(gcs::Client client,
                                                     std::string const& project_id,
                                                     std::string const& bucket_name,
                                                     std::string const& kms_key_id) {
  gcs::BucketIamConfiguration iam_config;
  iam_config.uniform_bucket_level_access = gcs::UniformBucketLevelAccess{true, {}};
  iam_config.public_access_prevention = gcs::PublicAccessPreventionEnforced();

  gcs::BucketEncryption encryption;
  encryption.default_kms_key_name = kms_key_id;
  encryption.customer_supplied_encryption_enforcement_config.restriction_mode = "FullyRestricted";
  encryption.customer_managed_encryption_enforcement_config.restriction_mode = "NotRestricted";
  encryption.google_managed_encryption_enforcement_config.restriction_mode = "NotRestricted";

  gcs::BucketLifecycle lifecycle;
  lifecycle.rule = {
      gcs::LifecycleRule(
          gcs::LifecycleRule::MaxAge(7),
          gcs::LifecycleRule::AbortIncompleteMultipartUpload()
      )
  };

  gcs::BucketMetadata metadata = gcs::BucketMetadata()
      .set_storage_class(gcs::storage_class::Standard())
      .set_location("us-central1")
      .set_iam_configuration(iam_config)
      .set_encryption(encryption)
      .set_soft_delete_policy(std::chrono::seconds(7 * 24 * 3600)) // 7 days
      .set_retention_policy(std::chrono::seconds(90 * 24 * 3600)) // 90 days
      .set_autoclass(gcs::BucketAutoclass{true})
      .upsert_label("data-class", "pii")
      .upsert_label("owner", "security-team")
      .set_lifecycle(lifecycle);

  // NOTE: IP Filtering is not supported via attributes in this C++ client library version.
  // It must be configured using the REST API or gcloud.

  return client.CreateBucket(bucket_name, std::move(metadata),
                             gcs::OverrideDefaultProject(project_id));
}

// Locking the retention policy is permanent and irreversible.
StatusOr<gcs::BucketMetadata> LockRetentionPolicy(gcs::Client client,
                                                  std::string const& bucket_name) {
  StatusOr<gcs::BucketMetadata> metadata = client.GetBucketMetadata(bucket_name);
  if (!metadata) return metadata;

  return client.LockBucketRetentionPolicy(bucket_name, metadata->metageneration());
}
```

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

```cpp
#include "google/cloud/storage/client.h"
#include <chrono>
#include <string>
#include <utility>

namespace gcs = ::google::cloud::storage;
using ::google::cloud::StatusOr;

StatusOr<gcs::BucketMetadata> CreateStaticWebsiteBucket(gcs::Client client,
                                                       std::string const& project_id,
                                                       std::string const& bucket_name) {
  gcs::CorsEntry cors;
  cors.max_age_seconds = 3600;
  cors.method = {"GET", "HEAD", "OPTIONS"};
  cors.origin = {"*"};
  cors.response_header = {"Content-Type"};

  gcs::BucketMetadata metadata = gcs::BucketMetadata()
      .set_storage_class(gcs::storage_class::Standard())
      .set_location("US")
      .set_iam_configuration(gcs::BucketIamConfiguration{
          gcs::UniformBucketLevelAccess{true, {}},
          gcs::PublicAccessPreventionInherited()
      })
      .set_versioning(gcs::BucketVersioning{true})
      .set_soft_delete_policy(std::chrono::seconds(7 * 24 * 3600)) // 7 days
      .set_website(gcs::BucketWebsite{"index.html", "404.html"})
      .set_cors({cors});

  StatusOr<gcs::BucketMetadata> bucket = client.CreateBucket(
      bucket_name, std::move(metadata), gcs::OverrideDefaultProject(project_id));
  if (!bucket) return bucket;

  // Grant public access
  auto current_policy = client.GetNativeBucketIamPolicy(
      bucket_name, gcs::RequestedPolicyVersion(3));
  if (!current_policy) return current_policy.status();

  current_policy->set_version(3);
  current_policy->bindings().emplace_back(
      gcs::NativeIamBinding("roles/storage.objectViewer", {"allUsers"}));

  auto updated = client.SetNativeBucketIamPolicy(bucket_name, *current_policy);
  if (!updated) return updated.status();

  return bucket;
}
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
*   **Soft Delete**: Disabled (0 days) (Soft delete is not supported for zonal
    buckets)
*   **Use-case specific settings**:
    *   Hierarchical Namespace: Enabled (Required for Zonal buckets)
    *   Lifecycle: Delete checkpoint files older than 14 days

```cpp
#include "google/cloud/storage/client.h"
#include <chrono>
#include <string>
#include <utility>

namespace gcs = ::google::cloud::storage;
using ::google::cloud::StatusOr;

StatusOr<gcs::BucketMetadata> CreateCheckpointBucket(gcs::Client client,
                                                     std::string const& project_id,
                                                     std::string const& bucket_name) {
  gcs::BucketIamConfiguration iam_config;
  iam_config.uniform_bucket_level_access = gcs::UniformBucketLevelAccess{true, {}};
  iam_config.public_access_prevention = gcs::PublicAccessPreventionEnforced();

  gcs::BucketLifecycle lifecycle;
  lifecycle.rule = {
      gcs::LifecycleRule(
          gcs::LifecycleRule::MaxAge(14),
          gcs::LifecycleRule::Delete()
      )
  };

  gcs::BucketMetadata metadata = gcs::BucketMetadata()
      .set_storage_class("RAPID")
      .set_location("us-east1")
      .set_custom_placement_config(gcs::BucketCustomPlacementConfig{{"us-east1-b"}})
      .set_iam_configuration(iam_config)
      .set_hierarchical_namespace(gcs::BucketHierarchicalNamespace{true})
      .set_soft_delete_policy(std::chrono::seconds(0))
      .set_lifecycle(lifecycle);

  return client.CreateBucket(bucket_name, std::move(metadata),
                             gcs::OverrideDefaultProject(project_id));
}
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
> Setting per-object retention mode to "Locked" is irreversible. Once
> set, the mode cannot be changed back and the retention date can only be
> extended.

```cpp
#include "google/cloud/storage/client.h"
#include <chrono>
#include <string>
#include <utility>

namespace gcs = ::google::cloud::storage;
using ::google::cloud::StatusOr;

StatusOr<gcs::BucketMetadata> CreateRegulatoryWormBucket(gcs::Client client,
                                                         std::string const& project_id,
                                                         std::string const& bucket_name,
                                                         std::string const& kms_key_id) {
  gcs::BucketIamConfiguration iam_config;
  iam_config.uniform_bucket_level_access = gcs::UniformBucketLevelAccess{true, {}};
  iam_config.public_access_prevention = gcs::PublicAccessPreventionEnforced();

  gcs::BucketLifecycle lifecycle;
  lifecycle.rule = {
      gcs::LifecycleRule(
          gcs::LifecycleRule::MaxAge(2555), // 7 years
          gcs::LifecycleRule::Delete()
      )
  };

  gcs::BucketMetadata metadata = gcs::BucketMetadata()
      .set_storage_class(gcs::storage_class::Archive())
      .set_location("us-east1")
      .set_iam_configuration(iam_config)
      .set_encryption(gcs::BucketEncryption{kms_key_id})
      .upsert_label("compliance-type", "regulatory")
      .upsert_label("retention-period", "7y")
      .set_soft_delete_policy(std::chrono::seconds(7 * 24 * 3600)) // 7 days
      .set_lifecycle(lifecycle);

  // Enable Object Retention during bucket creation
  return client.CreateBucket(bucket_name, std::move(metadata),
                             gcs::EnableObjectRetention(true),
                             gcs::OverrideDefaultProject(project_id));
}

StatusOr<gcs::ObjectMetadata> UploadObjectWithRetention(gcs::Client client,
                                                        std::string const& bucket_name,
                                                        std::string const& object_name,
                                                        std::string const& contents) {
  // Retain until Dec 31, 2030 23:59:59 UTC (1924991999 seconds since epoch)
  auto retain_until = std::chrono::system_clock::from_time_t(1924991999);

  return client.InsertObject(
      bucket_name, object_name, contents,
      gcs::WithObjectMetadata(gcs::ObjectMetadata{}.set_retention(
          gcs::ObjectRetention{gcs::ObjectRetentionLocked(), retain_until})));
}
```
