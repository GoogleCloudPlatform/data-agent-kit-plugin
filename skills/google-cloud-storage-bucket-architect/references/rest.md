# Cloud Storage JSON API Reference

> [!IMPORTANT]
>
> **DO NOT EXECUTE THESE COMMANDS AUTOMATICALLY.** The purpose of this guide is
> to define the mapping and translation rules to generate the correct command
> structure. These generated commands must be presented to the user for
> confirmation and are only executed in a subsequent phase if explicit
> confirmation is granted by the user.

This guide describes how to translate a **Draft Bucket Creation Plan** (from
Phase 2) into the corresponding JSON API (REST) request bodies/cURL commands.

## Official Documentation Reference

*   [Cloud Storage JSON API Overview](https://cloud.google.com/storage/docs/json_api)
*   [Buckets Resource Reference](https://cloud.google.com/storage/docs/json_api/v1/buckets)
*   [Objects Resource Reference](https://cloud.google.com/storage/docs/json_api/v1/objects)

--------------------------------------------------------------------------------

## Translation Mapping Table

Draft Plan Field / Setting         | REST API Resource Field / Path                      | Notes / Action
:--------------------------------- | :-------------------------------------------------- | :-------------
**Bucket Name**                    | `name`                                              | String in request body. Must be globally unique.
**Project**                        | Query Parameter: `?project=[project-id]`            | Passed in the query string of the request URL.
**Location**                       | `location`                                          | String. E.g., `us-central1`, `US`. For zonal buckets (using the Rapid storage class), use the region (e.g., `us-east1`) if the plan specifies a zone.
**Placement**                      | `customPlacementConfig.dataLocations`               | Array of strings. E.g., `["us-east1", "us-west1"]` (for custom dual-regions), or `["us-east1-a"]` (for zonal buckets).
**Replication Speed (RPO)**        | `rpo`                                               | String. E.g., `"ASYNC_TURBO"` (for dual-region buckets).
**Storage Class**                  | `storageClass`                                      | String. E.g., `"STANDARD"`, `"NEARLINE"`, `"COLDLINE"`, `"ARCHIVE"`.
**UBLA**                           | `iamConfiguration.uniformBucketLevelAccess.enabled` | Boolean. Always set to `true`.
**Public Access Prevention**       | `iamConfiguration.publicAccessPrevention`           | String. `"enforced"` or `"inherited"`.
**Soft Delete**                    | `softDeletePolicy.retentionDurationSeconds`         | Integer (seconds). E.g. `604800` (7 days). Set to `0` to disable.
**Object Versioning**              | `versioning.enabled`                                | Boolean. Enables/disables versioning.
**Encryption (CMEK)**              | `encryption.defaultKmsKeyName`                      | String. Full key ID: `projects/.../cryptoKeys/...`
**Restrict Encryption (CSEK)**     | `encryption` enforcement fields                     | Configuration for restricting encryption methods. See below.
**Autoclass**                      | `autoclass.enabled`                                 | Boolean. Set to `true` to enable.
**Hierarchical Namespace**         | `hierarchicalNamespace.enabled`                     | Boolean. Set to `true` to enable.
**Labels**                         | `labels`                                            | Object (key-value pairs of strings).
**IP Filtering**                   | `ipFilter`                                          | Object. Defines IP restriction rules. See below.
**Lifecycle Policies (OLM)**       | `lifecycle.rule`                                    | Array of rules. See template below.
**CORS**                           | `cors`                                              | Array of CORS rule objects.
**Website Configuration**          | `website.mainPageSuffix` / `website.notFoundPage`   | Strings for index and 404 pages.
**Public IAM Policy**              | `storage.buckets.setIamPolicy`                      | Separate PUT request to set IAM policy (adding `allUsers` as `roles/storage.objectViewer`).
**Pub/Sub Notifications**          | `storage.notifications.insert`                      | Separate POST request to `POST https://storage.googleapis.com/storage/v1/b/BUCKET_NAME/notificationConfigs`.
**Bucket Retention Period**        | `retentionPolicy.retentionPeriod`                   | Integer seconds. E.g. `7776000` (90 days).
**Lock Bucket Retention Policy**   | `storage.buckets.lockRetentionPolicy`               | Separate POST request to lock. **Irreversible.**
**Object Retention (Object Lock)** | Query Parameter: `enableObjectRetention=true`       | Boolean. Set to `true` during bucket creation (`buckets.insert`) to permanently enable object retention.
**Set Object Retention**           | Object `retention` property                         | Property on object: `{"mode": "Locked", "retainUntilTime": "..."}`. Applied via `PATCH` to object or during upload.
**Rapid Cache**                    | `storage.anywhereCaches.insert`                     | Separate POST request to `POST https://storage.googleapis.com/storage/v1/b/BUCKET_NAME/anywhereCaches`.

--------------------------------------------------------------------------------

## Helper Configuration Templates

### Encryption Enforcement (CSEK Restriction)

Unlike the `gcloud` CLI which abstracts these settings into short names at the
root, the JSON API requires the full config names nested under the `encryption`
object:

```json
{
  "encryption": {
    "googleManagedEncryptionEnforcementConfig": {
      "restrictionMode": "NotRestricted"
    },
    "customerManagedEncryptionEnforcementConfig": {
      "restrictionMode": "NotRestricted"
    },
    "customerSuppliedEncryptionEnforcementConfig": {
      "restrictionMode": "FullyRestricted"
    }
  }
}
```

### IP Filtering

```json
{
  "ipFilter": {
    "mode": "Enabled",
    "publicNetworkSource": {
      "allowedIpCidrRanges": [
        "192.0.2.0/24"
      ]
    },
    "vpcNetworkSources": [
      {
        "network": "projects/PROJECT_ID/global/networks/NETWORK_NAME",
        "allowedIpCidrRanges": [
          "10.0.0.0/16"
        ]
      }
    ],
    "allowCrossOrgVpcs": false,
    "allowAllServiceAgentAccess": true
  }
}
```

### Lifecycle Policy (OLM)

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 365
        }
      }
    ]
  }
}
```

### CORS Configuration

```json
{
  "cors": [
    {
      "origin": ["http://example.appspot.com"],
      "method": ["GET", "PUT", "POST", "DELETE"],
      "responseHeader": ["Content-Type", "Authorization"],
      "maxAgeSeconds": 3600
    }
  ]
}
```

--------------------------------------------------------------------------------

## Executing REST Requests via cURL

To execute the REST API requests documented below using `curl`, you must include
an Authorization header with a valid OAuth 2.0 access token, and the User-Agent
header for attribution.

You can retrieve a token using the Google Cloud SDK (`gcloud`):

```bash
curl -X POST \
  "https://storage.googleapis.com/storage/v1/b?project=PROJECT_ID" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)" \
  -H "Content-Type: application/json" \
  -d @body.json
