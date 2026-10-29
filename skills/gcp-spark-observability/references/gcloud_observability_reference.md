# gcloud Dataproc & Spark Observability Reference

Concise `gcloud` commands and field paths for observing Dataproc Serverless
(batches, sessions) and Dataproc on Compute Engine (clusters, jobs, operations).

---

## 1. Region Resolution & Multi-Region Discovery

```bash
# Default project and single-region config
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION=$(gcloud config get-value dataproc/region 2>/dev/null)
[ -z "$REGION" ] || [ "$REGION" = "(unset)" ] && REGION=$(gcloud config get-value compute/region 2>/dev/null)

# Project-wide region discovery via Cloud Asset Inventory (use locations to query live APIs)
gcloud asset search-all-resources --scope="projects/${PROJECT_ID}" \
  --asset-types="dataproc.googleapis.com/Cluster,dataproc.googleapis.com/Batch,dataproc.googleapis.com/Session,dataproc.googleapis.com/Job,dataproc.googleapis.com/WorkflowTemplate,dataproc.googleapis.com/AutoscalingPolicy,metastore.googleapis.com/Service" \
  --limit=200 --format="table(name.basename(),assetType,location,state,createTime)" --quiet

# Fallback region discovery via Cloud Logging if Asset API is unavailable
gcloud logging read 'resource.type=("cloud_dataproc_batch" OR "cloud_dataproc_cluster" OR "cloud_dataproc_job" OR "cloud_dataproc_session")' \
  --project="${PROJECT_ID}" --freshness=30d --limit=200 \
  --format="value(resource.type,resource.labels.region,resource.labels.location)"
```

---

## 2. Active Fleet & Environment Inventory (All 4 Surfaces)

Always inspect all 4 active workload surfaces per region (`batches`, `sessions`,
`clusters`, `jobs`) and always pass `--limit`:

```bash
for REGION in us-central1 asia-east1; do
  echo "=== ${REGION} ==="
  # 1. Serverless Batches
  gcloud dataproc batches list --region="${REGION}" \
    --filter="state=RUNNING OR state=PENDING OR state=CANCELLING" --limit=100 \
    --format="table(name.basename():label=BATCH,state,creator,createTime)"
  # 2. Serverless Interactive Sessions (requires beta + --location)
  gcloud beta dataproc sessions list --location="${REGION}" \
    --filter="state=ACTIVE OR state=CREATING" --limit=100 \
    --format="table(name.basename():label=SESSION,state,creator,createTime)"
  # 3. Dataproc Clusters
  gcloud dataproc clusters list --region="${REGION}" \
    --filter="status.state=RUNNING OR status.state=CREATING OR status.state=UPDATING OR status.state=STARTING" --limit=100 \
    --format="table(clusterName,status.state,labels.owner:label=OWNER,status.stateStartTime)"
  # 4. Active Cluster Jobs
  gcloud dataproc jobs list --region="${REGION}" --state-filter=active --limit=100 \
    --format="table(reference.jobId,placement.clusterName,status.state,status.stateStartTime)"
done

# Supporting environment resources (templates, autoscaling policies, Metastore)
gcloud beta dataproc session-templates list --location="${REGION}" --limit=50 --format="table(name.basename(),createTime,updateTime)"
gcloud dataproc workflow-templates list --region="${REGION}" --limit=50 --format="table(id,name.basename(),version,updateTime)"
gcloud dataproc autoscaling-policies list --region="${REGION}" --limit=50 --format="table(id,workerConfig.maxInstances,secondaryWorkerConfig.maxInstances)"
gcloud metastore services list --location="${REGION}" --limit=50 --format="table(name.basename(),state,tier,hiveMetastoreConfig.version)" --quiet
```

---

## 3. Failed Workloads & Scheduled Pipeline Cadence

