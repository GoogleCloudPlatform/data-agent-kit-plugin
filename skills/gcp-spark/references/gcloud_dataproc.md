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
> [!IMPORTANT] This section applies to **PySpark (.py) job**. For other
> batch jobs e.g. spark-sql use an appropriate job type.

> [!IMPORTANT] Dataproc Serverless batches (`gcloud dataproc batches submit`) do
> not require running cluster. You MUST NOT create or provision new Dataproc
> cluster when submitting serverless batch jobs.

Determine the properties and configuration required by the pyspark script before
executing the command for Job Submission

#### Basic batch submission command

Prefer MCP if available. If using gcloud, use this command template:

Augment the basic command with iceberg, spanner or xgboost related arguments as
needed by the script to be executed. When submitting batches with multiple
java dependencies, you must combine them with commas (e.g.
`spark.jars.packages=pkg1,pkg2`).

```
gcloud dataproc batches submit pyspark <SCRIPT_PATH.py> \
    --project=<PROJECT_ID> \
    --region=<GCP_REGION> \
    --version=2.3 \
    --deps-bucket=<GCS_PATH>
```

You MUST set the `--deps-bucket` to a GCS path to upload workload dependencies.

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

#### PostgreSQL

-   **Dependency**: `spark.jars.packages=org.postgresql:postgresql:42.6.0`
-   **Notes**: Pass `--subnet=...` for private IP

#### Iceberg REST

-   **Dependency**:
    `spark.jars.packages=org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0`
-   **Notes**: In code use `<CATALOG>.<DATASET>.<TABLE>` (not project ID)

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
    uv venv spark_env --python 3.12
    source spark_env/bin/activate
    uv pip install -U google-cloud-spark-connect
    ```

3.  **Pip environment**:

    ```bash
    python3 -m venv spark_env
    source spark_env/bin/activate
    pip install -U google-cloud-spark-connect
    ```

4.  **Initialize `ManagedSparkSession` & Execute**: Use `ManagedSparkSession`
    from `google.cloud.managed_spark_connect` to connect to Dataproc Serverless.
    Session provisioning takes **2–3 minutes**; execute scripts in the
    foreground (e.g. `python3 script.py | tee driver_log.txt`):

    ```python
    from google.cloud.managed_spark_connect import ManagedSparkSession

    spark = ManagedSparkSession.builder.getOrCreate()

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

    For advanced configuration, use the `Session` class:

    ```python
    from google.cloud.dataproc_v1 import Session
    from google.cloud.managed_spark_connect import ManagedSparkSession

    session_config = Session()
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

5.  **Local Environment Cleanup**:

    ```bash
    deactivate
    rm -rf spark_env
    ```

### Listing sessions

Prefer MCP if available. If using gcloud, use this command template:

```
gcloud dataproc sessions list \
    --format="json(createTime, uuid, creator, state, jupyterSession, sparkConnectSession)" \
    --sort-by="~createTime" \
    --limit=100
```

Tips:

-   **Important:** Always include a limit; the default is no limit, which may
    produce too much output to process.
-   Add a `--filter` to limit results, e.g. `state = ACTIVE AND labels.env =
    staging AND create_time >= "2023-01-01T00:00:00Z"`
