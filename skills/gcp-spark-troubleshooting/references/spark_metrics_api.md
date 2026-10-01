# Spark Metrics API (Serverless Batches and Sessions)

Serverless for Apache Spark persists per-application Spark metrics and exposes
them through the public Dataproc v1 REST API under
`batches/BATCH_ID/sparkApplications/...`. This is how you get stages, task
quantiles, executor rollups, and SQL plan graphs without a Persistent History
Server.

> [!IMPORTANT]
>
> These endpoints exist **only** for serverless `batches` and `sessions`. There
> is no `sparkApplications` resource for Dataproc on Compute Engine cluster jobs
> — for those, use the driver output file (see `spark_logs.md`).

There is no `gcloud` surface and no MCP tool for these methods today. Call them
with `curl`.

## Setup

```bash
PROJECT=my-project
REGION=us-central1
BATCH=my-batch-id

BASE="https://${REGION}-dataproc.googleapis.com/v1"
PARENT="projects/${PROJECT}/locations/${REGION}/batches/${BATCH}"
AUTH="Authorization: Bearer $(gcloud auth print-access-token)"
```

For sessions, replace `/batches/` with `/sessions/` everywhere. Requires
`dataproc.batches.sparkApplicationRead` (included in `roles/dataproc.viewer`).

## Step 1: Resolve the Spark application

```bash
APP_ID=$(curl -s -H "$AUTH" \
  "${BASE}/${PARENT}/sparkApplications:search?pageSize=10" \
  | jq -r '.sparkApplications[0].application.applicationId')

APP="${PARENT}/sparkApplications/${APP_ID}"
```

> [!CAUTION]
>
> The identifier you need is `.application.applicationId` (for example
> `app-20260914223021794-0542`), **not** `.name`. The `name` field holds the
> human-readable application name — the same string as `spark.app.name` — and
> building the path from it produces a 404 on every subsequent call.

> [!WARNING]
>
> An empty `sparkApplications` list means this batch has no persisted Spark
> telemetry (very old batch, aged-out data, or a workload that never started a
> Spark context). This is **not** an error to report as "no data" — fall back to
> the event log in Cloud Storage (`spark_logs.md`).

Every subsequent call takes the application in the path **and** requires
`parent` as a query parameter. Passing only one of them fails.

## Step 2: Executor rollup

```bash
curl -s -H "$AUTH" "${BASE}/${APP}:summarizeExecutors?parent=${PARENT}" \
  | jq '.totalExecutorSummary'
```

Gives `totalTasks`, `failedTasks`, `totalDurationMillis`, `totalInputBytes`,
`totalGcTimeMillis`, `totalShuffleRead/Write`, `diskUsed`, `memoryUsed`. Cheap;
always call it first to decide whether a deeper stage sweep is warranted.

> [!TIP]
>
> Compare `count` against the requested `spark.executor.instances`. A rollup
> reporting six executors for a two-executor batch means four were lost and
> replaced — strong evidence of OOM kills or preemption, visible here before you
> look at a single stage.

## Step 2b: Confirm the effective configuration

```bash
curl -s -H "$AUTH" "${BASE}/${APP}:accessEnvironmentInfo?parent=${PARENT}" \
  | jq '.applicationEnvironmentInfo.sparkProperties
        | with_entries(select(.key | test("memory|cores|shuffle.partitions|adaptive|autoBroadcast")))'
```

> [!CAUTION]
>
> This, not `gcloud dataproc batches describe`, is the authoritative record of
> what Spark actually ran with. `runtimeConfig.properties` reports what was
> requested at *submit* time; any `SparkSession.builder.config(...)` or
> `SparkConf().set(...)` in the application silently overrides it.
>
> A batch whose metadata advertises `spark.executor.memory: 9600m` can genuinely
> execute with `1024m` because the script set it. Diagnosing memory pressure
> from the submit-time value will produce a confidently wrong answer, and
> recommending a property that the code already overrides wastes the fix.

## Step 3: Stages with task quantiles