```bash
# Most recent failed Serverless batches (supports server-side labels.<key>=<value> and snake_case create_time)
gcloud dataproc batches list --region="${REGION}" \
  --filter='state=FAILED AND create_time>="2026-10-01T00:00:00Z"' --sort-by=~createTime --limit=20 \
  --format="table(name.basename():label=BATCH,state,createTime,stateTime,creator,stateMessage)"

# Filter failed batches by workload label (evaluated server-side before --limit)
gcloud dataproc batches list --region="${REGION}" \
  --filter="state=FAILED AND labels.task=revenue_analysis" --sort-by=~createTime --limit=20 \
  --format="table(name.basename():label=BATCH,state,createTime,stateTime,labels.task,stateMessage)"

# Failed cluster jobs (API rejects status.state=ERROR; list inactive and filter ERROR with awk)
gcloud dataproc jobs list --region="${REGION}" --state-filter=inactive --limit=200 \
  --format="value(reference.jobId,placement.clusterName,status.state,status.stateStartTime)" | awk -F'\t' '$3=="ERROR"'
gcloud dataproc jobs describe <JOB_ID> --region="${REGION}" --format="yaml(reference,placement,status)"

# Recurring batch runs & orchestrator labels for cadence/duration health
gcloud dataproc batches list --region="${REGION}" --sort-by=~createTime --limit=200 \
  --format="table(name.basename():label=BATCH,state,createTime,stateTime,labels.'airflow-dag-id':label=DAG,labels.'airflow-task-id':label=TASK,labels.'goog-dataproc-workflow-template-id':label=WF_TEMPLATE,labels.'goog-orchestration-pipeline-id':label=ORCH_PIPELINE,creator)"
```

* **Cadence grouping:** group runs by `labels.airflow-dag-id`/`airflow-task-id`
  (Composer batches), `labels.goog-dataproc-workflow-template-id` (Workflow
  Templates), `labels.goog-orchestration-pipeline-id`/
  `goog-orchestration-model-id` or `labels.dcs_pipeline_id`/`dcs_task_id` (DCS
  Serverless Orchestration), custom pipeline labels, or batch-ID prefix (strip
  trailing run hash/timestamp). Compute median runtime
  (`stateTime - createTime`) and median interval between `createTime` values to
  flag missed runs (`> 1.5x` median interval) or runtime regressions.
* **Safe cancellation (only after explicit user confirmation):**
  * Stop running batch:
    `gcloud dataproc batches cancel <BATCH_ID> --region=<REGION>`
    (`batches delete` only deletes terminal records).
  * Kill running job: `gcloud dataproc jobs kill <JOB_ID> --region=<REGION>`.
  * Terminate active session:
    `gcloud beta dataproc sessions terminate <SESSION_ID> --location=<REGION>`.

---

## 4. Serverless Usage (DCU-Hours), Idle Clusters & Config Audit

* **Formulas:**
  $\text{DCU-Hours} = \text{milliDcuSeconds} / 3{,}600{,}000$,
  $\text{Shuffle-GB-Months} = \text{shuffleStorageGbSeconds} / 2{,}592{,}000$.

