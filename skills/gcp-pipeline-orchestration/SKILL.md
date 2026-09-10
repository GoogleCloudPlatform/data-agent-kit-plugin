---
name: gcp-pipeline-orchestration
description: This skill helps the agent generate or update orchestration pipeline
  definitions for Google Cloud Composer to initialize orchestration pipeline or update
  the orchestration definition for orchestration of various data pipelines, like dbt
  pipelines, notebooks, Spark jobs, Dataform, Python scripts or inline BigQuery SQL
  queries. This skill also helps deploy and trigger orchestration pipelines.
license: Apache-2.0
metadata:
  version: v2
  publisher: google
---

## Mandatory Reference Routing

If relevant, call the associated reference file(s) before you take actions.
Refer to the table below to determine which reference file to retrieve in
different scenarios involving specific functions. [!IMPORTANT]: DO NOT GUESS
filenames. You MUST only use the exact paths provided below.

Function/Use Case                  | Required Reference File                        | Capabilities & Intent Keywords
---------------------------------- | ---------------------------------------------- | ------------------------------
**orchestration-pipelines schema** | `references/orchestration-pipelines-schema.md` | orchestrate, generate, create, update

## How to use this skill

Orchestration pipelines require creating two files to ensure a complete and
deployable pipeline:

1.  `Orchestration File` (e.g., `orchestration-pipeline.yaml`,
    `test-pipeline.yaml`): Defines the pipeline's logic, tasks, and schedule.
    **IMPORTANT:** Check if a `deployment.yaml` file exists and references an
    existing orchestration file. If it does, you **must update the existing
    orchestration file** (e.g.,`test_pipeline.yaml`) instead of creating a new
    one. The filename can be customized but must be referenced in the
    `deployment.yaml` file.
2.  `deployment.yaml`: Defines the environment-specific configurations.(e.g.,
    `dev`, `prod`). `deployment.yaml`should only exists in the repository root
    and must be named `deployment.yaml`

-   All files should always be maintained together. And all files should be
    placed on the root of the workspace folder.

-   This skill is helpful to create or update configuration files to orchestrate
    data pipelines.

## How to use this skill

### Step 1: Assess Orchestration Pipeline Status and Initialize if Necessary

Examine the repository's root directory for a `deployment.yaml` file.

1.  **Check for existing setup**: The absence of `deployment.yaml` indicates
    that orchestration has not been set up.
2.  **Determine if initialization is required**: Initialization is required if
    `deployment.yaml` is missing. you **MUST** run the `init` command in Step 3
    to scaffold the project if `deployment.yaml` is missing. Do NOT create the
    files manually.
3.  **Pipeline Name**: If initialization is needed, ask the user for the
    pipeline name. If user hasn't provided the orchestration pipeline name, name
    should be "orchestration_pipeline"
4.  **Environment Name**: If initialization is needed, you MUST ask the user for
    the environment name. If the user does not provide it, use **dev** as the
    default.

5.  **Execute Initialization**: Once you have the pipeline name, run the
    following command:

```
# Replace <ORCHESTRATION_PIPELINE_NAME> with the actual name
# Replace <ENV_NAME> with the actual environment name
gcloud beta orchestration-pipelines init <ORCHESTRATION_PIPELINE_NAME> --environment=<ENV_NAME>
```

### Step 2: Review the orchestration pipeline code structure and syntax instruction

*** Pipeline Models (mapping to YAML)

> [!IMPORTANT]
>
> While the internal pipeline models are defined using protobuf (which typically
> uses `snake_case`), the **YAML configuration expects `camelCase`** for almost
> all field names.
>
> **Mapping Rule:** Always convert `snake_case` proto fields (e.g.,
> `pipeline_id`) to `camelCase` in YAML (e.g., `pipelineId`).

#### Orchestration-Pipelines yaml structure and syntax instruction

Reference to file `references/orchestration-pipelines-schema.md`.

**Required Tags (Top-Level)**: You **MUST** add a `tags` field to the top-level
of the orchestration pipeline YAML definition. The value of this field depends
on the IDE environment:

-   For Antigravity, use `["job:datacloud:antigravity"]`.
-   For VS Code, use `["job:datacloud:vscode"]`.
-   For Gemini CLI, use `["job:datacloud:gemini-cli"]`.
-   For Claude Code, use `["job:datacloud:claude"]`.
-   For Codex, use `["job:datacloud:codex"]`.
-   For any other environment, use `["job:datacloud:other"]`.

#### Deployment yaml structure and syntax instruction.

**Top-Level Structure:** The root of the YAML should be an object with the
following fields:

-   `environments` (dictionary): A map where keys are environment names (e.g.,
    'dev', 'prod', etc) and values are Environment objects.

**Environment:** Each environment object contains the following fields:

-   `project` (string): The Google Cloud Project ID.
-   `region` (string): The Google Cloud region (e.g., 'us-central1').
-   `composer_environment` (string): The Cloud Composer environment name.
-   `artifact_storage`
    -   `bucket` (string): GCS bucket
    -   `path_prefix`(string): prefix of path that we want to put in bucket
-   `pipelines`
    -   `- source` (string): orchestration pipeline yaml file names. It can be
        multiple
-   `variables` (dictionary, optional): Key-value pairs representing environment
    variables. Values can be strings, numbers, or booleans.

> [!TIP]
>
> If the user doesn't provide specific paths for scripts, dbt projects, or GCP
> details (Project ID, Region), use tools like `find_by_name` to search the
> repository and `gcloud` commands (e.g., `gcloud config get-value project`) to
> retrieve the necessary information.

### Step 3: Generate the pipeline files

-   Before generating, check if an orchestration pipeline definition file and
    `deployment.yaml` already exist in the current directory. If they do, inform
    the user and ask if they want to update the existing files or create new
    ones with different names. Do not overwrite without confirmation.

-   First, before creating the orchestration pipeline definition file, you
    **must** first run the following command to get the list of available
    dataproc environments for the user's project. This avoids using placeholder
    values to run the jobs.

    ```
    # Replace <PROJECT_ID> with the actual project_id
    # Replace <REGION> with the actual region
    gcloud dataproc clusters list \
    --project <PROJECT_ID> \
    --region <REGION> \
    ```

    > [!TIP]
    >
    > Running the command without `--format=yaml` provides a clear, tabular
    > output that is easier to read.

-   Then use the returned dataproc list with details to create the orchestration
    pipeline definition file based on the user's requirements for the pipeline's
    logic and schedule. **IMPORTANT:** Every schedule **must** include an
    `endTime`. Every schedule **must** use the current date as `startTime` if
    the user hasn't specified.

    > [!IMPORTANT]
    >
    > A Composer environment is not a Dataproc cluster. If no Dataproc clusters
    > are available, do not use a Composer environment for the
    > `sparkHistoryServerConfig`. It is better to omit this configuration if a
    > dedicated Spark History Server is not available.

-   **Python Actions (`python`)**:
    -   Check the content of the Python script to determine if it is a Spark
        job. If it is, use `pyspark` action instead of `python`.
    -   **Environment & Dependencies**: The `environment` field on a `python`
        action is **optional**.
        -   When `environment` or `requirements` is **omitted**, the action runs
            as a standard `PythonOperator` directly in the Airflow worker's host
            environment (using pre-installed Composer packages). Do **not**
            add `environment.requirements` unnecessarily when standard
            libraries or existing Composer packages are sufficient.
        -   Only specify `environment.requirements` (via `path: requirements.txt`
            or `inline: { list: [...] }`) when custom, isolated third-party
            packages not available in Composer are needed. This compiles to
            `PythonVirtualenvOperator` to create an isolated virtual
            environment.

-   **BigQuery Dataset Location**: When creating a `sql` action with the `bigquery` engine, you **must inspect the location of any referenced BigQuery
    datasets** (e.g., whether it is multi-region `US`/`EU` or a specific region
    like `us-central1`).
    Run:

    ```
    # Replace <PROJECT_ID> and <DATASET_ID> with the actual project and dataset ID
    bq show --format=prettyjson <PROJECT_ID>:<DATASET_ID>
    ```

    Extract the `location` field (e.g., `US`, `EU`, `us-central1`) and set
    `actions[].sql.engine.bigquery.location: <LOCATION>` (or
    `actions[].dataIngestion.bigqueryDts.location: <LOCATION>`). Do NOT omit the
    location or assume `defaults.location` matches the BigQuery dataset
    location.

