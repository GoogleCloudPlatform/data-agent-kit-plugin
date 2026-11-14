# Cloud Spanner in PySpark

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow in `SKILL.md` when writing Spark code.

## Spark Session Configuration

The Spanner connector JAR is not pre-installed and must be attached at session
creation (`gs://` JAR URIs cannot be passed to `spark.jars.packages`, which only
accepts Maven coordinates). Use the JAR whose Spark version prefix matches the
Dataproc runtime version:

-   Runtime `3.0` (Spark 4.0; the `ManagedSparkSession` default and the only
    runtime supported by `google-cloud-spark-connect` 2.x clients):
    `gs://spark-lib/spanner/spark-4.0-spanner-1.5.0.jar`
-   Runtime `2.2` / `2.3` (Spark 3.5):
    `gs://spark-lib/spanner/spark-3.5-spanner-1.5.0.jar`

-   **Interactive Notebooks (`.ipynb`) & Spark Connect**: Initialize the session
    as described in `SKILL.md`, adding this builder call to the
    `ManagedSparkSession.builder` chain before `.getOrCreate()`:

    ```python
    .config("spark.jars", "gs://spark-lib/spanner/spark-4.0-spanner-1.5.0.jar")
    ```

    On a **Remote Spark** kernel (explicitly requested, or when running against
    a cluster) the JAR must already be configured on the session or cluster.

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