```bash
# Top Serverless compute consumers (completed batches sorted numerically by milliDcuSeconds)
gcloud dataproc batches list --region="${REGION}" \
  --filter='(state=SUCCEEDED OR state=FAILED OR state=CANCELLED) AND create_time>="2026-10-01T00:00:00Z"' \
  --sort-by=~runtimeInfo.approximateUsage.milliDcuSeconds --limit=20 \
  --format="table(name.basename():label=BATCH,state,createTime,runtimeInfo.approximateUsage.milliDcuSeconds:label=MILLI_DCU_SECONDS,runtimeInfo.approximateUsage.shuffleStorageGbSeconds:label=SHUFFLE_GB_SECONDS)"

# Running batches usage snapshot (currentUsage, not approximateUsage)
gcloud dataproc batches list --region="${REGION}" --filter="state=RUNNING OR state=PENDING" --limit=100 \
  --format="table(name.basename():label=BATCH,state,createTime,runtimeInfo.currentUsage.milliDcu:label=MILLI_DCU_NOW,runtimeInfo.currentUsage.shuffleStorageGb:label=SHUFFLE_GB_NOW)"

# Idle / zombie cluster audit (sizing, YARN activity snapshot, and lifecycle TTLs in one call)
gcloud dataproc clusters list --region="${REGION}" --filter="status.state=RUNNING" --limit=100 \
  --format="table(clusterName,status.stateStartTime:label=RUNNING_SINCE,config.masterConfig.numInstances:label=M,config.workerConfig.numInstances:label=W,config.secondaryWorkerConfig.numInstances:label=SW,metrics.yarnMetrics.'yarn-apps-running':label=YARN_RUN,metrics.yarnMetrics.'yarn-apps-pending':label=YARN_PEND,metrics.yarnMetrics.'yarn-memory-mb-allocated':label=YARN_MEM_MB,config.lifecycleConfig.idleDeleteTtl:label=IDLE_DEL_TTL,config.lifecycleConfig.autoDeleteTime:label=AUTO_DEL_TIME,config.lifecycleConfig.idleStopTtl:label=IDLE_STOP_TTL,config.lifecycleConfig.idleStartTime:label=IDLE_SINCE)"

# Most recent jobs per cluster + STOPPED clusters (disk-only cost)
gcloud dataproc jobs list --region="${REGION}" --cluster="${CLUSTER}" --sort-by=~status.stateStartTime --limit=5 \
  --format="table(reference.jobId,status.state,status.stateStartTime)"
gcloud dataproc clusters list --region="${REGION}" --filter="status.state=STOPPED" --limit=100 \
  --format="table(clusterName,status.stateStartTime:label=STOPPED_SINCE)"
```

* **Idle remediation (always report `config.lifecycleConfig` TTLs
  `idleDeleteTtl`/`idleStopTtl` and recommend only; never execute without
  confirmation):**
  `gcloud dataproc clusters update <CLUSTER> --region=<REGION> --max-idle=30m`
  (or `--stop-max-idle=30m` / `--delete-max-idle=30m`).
* **Key config fields to audit (`describe --format=json`):**
  * Serverless (`batches`/`sessions`): `runtimeConfig.version`,
    `runtimeConfig.properties` (`dataproc:dataproc.tier`,
    `spark:spark.dataproc.engine`, `spark.dynamicAllocation.*`,
    `spark.sql.adaptive.enabled`), `runtimeConfig.autotuningConfig.scenarios`,
    `environmentConfig.executionConfig.idleTtl`/`ttl`,
    `environmentConfig.peripheralsConfig.sparkHistoryServerConfig`.
  * Clusters: `config.softwareConfig.imageVersion`, `config.clusterTier`,
    `config.lifecycleConfig.*`, `config.autoscalingConfig.policyUri`,
    `config.secondaryWorkerConfig.preemptibility`,
    `config.*Config.diskConfig` (`bootDiskType`, `numLocalSsds`),
    `config.endpointConfig.enableHttpPortAccess`.
  * Workload-level tuning: hand off individual top-DCU or slow workloads to
    `@skill:gcp-spark-troubleshooting`.

---

## 5. Failed Cluster Operations, Stockouts, Quotas & Alerts

