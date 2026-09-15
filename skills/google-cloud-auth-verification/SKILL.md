---
name: google-cloud-auth-verification
description: >-
  Mandatory Step 0 pre-flight execution order and authentication verification for Google Cloud Platform (GCP),
  Application Default Credentials (ADC), gcloud CLI, Spark, Dataproc, BigQuery, GCS, and notebook runtimes.
  Use whenever interacting with GCP resources, running Spark/PySpark pipelines, BigQuery queries, GCS paths (gs://), or creating/running notebooks.
license: Apache-2.0
metadata:
  version: v3
  publisher: google
---

# Google Cloud Authentication Guidelines

## Mandatory Pre-Flight Execution & Auth Hierarchy

> [!IMPORTANT] **Pre-Flight Execution Priority Order**: Before generating code,
> implementation plans, or executing tasks for any GCP or Notebook workload:
>
> 1.  **Skip Pre-Flight Shell Probes When Live Notebook Execution or MCP Tools**
>         **Are Available**:
>     -   When a live notebook cell execution tool (`execute_cell` /
>         `notebook_execute_cell` / `notebook__execute_cell`) is available, or
>         when the task is handled directly by a connected MCP tool
>         (`bigquery__execute_sql`, `bigquery__get_table_info`,
>         `bigquery__list_table_ids`, etc.), **do NOT run a pre-flight
>         `gcloud auth list && gcloud config list` shell probe**. Instead,
>         verify authentication reactively only if a cell execution or MCP tool
>         call returns an authentication or credentials error (`401`, `403`,
>         `DefaultCredentialsError`, `Reauthentication is needed`).
>     -   When `gcloud` or `bq` shell commands are required, or when generating
>         standalone scripts or notebooks without a live cell execution tool
>         (`execute_cell`), verify credentials upfront via the single bundled
>         probe (`gcloud auth list && gcloud config list`) or Application
>         Default Credentials (ADC).
> 2.  **Distinguish Authentication vs. IAM Permissions**:
>     -   If `gcloud auth list` returns `No credentialed accounts`, **HARD
>         STOP** immediately and instruct the user to run `gcloud auth login`
>         and `gcloud auth application-default login`.
>     -   If Python throws `google.auth.exceptions.DefaultCredentialsError`,
>         explicitly direct the user to run `gcloud auth application-default
>         login`.
>     -   If `gcloud auth list` shows an active credentialed account but a
>         BigQuery/GCP call returns `403 Forbidden: Access Denied`, **DO NOT**
>         tell the user to log in again with `gcloud auth login`. Diagnose
>         missing IAM roles (e.g., `roles/bigquery.dataEditor`) on the active
>         account.
> 3.  **HARD STOP if Unauthenticated**: If no active GCP credentials or valid
>     `gcloud` authentication are detected, **STOP IMMEDIATELY**. Prompt the
>     user to run `gcloud auth login` and `gcloud auth application-default
>     login`. Do NOT attempt local virtualenv creation, package installation, or
>     local binary/JDK setup loops as workarounds.

## Common Error Messages

1.  **gcloud/bq CLI**:
    -   `ERROR: (bq) You do not currently have an active account selected.`
    -   `No credentialed accounts.`
    -   `Configuration error: No account is currently active.`
2.  **Execution Failures (Python/Notebooks)**:
    -   `google.auth.exceptions.DefaultCredentialsError: Could not automatically
        determine credentials.`
    -   `Forbidden: 403 Access Denied` (when it's clearly an auth issue).

## Verification Step

Before asking the user to log in, independently verify authentication status
using a single bundled probe command:

```bash
gcloud auth list --format="json" && gcloud config list --format="json"
```

*   If the output contains `No credentialed accounts.` or missing active
    account, proceed to **Corrective Action**.
*   If an account *is* listed but the user still receives a `403 Access Denied`
    error, the issue is likely **IAM permissions** (e.g., missing BigQuery
    roles) on their active account, rather than missing authentication. In this
    case, investigate permissions rather than asking them to log in again.

## Corrective Action

When missing credentials are confirmed, **DO NOT** attempt to fix credentials
via code or local virtualenv workarounds. Credentials must be established by the
user.

**Stop and ask the user to run the following commands in their terminal:**

1.  **To authenticate the gcloud CLI**: `gcloud auth login`
2.  **To set up Application Default Credentials (ADC)** (required for BQ CLI AND
    most libraries/notebooks): `gcloud auth application-default login`

## Post-Login Verification

After the user confirms they have logged in, verify with: `gcloud auth list`
Then proceed with the original task.
