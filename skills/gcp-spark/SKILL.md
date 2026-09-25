---
name: gcp-spark
description: |
  Develops, optimizes and executes Spark code on Managed Spark on Google Cloud (Dataproc Clusters and Serverless).
  Reads and writes data using BigLake Iceberg catalogs, BigQuery and Spanner.
  Debugs execution failures.
  Use when:
  - Writing Spark ETL pipelines on Google Cloud Platform.
  - Optimizing PySpark or Spark SQL code for performance, memory, or OOM risks.
  - Preparing Spark workloads for production submission.
  - Training or running inference with Machine Learning models with spark on Google Cloud Platform.
  - Managing Spark clusters, jobs, batches, and interactive sessions.
  Don't use when:
  - Writing generic Python scripts that don't use Spark.
  - Performing simple SQL queries that can be done directly in BigQuery.
  - Troubleshooting failed Spark workloads or analyzing logs (use @skill:gcp-spark-troubleshooting).
license: Apache-2.0
metadata:
  version: v20
  publisher: google
---

# Managed Spark on Google Cloud

> [!IMPORTANT]
>
> You MUST follow the Task Execution Workflow when writing spark code.

## Notebook Generation Environment Rules

> [!CAUTION]
>
> When the task is to **generate** a Spark notebook (as opposed to executing
> one), you **MUST NOT** modify your own local execution environment (i.e. do
> not run these commands with your shell or other tools). Specifically:
>
> -   **NEVER create a virtual environment** (`python -m venv`, `virtualenv`,
>     `conda create`, `uv venv`, `poetry init/install`, etc.).
> -   **NEVER install packages** (`pip install`, `%pip install`, `uv pip
>     install`, `conda install`, `poetry add`).
> -   **NEVER run environment discovery loops** such as activating a venv,
>     `pip list`, or probing for `ipykernel` / `google-cloud-spark-connect` as a
>     precondition for writing the notebook.
>
> Assume the user will select the appropriate
> kernel and dependencies after the notebook is generated.

## Task Execution Workflow

1.  **Understand user request**:

    -   When asked to generate a new spark notebook you **MUST** clarify with
        the user which kernel type will be used: "Local Python" (Spark Connect)
        or "Remote Spark". If the user selects "Local Python", you MUST
        additionally clarify which dataprocSessionConfig should be used (scan
        for existing serverless session templates), and **MUST** initialize the
        session with `ManagedSparkSession` by adding the following cells to the
        notebook:
        ```python
        from google.cloud.dataproc_v1 import Session
        # requires google-cloud-spark-connect pypi package for execution
        from google.cloud.managed_spark_connect import ManagedSparkSession

        session_config = Session()
        session_config.session_template = (
            "projects/<PROJECT_ID>/locations/<REGION>/sessionTemplates/<TEMPLATE_ID>"
        )
        spark = (
            ManagedSparkSession.builder.projectId("<PROJECT_ID>")
            .location("<REGION>")
            .dataprocSessionConfig(session_config)
            .getOrCreate()
        )
        ```
2.  **Understand schemas**: **ALWAYS** use `@skill:discovering-gcp-data-assets`
    skill or `references/schema_direct_inspection.md` to understand input and
    output schemas. Include the schema in your thought process BEFORE generating
    any code. Do NOT guess column names. Cap GCP data asset discovery attempts
    at **3 retries max**. Unless explicitly specified, assume
    that the assets are located in the same project. Avoid scanning for assets
    across other projects as it can take a long time. If an expected dataset or
    table does not exist, use `@skill:discovering-gcp-data-assets` to discover
    all similar tables in the namespace or project.

    *MINOR TYPO RULE*: If there is a minor typo (e.g. `employees` vs
    `employee`), you can fix the error and proceed.

    *STRICT HALT RULE*: If the discovered table names differ from the requested
    table by more than a minor typo (e.g. completely different words, prefixes,
    or suffixes), you must IMMEDIATELY report the missing table and a neutral
    list of all available alternatives in the same namespace to the user without
    making any recommendations. You MUST ask the user which alternative to use
    and then STOP EXECUTING your turn. Do NOT write any Spark code or notebooks.
    Do NOT proceed with code generation, do NOT add fallback logic to code, and
    do NOT automatically substitute any alternative table (even if its schema
    seems to match) without explicit user permission.
3.  **Verify source accessibility**: verify access/existence using `gcloud
    storage ls gs://<path-to-dataset>`. If accessing or reading a GCS path fails
    with a storage error e.g., permission errors like `403
    Forbidden`/`Forbidden`/`PermissionDenied`, or location errors like `404 Not
    Found`/`NotFound`/`FileNotFoundException` you should report the error
    immediately. Either (1) ask the user what to do next, or (2) if asked to
    execute a notebook, save the notebook with the error output and recommend
    next steps to resolve the issue. Do NOT scan all buckets for alternative
    fallback datasets when encountering GCS errors.
