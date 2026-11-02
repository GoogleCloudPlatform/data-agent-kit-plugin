# Managed Spark on Google Cloud (Dataproc) and Spark Integration

Manage Spark resources on Managed Spark on Google Cloud (Dataproc Clusters and
Serverless), including setting up clusters; launching jobs and batches; managing
serverless session templates; running Spark Connect sessions; and inspecting
outputs.

## Background

Managed Spark on Google Cloud (Dataproc) is Google Cloud's managed service for
running Hadoop and Spark workloads. The two basic flavors are:

-   **Clusters** aka **Dataproc on GCE**: users create a cluster, then submit
    one or more Spark or other jobs. Users have control over the underlying VM
    resources.
-   **Serverless Spark** aka **Dataproc Serverless**, where users do not control
    the underlying VM resources:
    -   Users may submit **batches**, which provision the underlying resources,
        launch a job, and tear down the resources, all in a single operation.
    -   Users may also create persistent **interactive sessions**. These are
        generally created through a Jupyter interface rather than gcloud, but
        existing sessions may be inspected with gcloud.
    -   Users can create **session templates** as a way to create multiple
        sessions using the same configuration.

Users may not always know the technically correct terminology for Clusters vs.
Serverless, for example they may ask for "jobs" or "spark jobs" but mean
Serverless Batches.

## Setup

## Project and region/location preferences

Users configure `gcloud` to point at their desired project and region/location.
Assume gcloud is already installed.

Look up the configuration with:

```
gcloud config get project
gcloud config get dataproc/region
gcloud config get dataproc/location
gcloud config get compute/region
```

If region and location are not set, you may suggest using the compute region.

### Prefer MCP if possible

> [!IMPORTANT] If you have access to one or more MCP servers related to Dataproc
> or Serverless Spark, you MUST use those MCP tools rather than gcloud. ONLY
> fall back to gcloud if MCP tools are not available.

When using MCP, the ONLY thing you use gcloud for is looking up
project/region/location to pass as arguments to the MCP tools.

### gcloud as backup

If MCP servers are not available or there are no tools that can be used for your
use case, use `gcloud` to interact with Dataproc.

In general, Dataproc Clusters and Serverless Batches commands accept `--region`.
Dataproc Serverless Sessions commands accept `--location`.

### Saving driver logs locally

> [!TIP] `gcloud dataproc jobs submit`, `gcloud dataproc batches submit`, and
> local `ManagedSparkSession` scripts stream driver output directly to
> stdout/stderr. When asked to save driver logs to a local file, pipe the output
> to a `.txt` file in the current directory (e.g., `2>&1 | tee driver_log.txt`).

## Dataproc Clusters

Use this section if the user requests "spark jobs", "spark clusters",
"clusters", "cluster jobs", or just "jobs". **Do not** use this section if the
user requests "serverless jobs", "serverless batches", or "batches".

### Listing clusters

Prefer MCP if available. If using gcloud, use this command template:

```
gcloud dataproc clusters list \
    --format="json(\
clusterName,\
clusterUuid,\
projectId,\
region,\
creator,\
status)" \
    --sort-by="~status.stateStartTime" \
    --limit=100
```

Tips:

-   **Important:** Always include a limit; the default is no limit, which may
    produce too much output to process.
-   Add a `--filter` to limit results, e.g. `status.state = ACTIVE AND
    clusterName = mycluster AND labels.env = staging AND labels.starred = *`

### Creating clusters

Only create a cluster when explicitly requested or when no existing cluster is
available. Prefer MCP if available. If using gcloud:

```bash
gcloud dataproc clusters create <CLUSTER_NAME> \
    --project=<PROJECT_ID> \
    --region=<REGION> \
    --subnet=<SUBNET>
```

-   **Auto Zone Placement**: Specify `--region=<REGION>` and **omit `--zone`**
    unless a specific zone is explicitly requested, so Dataproc automatically
    selects a zone with available GCE capacity.
