# Spark Event Log Structure & Streaming Parser Guide

Dataproc writes Spark event logs to Cloud Storage when event logging is enabled
(`spark.eventLog.enabled=true`, `spark.eventLog.dir=gs://...`). Event logs
record the entire lifecycle of applications, jobs, stages, tasks, and executors
as structured JSON lines.

--------------------------------------------------------------------------------

## 1. File Formats & Compression

Spark event logs can be found in several formats:

-   Plaintext JSON-lines: `gs://<bucket>/spark-events/app-id`
-   Gzip compressed: `.../app-id.gz`
-   Zstandard compressed: `.../app-id.zst` (default in Spark 3.x / Dataproc
    2.2+)

Because Spark event logs often reach several gigabytes in size for enterprise
workloads, **never load the entire file into memory**. Use
`scripts/spark_gcs_log_reader.py --action=summarize_events` for streaming
single-pass parsing.

--------------------------------------------------------------------------------

## 2. Key Event Types

-   `SparkListenerApplicationStart`
    -   Key fields: `App ID`, `App Name`, `Timestamp`, `User`
    -   Diagnostic relevance: Application startup time and metadata.
-   `SparkListenerApplicationEnd`
    -   Key fields: `Timestamp`
    -   Diagnostic relevance: Total job duration and end timestamp.
-   `SparkListenerStageSubmitted`
    -   Key fields: `Stage Info` (`Stage ID`, `Number of Tasks`)
    -   Diagnostic relevance: Stage start and concurrency level.
-   `SparkListenerStageCompleted`
    -   Key fields: `Stage Info` (`Stage ID`, `Failure Reason`, `Accumulables`)
    -   Diagnostic relevance: Stage failure detection, memory/disk spills.
-   `SparkListenerTaskEnd`
    -   Key fields: `Stage ID`, `Task Info`, `Task End Reason`, `Task Metrics`
    -   Diagnostic relevance: Failed task exceptions, task duration, executor
        IDs.
-   `SparkListenerExecutorRemoved`
    -   Key fields: `Executor ID`, `Removed Reason`, `Timestamp`
    -   Diagnostic relevance: Node evictions, spot VM preemptions, OOM deaths.
    -   Note: The field is `Removed Reason`, not `Reason`. Reading `Reason`
        yields `None` and silently hides every executor loss.
-   `SparkListenerEnvironmentUpdate`
    -   Key fields: `Spark Properties`, `JVM Information`
    -   Diagnostic relevance: Spark runtime configuration settings.

--------------------------------------------------------------------------------

## 3. Interpreting Event Log Summaries

When running `python3 scripts/spark_gcs_log_reader.py --uri="..."
--action=summarize_events`, look for:

1.  **Failed Stages**: Pinpoints which transformation in the DAG failed.
2.  **Sampled Failed Tasks**: Shows the specific task attempt, host VM, and
    unhandled exception.
3.  **Lost Executors**: If executors were removed with `Container killed by YARN
    for exceeding memory limits`, suspect executor OOM or memory leak. If
    removed with `Heartbeat missing` or `Pod evicted`, suspect VM preemption.
4.  **Memory/Disk Spills**: Shows which stages ran out of executor memory and
    were forced to write intermediate shuffle data to disk.
