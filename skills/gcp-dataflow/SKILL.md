---
name: gcp-dataflow
description: >
  Guides writing, packaging, executing, and troubleshooting Apache Beam
  pipelines on Dataflow. Use when creating new pipelines, configuring Flex
  Templates, or analyzing performance of Dataflow jobs. Capabilities include
  Java/Python/Go setup, Cloud Build integration, and deep diagnostic analysis
  of job health and autoscaling.

  Use when:
  - Creating an Apache Beam Dataflow pipeline.
  - Creating a Google Dataflow Flex Template.
  - Using an existing Google Dataflow Template.
  - Debugging Dataflow pipeline
  - Troubleshooting Dataflow pipeline
  - Analyzing Performance of Dataflow pipeline.

  Key capabilities: Java/Python/Go project setup, Flex Templates (with
  Cloud Build), and diagnostics for streaming job health, bottlenecks,
  and autoscaling.

  Do NOT use for:
  - General GCP resource management unrelated to Dataflow.
  - Issues with other GCP services (e.g., GCE, GCS, BigQuery) unless directly
    impacting Dataflow pipeline execution.
  - Pipeline technologies other than Apache Beam on Dataflow.

license: Apache-2.0
metadata:
  version: v5
  publisher: google
---

# Apache Beam Pipelines on Cloud Dataflow

## Pipeline authoring

Use this section when implementing Dataflow pipeline logic using Apache Beam.

### Check if existing Google Dataflow Template exists

Google provides a variety of pre-built, open source Dataflow templates that can
be used for common scenarios. Before implementing a pipeline from scratch, you
MUST follow the steps below to check whether a Dataflow template for the
pipeline logic you need to implement already exists.

-   **Step 1: Check for a matching Google Dataflow Template**

    -   Identify the **source** and **sink** (e.g., GCS to BigQuery) from the
        user's request. *Note*: You *MUST NOT* proceed until the source and sink
        are clearly identified.
    -   **Action**: List templates in the public `dataflow-templates` bucket:
        *   For Classic templates, check `gs://dataflow-templates/latest`.
        *   For Flex templates, check `gs://dataflow-templates/latest/flex`. Use
            `gcloud storage ls` to list the contents.
    -   Match templates by name or description to the source and sink.
    -   If no matching template is found, go to **Create a new pipeline from
        scratch**.

-   **Step 2: Confirm template selection**

    -   Present the matched template(s) to the user with a brief explanation of
        why they match, and make a note of whether it is a Classic or Flex
        template.
    -   **Action**: Ask the user for explicit confirmation to proceed with this
        template.
    -   If the user rejects or prefers a custom solution, proceed to **Create a
        new pipeline from scratch**.

### Create a new pipeline from scratch

Use this section when creating a new project for a Dataflow pipeline from
scratch.

-   If the user doesn't say explicitly which language (Java, Python, Go) shall
    be used to write the pipeline, you MUST confirm the language.
-   Determine which version of Beam SDK should be used by searching for the most
    recently released version of Apache Beam, unless the user already uses a
    particular version.
    -   **Action**: Run a web search for the latest Apache Beam SDK release.
-   YOU MUST use same version of Apache Beam consistently throughout the project
    in Dockerfiles, `requirements.txt`, and other similar files where versions
    are specified.

### Java projects using Gradle

Use this section when configuring a Dataflow Java pipeline project using gradle.

-   **Shadow Jars (Fat Jars)**: Do NOT propose to use the Shadow plugin
    (`com.github.johnrengelman.shadow`) unless the user explicitly requests a
    Fat Jar.
-   **Passing command-line parameters**: Use the `application` plugin for
    passing command-line parameters.
-   **SLF4J Logging Dependency Alignment**:
    -   Verify the `slf4j-api` version pulled transitively by Apache Beam.
    -   You MUST configure the application logging backend (`slf4j-simple`,
        `logback-classic`, etc.) to exactly match the major/minor version of the
        resolved `slf4j-api`.

