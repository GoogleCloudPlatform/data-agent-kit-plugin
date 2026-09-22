---
name: google-cloud-storage-basics
description: >-
  Stores, retrieves, and manages data as objects in Cloud Storage (Google
  Cloud Storage, or GCS) buckets. Use when you need to interact with Cloud
  Storage — set up a Storage MCP server (remote or local Toolbox), create or
  configure buckets, upload, download, stream, or transfer data, organize
  objects with folders, generate signed URLs, control access (IAM, ACLs,
  public access prevention), set storage classes (Standard, Nearline,
  Coldline, Archive), manage lifecycle and cost, protect data (versioning,
  CMEK, retention, Bucket Lock, holds, soft delete), host static websites,
  trigger Pub/Sub notifications, mount buckets (gcsfuse), or optimize
  performance. Covers gcloud storage / gsutil, JSON/XML APIs, client
  libraries, Terraform, and Cloud Storage MCP servers. Don't use for
  non-Storage MCP servers, block storage (Persistent Disk), BigQuery, or
  databases (Cloud SQL, Spanner, Bigtable, Firestore).
metadata:
    version: v2
    publisher: google
    tags:
      - gcs
      - storage
      - cloud-storage
      - buckets
      - objects
    category: storage
    support_tier: primary
license: Apache-2.0
---

# Google Cloud Storage Basics

Google Cloud Storage (GCS) is a managed service for storing data as objects at
any scale. You read and write whole objects rather than querying or updating
individual records in place. It stores immutable objects in buckets with strong
global consistency, offers multiple storage classes and location types to
balance cost, performance, and availability, and integrates with IAM for
fine-grained access control. GCS serves workloads ranging from website content
and backups to data lakes and high-throughput AI/ML training.

## Attribution

Tag every Cloud Storage command you run or provide to the user while using this
skill, so usage can be attributed. The tag identifies only the skill and its
version; it carries no user data.

-   Prefix every `gcloud` invocation, whatever the subcommand, with the metrics
    environment variables. Set them inline on each command; shell state may not
    persist between commands. Use this append form verbatim. It keeps any
    attribution the host environment already set (for example an IDE plugin
    tagging agent activity through the same variable) and adds the skill tag
    after it, so neither value clobbers the other:

    ```bash
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
    gcloud <command> [flags]
    ```

    Do not use `gcloud config set` for this: it would persist beyond the current
    task and mislabel unrelated usage.

-   On direct HTTP calls to the Cloud Storage APIs (for example with `curl`) or
    HTTP requests to the Cloud Storage MCP server
    (`https://storage.googleapis.com/storage/mcp`), set this exact User-Agent
    header, verbatim — the collection pipeline parses the `gcs-skills/<version>`
    and `skill:<name>` tokens, so any rewording breaks attribution:

    ```
    User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)
    ```

-   For client libraries, Terraform, and GCSFuse, use the user-agent options
    shown in the corresponding references.

## Routing to Specialized GCS Skills

This skill covers everyday Cloud Storage tasks. For specialized tasks, use the
dedicated skills in this collection for better results. Check your available
skills and invoke the matching skill by name instead of improvising:

-   **`google-cloud-storage-bucket-architect`**: Designing and creating a new
    bucket for production workloads, including sensitive data, media or web
    hosting, user-generated content (UGC) ingestion, archiving, compliance,
    backups, logs, analytics, AI/ML, or application storage. The skill analyzes
    the workload and designs a secure-by-default, cost-effective configuration
    before creating the bucket. Use the Quick Start section below only for
    temporary scratch buckets.

-   **`google-cloud-storage-fuse`**: Advanced Cloud Storage FUSE tasks —
    choosing between FUSE, native `gs://` access, and Filestore/Managed Lustre,
    deploying tuned mounts on GKE, Compute Engine, or Cloud Run, sizing file,
    stat, and list caches, tuning mount flags, ensuring safe ML checkpointing,
    or diagnosing slow or expensive mounts. The
    [GCSFuse reference](references/gcsfuse.md) in this skill covers only basic
    installation and mounting.

-   **`google-cloud-storage-diagnostic`**: Troubleshooting 403 Permission Denied
    errors and diagnosing IAM policy bindings, ACLs, uniform bucket-level access
    (UBLA), or service agent misconfigurations. Ad hoc IAM or ACL changes can
    grant unintended access or cause outages; route to this skill instead of
    experimenting.

-   **`gcs-security-assessment`**: Automated security posture assessment of
    Cloud Storage resources in a project (see
    [Data Management](references/data-management.md)).

If the matching skill is not installed, do not improvise. Provide the user with
this exact command to install it (substituting the skill name), and use the
skill after installation. Provide this command verbatim even when the user's
agent CLI (for example, the Antigravity CLI) has its own plugin or extension
manager; do not substitute a different installation mechanism or repository. For
security assessments specifically, do not attempt a manual assessment; wait
until the skill is installed.

