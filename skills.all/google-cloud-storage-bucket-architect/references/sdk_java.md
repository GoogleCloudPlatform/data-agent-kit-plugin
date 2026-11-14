# Java SDK Examples

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the Java SDK.

## Official Documentation Reference

*   [Cloud Storage Client for Java Documentation](https://cloud.google.com/java/docs/reference/google-cloud-storage/latest/overview)

## Version Requirements

> [!IMPORTANT]
> **Encryption Enforcement Config** requires the Java SDK version
> **2.55.0** or higher. If you are using a version below 2.55.0, you must
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

```java
import com.google.cloud.storage.Bucket;
import com.google.cloud.storage.BucketInfo;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageClass;
import com.google.cloud.storage.StorageOptions;
import java.time.Duration;

public class GcsExamples {

  public static Bucket createSecureBucket(String projectId, String bucketName) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();

    BucketInfo.IamConfiguration iamConfig = BucketInfo.IamConfiguration.newBuilder()
        .setIsUniformBucketLevelAccessEnabled(true)
        .setPublicAccessPrevention(BucketInfo.PublicAccessPrevention.ENFORCED)
        .build();

    BucketInfo.CustomerSuppliedEncryptionEnforcementConfig csekConfig =
        BucketInfo.CustomerSuppliedEncryptionEnforcementConfig.of(
            BucketInfo.EncryptionEnforcementRestrictionMode.FULLY_RESTRICTED);

    BucketInfo bucketInfo = BucketInfo.newBuilder(bucketName)
        .setLocation("us-east1")
        .setStorageClass(StorageClass.STANDARD)
        .setIamConfiguration(iamConfig)
        .setCustomerSuppliedEncryptionEnforcementConfig(csekConfig)
        .setSoftDeletePolicy(BucketInfo.SoftDeletePolicy.newBuilder()
            .setRetentionDuration(Duration.ofDays(7))
            .build())
        .build();

    return storage.create(bucketInfo);
  }
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

```java
import com.google.cloud.storage.Bucket;
import com.google.cloud.storage.BucketInfo;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageClass;
import com.google.cloud.storage.StorageOptions;
import java.time.Duration;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class GcsExamples {

  public static Bucket createComplianceBucket(String projectId, String bucketName, String kmsKeyId) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();

    BucketInfo.IamConfiguration iamConfig = BucketInfo.IamConfiguration.newBuilder()
        .setIsUniformBucketLevelAccessEnabled(true)
        .setPublicAccessPrevention(BucketInfo.PublicAccessPrevention.ENFORCED)
        .build();

    BucketInfo.CustomerSuppliedEncryptionEnforcementConfig csekConfig =
        BucketInfo.CustomerSuppliedEncryptionEnforcementConfig.of(
            BucketInfo.EncryptionEnforcementRestrictionMode.FULLY_RESTRICTED);
    BucketInfo.CustomerManagedEncryptionEnforcementConfig cmekConfig =
        BucketInfo.CustomerManagedEncryptionEnforcementConfig.of(
            BucketInfo.EncryptionEnforcementRestrictionMode.NOT_RESTRICTED);
    BucketInfo.GoogleManagedEncryptionEnforcementConfig gmekConfig =
        BucketInfo.GoogleManagedEncryptionEnforcementConfig.of(
            BucketInfo.EncryptionEnforcementRestrictionMode.NOT_RESTRICTED);

    // IP Filtering configuration
    BucketInfo.IpFilter.PublicNetworkSource publicSource = BucketInfo.IpFilter.PublicNetworkSource.of(
        Collections.singletonList("192.0.2.0/24"));

    BucketInfo.IpFilter.VpcNetworkSource vpcSource = BucketInfo.IpFilter.VpcNetworkSource.newBuilder()
        .setNetwork("projects/" + projectId + "/global/networks/NETWORK_NAME")
        .setAllowedIpCidrRanges(Collections.singletonList("10.0.0.0/16"))
        .build();

    BucketInfo.IpFilter ipFilter = BucketInfo.IpFilter.newBuilder()
        .setMode("Enabled")
        .setAllowAllServiceAgentAccess(true)
        .setAllowCrossOrgVpcs(false)
        .setPublicNetworkSource(publicSource)
        .setVpcNetworkSources(Collections.singletonList(vpcSource))
        .build();

    Map<String, String> labels = new HashMap<>();
    labels.put("data-class", "pii");
    labels.put("owner", "security-team");

    BucketInfo bucketInfo = BucketInfo.newBuilder(bucketName)
        .setLocation("us-central1")
        .setStorageClass(StorageClass.STANDARD)
        .setIamConfiguration(iamConfig)
        .setDefaultKmsKeyName(kmsKeyId)
        .setCustomerSuppliedEncryptionEnforcementConfig(csekConfig)
        .setCustomerManagedEncryptionEnforcementConfig(cmekConfig)
        .setGoogleManagedEncryptionEnforcementConfig(gmekConfig)
        .setIpFilter(ipFilter)
        .setSoftDeletePolicy(BucketInfo.SoftDeletePolicy.newBuilder()
            .setRetentionDuration(Duration.ofDays(7))
            .build())
        .setRetentionPeriodDuration(Duration.ofDays(90))
        .setAutoclass(BucketInfo.Autoclass.newBuilder().setEnabled(true).build())
        .setLabels(labels)
        .setLifecycleRules(Collections.singletonList(
            new BucketInfo.LifecycleRule(
                BucketInfo.LifecycleRule.LifecycleAction.newAbortIncompleteMPUploadAction(),
                BucketInfo.LifecycleRule.LifecycleCondition.newBuilder().setAge(7).build()
            )
        ))
        .build();

    return storage.create(bucketInfo);
  }

  // Locking the retention policy is permanent and irreversible.
  public static Bucket lockRetentionPolicy(String projectId, String bucketName) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();
    Bucket bucket = storage.get(bucketName);
    return bucket.lockRetentionPolicy(Storage.BucketTargetOption.metagenerationMatch());
  }
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