4.  **Generate spark code**:

    *   **Output Format**: **ALWAYS** generate code in **Python Notebooks
        (.ipynb)** format. Generate scripts (.py) only if explicitly requested.
    *   **Spark Session Initialization**:

        > [!IMPORTANT] Initializing a Spark session on Google Cloud can take 2-3
        > minutes. You MUST inform the user about the potential delay.

        > [!CAUTION] **NEVER** create a local Spark session. The following are
        > **BANNED**: - `SparkSession.builder.master("local")` -
        > `pyspark.sql.SparkSession.builder.getOrCreate()` when used without
        > `ManagedSparkSession` - Any `try/except` fallbacks that revert to a
        > local `SparkSession`.
        >
        > You **MUST ALWAYS** use `ManagedSparkSession` from
        > `google-cloud-spark-connect` to connect to **Managed Spark
        > Serverless**. No exceptions.

        Refer to `references/gcloud_dataproc.md` for detailed configuration.
        Minimal initialization:

        ```python
        from google.cloud.managed_spark_connect import ManagedSparkSession

        spark = ManagedSparkSession.builder.projectId(<PROJECT_ID>)
            .location(<REGION>)
            .getOrCreate()
        ```
    *   **Production Logging**: In all production PySpark jobs and scripts,
        you MUST use the standard Python `logging` module instead of `print()`
        statements for job lifecycle, progress, and record counts. Configure it
        with timestamps:

        ```python
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        ```
    *   **Security & Dynamic Variables**: You MUST NOT hardcode plaintext
        credentials, passwords, or tokens (use Secret Manager). You MUST NOT
        hardcode environment-specific variables; parameterize project IDs,
        dataset IDs, table names, and bucket paths via `os.environ.get(...)` or
        arguments.
    *   **Read and Write data**: **ALWAYS** Refer to
        `references/read_write_data.md` when reading or writing data.
    *   **Machine Learning Tasks**: Refer to `@skill:ml-best-practices` skill and `references/ml_tasks.md` when generating Machine Learning code.
    *   **Spark Optimizations & Broadcast Joins**: **ALWAYS** refer to
        `references/spark_optimizations.md`. When joining a large DataFrame with
        a small lookup or dimension table, you MUST use `broadcast()` (`from
        pyspark.sql.functions import broadcast`) on the small table. Treat about
        10 MB (Spark's default `spark.sql.autoBroadcastJoinThreshold`) as a
        guide to what counts as small, not a hard limit.
5.  **Verify schema before write**: **ALWAYS** verify that the dataframe and
    destination schema match, use `df.printSchema()` for dataframe schema and
    refer to `@skill:discovering-gcp-data-assets` skill or
    `references/schema_direct_inspection.md` to verify destination schema.
6.  **Compile code before executing**: For notebooks convert them to python
    script using `jupyter nbconvert --to script your-notebook.ipynb` first. Then
    compile the resulting python script using `python3 -m py_compile
    your-script.py`. The same can be done for pyspark source code.
7.  **Execute script or notebook**: When requested to run a job, script,
    session, or execute notebook cells against Managed Spark, refer to
    `references/gcloud_dataproc.md` on how to execute code on Dataproc
    Serverless using Spark Connect or Dataproc jobs.
8.  **Follow up with the user**: If a brand new notebook was generated, instruct the user to select the appropriate kernel in the dropdown for cell execution.

--------------------------------------------------------------------------------

## Common Mistakes Checklist

> [!CAUTION]
>
> Ensure you verify this checklist to avoid mistakes

Before submitting a job, verify:

-   [ ] **All imports present** (`col`, `when`, `lit`, `broadcast`, etc. from
    `pyspark.sql.functions`)
-   [ ] **`vector_to_array` from correct module** use `from pyspark.ml.functions
    import vector_to_array` (NOT `pyspark.sql.functions`)
-   [ ] **DataFrame schema matches target Iceberg table** verify with
    `df.printSchema()` before writing
-   [ ] **CSV files read with `header` and `inferSchema`** without these, the
    header row becomes data and all columns are strings
-   [ ] **Driver memory safety (`toPandas()` / `collect()`)** NEVER call
    `.toPandas()` or `.collect()` on raw or un-aggregated DataFrames. ALWAYS
    perform transformations, aggregations (`groupBy().agg()`), or data reduction
    (`limit()`, `sample()`) in Spark before converting small summaries to Pandas
    for plotting or display.
-   [ ] **No inline pip install in Spark batch/script jobs**: NEVER run pip
    install or subprocess package installations inside PySpark batch scripts
    (the `%pip install` setup cell in generated notebooks is exempt). Pass
    dependencies using --properties=spark.jars.packages=...,
    --archives=gs://.../env.tar.gz#environment, --py-files, or a custom
    --container-image.
-   [ ] **Optimization & Pre-Submission Refactoring** Verify the job against
    `references/spark_optimizations.md` and follow the confirmation protocol in
    `references/spark_refactoring_guide.md`.
-   [ ] **No full file reads of executed notebooks**: You MUST NOT use `read_file` or
    generic full file reading tools on executed `.ipynb` notebooks; they often
    contain massive base64-encoded image outputs that cause excessive token
    consumption. You MUST inspect execution outputs with cell-scoped reading tools
    (such as `notebook__read_cell`, `jupyter__read_cell`, or specific line
    slices).

--------------------------------------------------------------------------------

## IAM Requirements

The Managed Spark (Dataproc) service account needs:

*   `roles/dataproc.worker`: Job execution
*   `roles/biglake.admin`: Iceberg table management
*   `roles/bigquery.jobUser`: Query materialization
*   `roles/storage.objectUser`: Read/write GCS
*   `roles/spanner.databaseUser`: Spanner writes

--------------------------------------------------------------------------------

## Spark resource management

Refer to `references/gcloud_dataproc.md` for detailed guidelines on managing
Spark clusters, jobs, batches, interactive sessions, and Spark Connect sessions.

--------------------------------------------------------------------------------

## Code Optimization & Pre-Submission Verification

Before submitting any Spark job or Dataproc batch, enforce the pre-submission
verification protocol in `references/spark_refactoring_guide.md`: inspect the
code for the anti-patterns catalogued in `references/spark_optimizations.md` and
obtain explicit user confirmation before applying refactoring.

--------------------------------------------------------------------------------

## Troubleshooting & Root Cause Analysis

For troubleshooting failed Spark jobs or Dataproc batches, inspecting/tailing
GCS driver output logs, analyzing Spark event logs, or performing Root Cause
Analysis (RCA), use the `@skill:gcp-spark-troubleshooting` skill.