-   **Avoid Redundant Default Flags**: Do **NOT** pass flags that repeat
    Dataproc system defaults (such as `--master-machine-type=n1-standard-4`,
    `--worker-machine-type=n1-standard-4`, or `--num-workers=2`) unless custom
    sizing is explicitly requested.
-   **Connector-Specific Flags & Scopes**: Refer to the target connector's
    reference file (`references/biglake_iceberg.md`,
    `references/jdbc_cloudsql.md`, `references/aws_s3.md`,
    `references/azure_storage.md`, `references/spanner.md`) for required
    optional components, scopes, or properties.

### Listing jobs

Prefer MCP if available. If using gcloud, use this command template:

```
gcloud dataproc jobs list \
    --format="json(\
jobType,\
reference,\
placement.clusterName,\
status.state,\
status.stateStartTime)" \
    --sort-by="~status.stateStartTime" \
    --limit=100
```

Tips:

-   **Important:** Always include a limit; the default is no limit, which may
    produce too much output to process.
-   Add a `--filter` to limit results, e.g. `status.state = ACTIVE AND
    labels.env = staging AND labels.starred = *`

### Submitting jobs

Prefer MCP if available. If using gcloud, use the command template matching the
requested job type:

-   **PySpark job (`.py`)**:
    ```bash
    gcloud dataproc jobs submit pyspark <LOCAL_SCRIPT_PATH.py> \
        --project=<PROJECT_ID> \
        --cluster=<CLUSTER> \
        --region=<REGION>
    ```
-   **Spark SQL job (`.sql`)**:
    ```bash
    gcloud dataproc jobs submit spark-sql \
        --file=<LOCAL_SCRIPT_PATH.sql> \
        --project=<PROJECT_ID> \
        --cluster=<CLUSTER> \
        --region=<REGION> \
        --params="KEY1=VALUE1,KEY2=VALUE2"
    ```

> [!WARNING] The `gcloud dataproc jobs submit` commands directly accept local
> file paths and automatically stage them. You MUST NOT attempt to manually
> create GCS staging buckets or manually use `gcloud storage cp` to upload your
> scripts before submission.

## Dataproc Serverless

Use this section if the user requests:

-   batches, serverless batches, spark batches, serverless jobs
-   spark sessions, serverless spark sessions, spark interactive sessions,
    serverless interactive sessions, spark notebooks, spark kernels

**Do not** use this section if the user requests spark jobs, cluster jobs, or
just jobs, **unless** you have confirmed with the user that they are using
Serverless.

### Listing batches

Prefer MCP if available. If using gcloud, use this command template:

```
gcloud dataproc batches list \
    --format="json(batchType, createTime, creator, name, state, stateTime)" \
    --sort-by="~stateTime" \
    --limit=100
```

Tips:

-   **Important:** Always include a limit; the default is no limit, which may
    produce too much output to process.
-   Add a `--filter` to limit results, e.g. `(state = RUNNING and create_time <
    "2023-01-01T00:00:00Z") or labels.environment=production`

### Launching batches

> [!WARNING] This DOES NOT apply to executing **Python Notebooks (.ipynb)**.
> [!IMPORTANT] Match the batch subcommand to the requested job type: use
> `pyspark` for PySpark scripts (`.py`) and `spark-sql` for Spark SQL scripts
> (`.sql`). When asked for a Spark SQL script or `spark-sql` batch job, you MUST
> author a `.sql` script and submit it via
> `gcloud dataproc batches submit spark-sql` (do **NOT** substitute a `.py`
> PySpark script).

> [!IMPORTANT] Dataproc Serverless batches (`gcloud dataproc batches submit`) do
> not require running cluster. You MUST NOT create or provision new Dataproc
> cluster when submitting serverless batch jobs.

Determine the properties and configuration required by the script before
executing the command for Job Submission.

#### PySpark batch submission (`pyspark`)

Prefer MCP if available. If using gcloud, use this command template:

Augment the basic command with iceberg, spanner, jdbc, or xgboost related arguments as
needed by the script to be executed. When submitting batches with multiple
java dependencies, you must combine them with commas (e.g.
`spark.jars.packages=pkg1,pkg2`).

