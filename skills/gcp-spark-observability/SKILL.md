---
name: gcp-spark-observability
description: >-
  Monitors, inventories, and assesses Google Cloud Managed Service for Apache
  Spark (Dataproc Serverless and Dataproc on Compute Engine) environments,
  clusters, batches, jobs, sessions, metrics, logs, costs, and configurations
  across single and multiple regions. Use when listing active or historical
  Spark workloads, discovering failed batches or jobs, auditing multi-region
  fleet inventory, calculating Serverless compute (DCU-Hours) and shuffle
  storage consumption, detecting idle or zombie clusters, inspecting scheduled
  pipeline cadence health, investigating failed cluster operations or
  stockouts, checking quotas and alerting coverage, or querying Cloud
  Monitoring and Cloud Logging telemetry. Don't use for deep root-cause
  analysis or performance optimization of a specific job or batch (use
  gcp-spark-troubleshooting), authoring new PySpark code (use gcp-spark), or
  upgrading Spark versions (use gcp-managed-spark-upgrades).
license: Apache-2.0
metadata:
  version: v2
  publisher: google
---

# Google Cloud Spark & Dataproc Observability

Starter guide and `gcloud` lookup map for monitoring, inventorying, and
assessing **Google Cloud Managed Service for Apache Spark** (**Dataproc
Serverless** batches and interactive sessions, and **Dataproc on Compute
Engine** clusters and jobs). For exact `gcloud` commands, field paths, metric
names, and log filters, see
[gcloud Observability Reference](references/gcloud_observability_reference.md).

--------------------------------------------------------------------------------

## Skill Routing & Handoff

*   **Fleet inventory & observability** (multi-region discovery, active/failed
    workloads, DCU/cost ranking, idle clusters, schedule cadence,
    operations/stockouts, quotas, alerts, Monitoring/Logging):
    *   Skill: `gcp-spark-observability` (this skill).