-   Before creating or updating the `deployment.yaml` file, you **must** first
    run the following command to get the list of available Composer environments
    for the user's project.

    ```
    # Replace <PROJECT_ID> with the actual project_id
    # Replace <REGION> with the actual region
    gcloud composer environments list \
    --project <PROJECT_ID> \
    --locations <REGION> \
    ```

    After listing available Composer environments, you **must** check each
    environment to ensure the composer is using the right image version or has
    installed right PyPI packages. Run the following command for each
    environment:

    ```
    # Replace <ENVIRONMENT_NAME> with the Composer environment name
    # Replace <REGION> with the region
    gcloud composer environments describe <ENVIRONMENT_NAME> \
    --location <REGION> \
    --format="json(config.softwareConfig.imageVersion, config.softwareConfig.pypiPackages)"
    ```

    From the output, select an environment where the imageVersion value is one
    of is "composer-3-airflow-3.1.7-build.x, composer-3-airflow-2.11.1-build.x,
    composer-3-airflow-2.10.5-build.x, composer-3-airflow-2.9.3-build.x,
    composer-2.16.11-airflow-2.11.1, composer-2.16.11-airflow-2.10.5,
    composer-2.16.11-airflow-2.9.3" or select an environment
    where`orchestration-pipelines` field is presented listed in the PyPI
    packages. This ensures the selected environment is compatible with
    orchestration pipelines.

-   Third, before generating the `deployment.yaml` file, you **must ask the
    user** to provide the `artifact_storage` bucket name. Note that the
    `artifact_storage` bucket is typically initialized as a placeholder (e.g.,
    `YOUR_BUCKET`) by the `init` command in Step 1. You must identify any such
    placeholders, ask the user for the actual bucket name, and then update the
    `deployment.yaml` file with the provided value.

    Use the returned composer list with details, along with the project ID,
    region, and the bucket name provided by the user, to generate or update the
    `deployment.yaml` file. When generating or updating the `deployment.yaml`
    file, you **must** replace placeholders (e.g., "<YOUR_PROJECT_ID>",
    "<YOUR_REGION>", "<YOUR_COMPOSER>", "<YOUR_BUCKET>") with the actual
    retrieved and provided values. Additionally, you **must** remove any
    associated `# TODO:` comments once the placeholders are replaced.

-   Ensure both files adhere to the code structures and syntax specified in this
    document.

-   **Renaming Pipelines**: If requested to change the orchestration pipeline
    name, you must rename the orchestration YAML file accordingly (e.g., from
    `dbt_clean_pipeline.yaml` to `new_name.yaml`) and update the `source` field
    within the `pipelines` list in `deployment.yaml` to match the new filename.

> [!IMPORTANT]
>
> **Time Format**: Do NOT include the `Z` suffix in `startTime` and `endTime`.
> Use the format `"YYYY-MM-DDTHH:MM:SS"` (e.g., `"2025-10-01T00:00:00"`).

### Step 4: Validate the content (REQUIRED)

After creating or editing pipeline files, you **MUST** validate them using the
`gcloud beta orchestration-pipelines validate` command. you must: a. Read the
`deployment.yaml` file to identify all defined environments. b. Run the
`validate` command below for **each** environment found in `deployment.yaml`.

```
# Replace <ENV_NAME> with the identified environment name
gcloud beta orchestration-pipelines validate --environment=<ENV_NAME>
```

### Step 5: Handle Validation Errors

1.  Check the output of the validation command.

2.  If the command returns an error or failure message:

    -   Read the error message carefully.
    -   Edit the orchestration and deployment files to fix the specific issue
        mentioned.

3.  Re-run the validation command to confirm the fix. Do not mark the task as
    complete until the validation passes (exit code 0), and do not fall back to
    create airflow dag in python if validation fails.

## Declarative Pipeline Templates

When asked to generate or verify declarative pipeline files, ensure they follow
these compliant structures. **Do not use the exact values below; adapt them to
the user's specific project, region, and environment details.**

### `deployment.yaml` Template - IMPORTANT FORMAT MUST MATCH-

```yaml
environments:
  <environment_name>: # e.g., dev, prod
    project: <PROJECT_ID>
    region: <REGION>
    composer_environment: <COMPOSER_ENVIRONMENT_NAME>
    gcs_bucket: "" # Optional
    artifact_storage:
      bucket: <ARTIFACT_BUCKET_NAME>
      path_prefix: "<prefix>-" # e.g., namespace or username prefix
    pipelines:
      - source: '<orchestration-pipeline.yaml>' # e.g., list of pipeline yaml names
```

### Step 6: Deploy the Orchestration Pipeline (Optional)

If requested to **deploy** the orchestration pipeline:

1.  You MUST ask the user which environment to deploy to. If no environment name
    is provided, list the available environments from `deployment.yaml` and ask
    the user to choose one, defaulting to `dev` if it exists.

2.  Read the orchestration YAML to extract the `pipelineId`.

3.  Deploy with `--local`. This uploads the DAG without running it:

    ```
    # Replace <ENV_NAME> with the target environment
    # Replace <PIPELINE_SOURCE> with the orchestration YAML filename
    gcloud beta orchestration-pipelines deploy \
      --environment=<ENV_NAME> --local
    ```