```

Where:

*   `body.json` contains the JSON request payload.
*   `$(gcloud auth print-access-token)` dynamically generates a short-lived
    access token for your currently active `gcloud` credentials.

--------------------------------------------------------------------------------

## REST API Request Examples

All creation requests are sent to: `POST
https://storage.googleapis.com/storage/v1/b?project=PROJECT_ID`

All update/patch requests are sent to: `PATCH
https://storage.googleapis.com/storage/v1/b/BUCKET_NAME`

All headers must include:

*   `Authorization: Bearer <token>`
*   `User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-bucket-architect)`
*   `Content-Type: application/json`

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

#### Output REST Request

**Method/URL:** `POST
https://storage.googleapis.com/storage/v1/b?project=my-security-project`

**Request Body:**

```json
{
  "name": "my-company-secure-bucket",
  "location": "us-east1",
  "storageClass": "STANDARD",
  "iamConfiguration": {
    "uniformBucketLevelAccess": {
      "enabled": true
    },
    "publicAccessPrevention": "enforced"
  },
  "softDeletePolicy": {
    "retentionDurationSeconds": 604800
  },
  "encryption": {
    "customerSuppliedEncryptionEnforcementConfig": {
      "restrictionMode": "FullyRestricted"
    }
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

#### Output REST Request

**Method/URL:** `POST
https://storage.googleapis.com/storage/v1/b?project=my-compliance-project`

**Request Body:**

