# Spark Failure Scenarios

Symptom-to-root-cause catalog. Match the exception text first, then confirm with
stage metrics (`spark_metrics_api.md`) before proposing a fix.

## Out of Memory

**Symptoms**: `java.lang.OutOfMemoryError: Java heap space`, `RECEIVED SIGNAL
TERM`, `Exit code 137`, `Command exited with code 52`, `Python worker crashed`,
executor lost or disconnected.

> [!IMPORTANT]
>
> `MetadataFetchFailedException: Missing an output location for shuffle N` is
> usually **not** a shuffle bug. It means the executor holding that shuffle
> output died — most often from OOM — and the next stage cannot fetch it. Treat
> it as a pointer to an earlier executor loss and look for the OOM in the logs,
> rather than tuning shuffle settings. A rising executor `count` in
> `:summarizeExecutors` corroborates this.

First decide **driver vs executor** — the fixes are opposite:

-   **Driver OOM**: the traceback points at the main script, and the Java stack
    shows `collectToPython`, `toPandas`, or `collect`. Caused by pulling the
    dataset to the driver, or broadcasting a table that is too large.
-   **Executor OOM**: `Exit code 137`, `FetchFailedException`, killed tasks,
    executor-lost messages. Caused by skew, oversized partitions, memory-hungry
    UDFs, or excessive caching.

**Confirm**: `KILLED_TASKS` plus `HIGH_GC_RATIO` or spill findings on a specific
stage.

**Fix**:

-   Remove `collect()` / `toPandas()` on un-aggregated DataFrames; aggregate or
    `limit()` in Spark first.
-   Raise `spark.driver.memory` or `spark.executor.memory`.
-   If only a few tasks fail repeatedly, treat it as skew (below), not as a
    memory shortfall.

**Serverless sizing note**: default is roughly 9.6 GB per driver/executor;
minimum 1024 MB per core with a minimum of 4 cores. Account for this before
recommending a memory value.

## Data Skew

**Symptoms**: a handful of tasks run far longer than the rest; OOM or RPC
failures (`StacklessClosedChannelException`, `Failed to send RPC`) confined to
specific tasks; a stage that is 99% complete for a long time.

**Confirm**: `TASK_DURATION_SKEW` **and** `TASK_INPUT_SKEW` on the same stage.
Duration skew *without* input skew is not data skew — look for resource
contention, external RPC or database latency, or lock contention inside a UDF.

**Fix**: salt the join key; enable Adaptive Query Execution
(`spark.sql.adaptive.enabled=true`, plus `skewJoin` handling); increase
`spark.sql.shuffle.partitions`; broadcast the small side of the join; avoid
`collect_list()` / `collect_set()` over huge groups.

## Schema and Data Type Errors

**Symptoms**: `NumberFormatException`, `BadRecordException`, `AnalysisException`
referencing column types, `SparkException` with a cast message.

**Cause**: the declared read schema disagrees with the actual data — typically a
column declared `IntegerType` that contains non-numeric strings.

**Fix**: correct the schema to match the data; or read with `PERMISSIVE` mode
and a `_corrupt_record` column to inspect the offending rows; or add a cleaning
step before enforcement. Note the mode semantics: `FAILFAST` throws on the first
bad record, `PERMISSIVE` nulls bad fields, `DROPMALFORMED` silently drops rows.

## Serialization / Pickling Errors

**Symptoms**: `TypeError: cannot pickle`, `PicklingError`, `Could not serialize
object`, `Task not serializable`.

**Cause**: a non-serializable object captured in a UDF closure or RDD
transformation — `threading.Lock`, a database connection, a file handle, a
`SparkContext` reference, or a heavyweight custom class.

**Find it**: look for `cloudpickle` or `pyspark/serializers.py` in the
traceback; the offending UDF name is adjacent.

**Fix**: construct the object *inside* the UDF body so it is created per worker;
use broadcast variables for read-only shared data; use accumulators for
aggregation.

## Python UDF Exceptions

**Symptoms**: `ValueError`, `TypeError`, `KeyError`, `AttributeError`, or
`NotFittedError` wrapped in `PythonException`; Java stack contains
`BasePythonRunner$ReaderIterator.handlePythonException`.

**Find it**: the Python traceback in `jsonPayload.message` names the UDF and the
offending input value. This is usually logged at **INFO**, not ERROR.

**Fix**: handle `None` and malformed input inside the UDF; pre-filter invalid
rows; prefer built-in Spark SQL functions over Python UDFs where possible (also
a large performance win).

## File / Path Not Found

**Symptoms**: `AnalysisException: [PATH_NOT_FOUND]`, `Path does not exist`,
`FileNotFoundException`.

**Check**: the path exists (`gcloud storage ls gs://...`); the bucket name,
prefix, and extension are correct (`.parquet` vs `.csv`); the workload's service
account has `storage.objects.get` on the bucket; the upstream job that produces
the input actually completed.

**Fix**: correct the path, grant access, or add an existence check. Report
permission and location errors immediately rather than scanning other buckets
for a substitute dataset.

## Dependency / Import Errors

**Symptoms**: `ModuleNotFoundError: No module named '<package>'`,
`ClassNotFoundException`, `NoClassDefFoundError`.

**Cause**: the package is not present in the runtime. Serverless runtimes
preinstall a common set (pandas, numpy, scikit-learn, pyarrow); check the
runtime version documentation for the exact list rather than assuming.

**Fix**: ship dependencies properly —

-   `--py-files` for `.py` / `.zip` modules.
-   `--archives` with a `venv-pack` or `conda-pack` environment for complex
    Python dependencies.
-   `--properties spark.jars.packages=...` for Maven coordinates.
-   A custom container image for heavy or native dependencies.

Never run `pip install` or `subprocess` package installation inside a Spark job.

## Slow but Successful Workloads

No exception to anchor on; go straight to stage metrics.

-   Spill findings → raise memory or increase partitions.
-   `TOO_MANY_SMALL_TASKS` → coalesce inputs; address the small-files problem.
-   `LARGE_SHUFFLE_PARTITION_500MB` → raise `spark.sql.shuffle.partitions`.
-   High shuffle write time relative to run time → serialization bottleneck;
    reduce shuffled columns, or reconsider the join strategy.
-   `HIGH_SCAN_TASK_COUNT` → scan parallelism is far past useful; increase split
    size or compact the source.

Before recommending Adaptive Query Execution or autotuning, check
`runtimeConfig.properties` and `:accessEnvironmentInfo` — they may already be
enabled, and recommending an active setting undermines the whole analysis.