```bash
curl -s -H "$AUTH" \
  "${BASE}/${APP}:searchStages?parent=${PARENT}&pageSize=100&summaryMetricsMask=task_quantile_metrics" \
  > stages.json
```

> [!CAUTION]
>
> **`summaryMetricsMask=task_quantile_metrics` is mandatory.** Without it the
> response contains no `taskQuantileMetrics` at all, and every skew, straggler,
> and partition-size rule below silently evaluates to "no violations". The mask
> value uses the proto field name (snake_case), not camelCase.

Other useful parameters:

-   `stageStatus=STAGE_STATUS_FAILED` — only failed stages. Also accepts
    `..._ACTIVE`, `..._COMPLETE`, `..._PENDING`, `..._SKIPPED`.
-   `pageSize` — default 10, **maximum 100**. Large applications must be paged
    via `nextPageToken`; do not assume one call returned everything.

> [!IMPORTANT]
>
> `searchStages` returns **one entry per stage attempt**, not per stage. A stage
> that Spark retried four times appears four times with the same `stageId` and
> a different `stageAttemptId`, usually repeating the same `failureReason`. Do
> not read this as four distinct failing stages, and do not sum task counts
> across them. Deduplicate on `stageId` — keeping the highest `stageAttemptId`
> — before reporting, and treat repeated attempts as themselves a signal that
> the stage is failing and being resubmitted.

## JSON gotchas before you write any filter

-   **`int64` fields are JSON strings.** `executorRunTimeMillis`,
    `jvmGcTimeMillis`, `memoryBytesSpilled`, `bytesRead`, `stageId`, and every
    `Quantiles` value arrive quoted. You must `tonumber` before comparing, or
    every threshold check will compare strings and produce nonsense.
-   **`int32` fields are JSON numbers**: `numTasks`, `numFailedTasks`,
    `numKilledTasks`.
-   **Zero-valued fields are omitted entirely.** Always default with `// 0`.
    This bites hardest on `stageId`: **stage 0 has no `stageId` key at all**, so
    a naive `.stageId` yields `null` and the stage appears unidentified.
    `numFailedTasks` and `numKilledTasks` are likewise absent — not `0` — on
    healthy stages.

Every filter below therefore opens with the helper `def n: (. // 0) |
tonumber;`. It is written inline, not stored in a shell variable, so each
command stays self-contained and survives a new shell.

## Diagnostic rule catalog

Run the whole sweep at once and report only what fires:

```bash
jq 'def n: (. // 0) | tonumber;
  [ .sparkApplicationStages[]
    | { id: (.stageId|n), tasks: .numTasks, failed: .numFailedTasks,
        killed: .numKilledTasks,
        run: (.stageMetrics.executorRunTimeMillis|n),
        gc:  (.stageMetrics.jvmGcTimeMillis|n),
        memSpill: (.stageMetrics.memoryBytesSpilled|n),
        diskSpill: (.stageMetrics.diskBytesSpilled|n),
        durMax: (.taskQuantileMetrics.durationMillis.maximum|n),
        durMed: (.taskQuantileMetrics.durationMillis.percentile50|n),
        inMax: (.taskQuantileMetrics.inputMetrics.bytesRead.maximum|n),
        inMed: (.taskQuantileMetrics.inputMetrics.bytesRead.percentile50|n),
        swMax: (.taskQuantileMetrics.shuffleWriteMetrics.writeBytes.maximum|n),
        swMed: (.taskQuantileMetrics.shuffleWriteMetrics.writeBytes.percentile50|n) }
    | { stage: .id, findings: ([
        (if .failed > 0 then "HIGH_TASK_FAILURE_RATE" else empty end),
        (if .killed > 0 then "KILLED_TASKS (preemption or OOM)" else empty end),
        (if .run > 0 and (.gc / .run) > 0.1 then "HIGH_GC_RATIO" else empty end),
        (if .memSpill > 0 then "MEMORY_SPILL" else empty end),
        (if .diskSpill > 1073741824 then "EXCESSIVE_DISK_SPILL_1GB"
         elif .diskSpill > 0 then "DISK_SPILL" else empty end),
        (if .durMed > 0 and (.durMax / .durMed) > 5 then "TASK_DURATION_SKEW" else empty end),
        (if .inMed > 0 and (.inMax / .inMed) > 5 then "TASK_INPUT_SKEW" else empty end),
        (if .inMax > 524288000 then "LARGE_INPUT_PARTITION_500MB" else empty end),
        (if .swMax > 524288000 then "LARGE_SHUFFLE_PARTITION_500MB" else empty end),
        (if .tasks > 10000 and .durMed > 0 and .durMed < 100 then "TOO_MANY_SMALL_TASKS" else empty end),
        (if .tasks > 80000 then "HIGH_SCAN_TASK_COUNT" else empty end)
      ]) }
    | select(.findings | length > 0) ]' stages.json
```