```
gcloud dataproc batches submit pyspark <SCRIPT_PATH.py> \
    --project=<PROJECT_ID> \
    --region=<GCP_REGION> \
    --deps-bucket=gs://<BUCKET_NAME>
```

You MUST set the `--deps-bucket` to a root GCS bucket URI (`gs://<BUCKET_NAME>`). Do NOT pass a subfolder path (e.g. `gs://<BUCKET_NAME>/deps`), or `gcloud` will fail with `Invalid bucket name`.

#### Spark SQL batch submission (`spark-sql`)

Prefer MCP if available. If using gcloud, use this command template (pass
`--vars="KEY1=VALUE1,KEY2=VALUE2"` to substitute `${KEY}` variables in the
`.sql` script):

```bash
gcloud dataproc batches submit spark-sql <SCRIPT_PATH.sql> \
    --project=<PROJECT_ID> \
    --region=<GCP_REGION> \
    --deps-bucket=gs://<BUCKET_NAME> \
    --vars="KEY1=VALUE1,KEY2=VALUE2"
```

> [!IMPORTANT] Dataproc Serverless batches can be expected to take a very long
> time. **Typical initial execution time:** 10-15 minutes. This is **NORMAL**
> behavior. [!WARNING] **DO NOT CANCEL PREMATURELY!**

#### Checking batch completion

When batch is submitted synchronously, you can wait for the command to return.
For asynchronous execution, you must poll the batch status until state is
`SUCCEEDED`, `FAILED` or `CANCELLED`. You can check the batch status using
`gcloud dataproc batches describe <BATCH_ID>`.

### Connector Dependencies & Properties

> [!IMPORTANT] Examples below work for spark version 3.5 which is used in
> runtimes 2.2 and 2.3. For other runtimes you need to scan through libraries
> targeting the appropriate version of spark.

#### Spanner

-   **Dependency**: `--jars=gs://spark-lib/spanner/spark-3.5-spanner-1.4.0.jar`
-   **Notes**: Pass `.option("projectId", ...)` in PySpark

#### PostgreSQL & JDBC Databases

-   **Dependency**: `--jars=gs://<BUCKET_NAME>/<PATH_TO_DRIVER>.jar`
-   **Notes**: Pass `--subnet=<SUBNET>` for private IP. See `references/jdbc_cloudsql.md`.

#### Iceberg REST

-   **Dependency**:
    -   **Dataproc Serverless**: Pre-installed on the default Spark classpath (`/usr/lib/spark/jars/`). Do **NOT** pass `spark.jars.packages=org.apache.iceberg:...` (which risks Scala binary mismatches or missing `GCSFileIO` classes).
    -   **Dataproc on GCE Clusters**: Enable `--optional-components=ICEBERG` at cluster creation (which adds `/usr/lib/iceberg/lib/*` to `SPARK_DIST_CLASSPATH`), or pass the local VM JARs from `/usr/lib/iceberg/lib/` via `--jars` if submitting to an existing cluster without the optional component.
-   **Notes**:
    -   In code use `<CATALOG>.<DATASET>.<TABLE>` (not project ID).
    -   Before running a batch job that creates or writes to a BigLake Iceberg REST catalog, ensure the catalog exists on the GCS bucket (`gcloud biglake iceberg catalogs create <BUCKET_NAME> --catalog-type=gcs-bucket --project=<PROJECT_ID>`) and that the catalog name matches the GCS bucket name (`gs://<BUCKET_NAME>`).

#### Pub/Sub

-   **Dependency**: `from google.cloud import pubsub_v1`
-   **Notes**: Pre-installed in runtime

#### XGBoost

XGBoost requires spark dynamic allocation to be disabled. Set additional
properties:

```
--properties="spark.dynamicAllocation.enabled=false"
```

### Creating sessions

**Do not** create sessions using gcloud for use in notebooks. Instead, direct
the user to associate the notebook with a kernel using the Kernel Selector:

1.  Click "Remote Spark Kernels"
2.  Choose a kernel name ending in "on Serverless Spark"