```bash
# Failed control-plane CREATE operations (server-side filter operationType=CREATE AND status.state=DONE + --limit=100)
gcloud dataproc operations list --region="${REGION}" \
  --filter="operationType=CREATE AND status.state=DONE" --limit=100 \
  --format="value(name.basename(),metadata.operationType,metadata.clusterName,status.stateStartTime,error.code,error.message)" \
  | awk -F'\t' '$5!=""'
gcloud dataproc operations describe <OP_ID> --region="${REGION}" --format="yaml(metadata,error)"

# Zonal stockout errors in Admin Activity audit logs across all regions
gcloud logging read '"does not have enough resources available"' --project="${PROJECT_ID}" --freshness=14d --limit=20 \
  --format="table(timestamp,resource.labels.cluster_name,resource.labels.region,protoPayload.status.message)"

# Regional Compute Engine quotas (flag usage/limit > 80%; 9.22337e+18 = 2^63 means unlimited)
gcloud compute regions list --project="${PROJECT_ID}" --flatten=quotas --limit=100 \
  --filter="name=${REGION} AND quotas.metric=(CPUS N2_CPUS N2D_CPUS E2_CPUS C2_CPUS PREEMPTIBLE_CPUS DISKS_TOTAL_GB SSD_TOTAL_GB LOCAL_SSD_TOTAL_GB IN_USE_ADDRESSES)" \
  --format="table(name:label=REGION,quotas.metric:label=METRIC,quotas.usage:label=USAGE,quotas.limit:label=LIMIT)"

# Dataproc Serverless DCU quota per region (alpha track)
gcloud alpha services quota list --service=dataproc.googleapis.com --consumer="projects/${PROJECT_ID}" \
  --filter="metric=dataproc.googleapis.com/data_compute_units" --flatten="consumerQuotaLimits[].quotaBuckets[]" --limit=100 \
  --format="table(consumerQuotaLimits.quotaBuckets.dimensions.region:label=REGION,consumerQuotaLimits.quotaBuckets.effectiveLimit:label=EFFECTIVE_LIMIT)" --quiet

# Cloud Monitoring alerting policies covering Dataproc
gcloud monitoring policies list --project="${PROJECT_ID}" --limit=100 --format="json(name,displayName,enabled,conditions)"
```

---

## 6. Cloud Monitoring Metrics & Cloud Logging

* **Key Dataproc, Spark & Orchestration metrics:**
  * Serverless (`cloud_dataproc_batch`, `cloud_dataproc_session`):
    `dataproc.googleapis.com/{batch,session}/spark/executors` (`status` =
    `running`, `pending-delete`, `required`, `maximum-needed`, `target`),
    `dataproc.googleapis.com/{batch,session}/operation/{completed_by_terminal_state,failed,start_latency,gce_creation_latency}`
    (`terminal_state`, `error_code`, `error_source`). Note: internal
    `dataproc.googleapis.com/{spark,run}/*` metrics are `is_public = false` and
    are never queryable in customer Cloud Monitoring.
  * Clusters (`cloud_dataproc_cluster`):
    `dataproc.googleapis.com/cluster/yarn/allocated_memory_percentage`,
    `cluster/yarn/pending_memory_size`, `cluster/yarn/apps` (`status` =
    `running`, `pending`, `failed`), `cluster/yarn/nodemanagers` (`status` =
    `active`, `lost`, `unhealthy`),
    `cluster/nodes/{active_count,decommissioned_count,yarn_decommissioning_count}`,
    `cluster/hdfs/{storage_utilization,unhealthy_blocks}`,
    `cluster/job/{submitted_count,running_count,completed_count,failed_count,duration}`,
    `cluster/operation/failed_count`, and cluster-scoped
    `dataproc.googleapis.com/node/{problem_count,problem_state}` (`reason` =
    `OOM` | `ShuffleReadError` | `LateCheckin` | `Preempted`; lacks `job_id`, so
    correlate by timestamp window on shared clusters).
  * Cluster Jobs (`cloud_dataproc_job`): `dataproc.googleapis.com/job/state`
    (`state`), `dataproc.googleapis.com/job/yarn/vcore_seconds` (BETA, per
    `application_id`), `dataproc.googleapis.com/job/yarn/memory_seconds` (BETA,
    per `application_id`).
  * Spark & VM host time series: on Serverless Runtime `>= 3.0` (OpenTelemetry,
    controlled via `spark.dataproc.{driver,executor,system}.metrics`), exported
    under `workload.googleapis.com/spark/driver/*` (`DAGScheduler/*`,
    `BlockManager/*`, `JVMCPU/jvmCpuTime`, `ExecutorAllocationManager/*`),
    `workload.googleapis.com/spark/executor/*` (`runTime`, `jvmGCTime`,
    `JVMCPU/jvmCpuTime`, `bytesRead`, `bytesWritten`, `recordsRead`,
    `recordsWritten`, `memoryBytesSpilled`, `diskBytesSpilled`, `shuffle*`,
    `ExecutorMetrics/JVMHeapMemory`, `ExecutorMetrics/JVMOffHeapMemory`, labeled
    by `executor_id`), and `workload.googleapis.com/system.*` (`node` ending
    `-m` for driver vs `-w-*` for executors). On Serverless Runtime `1.x`/`2.x`
    and opt-in clusters (`--metric-sources=spark`), exported under
    `custom.googleapis.com/spark/...`.
  * DCS Serverless Orchestration (`orchestration.googleapis.com/Pipeline`,
    labels: `resource_container`, `location`, `pipeline_id`):
    `orchestration.googleapis.com/pipeline/{run_count,run_durations,model_execution_count,model_execution_durations}`
    (plus `action_execution_{count,durations}` when publicly exposed).
    Orchestration does not duplicate low-level Spark metrics; correlate
    downstream Spark runs via `labels.goog-orchestration-*` or
    `labels.dcs_{pipeline_id,version_id,run_id,task_id,sdp_dataset}` on
    batches/jobs, or `jsonPayload.external_job_reference` in
    `orchestration.googleapis.com%2F{action_execution_activity,model_execution_activity}`
    logs.

