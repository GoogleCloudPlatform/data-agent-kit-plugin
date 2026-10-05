# Cloud Storage SDK Reference

> [!IMPORTANT]
>
> **DO NOT RUN THESE CONFIGURATIONS AUTOMATICALLY.** The purpose of this guide
> is to define the mapping and translation rules to generate the correct snippet
> structure. These generated snippets must be presented to the user for
> confirmation.

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the corresponding SDK configuration in C++, Java, Python, and Go.

## Official Documentation Reference

### Cloud Storage (Data Plane)

*   [Cloud Storage C++ Client Library](https://cloud.google.com/cpp/docs/reference/storage/latest)
*   [Cloud Storage Go Package Reference](https://pkg.go.dev/cloud.google.com/go/storage)
*   [Cloud Storage Java Client Library](https://cloud.google.com/java/docs/reference/google-cloud-storage/latest/overview)
*   [Cloud Storage Python Client Library](https://cloud.google.com/python/docs/reference/storage/latest)

### Cloud Storage Control (Control Plane - Hierarchical Namespace, Folders, Rapid Cache)

*   [Cloud Storage Control C++ Client Library](https://cloud.google.com/cpp/docs/reference/storagecontrol/latest)
*   [Cloud Storage Control Go Package Reference](https://pkg.go.dev/cloud.google.com/go/storage/control/apiv2)
*   [Cloud Storage Control Java Client Library](https://cloud.google.com/java/docs/reference/google-cloud-storage/latest/com.google.storage.control.v2.StorageControlClient)
*   [Cloud Storage Control Python Client Library](https://cloud.google.com/python/docs/reference/google-cloud-storage-control/latest/google.cloud.storage_control_v2.services.storage_control.StorageControlClient)

--------------------------------------------------------------------------------

## Client Initialization

Here is how to initialize the Storage Client in each language:

### Python

```python
from google.cloud import storage

client = storage.Client(project=project_id)
```

### Go

```go
import (
    "context"
    "cloud.google.com/go/storage"
)

ctx := context.Background()
client, err := storage.NewClient(ctx)
```

### C++

```cpp
#include "google/cloud/storage/client.h"

namespace gcs = ::google::cloud::storage;
auto client = gcs::Client();
```

### Java

```java
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageOptions;

Storage storage = StorageOptions.newBuilder()
    .setProjectId(projectId)
    .build()
    .getService();
```

## SDK Feature Support Matrix

> [!NOTE]
> For features marked as *Not exposed* in a specific language's client
> library, consider using alternative configuration methods such as
> [Terraform](terraform.md), [gcloud](gcloud.md), or the raw
> [REST API](rest.md).

Draft Plan Field / Setting          | Python SDK Feature / Attribute                                                                                                                                                            | Go SDK Feature / Attribute                                                                                                                                                                          | C++ SDK Feature / Attribute                                                                   | Java SDK Feature / Attribute
:---------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------- | :---------------------------
**Bucket Name**                     | `bucket_or_name` (arg in `create_bucket`, accepts `Bucket` or `str`)                                                                                                                      | Passed to `client.Bucket(name)`                                                                                                                                                                     | Passed to `Client::CreateBucket(bucket_name, ...)`                                            | Passed to `BucketInfo.newBuilder(name)`
**Location**                        | `location` (arg in `create_bucket`)                                                                                                                                                       | `BucketAttrs.Location`                                                                                                                                                                              | `bucket.set_location(location)`                                                               | `BucketInfo.Builder.setLocation(location)`
**Placement (Dual-Region / Zonal)** | `data_locations=[...]` (arg in `create_bucket`)                                                                                                                                           | `BucketAttrs.CustomPlacementConfig`                                                                                                                                                                 | `bucket.set_custom_placement_config(BucketCustomPlacementConfig{{...}})`                      | `BucketInfo.Builder.setCustomPlacementConfig(...)`
**Replication Speed (RPO)**         | `bucket.rpo = "ASYNC_TURBO"`                                                                                                                                                              | `BucketAttrs.RPO`                                                                                                                                                                                   | `bucket.set_rpo("ASYNC_TURBO")`                                                               | `BucketInfo.Builder.setRpo(Rpo.ASYNC_TURBO)`
**Storage Class**                   | `bucket.storage_class = "STANDARD"`                                                                                                                                                       | `BucketAttrs.StorageClass`                                                                                                                                                                          | `bucket.set_storage_class(storage_class)`                                                     | `BucketInfo.Builder.setStorageClass(StorageClass.STANDARD)`
**UBLA**                            | `bucket.iam_configuration.uniform_bucket_level_access_enabled = True`                                                                                                                     | `BucketAttrs.UniformBucketLevelAccess`                                                                                                                                                              | `bucket.set_iam_configuration(BucketIamConfiguration{UniformBucketLevelAccess{true, {}}})`    | `BucketInfo.Builder.setIamConfiguration(...)` (with `setIsUniformBucketLevelAccessEnabled(true)`)
**Public Access Prevention**        | `bucket.iam_configuration.public_access_prevention = "enforced"`                                                                                                                          | `BucketAttrs.PublicAccessPrevention`                                                                                                                                                                | `bucket.set_iam_configuration(BucketIamConfiguration{std::nullopt, "enforced"})`              | `BucketInfo.Builder.setIamConfiguration(...)` (with `setPublicAccessPrevention(PublicAccessPrevention.ENFORCED)`)
**Soft Delete**                     | `bucket.soft_delete_policy.retention_duration_seconds = seconds`                                                                                                                          | `BucketAttrs.SoftDeletePolicy`                                                                                                                                                                      | `bucket.set_soft_delete_policy(BucketSoftDeletePolicy{std::chrono::seconds(seconds)})`        | `BucketInfo.Builder.setSoftDeletePolicy(...)` (with `setRetentionDuration(Duration)`)
**Object Versioning**               | `bucket.versioning_enabled = True`                                                                                                                                                        | `BucketAttrs.VersioningEnabled`                                                                                                                                                                     | `bucket.enable_versioning()`                                                                  | `BucketInfo.Builder.setVersioningEnabled(true)`
**Encryption (CMEK)**               | `bucket.default_kms_key_name = "projects/..."`                                                                                                                                            | `BucketAttrs.Encryption`                                                                                                                                                                            | `bucket.set_encryption(BucketEncryption("key_name"))`                                         | `BucketInfo.Builder.setDefaultKmsKeyName(keyName)`
**Restrict Encryption (CSEK)**      | `bucket.encryption.customer_supplied_encryption_enforcement_config = EncryptionEnforcementConfig(restriction_mode="FullyRestricted")` (v3.10.0+)                                          | `BucketAttrs.CustomerSuppliedEncryptionEnforcementConfig` (with `RestrictionMode: storage.FullyRestricted`) (v1.61.0+)                                                                              | `BucketEncryption` fields (e.g. `customer_supplied_encryption_enforcement_config`) (v2.46.0+) | `BucketInfo.Builder.setCustomerSuppliedEncryptionEnforcementConfig(...)` (v2.55.0+)
**Autoclass**                       | `bucket.autoclass_enabled = True`                                                                                                                                                         | `BucketAttrs.Autoclass`                                                                                                                                                                             | `bucket.set_autoclass(BucketAutoclass(true))`                                                 | `BucketInfo.Builder.setAutoclass(...)` (with `setEnabled(true)`)
**Hierarchical Namespace**          | `bucket.hierarchical_namespace_enabled = True`                                                                                                                                            | `BucketAttrs.HierarchicalNamespace`                                                                                                                                                                 | `bucket.set_hierarchical_namespace(BucketHierarchicalNamespace{true})`                        | `BucketInfo.Builder.setHierarchicalNamespace(...)` (with `setEnabled(true)`)
**Labels**                          | `bucket.labels = {"key": "value"}`                                                                                                                                                        | `BucketAttrs.Labels`                                                                                                                                                                                | `bucket.upsert_label(key, value)`                                                             | `BucketInfo.Builder.setLabels(Map)`
**IP Filtering**                    | `from google.cloud.storage.ip_filter import IPFilter`<br>`ip_filter = IPFilter()`<br>`bucket.ip_filter = ip_filter`                                                                       | *Not exposed in Go v1 client library*                                                                                                                                                               | *Not exposed in C++ client library*                                                           | `BucketInfo.Builder.setIpFilter(...)`
**Allow Cross-Org VPCs**            | `ip_filter.allow_cross_org_vpcs = False`                                                                                                                                                  | *Not exposed in Go v1 client library*                                                                                                                                                               | *Not exposed in C++ client library*                                                           | `IpFilter.Builder.setAllowCrossOrgVpcs(allow)`
**Lifecycle Policies (OLM)**        | `bucket.lifecycle_rules = [...]`                                                                                                                                                          | `BucketAttrs.Lifecycle`                                                                                                                                                                             | `bucket.set_lifecycle(BucketLifecycle{{LifecycleRule(...)}})`                                 | `BucketInfo.Builder.setLifecycleRules(rules)`
**CORS**                            | `bucket.cors = [...]`                                                                                                                                                                     | `BucketAttrs.CORS`                                                                                                                                                                                  | `bucket.set_cors({CorsEntry{...}})`                                                           | `BucketInfo.Builder.setCors(cors)`
**Website Configuration**           | `bucket.configure_website(...)`                                                                                                                                                           | `BucketAttrs.Website`                                                                                                                                                                               | `bucket.set_website(BucketWebsite{main_page, error_page})`                                    | `BucketInfo.Builder.setIndexPage(index)` / `setNotFoundPage(404)`
**Public IAM Policy**               | `bucket.set_iam_policy(policy)`                                                                                                                                                           | `bucket.IAM().SetPolicy(ctx, policy)`                                                                                                                                                               | `client.SetNativeBucketIamPolicy(bucket_name, policy)`                                        | `storage.setIamPolicy(bucketName, policy)`
**Pub/Sub Notifications**           | `notification = bucket.notification(...)` & `notification.create()`                                                                                                                       | `BucketHandle.AddNotification(ctx, &Notification{...})`                                                                                                                                             | `client.CreateNotification(bucket_name, topic_name, ...)`                                     | `storage.createNotification(bucket, notificationInfo)`
**Bucket Retention Period**         | `bucket.retention_period = seconds`                                                                                                                                                       | `BucketAttrs.RetentionPolicy`                                                                                                                                                                       | `bucket.set_retention_policy(std::chrono::seconds(seconds))`                                  | `BucketInfo.Builder.setRetentionPeriodDuration(Duration)`
**Lock Bucket Retention Policy**    | `bucket.lock_retention_policy()`                                                                                                                                                          | `bucket.If(storage.BucketConditions{MetagenerationMatch: attrs.MetaGeneration}).LockRetentionPolicy(ctx)`                                                                                           | `client.LockBucketRetentionPolicy(bucket_name, metageneration)`                               | `storage.lockRetentionPolicy(bucketInfo, BucketTargetOption.metagenerationMatch())`
**Object Retention (Object Lock)**  | `enable_object_retention=True` (arg in `create_bucket`)                                                                                                                                   | `client.Bucket(name).SetObjectRetention(true)`                                                                                                                                                      | `bucket.set_object_retention(BucketObjectRetention{true})`                                    | `Storage.BucketTargetOption.enableObjectRetention(true)` (arg in `storage.create`)
**Set Object Retention**            | `retention = blob.retention`<br>`retention.mode = "Unlocked"`<br>`retention.retain_until_time = dt`<br>`blob.patch()` (use `override_unlocked_retention=True` to shorten/remove Unlocked) | `Writer.ObjectAttrs.Retention` (on create)<br>or `ObjectHandle.Update(...)` with `ObjectAttrsToUpdate.Retention`<br>(use `ObjectHandle.OverrideUnlockedRetention(true)` to shorten/remove Unlocked) | `object.set_retention(ObjectRetention{mode, timestamp})`                                      | `BlobInfo.Builder.setRetention(BlobInfo.Retention)`
**Rapid Cache**                     | `StorageControlClient.create_anywhere_cache`                                                                                                                                              | `StorageControlClient.CreateAnywhereCache`                                                                                                                                                          | `StorageControlClient::CreateAnywhereCache`                                                   | `StorageControlClient.createAnywhereCache`

--------------------------------------------------------------------------------

## Handling Unexposed Features

If a required feature is marked as *Not exposed* in the target language's client
library, developers can use one of the following integration patterns:

### Pattern 1: Separate Provisioning from Application Logic (Recommended)

Separate infrastructure management from application code. Use
[Terraform](terraform.md) or [gcloud](gcloud.md) to create and configure the
bucket (including advanced settings like IP Filtering). The application code,
using the SDK, only handles data plane operations (reading/writing objects) and
does not need to configure these settings.

### Pattern 2: Hybrid SDK + Direct REST API Call

If the application must configure the unexposed setting at runtime, use the SDK
for standard operations and perform a direct HTTP REST call for the unexposed
feature:

1.  **Auth**: Use the SDK credentials helper to obtain an OAuth2 access token.
2.  **Request**: Send a `PATCH` request to the Cloud Storage REST API (e.g.,
    `https://storage.googleapis.com/storage/v1/b/BUCKET_NAME`) containing the
    JSON payload for the unexposed feature (refer to
    [REST API Reference](rest.md)), passing the token in the `Authorization:
    Bearer <token>` header.

### Pattern 3: Hybrid SDK + Auto-generated Client (Go Only)

For Go applications, developers can use the raw, auto-generated API client
(`google.golang.org/api/storage/v1`) specifically for the unexposed
configuration, while using the standard `cloud.google.com/go/storage` client for
other operations. Both clients can share the same authenticated HTTP client.

--------------------------------------------------------------------------------

## SDK Language-Specific Examples

Detailed examples for each supported language can be found in the following
reference documents:

*   [C++ SDK Examples](sdk_cpp.md)
*   [Go SDK Examples](sdk_go.md)
*   [Java SDK Examples](sdk_java.md)
*   [Python SDK Examples](sdk_python.md)
