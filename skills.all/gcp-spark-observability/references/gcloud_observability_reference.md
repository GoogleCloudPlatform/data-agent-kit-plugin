# gcloud Dataproc & Spark Observability Reference

Concise `gcloud` commands and field paths for observing Dataproc Serverless (batches, sessions) and Dataproc on Compute Engine (clusters, jobs, operations).

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

Always inspect all 4 active workload surfaces per region (`batches`, `sessions`, `clusters`, `jobs`) and always pass `--limit`:

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
  --format="table(name.basename():label=BATCH,state,createTime,stateTime,labels.'airflow-dag-id':label=DAG,labels.'airflow-task-id':label=TASK,labels.'goog-dataproc-workflow-template-id':label=WF_TEMPLATE,creator)"
```
* **Cadence grouping:** group runs by `labels.airflow-dag-id`/`airflow-task-id` (Composer batches), `labels.goog-dataproc-workflow-template-id` (Workflow Templates), or batch-ID prefix (strip trailing run hash/timestamp). Compute median runtime (`stateTime - createTime`) and median interval between `createTime` values to flag missed runs (`> 1.5x` median interval) or runtime regressions.
* **Safe cancellation (only after explicit user confirmation):**
  * Stop running batch: `gcloud dataproc batches cancel <BATCH_ID> --region=<REGION>` (`batches delete` only deletes terminal records).
  * Kill running job: `gcloud dataproc jobs kill <JOB_ID> --region=<REGION>`.
  * Terminate active session: `gcloud beta dataproc sessions terminate <SESSION_ID> --location=<REGION>`.

---

## 4. Serverless Usage (DCU-Hours), Idle Clusters & Config Audit

* **Formulas:** $\text{DCU-Hours} = \text{milliDcuSeconds} / 3{,}600{,}000$, $\text{Shuffle-GB-Months} = \text{shuffleStorageGbSeconds} / 2{,}592{,}000$.

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
* **Idle remediation (always report `config.lifecycleConfig` TTLs `idleDeleteTtl`/`idleStopTtl` and recommend only; never execute without confirmation):** `gcloud dataproc clusters update <CLUSTER> --region=<REGION> --max-idle=30m` (or `--stop-max-idle=30m` / `--delete-max-idle=30m`).
* **Key config fields to audit (`describe --format=json`):**
  * Serverless (`batches`/`sessions`): `runtimeConfig.version`, `runtimeConfig.properties` (`dataproc:dataproc.tier`, `spark:spark.dataproc.engine`, `spark.dynamicAllocation.*`, `spark.sql.adaptive.enabled`), `runtimeConfig.autotuningConfig.scenarios`, `environmentConfig.executionConfig.idleTtl`/`ttl`, `environmentConfig.peripheralsConfig.sparkHistoryServerConfig`.
  * Clusters: `config.softwareConfig.imageVersion`, `config.clusterTier`, `config.lifecycleConfig.*`, `config.autoscalingConfig.policyUri`, `config.secondaryWorkerConfig.preemptibility`, `config.*Config.diskConfig` (`bootDiskType`, `numLocalSsds`), `config.endpointConfig.enableHttpPortAccess`.
  * Workload-level tuning: hand off individual top-DCU or slow workloads to `@skill:gcp-spark-troubleshooting`.

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

* **Key Dataproc metrics (`dataproc.googleapis.com/...`):**
  * Serverless (`cloud_dataproc_batch`, `cloud_dataproc_session`): `batch/spark/executors` and `session/spark/executors` (labels: `status` = `running`, `pending-delete`, `required`, `maximum-needed`, `target`).
  * Clusters (`cloud_dataproc_cluster`): `cluster/yarn/allocated_memory_percentage`, `cluster/yarn/pending_memory_size`, `cluster/yarn/apps` (`status` = `running`, `pending`, `failed`), `cluster/yarn/nodemanagers` (`status` = `active`, `lost`, `unhealthy`), `cluster/hdfs/storage_utilization`, `cluster/hdfs/unhealthy_blocks`, `cluster/job/failed_count`, `cluster/operation/failed_count`.
  * Spark metrics (`custom.googleapis.com/spark/...`): enabled by default on Serverless; opt-in via `--metric-sources=spark` on clusters.

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

# Cloud Logging: batch/cluster errors and cross-region Admin Activity audit trail
gcloud logging read 'resource.type="cloud_dataproc_batch" AND resource.labels.batch_id="<BATCH_ID>" AND severity>=ERROR' \
  --project="${PROJECT_ID}" --limit=50 --format="table(timestamp,severity,jsonPayload.message,textPayload)"
gcloud logging read 'logName:"cloudaudit.googleapis.com%2Factivity" AND protoPayload.serviceName="dataproc.googleapis.com"' \
  --project="${PROJECT_ID}" --freshness=7d --limit=50 \
  --format="table(timestamp,protoPayload.methodName,protoPayload.authenticationInfo.principalEmail,resource.labels.region,protoPayload.resourceName,protoPayload.status.message)"
```