Thresholds and their interpretation, one entry per finding:

-   **`HIGH_TASK_FAILURE_RATE`**
    -   Threshold: `numFailedTasks > 0`.
    -   Interpretation: real failures. Pair with the exception in the logs.
-   **`KILLED_TASKS`**
    -   Threshold: `numKilledTasks > 0`.
    -   Interpretation: executor loss from an OOM kill, preemption, or heartbeat
        timeout.
-   **`HIGH_GC_RATIO`**
    -   Threshold: GC time over run time > 10%.
    -   Interpretation: memory pressure. Raise executor memory or reduce
        per-task data.
-   **`MEMORY_SPILL` and `DISK_SPILL`**
    -   Threshold: any bytes spilled.
    -   Interpretation: the working set exceeds execution memory.
-   **`EXCESSIVE_DISK_SPILL_1GB`**
    -   Threshold: more than 1 GiB spilled to disk.
    -   Interpretation: severe. Usually under-partitioning or a skewed join.
-   **`TASK_DURATION_SKEW`**
    -   Threshold: maximum duration > 5x the median.
    -   Interpretation: if input is NOT also skewed, suspect contention or
        external calls rather than data skew.
-   **`TASK_INPUT_SKEW`**
    -   Threshold: maximum input > 5x the median.
    -   Interpretation: data skew. Salt keys, enable AQE, or repartition.
-   **`LARGE_INPUT_PARTITION_500MB`**
    -   Threshold: maximum task input > 500 MB.
    -   Interpretation: increase the partition count or reduce the split size.
-   **`LARGE_SHUFFLE_PARTITION_500MB`**
    -   Threshold: maximum shuffle write > 500 MB.
    -   Interpretation: increase `spark.sql.shuffle.partitions`.
-   **`TOO_MANY_SMALL_TASKS`**
    -   Threshold: more than 10,000 tasks with a median duration under 100 ms.
    -   Interpretation: overhead-dominated. Typically a small-files problem.
-   **`HIGH_SCAN_TASK_COUNT`**
    -   Threshold: more than 80,000 tasks.
    -   Interpretation: scan parallelism far beyond what is useful.

Combine findings before concluding: duration skew **with** input skew is data
skew; duration skew **without** input skew points to resource contention,
external RPC latency, or lock contention. High GC **with** large peak execution
memory is memory pressure rather than a partitioning problem.

> [!CAUTION]
>
> **A stage that died does not report what killed it.** Task metrics are
> recorded on task *completion*, so a task killed by an executor OOM contributes
> nothing: `peakExecutionMemoryBytes`, spill, and input quantiles all collapse
> toward zero. A stage can show a 15 MB peak and no spill and still have failed
> with `java.lang.OutOfMemoryError`.
>
> Therefore **low memory metrics never rule out OOM**. Whenever
> `HIGH_TASK_FAILURE_RATE` or `KILLED_TASKS` fires, the metrics describe only
> the tasks that survived — go to the logs (`spark_logs.md`) for the cause, and
> do not report the stage as healthy on the strength of its quantiles.
>
> `MetadataFetchFailedException` / "Missing an output location for shuffle" in
> `failureReason` is a *downstream* symptom of this: an executor died and took
> its shuffle output with it. Diagnose the executor loss, not the fetch.

## Drill down into one stage

