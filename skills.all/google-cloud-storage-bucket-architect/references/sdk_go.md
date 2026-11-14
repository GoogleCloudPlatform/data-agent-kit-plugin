# Go SDK Examples

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the Go SDK.

## Official Documentation Reference

*   [Cloud Storage Go Package Reference](https://pkg.go.dev/cloud.google.com/go/storage)

## Client Initialization

```go
import (
    "context"

    "cloud.google.com/go/storage"
)

// ...
ctx := context.Background()
client, err := storage.NewClient(ctx)
```

## Version Requirements

> [!IMPORTANT]
> **Encryption Enforcement Config** requires the Go Cloud Storage
> SDK version **1.61.0** or higher. If you are using a version below 1.61.0, you
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

```go
import (
    "context"
    "time"

    "cloud.google.com/go/storage"
)

func CreateSecureBucket(ctx context.Context, client *storage.Client, projectID, bucketName string) (*storage.BucketAttrs, error) {
    bucket := client.Bucket(bucketName)
    attrs := &storage.BucketAttrs{
        Location:      "us-east1",
        StorageClass:  "STANDARD",
        UniformBucketLevelAccess: storage.UniformBucketLevelAccess{
            Enabled: true,
        },
        PublicAccessPrevention: storage.PublicAccessPreventionEnforced,
        CustomerSuppliedEncryptionEnforcementConfig: &storage.EncryptionEnforcementConfig{
            RestrictionMode: storage.FullyRestricted,
        },
        SoftDeletePolicy: &storage.SoftDeletePolicy{
            RetentionDuration: 7 * 24 * time.Hour,
        },
    }
    if err := bucket.Create(ctx, projectID, attrs); err != nil {
        return nil, err
    }
    return bucket.Attrs(ctx)
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

```go
import (
    "context"
    "time"

    "cloud.google.com/go/storage"
)

func CreateComplianceBucket(ctx context.Context, client *storage.Client, projectID, bucketName, kmsKeyID string) (*storage.BucketAttrs, error) {
    bucket := client.Bucket(bucketName)
    attrs := &storage.BucketAttrs{
        Location:      "us-central1",
        StorageClass:  "STANDARD",
        UniformBucketLevelAccess: storage.UniformBucketLevelAccess{
            Enabled: true,
        },
        PublicAccessPrevention: storage.PublicAccessPreventionEnforced,
        Encryption: &storage.BucketEncryption{
            DefaultKMSKeyName: kmsKeyID,
        },
        CustomerSuppliedEncryptionEnforcementConfig: &storage.EncryptionEnforcementConfig{
            RestrictionMode: storage.FullyRestricted,
        },
        // NOTE: IP Filtering is not supported via attributes in this Go client
        // library version. This must be configured using the REST API or gcloud.
        RetentionPolicy: &storage.RetentionPolicy{
            RetentionPeriod: 90 * 24 * time.Hour,
        },
        Autoclass: &storage.Autoclass{
            Enabled: true,
        },
        Labels: map[string]string{
            "data-class": "pii",
            "owner":      "security-team",
        },
        Lifecycle: storage.Lifecycle{
            Rules: []storage.LifecycleRule{
                {
                    Action: storage.LifecycleAction{
                        Type: "AbortIncompleteMultipartUpload",
                    },
                    Condition: storage.LifecycleCondition{
                        AgeInDays: 7,
                    },
                },
            },
        },
        SoftDeletePolicy: &storage.SoftDeletePolicy{
            RetentionDuration: 7 * 24 * time.Hour,
        },
    }
    if err := bucket.Create(ctx, projectID, attrs); err != nil {
        return nil, err
    }
    return bucket.Attrs(ctx)
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

```go
import (
    "context"
    "time"

    "cloud.google.com/go/iam"
    "cloud.google.com/go/storage"
)

func CreateStaticWebsiteBucket(ctx context.Context, client *storage.Client, projectID, bucketName string) (*storage.BucketAttrs, error) {
    bucket := client.Bucket(bucketName)
    attrs := &storage.BucketAttrs{
        Location:      "US",
        StorageClass:  "STANDARD",
        UniformBucketLevelAccess: storage.UniformBucketLevelAccess{
            Enabled: true,
        },
        PublicAccessPrevention: storage.PublicAccessPreventionInherited,
        VersioningEnabled: true,
        SoftDeletePolicy: &storage.SoftDeletePolicy{
            RetentionDuration: 7 * 24 * time.Hour,
        },
        Website: &storage.BucketWebsite{
            MainPageSuffix: "index.html",
            NotFoundPage:   "404.html",
        },
        CORS: []storage.CORS{{
            MaxAge:          3600 * time.Second,
            Methods:         []string{"GET", "HEAD", "OPTIONS"},
            Origins:         []string{"*"},
            ResponseHeaders: []string{"Content-Type"},
        }},
    }
    if err := bucket.Create(ctx, projectID, attrs); err != nil {
        return nil, err
    }

    // Grant public access
    iamHandle := bucket.IAM()
    policy, err := iamHandle.Policy(ctx)
    if err != nil {
        return nil, err
    }
    policy.Add(iam.AllUsers, "roles/storage.objectViewer")
    if err := iamHandle.SetPolicy(ctx, policy); err != nil {
        return nil, err
    }
    return bucket.Attrs(ctx)
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

```go
import (
    "context"
    "time"

    "cloud.google.com/go/storage"
)

func CreateCheckpointBucket(ctx context.Context, client *storage.Client, projectID, bucketName string) (*storage.BucketAttrs, error) {
    bucket := client.Bucket(bucketName)
    attrs := &storage.BucketAttrs{
        Location:      "us-east1",
        StorageClass:  "RAPID",
        UniformBucketLevelAccess: storage.UniformBucketLevelAccess{
            Enabled: true,
        },
        PublicAccessPrevention: storage.PublicAccessPreventionEnforced,
        CustomPlacementConfig: &storage.CustomPlacementConfig{
            DataLocations: []string{"us-east1-b"},
        },
        HierarchicalNamespace: &storage.HierarchicalNamespace{
            Enabled: true,
        },
        Lifecycle: storage.Lifecycle{
            Rules: []storage.LifecycleRule{
                {
                    Action: storage.LifecycleAction{
                        Type: "Delete",
                    },
                    Condition: storage.LifecycleCondition{
                        AgeInDays: 14,
                    },
                },
            },
        },
        SoftDeletePolicy: &storage.SoftDeletePolicy{
            RetentionDuration: 0,
        },
    }
    if err := bucket.Create(ctx, projectID, attrs); err != nil {
        return nil, err
    }
    return bucket.Attrs(ctx)
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

```go
import (
    "context"
    "time"

    "cloud.google.com/go/storage"
)

func CreateRegulatoryWormBucket(ctx context.Context, client *storage.Client, projectID, bucketName, kmsKeyID string) (*storage.BucketAttrs, error) {
    // 1. Enable Object Retention on the BucketHandle before creating
    bucket := client.Bucket(bucketName).SetObjectRetention(true)

    // 2. Configure bucket attributes
    attrs := &storage.BucketAttrs{
        Location:      "us-east1",
        StorageClass:  "ARCHIVE",
        UniformBucketLevelAccess: storage.UniformBucketLevelAccess{
            Enabled: true,
        },
        PublicAccessPrevention: storage.PublicAccessPreventionEnforced,
        Encryption: &storage.BucketEncryption{
            DefaultKMSKeyName: kmsKeyID,
        },
        Labels: map[string]string{
            "compliance-type":  "regulatory",
            "retention-period": "7y",
        },
        SoftDeletePolicy: &storage.SoftDeletePolicy{
            RetentionDuration: 7 * 24 * time.Hour,
        },
        Lifecycle: storage.Lifecycle{
            Rules: []storage.LifecycleRule{
                {
                    Action: storage.LifecycleAction{
                        Type: "Delete",
                    },
                    Condition: storage.LifecycleCondition{
                        AgeInDays: 2555,
                    },
                },
            },
        },
    }

    if err := bucket.Create(ctx, projectID, attrs); err != nil {
        return nil, err
    }
    return bucket.Attrs(ctx)
}

func UploadObjectWithRetention(ctx context.Context, client *storage.Client, bucketName, objectName string) error {
    bucket := client.Bucket(bucketName)
    obj := bucket.Object(objectName)

    wc := obj.NewWriter(ctx)
    wc.ObjectAttrs.Retention = &storage.ObjectRetention{
        Mode:        "Locked",
        RetainUntil: time.Date(2030, 12, 31, 23, 59, 59, 0, time.UTC),
    }

    // Write object content
    if _, err := wc.Write([]byte("compliance data")); err != nil {
        wc.Close()
        return err
    }
    return wc.Close()
}
```