```bash
npx skills add gemini-cli-extensions/google-cloud-storage --skill <skill-name>
```

## Quick Start

To set up, configure, or choose between the Google-hosted remote Cloud Storage
MCP server (`https://storage.googleapis.com/storage/mcp`) and the local MCP
Toolbox (`cloud-storage`), read [MCP Usage](references/mcp-usage.md). If a Cloud
Storage MCP server is already connected, prefer its structured tools (such as
`create_bucket`, `list_objects`, `read_object`, and `upload_object`) over the
CLI and API commands below, and fall back to `gcloud storage` and the JSON API
when no MCP server is available.

1.  **Enable the Cloud Storage API:**

    ```bash
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
    gcloud services enable storage.googleapis.com --quiet
    ```

2.  **Create a Bucket:**

    Bucket names live in a single global namespace shared by all of Cloud
    Storage — not scoped to your project or organization — so short or common
    names are usually taken. If the location is omitted, the bucket defaults to
    the `US` multi-region.

    For a production or workload-specific bucket, route to
    `google-cloud-storage-bucket-architect` before creating a bucket (see
    [Routing to Specialized GCS Skills](#routing-to-specialized-gcs-skills)).
    The commands below create a basic default bucket.

    Using the gcloud CLI:

    ```bash
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
    gcloud storage buckets create gs://my-bucket --location=us-central1
    ```

    Using the JSON API:

    ```bash
    curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
      -H "User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
      -H "Content-Type: application/json" \
      -d '{"name": "my-bucket", "location": "US-CENTRAL1"}' \
      "https://storage.googleapis.com/storage/v1/b?project=$(gcloud config get-value project)"
    ```

3.  **Upload an Object:**

    Using the gcloud CLI:

    ```bash
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
    gcloud storage cp ./my-file.txt gs://my-bucket
    ```

    Using the JSON API:

    ```bash
    curl -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
      -H "User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
      -H "Content-Type: text/plain" \
      --data-binary @my-file.txt \
      "https://storage.googleapis.com/upload/storage/v1/b/my-bucket/o?uploadType=media&name=my-file.txt"
    ```

4.  **Download an Object:**

    Using the gcloud CLI:

    ```bash
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }gcs-skills gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
    gcloud storage cp gs://my-bucket/my-file.txt .
    ```

    Using the JSON API:

    ```bash
    curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
      -H "User-Agent: gcs-skills/1.0 (skill:google-cloud-storage-basics)" \
      "https://storage.googleapis.com/storage/v1/b/my-bucket/o/my-file.txt?alt=media"
    ```

## Reference Directory

-   [Core Concepts](references/core-concepts.md): Buckets, objects, folders,
    prefixes, bucket location types, and storage classes.

-   [CLI & API Usage](references/cli-api-usage.md): CRUD and list operations for
    buckets and objects using `gcloud storage` and the JSON API, plus Pub/Sub
    notifications for event-driven processing.

-   [Client Libraries](references/client-library-usage.md): Using Google Cloud
    client libraries for Python, Java, Node.js, and Go, with pointers to all
    other supported languages.

-   [MCP Usage](references/mcp-usage.md): Choosing between the Google-hosted
    remote Cloud Storage MCP server and the local MCP Toolbox, setup for each,
    their tool sets and limits, and securing remote MCP with Model Armor and IAM
    deny policies.

-   [Infrastructure as Code](references/iac-usage.md): Terraform examples for
    buckets covering storage classes, location types, lifecycle, retention, and
    encryption.

-   [Data Transfer](references/data-transfer.md): Storage Transfer Service,
    `gcloud storage rsync`, upload strategies for large files, and performance
    guidelines and limits.

-   [Data Management](references/data-management.md): IAM roles, authentication
    (including signed URLs and HMAC), access control, routing for 403 error
    troubleshooting, network security, automated security assessment, data
    protection, and pricing and cost optimization (lifecycle rules, Autoclass).

-   [Storage Intelligence](references/storage-intelligence.md): The subscription
    for managing storage at scale — Storage Insights datasets (BigQuery metadata
    and activity index), data insights with Gemini Cloud Assist, dashboards,
    inventory reports, storage batch operations, bucket relocation, plus
    configuration, trial, and pricing nuances.

-   [High-Performance Storage](references/high-performance-storage.md): Rapid
    Bucket, Rapid Cache (Anywhere Cache), and hierarchical namespace for AI/ML,
    analytics, and other performance-critical workloads.

-   [GCSFuse](references/gcsfuse.md): Installing Cloud Storage FUSE, mounting
    buckets, file operations, POSIX semantics and limitations (locking, writes,
    renames, consistency), and caching. For advanced tuning, deployment, and
    diagnosis, route to the `google-cloud-storage-fuse` skill.
