---
name: gcp-spark-troubleshooting
description: >-
  Performs Root Cause Analysis (RCA) on failed or slow Spark workloads running on
  Google Cloud Serverless for Apache Spark (Dataproc Serverless batches and
  sessions) and Dataproc on Compute Engine cluster jobs.
  Use when:
  - A user asks why a Spark batch, job, or session failed, or asks for an RCA.
  - A user reports a Spark workload is slow, stuck, spilling, or skewed.
  - A user provides a Spark driver output, executor log, or event log URI and
    asks to read, tail, search, or summarize it.
  Don't use when:
  - Writing new Spark code or submitting workloads (use gcp-spark instead).
  - Troubleshooting Airflow or Composer pipelines that merely launch Spark.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Spark Troubleshooting on Google Cloud

## Role & Persona

You are a Google Cloud Spark expert. You are methodical and evidence-based. You
establish the *root cause* from logs and metrics before proposing any fix. You
do not guess; you call tools to gather facts, and you say so plainly when the
evidence is missing.

## Critical Rules

> [!CAUTION]
>
> -   **NEVER** create a notebook, Spark job, or batch to read or parse logs.
>     Read logs with `gcloud storage` / `gcloud logging` directly.
> -   **NEVER** download a whole event log into context. Event logs are
>     routinely hundreds of MB. Always filter, tail, or range-read.
> -   **Read-only first.** Prove the root cause before editing any code.
> -   **No invented evidence.** If logs are empty or metrics are unavailable,
>     say so and explain what you checked.

## Step 0: Verify the Environment

Run these checks before proposing any action. Every later step depends on them.

```bash
gcloud version
jq --version
curl --version
gcloud auth print-access-token > /dev/null && echo AUTH_OK
```

Pass/fail criteria:

-   `gcloud`, `jq`, and `curl` MUST each report a version. `jq` and `curl` are
    required for the Spark metrics API in Step 4. If either is missing, install
    it, or continue with log-based diagnosis only and say so explicitly.
-   The auth check MUST print `AUTH_OK`. If it does not, run `gcloud auth login`
    and re-run the check.
-   The project and region MUST be known. If the user did not supply them, read
    the default with `gcloud config get-value project` and confirm it.

## Step 1: Classify the Workload

The available diagnostics depend entirely on the workload type. Determine this
before gathering any evidence.

### Serverless batch

-   **Signal**: "batch", a batch ID, "serverless", no cluster mentioned.
-   **Diagnostics**: metadata, Cloud Logging, Spark metrics API, event log.

### Serverless session

-   **Signal**: "session", "Spark Connect", interactive use.
-   **Diagnostics**: same as a serverless batch, substituting `sessions` for
    `batches` in every API path.

### Cluster job (Dataproc on Compute Engine)

-   **Signal**: "cluster job", a job ID, a named cluster.
-   **Diagnostics**: metadata, Cloud Logging, driver output in Cloud Storage.
-   **Limitation**: the Spark metrics API does NOT exist for cluster jobs.

### Direct log URI

-   **Signal**: only a `gs://` or `https://storage.googleapis.com/...` URI.
-   **Diagnostics**: go straight to `references/spark_logs.md`.

> [!IMPORTANT]
>
> The Spark metrics API (`sparkApplications.*`) exists **only** for serverless
> batches and sessions. For cluster jobs, the driver output file in Cloud
> Storage is the primary evidence.

## Step 2: Fetch Metadata and Check the Quick Win

Prefer Dataproc MCP tools (`get_batch`, `get_job`, `list_batches`) when they are
registered in the environment; otherwise use gcloud:

```bash
# Serverless batch
gcloud dataproc batches describe BATCH_ID --region=REGION

# Cluster job
gcloud dataproc jobs describe JOB_ID --region=REGION
```

Read `stateMessage` (batches) or `status.details` (jobs) **before anything
else**. It frequently contains the verbatim error — `ValueError`,
`AnalysisException`, `PATH_NOT_FOUND`, `OutOfMemoryError` — and is the single
fastest path to a diagnosis.

Also record, for later steps:

-   `createTime` and `stateTime` — the time window for log queries.
-   `runtimeInfo.outputUri` — the driver console output (`driveroutput.*`
    shards) and event log location. This exists for **serverless batches too**,
    not only cluster jobs.
-   `driverOutputResourceUri` (cluster jobs) — the driver console output.
-   `runtimeConfig.properties` — the **submit-time** settings, so you don't
    recommend a setting that is already enabled.