4.  Parse the deploy output to extract the **bundle ID** (version). The output
    includes a line like: `Pipeline deployment successful for version
    local-b32d15e307b5` The version string (e.g., `local-b32d15e307b5`) is the
    bundle ID.

> [!IMPORTANT]
>
> `--local` deployments now default to `--paused=true`. The deployed DAG will be
> visible in Airflow as a paused DAG without a schedule. It will **not**
> auto-run. Use Step 7 to trigger it.

### Step 7: Trigger the Orchestration Pipeline Run (Optional)

If requested to **trigger/run** the orchestration pipeline, you MUST follow the
Deploy → Poll → Trigger flow.

1.  **Ask for environment**: You MUST ask the user which environment to use.
    Default to `dev` if it exists in `deployment.yaml`.

2.  **Deploy first** (Step 6): Always deploy before triggering to ensure the run
    uses the latest code. Extract the `bundle ID` from deploy output and the
    `pipelineId` from the orchestration YAML.

3.  **Poll for DAG readiness**: Wait for the DAG to be registered in Composer.

    ```bash
    # Initial delay: wait 30 seconds after deploy
    sleep 30

    # Poll every 15 seconds, up to 2 minutes total
    # Replace <ENV_NAME>, <BUNDLE_ID> with actual values

    gcloud beta orchestration-pipelines list \
    --environment=<ENV_NAME> \
    --bundle=<BUNDLE_ID>
    ```

    The pipeline is ready when it appears in the list output. If it does not
    appear after 2 minutes, report failure and advise the user to check YAML
    validity.

4.  **Trigger the pipeline**:

    ```
    # Replace <ENV_NAME>, <BUNDLE_ID>, <PIPELINE_ID> with actual values
    gcloud beta orchestration-pipelines trigger \
    --environment=<ENV_NAME> \
    --bundle=<BUNDLE_ID> \
    --pipeline=<PIPELINE_ID>
    ```

5.  **Verify the run started**:

    ```
    gcloud beta orchestration-pipelines runs list \
    --environment=<ENV_NAME> \
    --bundle=<BUNDLE_ID> \
    --pipeline=<PIPELINE_ID>
    ```

> [!TIP]
>
> **Trigger-only (no deploy):** If the user wants to trigger an already-deployed
> pipeline, skip Step 6. Use `gcloud beta orchestration-pipelines list
> --environment=<ENV_NAME>` to find the bundle ID, then trigger directly with
> Step 7.4.

> [!IMPORTANT]
>
> **Fallback:** If `gcloud trigger` fails, use the bundled script: Run script
> with -- help to discover and learn the interface.
>
> ```
> python scripts/trigger/airflow_trigger.py \ --project <PROJECT_ID>
> --location <REGION> \ --environment <COMPOSER_ENV> --dag_id <PIPELINE_ID>
> ```
>
> Get `project`, `region`, and `composer_environment` from `deployment.yaml`.

## Definition of done

-   `deployment.yaml` file is created successfully.
-   The orchestration pipeline file (e.g., `orchestration_pipeline.yaml`) is
    created successfully, includes a mandatory `endTime` for every schedule, and
    passes the validation command: `gcloud beta orchestration-pipelines validate
    --environment=<ENV_NAME>`
-   If user requested to **deploy** the orchestration pipeline, the `gcloud beta
    orchestration-pipelines deploy --environment=<ENV_NAME> --local` command
    should return a success message with a version/bundle ID.
-   If user requested to **trigger/run** the orchestration pipeline:
    1.  Deploy succeeded (bundle ID extracted from output)
    2.  DAG appeared in `gcloud beta orchestration-pipelines list` within 2 min
    3.  `gcloud beta orchestration-pipelines trigger` returned success
    4.  Run is visible in `gcloud beta orchestration-pipelines runs list`

## Other actions

If requested to pause/stop the orchestration pipeline, use

```bash
    # Replace <ENV_NAME>, <BUNDLE_ID>, <PIPELINE_ID> with actual values
    gcloud beta orchestration-pipelines pause \
    --environment=<ENV_NAME> \
    --bundle=<BUNDLE_ID> \
    --pipeline=<PIPELINE_ID>
```

If requested to unpause/resume the orchestration pipeline, use

```bash
    # Replace <ENV_NAME>, <BUNDLE_ID>, <PIPELINE_ID> with actual values
    gcloud beta orchestration-pipelines unpause \
    --environment=<ENV_NAME> \
    --bundle=<BUNDLE_ID> \
    --pipeline=<PIPELINE_ID>
```