```json
{
  "name": "my-compliance-pii-bucket",
  "location": "us-central1",
  "storageClass": "STANDARD",
  "iamConfiguration": {
    "uniformBucketLevelAccess": {
      "enabled": true
    },
    "publicAccessPrevention": "enforced"
  },
  "encryption": {
    "defaultKmsKeyName": "projects/my-kms-project/locations/us-central1/keyRings/my-keyring/cryptoKeys/my-key",
    "customerSuppliedEncryptionEnforcementConfig": {
      "restrictionMode": "FullyRestricted"
    },
    "customerManagedEncryptionEnforcementConfig": {
      "restrictionMode": "NotRestricted"
    },
    "googleManagedEncryptionEnforcementConfig": {
      "restrictionMode": "NotRestricted"
    }
  },
  "softDeletePolicy": {
    "retentionDurationSeconds": 604800
  },
  "retentionPolicy": {
    "retentionPeriod": 7776000
  },
  "autoclass": {
    "enabled": true
  },
  "labels": {
    "data-class": "pii",
    "owner": "security-team"
  },
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "AbortIncompleteMultipartUpload"
        },
        "condition": {
          "age": 7
        }
      }
    ]
  },
  "ipFilter": {
    "mode": "Enabled",
    "allowAllServiceAgentAccess": true,
    "publicNetworkSource": {
      "allowedIpCidrRanges": ["192.0.2.0/24"]
    },
    "vpcNetworkSources": [
      {
        "network": "projects/my-project/global/networks/my-vpc-network",
        "allowedIpCidrRanges": ["10.0.0.0/16"]
      }
    ],
    "allowCrossOrgVpcs": false
  }
}
```

*(Note: The retention policy is created unlocked. To lock it (making it
permanent and irreversible), send an empty POST request to: `POST
https://storage.googleapis.com/storage/v1/b/my-compliance-pii-bucket/lockRetentionPolicy?ifMetagenerationMatch=METAGENERATION`).*

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
    *   CORS: Allowed GET/HEAD/OPTIONS from any domain
    *   Versioning: Enabled
```

#### Output REST Request

**1. Create the Bucket:**

**Method/URL:** `POST
https://storage.googleapis.com/storage/v1/b?project=my-frontend-project`

**Request Body:**

```json
{
  "name": "www.my-company-site.com",
  "location": "US",
  "storageClass": "STANDARD",
  "iamConfiguration": {
    "uniformBucketLevelAccess": {
      "enabled": true
    },
    "publicAccessPrevention": "inherited"
  },
  "softDeletePolicy": {
    "retentionDurationSeconds": 604800
  }
}
```

**2. Configure Website, CORS, and Versioning:**

**Method/URL:** `PATCH
https://storage.googleapis.com/storage/v1/b/www.my-company-site.com`

**Request Body:**

```json
{
  "website": {
    "mainPageSuffix": "index.html",
    "notFoundPage": "404.html"
  },
  "cors": [
    {
      "origin": ["*"],
      "method": ["GET", "HEAD", "OPTIONS"],
      "responseHeader": ["Content-Type"],
      "maxAgeSeconds": 3600
    }
  ],
  "versioning": {
    "enabled": true
  }
}
```

**3. Set Public Read Access (Read-Modify-Write):**

> [!WARNING]
> Setting the IAM policy (`PUT /iam`) replaces the entire existing
> policy. To avoid silently dropping default project convenience bindings or
> other existing permissions, you must perform a read-modify-write operation:
> GET the current policy, append the new binding, and PUT the updated policy
> back.

**Step 3a: Get the current IAM Policy:**

**Method/URL:** `GET
https://storage.googleapis.com/storage/v1/b/www.my-company-site.com/iam`

**Response Body (Example of current policy):**

```json
{
  "kind": "storage#policy",
  "resourceId": "projects/_/buckets/www.my-company-site.com",
  "bindings": [
    {
      "role": "roles/storage.legacyBucketOwner",
      "members": [
        "projectOwner:my-frontend-project",
        "projectEditor:my-frontend-project"
      ]
    },
    {
      "role": "roles/storage.legacyBucketReader",
      "members": [
        "projectViewer:my-frontend-project"
      ]
    }
  ],
  "etag": "CAE="
}
```