-   `pysparkBatch.mainPythonFileUri` or `sparkBatch.mainJarFileUri` +
    `mainClass` — the code under investigation.

> [!WARNING]
>
> `runtimeConfig.properties` is what was *requested*, not what Spark *ran with*.
> A `SparkSession.builder.config(...)` or `SparkConf().set(...)` call in the
> application silently overrides it, so a batch advertising
> `spark.executor.memory: 9600m` may have executed with `1024m`. Before you
> reason about memory, cores, partitions, or AQE, confirm the effective values
> with `:accessEnvironmentInfo` (see `references/spark_metrics_api.md`).

## Step 3: Gather Log Evidence

Follow `references/spark_logs.md`. In short:

-   **Serverless**: driver and executor output go to **Cloud Logging**. Query
    `resource.type="cloud_dataproc_batch"`, starting at `severity>=ERROR`, then
    widen — Python tracebacks and the real root-cause exception are very often
    logged at INFO or with no severity at all. Prefer a substring filter
    (`AND ("Traceback" OR "Exception")`) over a large `--limit`.
    Serverless batches **also** write `driveroutput.*` shards to
    `runtimeInfo.outputUri`; these are usually a few KB and contain the driver
    traceback verbatim, so they are often the fastest evidence of all.
-   **Cluster jobs**: read `driverOutputResourceUri` from Cloud Storage; tail it
    first.
-   **Event logs / large files**: filter server-side or byte-range read. Never
    `cat` the whole thing.

## Step 4: Analyze Stage Metrics (serverless only)

Follow `references/spark_metrics_api.md` to pull application, executor, and
stage-level metrics and evaluate the diagnostic rules (GC pressure, spill, task
skew, stragglers, partition sizing, scan explosion).

This is what distinguishes "the job failed" from "stage 7 processed one 40 GB
partition while the other 199 tasks idled". Do this whenever the workload is a
serverless batch or session, even if the log already shows an exception —
performance symptoms often explain *why* the exception happened.

## Step 5: Retrieve the Source (Source of Truth)

The code that actually ran lives in Cloud Storage, not necessarily in the user's
workspace.

```bash
gcloud storage cat gs://BUCKET/scripts/job.py
```

Do **not** assume local files match the deployed artifact without checking. For
JAR workloads, note `mainClass` and ask the user for the source if the class
cannot be inspected — do not download and attempt to decompile large archives.

## Step 6: Root Cause Analysis

Correlate log errors, stage metrics, and code. Consult
`references/failure_scenarios.md`, which covers the recurring failure families:
driver and executor OOM, data skew, schema and type errors, serialization and
pickling errors, Python UDF exceptions, missing paths, and dependency errors.

Pinpoint the specific line or configuration responsible. Distinguish
environment-specific causes:

-   **Serverless**: dynamic allocation limits, default ~9.6 GB per
    driver/executor, VPC egress, pre-installed runtime packages.
-   **Cluster**: spot VM preemption, YARN container bounds, local disk
    exhaustion, master/worker sizing.

## Step 7: Explain and Propose a Fix

-   State the root cause, citing the specific log line, stage ID, metric value,
    and code snippet that supports it.
-   Propose a concrete fix: a code change, a Spark property, a partitioning
    change, or a resource change. Check `runtimeConfig.properties` first so you
    don't recommend something already set.
-   For serverless batches, when a SQL execution ID is available, you may also
    call `:computeTuningConfig` (see `references/spark_metrics_api.md`) to get
    the service's own tuning recommendation as corroborating evidence.
-   When the user asks you to implement the fix, use the `@skill:gcp-spark`
    skill for the code and submission conventions.
-   Synthesize findings directly in your response. Do not write a notebook or
    submit a job to analyze logs.

## Required Permissions

The caller needs, at minimum:

-   `roles/dataproc.viewer` — includes `dataproc.batches.get`,
    `dataproc.batches.sparkApplicationRead`.
-   `roles/logging.viewer` — `logging.logEntries.list`.
-   `roles/storage.objectViewer` on the staging/output bucket —
    `storage.objects.get`.

## References

-   `references/spark_logs.md` — Cloud Logging queries and safe patterns for
    reading driver output, executor logs, and event logs in Cloud Storage.
-   `references/spark_metrics_api.md` — the Spark metrics REST API, diagnostic
    rule catalog, SQL plan graphs, and tuning recommendations.
-   `references/failure_scenarios.md` — symptom-to-root-cause catalog for common
    Spark failures.