```java
import com.google.cloud.Identity;
import com.google.cloud.Policy;
import com.google.cloud.storage.Bucket;
import com.google.cloud.storage.BucketInfo;
import com.google.cloud.storage.Cors;
import com.google.cloud.storage.HttpMethod;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageClass;
import com.google.cloud.storage.StorageOptions;
import com.google.cloud.storage.StorageRoles;
import java.time.Duration;
import java.util.Arrays;
import java.util.Collections;

public class GcsExamples {

  public static Bucket createStaticWebsiteBucket(String projectId, String bucketName) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();

    Cors cors = Cors.newBuilder()
        .setMaxAgeSeconds(3600)
        .setMethods(Arrays.asList(HttpMethod.GET, HttpMethod.HEAD, HttpMethod.OPTIONS))
        .setOrigins(Collections.singletonList(Cors.Origin.of("*")))
        .setResponseHeaders(Collections.singletonList("Content-Type"))
        .build();

    BucketInfo.IamConfiguration iamConfig = BucketInfo.IamConfiguration.newBuilder()
        .setIsUniformBucketLevelAccessEnabled(true)
        .setPublicAccessPrevention(BucketInfo.PublicAccessPrevention.INHERITED) // allow public
        .build();

    BucketInfo bucketInfo = BucketInfo.newBuilder(bucketName)
        .setStorageClass(StorageClass.STANDARD)
        .setLocation("US")
        .setIamConfiguration(iamConfig)
        .setVersioningEnabled(true)
        .setSoftDeletePolicy(BucketInfo.SoftDeletePolicy.newBuilder()
            .setRetentionDuration(Duration.ofDays(7))
            .build())
        .setIndexPage("index.html")
        .setNotFoundPage("404.html")
        .setCors(Collections.singletonList(cors))
        .build();

    Bucket bucket = storage.create(bucketInfo);

    // Grant public access
    Policy policy = storage.getIamPolicy(bucketName);
    policy = policy.toBuilder()
        .addIdentity(StorageRoles.objectViewer(), Identity.allUsers())
        .build();
    storage.setIamPolicy(bucketName, policy);

    return bucket;
  }
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
*   **Soft Delete**: Disabled (Not supported for zonal buckets)
*   **Use-case specific settings**:
    *   Hierarchical Namespace: Enabled (Required for Zonal buckets)
    *   Lifecycle: Delete checkpoint files older than 14 days

```java
import com.google.cloud.storage.Bucket;
import com.google.cloud.storage.BucketInfo;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageClass;
import com.google.cloud.storage.StorageOptions;
import com.google.cloud.storage.BucketInfo.CustomPlacementConfig;
import java.time.Duration;
import java.util.Collections;

