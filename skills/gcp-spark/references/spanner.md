# Cloud Spanner in PySpark

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow in `SKILL.md` when writing Spark code.

## Spark Session Configuration

The Spanner connector JAR is not pre-installed and must be attached at session
creation (`gs://` JAR URIs cannot be passed to `spark.jars.packages`, which only
accepts Maven coordinates). Ensure the Spanner JAR's Spark version prefix
(e.g., `spark-3.5-spanner-*` for Dataproc runtime `2.3` / Spark 3.5, or
`spark-4.0-spanner-*` for Dataproc runtime `3.0` / Spark 4.0) matches the
Dataproc runtime version:

-   **Interactive Notebooks (`.ipynb`) & Spark Connect**: Attach the JAR via a
    Session Template or `session_config.runtime_config.properties["spark.jars"]`
    (and ensure `session_config.runtime_config.version` matches the JAR's Spark
    version, as `ManagedSparkSession` defaults to runtime `3.0`):

    ```python
    from google.cloud.dataproc_v1 import Session
    from google.cloud.managed_spark_connect import ManagedSparkSession

    session_config = Session()
    session_config.runtime_config.version = "2.3"
    session_config.runtime_config.properties["spark.jars"] = (
        "gs://spark-lib/spanner/spark-3.5-spanner-1.4.0.jar"
    )
    spark = (
        ManagedSparkSession.builder.projectId("<PROJECT_ID>")
        .location("<REGION>")
        .dataprocSessionConfig(session_config)
        .getOrCreate()
    )
    ```

-   **Dataproc Batch & Cluster Jobs (`.py`)**: Pass
    `--jars=gs://spark-lib/spanner/spark-3.5-spanner-1.4.0.jar` on the `gcloud`
    CLI (see `references/gcloud_dataproc.md`), or set `spark.jars`:

    ```python
    spark = (
        SparkSession.builder.appName("<APP_NAME>")
        .config(
            "spark.jars",
            "gs://spark-lib/spanner/spark-3.5-spanner-1.4.0.jar",
        )
        .getOrCreate()
    )
    ```

## Reading Spanner Tables

```python
df = (
    spark.read.format("cloud-spanner")
    .option("projectId", "<PROJECT_ID>")
    .option("instanceId", "<INSTANCE_ID>")
    .option("databaseId", "<DATABASE_ID>")
    .option("table", "<TABLE_NAME>")
    .load()
)
```

## Writing to Spanner

The connector supports writing to Spanner tables using the DataFrame `write`
API.

### Write Modes

*   **`Append`**: Inserts rows into the existing Spanner table. This is the
    default write mode.

    ```python
    df.write.format("cloud-spanner") \
        .option("projectId", "<PROJECT_ID>") \
        .option("instanceId", "<INSTANCE_ID>") \
        .option("databaseId", "<DATABASE_ID>") \
        .option("table", "<TABLE_NAME>") \
        .mode("append") \
        .save()
    ```

*   **`Overwrite`**: Clears the existing data before writing.

    ```python
    df.write.format("cloud-spanner") \
        .option("projectId", "<PROJECT_ID>") \
        .option("instanceId", "<INSTANCE_ID>") \
        .option("databaseId", "<DATABASE_ID>") \
        .option("table", "<TABLE_NAME>") \
        .mode("overwrite") \
        .save()
    ```