**Step 3b: Append the public read binding and update the policy:**

**Method/URL:** `PUT
https://storage.googleapis.com/storage/v1/b/www.my-company-site.com/iam`

**Request Body (Merged with the new binding, keeping the etag):**

```json
{
  "kind": "storage#policy",
  "resourceId": "projects/_/buckets/www.my-company-site.com",
  "bindings": [
    {
      "role": "roles/storage.legacyBucketOwner",
      "members": [
        "projectOwner:my-frontend-project",
        "projectEditor:my-frontend-project"
      ]
    },
    {
      "role": "roles/storage.legacyBucketReader",
      "members": [
        "projectViewer:my-frontend-project"
      ]
    },
    {
      "role": "roles/storage.objectViewer",
      "members": [
        "allUsers"
      ]
    }
  ],
  "etag": "CAE="
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
*   **Soft Delete**: Disabled (Not supported for zonal buckets)
*   **Use-case specific settings**:
    *   Hierarchical Namespace: Enabled (Required for Zonal buckets)
    *   Lifecycle: Delete checkpoint files older than 14 days
```

#### Output REST Request

**Method/URL:** `POST
https://storage.googleapis.com/storage/v1/b?project=my-ai-project`

**Request Body:**

```json
{
  "name": "my-training-checkpoints-us-east1-b",
  "location": "us-east1",
  "storageClass": "RAPID",
  "customPlacementConfig": {
    "dataLocations": ["us-east1-b"]
  },
  "iamConfiguration": {
    "uniformBucketLevelAccess": {
      "enabled": true
    },
    "publicAccessPrevention": "enforced"
  },
  "hierarchicalNamespace": {
    "enabled": true
  },
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 14
        }
      }
    ]
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
    *   Lifecycle: Delete objects older than 7 years (2555 days)
```

#### Output REST Request

**Method/URL:** `POST
https://storage.googleapis.com/storage/v1/b?project=my-legal-project&enableObjectRetention=true`

**Request Body:**

```json
{
  "name": "my-legal-archive-bucket",
  "location": "us-east1",
  "storageClass": "ARCHIVE",
  "iamConfiguration": {
    "uniformBucketLevelAccess": {
      "enabled": true
    },
    "publicAccessPrevention": "enforced"
  },
  "encryption": {
    "defaultKmsKeyName": "projects/my-kms-project/locations/us-east1/keyRings/my-keyring/cryptoKeys/my-key"
  },
  "softDeletePolicy": {
    "retentionDurationSeconds": 604800
  },
  "labels": {
    "compliance-type": "regulatory",
    "retention-period": "7y"
  },
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 2555
        }
      }
    ]
  }
}
```

--------------------------------------------------------------------------------

## Object Operations for Object Lock

### Set Object Retention on Upload

Upload an object with a specific retention period. `POST
https://storage.googleapis.com/upload/storage/v1/b/my-legal-archive-bucket/o?uploadType=multipart`

**Multipart Request Body (Metadata part):**

> [!CAUTION]
>
> Locking a retention policy is permanent and irreversible. Once locked, the
> retention period cannot be reduced or removed.

```json
{
  "name": "compliance_report_2026.pdf",
  "retention": {
    "mode": "Unlocked",
    "retainUntilTime": "2030-12-31T23:59:59Z"
  }
}
```

### Set Object Retention on Existing Object

> [!IMPORTANT]
> If you are modifying an existing `Unlocked` retention
> configuration on an object, you must append `?overrideUnlockedRetention=true`
> to the request URL if you want to:
>
> *   Change the mode to `Locked`.
> *   Reduce the `retainUntilTime`.
> *   Remove the retention configuration.
>
> If this parameter is omitted when performing these actions on an object with
> existing `Unlocked` retention, the request will fail.

Update an existing object to apply retention. `PATCH
https://storage.googleapis.com/storage/v1/b/my-legal-archive-bucket/o/compliance_report_2026.pdf?overrideUnlockedRetention=true`

**Request Body:**

```json
{
  "retention": {
    "mode": "Locked",
    "retainUntilTime": "2030-12-31T23:59:59Z"
  }
}
```