```bash
# Query Cloud Monitoring time series via REST (use application-default token)
FILTER='metric.type="dataproc.googleapis.com/cluster/yarn/allocated_memory_percentage" AND resource.labels.cluster_name="my-cluster"'
curl -sS -G "https://monitoring.googleapis.com/v3/projects/${PROJECT_ID}/timeSeries" \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  --data-urlencode "filter=${FILTER}" \
  --data-urlencode "interval.startTime=2026-10-23T00:00:00Z" \
  --data-urlencode "interval.endTime=2026-10-23T18:00:00Z" \
  --data-urlencode "aggregation.alignmentPeriod=300s" \
  --data-urlencode "aggregation.perSeriesAligner=ALIGN_MEAN"

# Cloud Logging: batch/cluster errors, autoscaler decisions, Spot VM preemptions, orchestration, and audit trail
gcloud logging read 'resource.type="cloud_dataproc_batch" AND resource.labels.batch_id="<BATCH_ID>" AND severity>=ERROR' \
  --project="${PROJECT_ID}" --limit=50 --format="table(timestamp,severity,jsonPayload.message,textPayload)"
gcloud logging read 'logName:"dataproc.googleapis.com%2Fautoscaler" AND (resource.labels.batch_id="<BATCH_ID>" OR resource.labels.cluster_name="<CLUSTER>")' \
  --project="${PROJECT_ID}" --limit=50 --format="table(timestamp,jsonPayload.scalingDecisionType,jsonPayload.scalingReason,jsonPayload.message)"
gcloud logging read 'logName:"cloudaudit.googleapis.com%2Fsystem_event" AND (protoPayload.methodName="compute.instances.preempted" OR protoPayload.serviceName="dataprocrm.googleapis.com")' \
  --project="${PROJECT_ID}" --freshness=7d --limit=50 --format="table(timestamp,protoPayload.methodName,protoPayload.resourceName)"
gcloud logging read 'resource.type="orchestration.googleapis.com/Pipeline" AND resource.labels.pipeline_id="<PIPELINE_ID>"' \
  --project="${PROJECT_ID}" --limit=50 --format="table(timestamp,labels.pipeline_run_id,labels.engine,labels.state,jsonPayload.external_job_reference,jsonPayload.duration_seconds)"
gcloud logging read 'logName:"cloudaudit.googleapis.com%2Factivity" AND protoPayload.serviceName="dataproc.googleapis.com"' \
  --project="${PROJECT_ID}" --freshness=7d --limit=50 \
  --format="table(timestamp,protoPayload.methodName,protoPayload.authenticationInfo.principalEmail,resource.labels.region,protoPayload.resourceName,protoPayload.status.message)"
```

