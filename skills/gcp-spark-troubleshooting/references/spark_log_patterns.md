# Spark Error Patterns & Remediation Playbook

This reference provides exact log signatures, root cause mechanisms, and proven
remediation steps for common Spark and Dataproc failures.

--------------------------------------------------------------------------------

## 1. Out of Memory (OOM) Errors

### A. Driver OOM (`java.lang.OutOfMemoryError: Java heap space`)

-   **Log Signature**:

    ```
    java.lang.OutOfMemoryError: Java heap space
      at java.util.Arrays.copyOf(Arrays.java:3236)
      at org.apache.spark.sql.execution.SparkPlan.executeCollect(SparkPlan.scala:390)
      at org.apache.spark.sql.Dataset.collectToPython(Dataset.scala:3538)
    ```
-   **Root Cause**: The driver node attempted to pull all distributed partitions
    into a single local JVM/Python memory space via `df.collect()`,
    `df.toPandas()`, or broadcasting a table larger than
    `spark.sql.autoBroadcastJoinThreshold`.
-   **Remediation**:

    1.  Replace `df.collect()` or `df.toPandas()` with distributed writes
        (`df.write.format("bigquery").save(...)` or `df.write.parquet(...)`).
    2.  Use `df.take(N)` or `df.limit(N)` for small samples.
    3.  Increase driver memory via Spark properties: `--properties
        spark.driver.memory=8g,spark.driver.maxResultSize=4g`

--------------------------------------------------------------------------------

### B. Executor OOM & Container Eviction (`Exit code 137`)

-   **Log Signature**:

    ```
    ERROR org.apache.spark.executor.CoarseGrainedExecutorBackend: RECEIVED SIGNAL TERM
    Container killed by YARN for exceeding memory limits. 12.2 GB of 12.0 GB physical memory used.
    org.apache.spark.shuffle.FetchFailedException: Failed to connect to /10.x.x.x:7337
    ```
-   **Root Cause**: An individual executor partition exceeded the physical
    memory allocated by the container manager (YARN or Dataproc Serverless
    cgroup). Often caused by severe data skew, large memory-heavy Python UDFs,
    or in-memory aggregation of millions of rows per key.
-   **Remediation**:

    1.  Increase `spark.executor.memory` (e.g. from 4g to 8g or 16g).
    2.  Increase `spark.executor.memoryOverhead` (e.g. from default 10% to
        20-30% of executor memory): `--properties
        spark.executor.memory=8g,spark.executor.memoryOverhead=2g`
    3.  Increase shuffle partitions to make each task handle less data:
        `--properties spark.sql.shuffle.partitions=1000`

--------------------------------------------------------------------------------

## 2. Data Skew & Partition Stragglers

-   **Log Signature**:

    -   Spark stage hangs at 99% (e.g. 199/200 tasks complete in 1 minute, task
        200 takes 2 hours).
    -   Warnings in driver logs:

    ```
    WARN TaskSetManager: Lost task 199.0 in stage 3.0: java.io.IOException: Connection reset by peer
    ```
-   **Root Cause**: A single join or groupBy key (often `NULL` or a default
    value like `0` or `"unknown"`) concentrates an extreme volume of records
    into one partition.
-   **Remediation**:

    1.  Enable Adaptive Query Execution (AQE) skew join handling:

        ```
        spark.sql.adaptive.enabled=true
        spark.sql.adaptive.skewJoin.enabled=true
        spark.sql.adaptive.skewJoin.skewedPartitionFactor=5
        spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes=268435456
        ```
    2.  Salt skewed keys prior to joining:

        ```python
        import pyspark.sql.functions as F
        df_salted = df.withColumn("salt", F.concat(F.col("skewed_key"), F.lit("_"), F.floor(F.rand() * 10)))
        ```

--------------------------------------------------------------------------------

## 3. Python UDF Exceptions

-   **Log Signature**:

    ```
    org.apache.spark.api.python.PythonException: An exception was thrown from the Python worker:
    Traceback (most recent call last):
      File "/usr/lib/spark/python/lib/pyspark.zip/pyspark/worker.py", line 1236, in main
      File "main.py", line 45, in parse_user_record
    KeyError: 'user_id'
    ```
-   **Root Cause**: Unhandled exception in Python UDF executing inside worker
    processes. Note that Spark Java logs wrap this in `PythonException`. The
    actual traceback is located inside the worker log message.
-   **Remediation**:

    1.  Add defensive null/key checks inside the Python function:
        `record.get("user_id", "default")`.
    2.  Convert standard Python UDFs to native Spark SQL expressions (`when()`,
        `coalesce()`, `regexp_extract()`) for 10x better performance.

--------------------------------------------------------------------------------

## 4. Serialization & Pickling Errors

-   **Log Signature**:

    ```
    _pickle.PicklingError: Could not serialize object: TypeError: cannot pickle '_thread.lock' object
    org.apache.spark.SparkException: Task not serializable
    ```
-   **Root Cause**: A Python UDF or RDD transformation references an object from
    the driver scope that cannot be serialized (e.g., database connections, file
    handles, threading locks, or active `SparkSession` instances).
-   **Remediation**:

    1.  Instantiate non-serializable objects **inside** the partition or UDF
        function:

        ```python
        def process_partition(records):
            # Create client inside worker process
            client = create_database_client()
            for r in records:
                yield client.enrich(r)
        ```
    2.  Use broadcast variables for static read-only lookups:
        `sc.broadcast(my_dict)`.

--------------------------------------------------------------------------------

## 5. Path Not Found & IAM Access Denied

-   **Log Signature**:

    ```
    org.apache.spark.sql.AnalysisException: [PATH_NOT_FOUND] Path does not exist: gs://my-bucket/data/input.parquet
    com.google.cloud.hadoop.repackaged.gcs.com.google.api.client.googleapis.json.GoogleJsonResponseException: 403 Forbidden
    ```
-   **Root Cause**: Missing GCS files, typos in bucket or table prefix, or the
    Dataproc Service Account lacks `roles/storage.objectViewer` on the target
    bucket.
-   **Remediation**:

    1.  Verify GCS path with `gcloud storage ls gs://bucket/path`.
    2.  Grant the Dataproc VM/batch service account `roles/storage.objectViewer`
        (read) or `roles/storage.objectUser` (read/write).
