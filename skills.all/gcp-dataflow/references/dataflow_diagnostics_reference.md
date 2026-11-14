# Dataflow Diagnostics Reference

> [!IMPORTANT] To perform a complete Root Cause Analysis (RCA), you MUST get
> **Job Messages/Events** and both **Monitoring** and **Logging** to
> correlate metrics spikes/drops with log errors. Always follow the sample
> queries provided in the below sections.

## 1. Monitoring

### Streaming Jobs

Key metrics to look at for Streaming jobs:

*   **Data Freshness**:
    *   `job/per_stage_data_watermark_age` (Filters: `job_id`, `stage`)
    *   `job/data_watermark_age` (Filters: `job_id`)
*   **Throughput**:
    *   `job/elements_produced_count` (Filters: `job_id`, `pcollection`,
        `ptransform`)
    *   `job/estimated_bytes_produced_count` (Filters: `job_id`, `pcollection`,
        `ptransform`)
*   **Backlog**:
    *   `job/estimated_backlog_processing_time` (Filters: `job_id`, `stage`)
    *   `job/backlog_bytes` (Filters: `job_id`, `stage`)
*   **System Latency**:
    *   `job/per_stage_system_lag` (Filters: `job_id`, `stage`)
    *   `job/system_lag` (Filters: `job_id`)
*   **Autoscaling**:
    *   `job/horizontal_worker_scaling` (Filters: `job_id`, `rationale`,
        `direction`)
*   **Bottleneck**:
    *   `job/is_bottleneck` (Filters: `job_id`, `stage`, `likely_cause`,
        `bottleneck_kind`)
    *   `job/backlogged_keys` (Filters: `job_id`, `stage`)
*   **Resource Utilization (CPU/Memory)**:
    *   `compute.googleapis.com/instance/cpu/utilization`
    *   `compute.googleapis.com/guest/memory/bytes_used`

### Batch Jobs

Key metrics to look at for Batch jobs:

*   **Resource Utilization (CPU/Memory)**:
    *   `compute.googleapis.com/instance/cpu/utilization`
    *   `compute.googleapis.com/guest/memory/bytes_used`
*   **Throughput**:
    *   `job/elements_produced_count` (Filters: `job_id`, `pcollection`,
        `ptransform`) *(Throughput is the primary indicator for Batch jobs)*

### Monitoring API Request

```bash
curl -s -G -H \"Authorization: Bearer \$(gcloud auth print-access-token)\" \\
  --data-urlencode 'filter=metric.type=\"<METRIC_TYPE>\" AND metric.labels.job_id=\"<JOB_ID>\"' \\
  --data-urlencode 'interval.startTime=<START_TIME>' \\
  --data-urlencode 'interval.endTime=<END_TIME>' \\
  \"https://monitoring.googleapis.com/v3/projects/<PROJECT_ID>/timeSeries\"
```

Placeholders: Replace `<METRIC_TYPE>`, `<JOB_ID>`, `<START_TIME>`, `<END_TIME>`,
and `<PROJECT_ID>` with actual values. Timestamps: Must be in ISO 8601 format
(e.g., 2026-04-20T23:16:03Z).

## 2. Log Analysis

Use `gcloud logging read` to fetch Dataflow job logs

## 3. Dataflow REST API (Direct Queries)

Use the Dataflow REST API (v1b3) to fetch current snapshot metrics or high-level
job messages.

**Get Job Metrics (Snapshot):** `bash curl -X GET \ -H "Authorization: Bearer
$(gcloud auth print-access-token)" \
"https://dataflow.googleapis.com/v1b3/projects/<PROJECT_ID>/locations/<REGION>/jobs/<JOB_ID>/metrics"`

**Get High level Job Messages/Events:** `bash curl -X GET \ -H "Authorization:
Bearer $(gcloud auth print-access-token)" \
"https://dataflow.googleapis.com/v1b3/projects/<PROJECT_ID>/locations/<REGION>/jobs/<JOB_ID>/messages"`

## 4. Additional Dataflow Metrics
Only when you need more metrics not covered by the above sections, or want to
check source/sink based performance, refer to:

* [Core Job Metrics](dataflow_metrics_core_job.md)
* [Pub/Sub Metrics](dataflow_metrics_pubsub.md)
* [BigQuery Metrics](dataflow_metrics_bigquery.md)
* [Streaming Engine Metrics](dataflow_metrics_streaming_engine.md)