### Packaging a pipeline as a Flex Template

Use this section to package pipeline code as a Flex template.

Flex Templates offer a hermetic and reproducible launch environment for a
pipeline. They are easy to launch with `gcloud` or with orchestrators like Cloud
Composer. You **MUST** package the pipeline as a Flex Template when creating new
Dataflow pipeline projects.

Follow the steps below:

-   **Provide Instructions**: Provide instructions on rebuilding and running
    Flex Templates to the user in walkthrough.
-   **Use Single Docker Image for Python pipelines**: For Python Flex Templates,
    it is better to use a single image for the template launcher image and for
    the worker runtime environment (`--sdk_container_image`). Does the Python
    pipeline require extra dependencies (e.g., using `--requirements_file`,
    `--setup_file`, or `--extra_package`)? If so, **YOU MUST recommend the**
    **Single Docker Image Configuration** for the Flex Template. See
    [python_flex_template_reference.md][py-flex-ref] for details.
-   **Prefer Cloud Build over Local Docker**:
    -   Do NOT assume local Docker availability on the workspace machine.
    -   **Action**: Suggest and provide `cloudbuild.yaml` out-of-the-box for
        building and pushing images unless local setup is explicitly requested.
    -   When building images with Cloud Build in the background you MUST provide
        the link where the user can monitor the long-running operation.
-   **Providing SSL certificates and Secrets to Workers**:
    -   If certificates or keys are stored in Secret Manager, **NEVER** bake
        them into the Docker image layers. Instead, retrieve them dynamically at
        runtime inside the Apache Beam `DoFn.setup()` lifecycle using the Secret
        Manager client library (writing them to ephemeral worker disk like
        `/tmp` only if physical file paths are strictly required). Ensure the
        Dataflow Worker Service Account has the
        `roles/secretmanager.secretAccessor` role.

## Configuring Google-provided templates

Use this section when the user has selected a Google-provided template (Classic
or Flex) and you need to configure it.

-   **Step 1: Get template metadata**

    -   Identify template type:
        *   **Classic**: Metadata files are in `gs://dataflow-templates` and end
            with `_metadata` (e.g.,
            `gs://dataflow-templates/latest/Word_Count_metadata`).
        *   **Flex**: Metadata are embedded in the template spec file under
            `gs://dataflow-templates/latest/flex` (e.g.
            `gs://dataflow-templates/latest/flex/Cloud_Datastream_to_BigQuery`).
    -   Read the corresponding template metadata file to identify required
        parameters.
    -   **Note**:
        *   Make sure to run a recursive search over the bucket if needed to
            locate the metadata.
        *   If the template parameters include UDF-related fields (e.g.,
            `javascriptTextTransformGcsPath`,
            `javascriptTextTransformFunctionName`), refer to the
            [UDF guide][udf-guide] to write and configure the UDF.
        *   **Parameter-Based SSL / Secret Staging**: If the Google-provided
            template requires local SSL certificates or Secret Manager secrets,
            pass comma-separated GCS paths via the `extraFilesToStage`
            parameter. The runner will drop them into `/extra_files` on worker
            VMs. Refer to the [SSL certificates guide][ssl-cert-guide] for local
            referencing syntax (`/extra_files/...`).

-   **Step 2: Get network configuration**

    -   **Action**: Run `gcloud` commands to list networks and subnetworks.
    -   Confirm the network and subnetwork to use with the user.