---

## 7. Workload & Ingestion Key Metrics Extraction

When answering questions about a workload's or pipeline's key metrics (duration,
compute usage, rows/bytes read & written, file/partition counts, source/sink
schemas, shuffle/spill/GC, peak memory, or partition skew), combine **Dataproc
control-plane metadata**, **Spark application / event-log telemetry** (via
`@skill:gcp-spark-troubleshooting` helper scripts), and **source/sink storage
metadata**:

### A. Control-Plane Duration & Resource Usage

```bash
# 1. Serverless Batch (or beta sessions describe --location=...)
gcloud dataproc batches describe "<BATCH_ID>" --region="${REGION}" --project="${PROJECT_ID}" --format=json
# Extract:
# - Total elapsed time: stateTime - createTime
# - Active RUNNING wall-clock: stateTime - stateHistory[state=="RUNNING"].stateStartTime
# - Startup overhead: RUNNING.stateStartTime - createTime (also tracked in batch/operation/start_latency)
# - Compute & shuffle usage: runtimeInfo.approximateUsage.{milliDcuSeconds, shuffleStorageGbSeconds}
#   (DCU-Hours = milliDcuSeconds / 3600000; Shuffle-GB-Months = shuffleStorageGbSeconds / 2592000)

# 2. Dataproc GCE Cluster Job (persists even after ephemeral cluster deletion)
gcloud dataproc jobs describe "<JOB_ID>" --region="${REGION}" --project="${PROJECT_ID}" --format=json
# Extract:
# - Active RUNNING wall-clock: status.stateStartTime - statusHistory[state=="RUNNING"].stateStartTime
# - YARN resource consumption: yarnApplications[].{vcoreSeconds, memoryMbSeconds, state, trackingUrl}
# - Spark application ID: trailing application_<ts>_<id> segment of yarnApplications[].trackingUrl
```

### B. Spark Stage, SQL Operator, Peak Memory, Schema & Partition Skew Telemetry

* **Dataproc Serverless (`batches` / `sessions`):** activate
  `@skill:gcp-spark-troubleshooting` first to get its resolved skill directory
  (`<TROUBLESHOOTING_SKILL_DIR>`; do not search symlinked skill directories with
  `find` without `-L`), then run `scripts/spark_applications.py` (works after
  completion without a History Server):
  ```bash
  # App attempt duration, jobs/stages/tasks, cores/maxTasks, GC overhead %, dead executors
  python3 <TROUBLESHOOTING_SKILL_DIR>/scripts/spark_applications.py --project="${PROJECT_ID}" --region="${REGION}" --batch-id="<BATCH_ID>" --action=summary
  # Per-stage & summed I/O + task duration/partition skew table (stage_skew_score & job_skew_score)
  python3 <TROUBLESHOOTING_SKILL_DIR>/scripts/spark_applications.py --project="${PROJECT_ID}" --region="${REGION}" --batch-id="<BATCH_ID>" --action=stages --quantiles
  # Per-executor Cores (maxTasks) & Peak Heap / Off-Heap (JVMHeapMemory/JVMOffHeapMemory; storage memoryUsed is 0% unless RDDs are cached)
  python3 <TROUBLESHOOTING_SKILL_DIR>/scripts/spark_applications.py --project="${PROJECT_ID}" --region="${REGION}" --batch-id="<BATCH_ID>" --action=executors
  # SQL execution durations, join counts, operator I/O metrics, and Source & Sink Operator Schemas
  python3 <TROUBLESHOOTING_SKILL_DIR>/scripts/spark_applications.py --project="${PROJECT_ID}" --region="${REGION}" --batch-id="<BATCH_ID>" --action=sql
  python3 <TROUBLESHOOTING_SKILL_DIR>/scripts/spark_applications.py --project="${PROJECT_ID}" --region="${REGION}" --batch-id="<BATCH_ID>" --action=sql --execution-id=0
  ```
  * **Normalized skew & worker utilization formulas:**
    `stage_skew_score = max(0, T_max / (5 * max(T_median, 1ms)) - 1)` (`> 0`
    indicates tasks exceeding `5x` median; `job_skew_score` weights completed
    stages by stage duration);
    `worker_utilization_pct = (sum(activeTasks) / sum(maxTasks)) * 100` (`< 40%`
    indicates over-provisioning).