public class GcsExamples {

  public static Bucket createCheckpointBucket(String projectId, String bucketName) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();

    BucketInfo.IamConfiguration iamConfig = BucketInfo.IamConfiguration.newBuilder()
        .setIsUniformBucketLevelAccessEnabled(true)
        .setPublicAccessPrevention(BucketInfo.PublicAccessPrevention.ENFORCED)
        .build();

    BucketInfo bucketInfo = BucketInfo.newBuilder(bucketName)
        .setStorageClass(StorageClass.valueOf("RAPID"))
        .setLocation("us-east1")
        .setCustomPlacementConfig(CustomPlacementConfig.newBuilder()
            .setDataLocations(Collections.singletonList("us-east1-b"))
            .build())
        .setIamConfiguration(iamConfig)
        .setHierarchicalNamespace(BucketInfo.HierarchicalNamespace.newBuilder().setEnabled(true).build())
        .setSoftDeletePolicy(BucketInfo.SoftDeletePolicy.newBuilder()
            .setRetentionDuration(Duration.ZERO)
            .build())
        .setLifecycleRules(Collections.singletonList(
            new BucketInfo.LifecycleRule(
                BucketInfo.LifecycleRule.LifecycleAction.newDeleteAction(),
                BucketInfo.LifecycleRule.LifecycleCondition.newBuilder().setAge(14).build()
            )
        ))
        .build();

    return storage.create(bucketInfo);
  }
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
>
> Setting per-object retention mode to "Locked" is irreversible. Once set, the
> mode cannot be changed back and the retention date can only be extended.

```java
import com.google.cloud.storage.Blob;
import com.google.cloud.storage.BlobInfo;
import com.google.cloud.storage.Bucket;
import com.google.cloud.storage.BucketInfo;
import com.google.cloud.storage.Storage;
import com.google.cloud.storage.StorageClass;
import com.google.cloud.storage.StorageOptions;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class GcsExamples {

  public static Bucket createRegulatoryWormBucket(String projectId, String bucketName, String kmsKeyId) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();

    BucketInfo.IamConfiguration iamConfig = BucketInfo.IamConfiguration.newBuilder()
        .setIsUniformBucketLevelAccessEnabled(true)
        .setPublicAccessPrevention(BucketInfo.PublicAccessPrevention.ENFORCED)
        .build();

    Map<String, String> labels = new HashMap<>();
    labels.put("compliance-type", "regulatory");
    labels.put("retention-period", "7y");

    BucketInfo bucketInfo = BucketInfo.newBuilder(bucketName)
        .setStorageClass(StorageClass.ARCHIVE)
        .setLocation("us-east1")
        .setIamConfiguration(iamConfig)
        .setDefaultKmsKeyName(kmsKeyId)
        .setLabels(labels)
        .setSoftDeletePolicy(BucketInfo.SoftDeletePolicy.newBuilder()
            .setRetentionDuration(Duration.ofDays(7))
            .build())
        .setLifecycleRules(Collections.singletonList(
            new BucketInfo.LifecycleRule(
                BucketInfo.LifecycleRule.LifecycleAction.newDeleteAction(),
                BucketInfo.LifecycleRule.LifecycleCondition.newBuilder().setAge(2555).build() // 7 years
            )
        ))
        .build();

    // Enable Object Retention during bucket creation
    return storage.create(bucketInfo,
        Storage.BucketTargetOption.enableObjectRetention(true));
  }

  public static Blob uploadObjectWithRetention(String projectId, String bucketName, String objectName, byte[] content) {
    Storage storage = StorageOptions.newBuilder()
        .setProjectId(projectId)
        .build()
        .getService();

    // Retain until Dec 31, 2030
    OffsetDateTime retainUntil = OffsetDateTime.of(2030, 12, 31, 23, 59, 59, 0, ZoneOffset.UTC);

    BlobInfo.Retention retention = BlobInfo.Retention.newBuilder()
        .setMode(BlobInfo.Retention.Mode.LOCKED)
        .setRetainUntilTime(retainUntil)
        .build();

    BlobInfo blobInfo = BlobInfo.newBuilder(bucketName, objectName)
        .setRetention(retention)
        .build();

    return storage.create(blobInfo, content);
  }
}
```