-   **Step 3: Identify required parameters and prepare resources**

    -   Extract required parameters from the template metadata.
    -   > [!IMPORTANT]
    -   > **Strict parameter validation**: Any parameter in the metadata JSON
    -   > that does **NOT** explicitly have `"isOptional": true` is **strictly
    -   > required** by the Dataflow API.
    -   > This applies even if the description suggests it has a default value
    -   > (e.g., `csvFormat` or `badRecordsOutputTable` in some templates).
    -   > You must identify and supply all of them.
    -   Identify which parameters are provided by the user and which need to be
        resolved or created by you.
        *   **Action**: Present these parameters to the user using Markdown
            Key-Value (bullet points) for clarity and confirmation.
    -   **Schema Handling**: If a schema JSON parameter (like `schemaJSONPath`
        or `JSONPath`) is required:
        *   **Action**: Ask the user to provide the GCS path to an existing
            schema file or the JSON content.
        *   If the user does not have a schema file, ask them to provide the
            field names and their types. Construct the schema JSON locally and
            present it to the user for validation.
        *   Once confirmed by the user, write the schema JSON file locally and
            upload it to a GCS staging location, then supply this path to the
            parameter.
    -   **Pre-create Target Sink (Best Practice)**: To ensure stability and
        avoid runtime creation schema mismatches:
        *   **Action**: Clarify with the user whether the target sink (e.g.,
            BigQuery table, Spanner database/table) already exists. If the user
            confirms it exists, proceed to the remaining steps as-is.
        *   If it does not exist, ask for permission to create it. If permitted,
            create it yourself. Otherwise, provide the exact creation commands
            to the user.
        *   If the sink is BigQuery, refer to
            [Destination-specific prerequisites][dest-prereqs] for crucial table
            and error table setup.
    -   Include additional parameters such as service accounts, network details,
        and other pipeline options.
        *   **Specifying Options**: For Google-provided Flex Templates, refer to
            the [Specifying options for Flex Templates][flex-template-options]
            guide for how to pass parameters and additional experiments.

### Destination-specific prerequisites

Different templates might require specific resources to be prepared in the
target sink before execution. Follow the instructions for your target sink
below.

#### BigQuery

When running templates that write to BigQuery, you MUST ensure the following
resources are prepared to prevent job failures:

-   **Pre-create Target Table**: Create the target BigQuery table (e.g., using
    `bq mk`) before launching the job. Ensure the schema matches the template's
    expectations.
-   **Pre-create Error/Bad Records Table**: Many templates that write to
    BigQuery have a parameter for redirecting failed records (e.g.,
    `badRecordsOutputTable` or `outputDeadletterTable`). Some templates attempt
    to auto-create this table. However, pre-creating it is a best practice. This
    ensures correct schema and permissions.
    *   **How to Determine the Error Schema**: Trace the schema definition in
        the public [DataflowTemplates GitHub repository][df-templates-repo]:
        1.  Locate the source code or README for the template you are using
            (e.g., in `v1/` or `v2/` directories).
        2.  Identify the parameter name used for the error table (e.g.,
            `badRecordsOutputTable` or `outputDeadletterTable`).
        3.  Search the source code to see how the schema is defined or loaded
            for that parameter:
            *   **Example (Code Reference)**: In `PubSubToBigQuery.java`, the
                schema is set using
                `ResourceUtils.getDeadletterTableSchemaJson()`. Tracing
                `ResourceUtils.java` shows it loads the schema from
                [streaming_source_deadletter_table_schema.json on GitHub][deadletter-schema].
            *   **Example (Documentation Reference)**: For simpler templates,
                the schema might be listed in the official documentation, such
                as the `RawContent`/`ErrorMsg` schema shown in the
                [CSV to BigQuery DevSite Doc][csv-bq-doc].

## Configuring Custom Pipelines (Dataflow Runner)

Use this section when preparing to run a custom Apache Beam pipeline on
Dataflow.

-   When launching Python Pipelines without a Flex Template with
    `DataflowRunner`, you MUST scan the pipeline project directory for the
    following files:
    -   **`requirements.txt`**:
        -   If found, you MUST include `--requirements_file` pipeline option.
    -   **`setup.py`**:
        -   If found, you MUST include `--setup_file` pipeline option. This is
            critical if the pipeline uses local modules or packages.

-   When launching Python Pipelines with a Flex Template, if the Flex Template
    image is also the SDK Container image (Single Docker Image Configuration),
    then you MUST supply the image in the `sdk_container_image` parameter.

### Lookup environment resources instead of using placeholder values