* **Dataproc GCE Cluster Jobs (including deleted clusters):** locate the Spark
  event log from `spark:spark.eventLog.dir` (in job/cluster properties) or
  `gcloud storage ls "gs://<BUCKET>/**/*application_<ts>_<id>*"`, activate
  `@skill:gcp-spark-troubleshooting`, and run `scripts/spark_gcs_log_reader.py`:
  ```bash
  python3 <TROUBLESHOOTING_SKILL_DIR>/scripts/spark_gcs_log_reader.py --uri="gs://<BUCKET>/<PATH>/application_<ts>_<id>" --action=summarize_events
  # Supports single-file (.zstd/.gz/plain) and rolling eventlog_v2_application_<ts>_<id> shards;
  # reports Spark app duration, executors/cores, peak JVMHeap/JVMOffHeap/PyRSS memory,
  # deduplicated task-summed input/output/shuffle bytes & rows, GC %, stage_skew_score & job_skew_score,
  # SQL operator metrics + source/sink column schemas, and Spark Connect / SDP operations.
  ```

### C. Connector, Pushdown, Construct Artifacts & Failed-Run Precedence Rules

1. **DataSourceV2, `spark-bigquery-connector` & `avg file size written`:**
   Spark Hadoop RDD counters (`stageInputMetrics.bytesRead`,
   `stageOutputMetrics.bytesWritten`/`recordsWritten`) report `0 B` on
   DataSourceV2 scans (`BatchScan` BigQuery Storage Read, Iceberg) and
   `SaveIntoDataSourceCommand` writes (`spark-bigquery-connector` Direct V2).
   In addition, Spark's `BasicWriteJobStatsTracker` declares `avg file size
   written` as a `size`-summed accumulator across tasks/driver, inflating its
   `total` on multi-file writes — always compute true average file size as
   `written output / number of written files`. Inspect
   `--action=sql --execution-id=<ID>` **and** verify storage metadata directly:
   * **BigQuery table:**
     `bq show --project_id="${PROJECT_ID}" --format=json <DATASET>.<TABLE>`
     (`numRows`, `numBytes`, and `schema.fields` column count/names).
   * **BigLake Iceberg REST catalog table:**
     `gcloud biglake iceberg tables describe <TABLE> --catalog=<CATALOG>`
     `--namespace=<NAMESPACE> --project="${PROJECT_ID}" --format=json`
     (`metadata.snapshots[-1].summary` for `app-id`, `total-records`,
     `added-records`, `added-data-files`, `added-files-size`,
     `total-files-size`, and `metadata.schemas[-1].fields` for schema).
   * **Cloud Storage Parquet/ORC/CSV/JSON:**
     `gcloud storage ls -l -r "gs://<BUCKET>/<PREFIX>/"` (count non-empty data
     files excluding `_SUCCESS`, count `col=val/` partition directories, sum
     object byte sizes, and inspect per-file sizes when checking output
     partition skew).
2. **Filter pushdown vs. raw source rows:** CSV/JSON/Parquet pushed filters can
   make stage `inputRecords` and SQL scan `number of output rows` report
   **post-filter** surviving rows while `size of files read` reflects raw file
   bytes. If `Filter` / `PushedFilters` is present in the plan (or code),
   inspect `pysparkBatch.mainPythonFileUri` / `pysparkJob.mainPythonFileUri` and
   any unfiltered Spark SQL/stage scan or driver log output (never stream or
   download full GCS data files or event logs via `gcloud storage cat` or
   `mcp_cloud_storage_download_object` to count lines), and state clearly
   whether reported input rows are raw or post-filter.
3. **Failed or aborted runs guardrail:** a `FAILED` batch or `ERROR` job can
   complete upstream scan/count stages (`inputRecords > 0`,
   `milliDcuSeconds > 0`) before raising an exception prior to sink commit.
   Never report scanned or intermediate rows as written output: verify whether
   any write execution committed and check the target BigQuery table, BigLake
   Iceberg snapshot, or GCS sink prefix directly (`0` committed rows/bytes if
   untouched), alongside `stateMessage` / driver error details.
4. **Multi-batch & orchestrated pipeline rollups:** filter runs with
   `--limit=100` and explicit field projection across custom pipeline labels
   (`labels.pipeline=<ID>`), Composer (`labels.airflow-dag-id`), Workflow
   Templates (`labels.goog-dataproc-workflow-template-id`), or DCS Serverless
   Orchestration (`labels.goog-orchestration-pipeline-id` /
   `labels.goog-orchestration-run-id`, `labels.dcs_pipeline_id` /
   `labels.dcs_run_id` / `labels.dcs_task_id`, or downstream batch URIs from
   `jsonPayload.external_job_reference` in `orchestration.googleapis.com`
   activity logs):
   `gcloud dataproc batches list --region="${REGION}" --project="${PROJECT_ID}"`
   `--filter="labels.<key>=<value>" --limit=100`
   `--format="json(name,uuid,state,createTime,stateTime,stateHistory,runtimeInfo.approximateUsage,labels)"`
   (never run unfiltered `batches list --format=json` without `--filter` and
   field projection on shared projects). Sum `milliDcuSeconds`,
   `shuffleStorageGbSeconds`, and active/total durations across pipeline stages,
   and inspect each batch via `spark_applications.py` (`stages --quantiles` +
   `sql`) to attribute bottleneck duration, skew, shuffle volume, and I/O.
5. **Construct-specific pipeline artifacts (Notebooks, `dbt-spark`, & SDP):**
   * **Papermill notebooks (`NotebookAction`):** inspect the executed `.ipynb`
     in GCS for per-cell
     `cells[].metadata.papermill.{status,duration,start_time,end_time,exception}`.
   * **`dbt-spark` (`DbtAction` / `DbtDataModel`):** inspect GCS
     `target/run_results.json`
     (`results[].{unique_id,status,execution_time,adapter_response,timing[]}`)
     and `target/manifest.json`. Note: Multi-Tenant Service
     (`cloud-dataform-mst-*`) runtimes execute inside a Google-managed tenant
     project, so customer projects expose `orchestration.googleapis.com`
     telemetry and target sink audit logs rather than `cloud_dataproc_*`
     resources.
   * **Spark Declarative Pipelines (`PipelineAction (sdp)` / `SdpDataModel`):**
     on Spark 4.1+ Connect, use
     `spark_gcs_log_reader.py --action=summarize_events` on the batch's GCS
     event log to extract `SparkListenerConnectOperation*` (`operationId`,
     `jobTag` such as `dcs_sdp_dataset:<dataset>`, `sessionId`, per-flow
     duration, `producedRowCount`, `errorMessage`); apportion shared batch
     `milliDcuSeconds` across flows proportional to each flow's
     `sum(executorRunTimeMillis)`.