*   **Root-cause analysis (RCA) of a specific failed or slow batch or job**
    (driver stack traces, executor OOMs, shuffle spill, stage skew,
    `sparkApplications` API, GCS event logs):
    *   Skill: `@skill:gcp-spark-troubleshooting`.
    *   Handoff: if no `batch_id` or `job_id` is given (for example, *"Why did
        my last Spark batch fail?"*), use this skill first to find the latest
        failed ID, region, and `stateMessage`/`status.details`, then hand off to
        `@skill:gcp-spark-troubleshooting`.
*   **Optimizing a specific batch or job** (runtime or DCU regression, GC,
    spill, skew, partitioning, Spark property tuning, AQE, autotuning, executor
    sizing, code anti-patterns):
    *   Skill: `@skill:gcp-spark-troubleshooting`.
    *   Handoff: use this skill first to identify top DCU consumers, regressed
        schedules, or saturated clusters, then hand off one workload at a time
        with its ID, region, usage/runtime metrics, and
        `runtimeConfig`/`softwareConfig` properties. Do not propose Spark
        property tuning from fleet metrics alone.
*   **Authoring or submitting new PySpark/Spark code, notebooks, or creating new
    clusters/batches**:
    *   Skill: `gcp-spark`.

--------------------------------------------------------------------------------

## Non-Obvious CLI & API Gotchas (Read First)

1.  **MCP field projection vs. `gcloud`:** Dataproc MCP list/get tools
    (`list_batches`, `get_batch`, `list_sessions`, `list_clusters`,
    `get_cluster`) return minimal summaries and omit `runtimeInfo` (DCU/shuffle
    usage), `stateMessage`, `creator`, cluster `config` (machine types,
    lifecycle TTLs, autoscaling), and `metrics.yarnMetrics`. Always run
    `gcloud dataproc ... list|describe --format=json` when you need those
    fields.
2.  **Release tracks & location flags:**
    *   `clusters`, `jobs`, `batches`, `operations`, `workflow-templates`, and
        `autoscaling-policies` are GA and use `--region=<REGION>`.
    *   `sessions` and `session-templates` require the `beta` track and
        `--location=<REGION>`
        (`gcloud beta dataproc sessions list --location=<REGION>`).
    *   Always pass `--quiet` to `asset`, `metastore`, `composer`, and
        `scheduler` commands so disabled APIs do not hang on interactive
        prompts. Never enable APIs.
3.  **Always specify `--limit` & respect server-side `--filter` restrictions:**
    *   Always pass an explicit `--limit` (for example `--limit=20` to
        `--limit=200`) on every `gcloud ... list`,
        `gcloud asset search-all-resources`, and `gcloud logging read` query so
        list calls stay bounded.
    *   `batches list --filter`: accepts `state`, `create_time>="<RFC3339>"`
        (snake_case; `createTime>=` is rejected), and `labels.<key>=<value>`.
    *   `jobs list --filter`: `status.state` only accepts `ACTIVE`, `INACTIVE`,
        or `NON_ACTIVE` (`status.state=ERROR` is rejected with
        `INVALID_ARGUMENT`). Use `--state-filter=inactive --limit=100` and
        filter `ERROR` client-side.
    *   `operations list --filter`: `status.state` only accepts `PENDING`,
        `RUNNING`, or `DONE`. Filter server-side with
        `operationType=CREATE AND status.state=DONE --limit=100` and filter
        client-side where `error.code` is set.
4.  **Region resolution:**
    *   **Single region:** use the user-specified region,
        `@skill:resolving-mcp-region-configs`, or
        `gcloud config get-value dataproc/region` (fallback `compute/region`).
    *   **Project-wide / multi-region:** discover regions with Cloud Asset
        Inventory (`gcloud asset search-all-resources
        --asset-types="dataproc.googleapis.com/Cluster,dataproc.googleapis.com/Batch,dataproc.googleapis.com/Session,dataproc.googleapis.com/Job"
        --limit=200`), then query each discovered region live via
        `gcloud dataproc` (Asset Inventory states can be stale). Always state
        which regions were inspected.
5.  **Usage, idle clusters, and safety:**
    *   `runtimeInfo.approximateUsage` (`milliDcuSeconds`,
        `shuffleStorageGbSeconds`) is populated only after a batch/session
        completes; running workloads expose `runtimeInfo.currentUsage`.
    *   $\text{DCU-Hours} = \text{milliDcuSeconds} / 3{,}600{,}000$;
        $\text{Shuffle-GB-Months} = \text{shuffleStorageGbSeconds} /
        2{,}592{,}000$. DCU-hours measure compute usage, not dollar spend (use
        Cloud Billing export for dollars; never fabricate dollar amounts).
    *   A `RUNNING` cluster is **idle** only when it has **0 active Jobs API
        jobs** AND **0 running/pending YARN applications**
        (`metrics.yarnMetrics.yarn-apps-running` and `yarn-apps-pending` in
        `clusters list`), because notebooks, SSH `spark-submit`, and Spark
        Connect bypass the Jobs API.
    *   Audit log entries with a non-empty `protoPayload.status` (such as
        `PERMISSION_DENIED`) are rejected API calls, not cluster operations.
    *   Never cancel, kill, stop, or delete any workload or cluster without
        explicit user confirmation.

--------------------------------------------------------------------------------

## Where to Look (Quick Map)

*   **Active fleet inventory (all 4 surfaces):** query `batches list`
    (`RUNNING`/`PENDING`), `beta dataproc sessions list` (`ACTIVE`/`CREATING`),
    `clusters list` (`RUNNING`/`CREATING`/`UPDATING`), and `jobs list`
    (`--state-filter=active`) with `--limit=100` across target regions.
*   **Recent failed batches or jobs:**
    `batches list --filter="state=FAILED" --sort-by=~createTime --limit=20`
    (append `AND labels.<key>=<value>` when a workload label is given; inspect
    `stateMessage`) and `jobs list --state-filter=inactive --limit=100` filtered
    to `status.state=ERROR` (`status.details`).
*   **Scheduled pipeline cadence:**
    `batches list --sort-by=~createTime --limit=200` grouped by
    `labels.airflow-dag-id` / `labels.airflow-task-id`,
    `labels.goog-dataproc-workflow-template-id`, or batch-ID prefix; check
    median interval and runtime (`stateTime - createTime`).
*   **Top Serverless compute consumers:** `batches list
    --sort-by=~runtimeInfo.approximateUsage.milliDcuSeconds --limit=20` and
    convert to DCU-hours and Shuffle-GB-Months.
*   **Idle / zombie clusters:**
    `clusters list --filter="status.state=RUNNING" --limit=100` (always report
    `metrics.yarnMetrics`, `config.lifecycleConfig` TTLs
    `idleDeleteTtl`/`autoDeleteTime`/`idleStopTtl`, and recent
    `jobs list --cluster=<NAME> --limit=5`; recommend
    `gcloud dataproc clusters update <NAME> --region=<REGION> --max-idle=30m` or
    `--stop-max-idle=30m` / `--delete-max-idle=30m`).
*   **Failed cluster operations & stockouts:** `operations list
    --filter="operationType=CREATE AND status.state=DONE" --limit=100` (always
    specify `--limit` and filter client-side where `error.code` is set), plus
    Admin Activity audit logs (`--limit=50`) for zonal stockouts
    (`does not have enough resources available`).
*   **Quotas & alerting coverage:**
    `compute regions list --flatten=quotas --limit=100`,
    `alpha services quota list --service=dataproc.googleapis.com --limit=100`
    (`data_compute_units`), and `monitoring policies list --limit=100`.
*   **Cloud Monitoring & Logging:** `dataproc.googleapis.com/cluster/yarn/*`,
    `dataproc.googleapis.com/batch/spark/executors`, and Cloud Logging resource
    types `cloud_dataproc_{batch,session,cluster,job}`.

See
[gcloud Observability Reference](references/gcloud_observability_reference.md)
for all commands and field paths.