-   Avoid using generic placeholders (e.g., `your-gcp-project-id`) for GCP
    resources when drafting run scripts or configs. **Action**: If values are
    unknown, proactively run commands like `gcloud config get-value project` to
    find active resources to pre-fill scripts for the user. Confirm the values
    with the user before proceeding.

## Job Execution

Use this section when configuration is complete and you are ready to launch any
Dataflow job (Google-provided template, Custom Flex template, or standalone
pipeline).

### Universal Execution Workflow

1.  **Construct Launch Command**: Draft the full launch command based on the
    pipeline type (e.g., `gcloud dataflow flex-template run` or `python main.py
    --runner=DataflowRunner`). Ensure workers default to private IP
    configuration unless specified otherwise, and verify target project
    permissions.
2.  **Mandatory Pre-Launch Confirmation**: Present the *entire* drafted command
    to the user at once. Explain the purpose of all parameters (including
    experimental flags) and allow the user to review and correct the command as
    a batch instead of confirming piecemeal. **Do NOT proceed** with execution
    until explicitly approved.
3.  **Trigger Job**: Once approved, execute the command and note the resulting
    Job ID (displaying it to the user).
4.  **Display Console URL**: Construct and present the direct Cloud Console
    monitoring URL:
    https://console.cloud.google.com/dataflow/jobs/<region>/<job_id>?project=<project_id>

## Job Monitoring

Use this section to monitor the progress of a running Dataflow job.

-   Check the status of the triggered Dataflow job using the job ID.
-   Run the check every 30 seconds for the first 2 minutes, then check every 3
    minutes, unless specified otherwise by the user.
-   **Note**: Do NOT perform data check queries on the sink until the job has
    reached a stable `RUNNING` or `DONE` state.

## Diagnostics & Troubleshooting

> [!IMPORTANT] YOU MUST use this section when the user asks about performance of
> their Dataflow pipelines. This can be used to debug issues like pipeline
> slowness, pipeline failures, etc.

### Task Execution Workflow

1.  **Understand User Request**: Extract Job ID, Project ID, Transform Name
    (optional), and Time Window.
2.  **Transform Name Mapping**: If the user requires transform-based debugging,
    map user-provided Transform Names to actual Dataflow `stage` or `ptransform`
    and apply to filters while querying:

    This mapping can be extracted from `gcloud dataflow jobs describe JOB_ID
    --full --format="json(pipelineDescription.executionPipelineStage)"`.

    1.  **Extract the targets**:
        *   Get stage_id: **`name`** property at the parent stage level. This
            matches `"F[digit]"` (e.g. `"F6"`).
        *   Get ptransform: inside the `componentTransform` array, read
            precisely from **`userName`** or **`originalTransform`** (e.g.
            `"RateLimitAndLog/ParMultiDo(RateLimitAndLog)"`). and use it as
            **`ptransform`**.
    2.  **Apply the filters strictly following mapping mechanics**:
        *   **For Cloud Logging queries**: Apply extracted ptransform name to
            filter `resource.labels.step_id="[Extracted ptransform name]"`.
        *   **For Monitoring queries**: Use the stage_id/ptransform filters
            based on filters supported by metric:
            `metric.labels.ptransform="[Extracted ptransform name]"` or
            `metric.labels.stage="[Extracted stage_id]"`.

3.  **Query Telemetry**:

    *   Use Dataflow REST API to get High level Job Messages/Events that
        happened in the job.
    *   Refer to [dataflow_diagnostics_reference.md][diag-ref] for
        key metrics and logging query patterns based on Job Type.
    *   Use Monitoring REST API to fetch metrics.
    *   Use GCloud Logging command to fetch logs.
    *   Use Dataflow REST API to fetch current snapshot metrics when historical
        time-series are not needed.

