---
name: bigquery-data-transfer-service
description: Discovers and inspects BigQuery Data Transfer Service (DTS) configurations.
  Use this to identify existing ingestion pipelines and extract datasource or transfer
  config metadata for data pipelines. Use when a user asks for ingestion scenarios
  while building or managing data pipelines or when a user asks to "ingest" or "add"
  data that may already be managed by a DTS transfer.
license: Apache-2.0
metadata:
  version: v2
  publisher: google
---

# BigQuery Data Transfer Service (DTS)

## Mandatory Guidelines

> [!IMPORTANT]
>
> All new BigQuery Data Transfer Service (DTS) configurations **MUST** be
> provisioned through the **gcp pipeline resource provisioning** framework,
> which includes generating a `deployment.yaml`.
>
> -   **Do NOT** use imperative CLI commands (e.g., `bq mk` or `gcloud`) to
>     create or update configurations.
> -   CLI commands are permitted **only** for discovery (listing/showing) and
>     triggering manual runs.

This guide enables the discovery of existing ingestion resources and provides
metadata related to ingestion when needed.

## Workflow

### Step 0: Discover Environment Parameters

Before generating configurations, discover the actual values for the target
project and region.

> [!TIP]
>
> If `deployment.yaml` already exists in the repository root, prioritize
> extracting `project` and `region` from the target environment configuration
> (e.g., `dev`).

1.  **Project**: `gcloud config get project`
2.  **Region**: `gcloud config get compute/region`

> [!TIP]
>
> Use these commands to replace placeholders like `<PROJECT_ID>` with actual
> values. Always remove associated comments that start with TODO once replaced.

### Step 1: Check for Existing Transfers

Before assuming a new transfer is needed, check for existing ones in the target
region.

1.  **List Transfers**:

    ```bash
    bq ls --transfer_config \
      --transfer_location=<REGION> \
      --project_id=<PROJECT_ID>
    ```

2.  **Analyze Existing Transfers**:

    -   **Single Transfer Found**:

        -   Check if the transfer has at least one successful run:
            `bq ls --transfer_run --transfer_config=<RESOURCE_NAME>`
        -   If found: Use existing transfer config.
        -   If not found: Confirm with user if it's ok to trigger the transfer
            run.

    -   **Multiple Transfers Found**:

        -   Attempt to guess the correct one based on context.
        -   Ask user to confirm.

    -   **Disabled Transfers Found**:

        -   Ask user if they want to enable it or create a new one.
        -   To Enable: Instruct the user to update the transfer configuration
            within their `deployment.yaml` file by setting the `disabled` field
            to `false` for the specific transfer resource.

    -   **No Transfers Found**: Proceed to create new if needed.

### Step 2: Discover & Validate Parameters (New Transfers)

If creating a new transfer, discover the required parameters using the REST API
and validate them with the user.

> [!TIP]
>
> If `<DATA_SOURCE_ID>` is unknown, run the discovery script without
> `<DATA_SOURCE_ID>` argument to list available source IDs (e.g.,
> `google_cloud_storage`). It uses the derived project and location from Step 0.

```bash
python3 scripts/bigquery_dts.py --project_id=<PROJECT_ID>
```

1.  **Run Discovery Script**: Use the `bigquery_dts.py` script to inspect Data
    Source parameters via the REST API.

    ```bash
    # Passes the derived project and region to the script.
    python3 scripts/bigquery_dts.py --project_id=<PROJECT_ID> <DATA_SOURCE_ID> <REGION>
    ```

    > [!IMPORTANT]
    >
    > Run this command every time a new transfer is being planned.

2.  > [!CAUTION]
    >
    > **Mandatory User Questionnaire (CRITICAL)**:

    -   **Explicitly identify ALL specific parameters** returned by the
        discovery script. **You MUST NOT generalize or vaguely summarize them.**
    -   **OAuth Authorization (Google Data Sources)**: For Google ecosystem data
        sources (Google Ads, Youtube, etc.), if the user is not using a service
        account to configure the DTS transfer config (meaning the user is using
        End User Credentials or EUC to configure the transfer config), then
        generate an OAuth URI. Ask the user to visit this URL to authorize. Once
        the user provides the versionInfo code, use the code as
        `definition.versionInfo` in `deployment.yaml` and then you can proceed.
    -   If any parameters are related to authentication, explicitly ask the user
        to provide the Secret Manager Resource ID (e.g.,
        projects/my-project/secrets/my-secret) for these parameters
    -   Present every required parameter to the user BEFORE generating config
        files.
    -   Ask for verification of assets/tables to be ingested.

3.  **Wait for User Response**: You **MUST NOT** proceed until parameters are
    confirmed.

### Step 3: Extract Transfer Config Data

Retrieve the configuration details for the selected transfer.

```bash
bq show --format=prettyjson --transfer_config <RESOURCE_NAME>
```

### Step 4: Trigger and Verify Transfer

After the transfer is deployed via the resource provisioning framework, you MUST
ensure there is at least a single successful run before proceeding with the rest
of the tasks.

1.  **Trigger a Manual Run**: If no successful runs or ongoing runs are found,
    or the transfer was just created, trigger a manual run for the current time.

    ```bash
    bq mk --transfer_run \
      --transfer_config=<RESOURCE_NAME> \
      --run_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    ```

2.  **Poll for Completion (5-Minute Rule)**: Attempt to check the status of the
    run every 30-60 seconds for up to **5 minutes**.

    ```bash
    bq ls --format=prettyjson --transfer_run --transfer_config=<RESOURCE_NAME>
    ```

    -   **Success**: If the run completes successfully, proceed with the rest of
        the pipeline.
    -   **Failure**: If the run fails, analyze the logs and ask the user for
        help.
    -   **Timeout (5 mins)**: If the run is still in progress after 5 minutes,
        **STOP** and ask the user: "The Data Transfer Service ingestion is still
        in progress. Please provide 'proceed guidance' once the ingestion has
        finished so that I can continue building the rest of the data pipeline
        using the ingested schema and samples."

3.  **Wait for User Guidance**: Do NOT proceed until the user confirms ingestion
    is complete or provides guidance.

4.  Once user confirms to proceed, start work on rest of the tasks.

## Definition of Done

-   A BigQuery DTS transfer configuration has been discovered or provisioned
    declaratively (via **gcp pipeline resource provisioning** with a generated
    `deployment.yaml`).
-   Mandatory datasource parameters have been identified and confirmed with the
    user.
-   A manual transfer run has been triggered and monitored.
-   The transfer run has completed successfully OR the user has provided
    "proceed guidance" for a long-running transfer.