```bash
curl -s -H "$AUTH" \
  "${BASE}/${APP}:accessStageAttempt?parent=${PARENT}&stageId=7&stageAttemptId=0&summaryMetricsMask=task_quantile_metrics"

# Individual tasks in a stage attempt: can be tens of thousands. Always page.
curl -s -H "$AUTH" \
  "${BASE}/${APP}:searchStageAttemptTasks?parent=${PARENT}&stageId=7&stageAttemptId=0&pageSize=100"
```

`StageData.failureReason` on a failed stage usually carries the exception that
killed it; read it before pulling tasks.

## SQL plan graph

Two calls — the plan graph is per *SQL execution*, not per application:

```bash
# 1. Find execution IDs.
curl -s -H "$AUTH" "${BASE}/${APP}:searchSqlQueries?parent=${PARENT}&pageSize=100" \
  | jq '.sparkApplicationSqlQueries[] | {executionId, description, errorMessage}'

# 2. Fetch the plan graph for one of them.
curl -s -H "$AUTH" "${BASE}/${APP}:accessSqlPlan?parent=${PARENT}&executionId=3" \
  | jq '.sparkPlanGraph.nodes[] | {sparkPlanGraphNodeId, name}'
```

The graph is capped at 10,000 clusters and is far too large to put in context
raw. Project to node names and the one or two metrics you care about, or filter
to join/exchange/scan nodes. Use `planDescription=true` on `searchSqlQueries`
only when you specifically need the physical plan text.

## Autotuning recommendation (optional)

```bash
curl -s -H "$AUTH" \
  "${BASE}/${APP}:computeTuningConfig?parent=${PARENT}&executionId=3&semanticQueryId=SEMANTIC_QUERY_ID"
```

This is scoped to a single SQL execution and requires both `executionId` and
`semanticQueryId`. Treat it as corroborating evidence when those identifiers are
available; do not block an RCA on it.

## Response-size discipline

-   Always `jq`-project before reading a response into your analysis. A raw
    100-stage response with quantiles is hundreds of KB.
-   Page with `nextPageToken` rather than raising `pageSize` past 100 (the
    server caps it).
-   Write large intermediate responses to a temp file and filter the file,
    instead of re-fetching.

## Field reference

JSON paths, relative to a single entry in `.sparkApplicationStages[]`:

-   **Stage identity**: `stageId`, `stageAttemptId`, `status`, `name`,
    `failureReason`.
-   **Task counts**: `numTasks`, `numCompleteTasks`, `numFailedTasks`,
    `numKilledTasks`.
-   **CPU and GC**: `stageMetrics.executorRunTimeMillis`,
    `stageMetrics.jvmGcTimeMillis`.
-   **Spill**: `stageMetrics.memoryBytesSpilled`,
    `stageMetrics.diskBytesSpilled`.
-   **Peak memory**: `stageMetrics.peakExecutionMemoryBytes`.
-   **I/O**: `stageMetrics.stageInputMetrics.bytesRead`,
    `stageMetrics.stageOutputMetrics.bytesWritten`.
-   **Shuffle**: `stageMetrics.stageShuffleReadMetrics.bytesRead`,
    `stageMetrics.stageShuffleWriteMetrics.bytesWritten`,
    `stageMetrics.stageShuffleWriteMetrics.writeTimeNanos`.
-   **Task quantiles**: `taskQuantileMetrics.durationMillis`,
    `taskQuantileMetrics.jvmGcTimeMillis`,
    `taskQuantileMetrics.memoryBytesSpilled`,
    `taskQuantileMetrics.diskBytesSpilled`,
    `taskQuantileMetrics.peakExecutionMemoryBytes`.
-   **Quantile I/O**: `taskQuantileMetrics.inputMetrics.bytesRead`,
    `taskQuantileMetrics.outputMetrics.bytesWritten`,
    `taskQuantileMetrics.shuffleWriteMetrics.writeBytes`,
    `taskQuantileMetrics.shuffleReadMetrics.readBytes`.
-   **Quantile values**: every quantile object above exposes `.minimum`,
    `.percentile25`, `.percentile50`, `.percentile75`, `.maximum`, `.sum`, and
    `.count`.