4.  **Analysis**:

    *   For Streaming Jobs
        *   Overall Job Health: YOU MUST refer to
            [streaming_job_health](references/streaming_job_health.md) to analyze
            overall streaming job health.
        *   Analyze Bottlenecks and Parallelism. YOU MUST refer to
            [bottlenecks_and_parallelism_context][bottlenecks-context] and
            interpret the bottlenecks and parallelism metrics in that context.
        *   Analyze Autoscaling Behavior. YOU MUST refer to
            [streaming_horizontal_autoscaling_analysis.md][autoscaling-analysis-link]
    *   For Batch Jobs
        *   Correlate metrics spikes/drops with log errors.
        *   Identify Issues.

5.  **Output**: Provide a synthesized diagnosis containing symptoms, root
    causes, and target code links (using `file:///...` format). Refer to
    [reporting_findings.md][reporting-findings] for report structure, evidence
    standards, and verification guidelines. Strictly follow the appropriate
    response structure for the job type:

    **For Streaming Jobs:**

    1.  **Overall Job State**: State categorization (Healthy, Mostly Healthy,
        Not Healthy) per
        [streaming_job_health](references/streaming_job_health.md).
    2.  **High-level Job Events**: Notable control plane events, errors, or
        stage failures parsed from job messages.
    3.  **Data Freshness**: Current data delay utilizing
        `job/data_watermark_age` / `job/per_stage_data_watermark_age` and system
        lag.
    4.  **Throughput**: Processing rate trends utilizing
        `job/elements_produced_count` / `job/estimated_bytes_produced_count`.
    5.  **Backlog**: Input backlog (if source stage) or inter-stage backlog
        using `job/estimated_backlog_processing_time` / `job/backlog_bytes`.
    6.  **Bottlenecks & Parallelism**: Queue delay diagnostics using
        `job/is_bottleneck` (interpreting `likely_cause` / `bottleneck_kind`)
        and key metrics `job/backlogged_keys` /
        `job/processing_parallelism_keys` interpreted in the context of
        [bottlenecks_and_parallelism_context][bottlenecks-context].
    7.  **Autoscaling Analysis**: Scaling trends using
        `job/horizontal_worker_scaling` (and label `rationale`), clamp limits
        (`job/max_worker_instances_limit` / `job/min_worker_instances_limit`),
        and utilization hints in the context of
        [streaming_horizontal_autoscaling_analysis][autoscaling-analysis-link].
    8.  **Recommendations**: Direct remediation plans (in-flight updates,
        client-side configurations, or code corrections linked via absolute
        `file:///` URIs).

    **For Batch Jobs:**

    1.  **High-level Job Events**: Notable control plane events, errors, or
        stage failures parsed from job messages.
    2.  **Throughput**: Processing rate trends utilizing
        `job/elements_produced_count` (primary performance indicator).
    3.  **Recommendations**: Direct remediation plans to future runs
        (client-side configurations, or code corrections linked via absolute
        `file:///` URIs).

[py-flex-ref]: references/python_flex_template_reference.md
[udf-guide]: https://docs.cloud.google.com/dataflow/docs/guides/templates/create-template-udf
[ssl-cert-guide]: https://docs.cloud.google.com/dataflow/docs/guides/templates/ssl-certificates
[dest-prereqs]: #destination-specific-prerequisites
[flex-template-options]: https://docs.cloud.google.com/dataflow/docs/guides/templates/run-flex-templates#specify-options
[df-templates-repo]: https://github.com/GoogleCloudPlatform/DataflowTemplates
[deadletter-schema]: https://github.com/GoogleCloudPlatform/DataflowTemplates/blob/main/v2/common/src/main/resources/schema/streaming_source_deadletter_table_schema.json
[csv-bq-doc]: https://cloud.google.com/dataflow/docs/guides/templates/provided/cloud-storage-csv-to-bigquery#GcsCSVToBigQueryBadRecordsSchema
[diag-ref]: references/dataflow_diagnostics_reference.md
[bottlenecks-context]: references/bottlenecks_and_parallelism_context.md
[autoscaling-analysis-link]: references/streaming_horizontal_autoscaling_analysis.md
[reporting-findings]: references/reporting_findings.md