It is expected for Serverless kernel creation to take approximately 2 minutes or
more.

### Spark Connect on Dataproc (Notebooks and Scripts)

To initialize, run, or author Spark Connect sessions in PySpark notebooks or
Python scripts, follow these steps:

1.  **Activating environment**:

    *   **UV installed** (`command -v uv`): Follow **UV environment** (ensure
        Python version matches runtime e.g. 3.12).
    *   **Otherwise**: Follow **Pip environment**.

2.  **UV environment**:

    ```bash
    uv venv venv --python 3.12
    source venv/bin/activate
    uv pip install -U google-cloud-spark-connect
    ```

3.  **Pip environment**:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -U google-cloud-spark-connect
    ```

4.  **Project and region settings**:

    You SHOULD specify project and region in the code. When not set by the user,
    project and region MUST be retrieved **BEFORE** writing any code, in the
    following order:

    -   IDE configuration: `google.cloud.project`, `google.cloud.region`
    -   Environment variables: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`
    -   GCloud config: `gcloud config get project`, `gcloud config get-value
        dataproc/region`

    Retrieve those values and put them using builder methods.

5.  **Initialize `ManagedSparkSession` & Execute**: Use `ManagedSparkSession`
    from `google.cloud.managed_spark_connect` to connect to Dataproc Serverless.
    Session provisioning takes **2–3 minutes**; execute scripts in the
    foreground (e.g. `python3 script.py`):

    ```python
    from google.cloud.managed_spark_connect import ManagedSparkSession

    spark = (
        ManagedSparkSession.builder.projectId("<PROJECT_ID>")
        .location("<REGION>")
        .getOrCreate()
    )

    # Run Spark DataFrame or SQL operations
    df = spark.sql("SELECT 'Hello from Spark Connect' AS message")
    df.show()

    # Deactivate / stop the session
    spark.stop()
    ```

    You can configure Spark properties using the `.config()` method:

    ```python
    from google.cloud.managed_spark_connect import ManagedSparkSession

    spark = (
        ManagedSparkSession.builder.config("spark.executor.memory", "4g")
        .config("spark.executor.cores", "2")
        .getOrCreate()
    )
    ```

    For advanced configuration e.g. when using session templates, use the
    `Session` class:

    ```python
    from google.cloud.dataproc_v1 import Session
    from google.cloud.managed_spark_connect import ManagedSparkSession

    session_config = Session()
    session_config.session_template = (
        "projects/<PROJECT_ID>/locations/<REGION>/sessionTemplates/<TEMPLATE_ID>"
    )
    session_config.environment_config.execution_config.subnetwork_uri = (
        "<SUBNET_URI>"
    )
    session_config.runtime_config.version = "3.0"
    spark = (
        ManagedSparkSession.builder.projectId("<PROJECT_ID>")
        .location("<REGION>")
        .dataprocSessionConfig(session_config)
        .getOrCreate()
    )
    ```

6.  **Local Environment Cleanup**:

    ```bash
    deactivate
    rm -rf venv
    ```

### Listing sessions

Prefer MCP if available. If using gcloud, use this command template:

```
gcloud beta dataproc sessions list --location=<REGION> \
    --format="json(createTime, uuid, creator, state, jupyterSession, sparkConnectSession)" \
    --sort-by="~createTime" \
    --limit=100
```

Note: use the `beta` track. The GA `gcloud dataproc sessions` group is missing
in older Cloud SDK releases (for example, 590 fails with `Invalid choice:
'sessions'`), and sessions take `--location`, not `--region`.

Tips:

-   **Important:** Always include a limit; the default is no limit, which may
    produce too much output to process.
-   Add a `--filter` to limit results, e.g. `state = ACTIVE AND labels.env =
    staging AND create_time >= "2023-01-01T00:00:00Z"`

--------------------------------------------------------------------------------

## Workload Monitoring & Fleet Observability

For comprehensive single-region and multi-region fleet assessments, Cloud Asset
Inventory discovery, configuration auditing, and Cloud Monitoring/Logging
telemetry, use `@skill:gcp-spark-observability`. Use the following patterns for
common workload monitoring tasks:

### 1. Failed Workload Triage & Discovery Bridge

When the user asks why a recent Spark batch or job failed without providing an
ID (e.g., *"Why did my last Spark batch fail?"* or *"Did any Spark jobs fail
today?"*):

1.  Resolve the active region (`gcloud config get-value dataproc/region` or
    session context).
2.  List recent failed Serverless batches (`state = FAILED`, `limit=10`):

    ```bash
    gcloud dataproc batches list --region=<REGION> \
        --filter="state = FAILED" \
        --limit=10 \
        --format="json(name,uuid,state,createTime,stateTime,stateMessage,creator)"
    ```

    *(Or call MCP `list_batches` with `filter="state = FAILED"`,
    `order_by="create_time desc"` and `page_size=10`; MCP omits `stateMessage`,
    so follow up with `gcloud dataproc batches describe`.)*
3.  Identify the most recent failed batch ID (sorted by `stateTime` /
    `createTime` descending) and hand off to `@skill:gcp-spark-troubleshooting`
    to inspect driver logs, executor exceptions, and stage diagnostics.

### 2. Active Fleet & Resource Inventory

When asked what Spark workloads or sessions are running right now, inspect all
active surfaces in the target region(s) and summarize in a Markdown table with
columns `Type`, `ID / Name`, `Region`, `Status`, `Creator`, and `Started`:

-   **Serverless Batches**: `gcloud dataproc batches list --region=<REGION>
    --filter="state = RUNNING OR state = PENDING" --format=json`
-   **Interactive Sessions** (uses `--location`, **not** `--region`): `gcloud
    beta dataproc sessions list --location=<REGION> --filter="state = ACTIVE OR
    state = CREATING" --format=json`
-   **Dataproc Clusters**: `gcloud dataproc clusters list --region=<REGION>
    --filter="status.state = RUNNING OR status.state = CREATING OR status.state
    = UPDATING" --format=json`
-   **Cluster Jobs**: `gcloud dataproc jobs list --region=<REGION>
    --state-filter=active --format=json`

### 3. Serverless Compute (DCU-Hours) & Shuffle Consumption

Note that MCP `list_batches` and `get_batch` omit `runtimeInfo`. Use
`gcloud dataproc batches describe <BATCH_ID> --region=<REGION> --format=json`
(or `gcloud dataproc batches list --region=<REGION> --format=json`) to read
`runtimeInfo.approximateUsage`, which is populated only after a batch
completes (running batches expose `runtimeInfo.currentUsage` instead):

-   $\text{DCU-Hours} = \frac{\text{milliDcuSeconds}}{3,600,000}$
-   $\text{Shuffle-GB-Months} = \frac{\text{shuffleStorageGbSeconds}}{2,592,000}$

Rank batches descending by `DCU-Hours` when identifying top compute consumers.

### 4. Zombie / Idle Cluster Waste Detection

To detect idle clusters wasting compute spend:

1.  List active clusters (`status.state = RUNNING`) via `gcloud dataproc
    clusters list --region=<REGION> --filter="status.state = RUNNING"
    --format=json`.
2.  For each active cluster, list recent jobs (`gcloud dataproc jobs list
    --region=<REGION> --cluster=<CLUSTER_NAME> --limit=20 --format=json`).
3.  Flag any cluster with **0 active (`RUNNING`/`PENDING`) jobs** whose most
    recent job completed **> 2 hours ago** (or cluster running > 2 hours with 0
    jobs ever run) **and** zero running or pending YARN applications
    (`metrics.yarnMetrics.yarn-apps-running` / `yarn-apps-pending` in the
    `clusters list` output), since notebooks and `spark-submit` over SSH do not
    appear in `jobs list`.
4.  Recommend `gcloud dataproc clusters update <CLUSTER_NAME> --region=<REGION>
    --stop-max-idle=30m` (or `--delete-max-idle=30m`), or deleting the cluster
    after explicit user confirmation. **Never delete a running cluster without
    user confirmation.**
