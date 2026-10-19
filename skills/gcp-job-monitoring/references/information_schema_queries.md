# BigQuery `INFORMATION_SCHEMA` Job Monitoring Queries

Use these SQL templates when querying historical BigQuery jobs via MCP
(`bigquery__execute_sql`) or when you need longer retention / SQL aggregations
beyond the last 1,000 jobs returned by `gcp_job_monitor.py`.

## Crucial Gotchas

1. **Regional Scoping is Mandatory (`region-<location>`):**
   `INFORMATION_SCHEMA.JOBS_BY_PROJECT` and `INFORMATION_SCHEMA.JOBS_BY_USER`
   are **strictly regional**. You must prefix the view with a region qualifier
   such as `` `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT `` or
   `` `region-us-central1`.INFORMATION_SCHEMA.JOBS_BY_PROJECT ``. A query on
   `region-us` will **not** return jobs executed in `us-central1` or `EU`.
2. **Permission Fallback (`JOBS_BY_PROJECT` vs. `JOBS_BY_USER` vs. REST API):**
   - `JOBS_BY_PROJECT` requires `bigquery.jobs.listAll` (typically
     `roles/bigquery.admin` or `roles/bigquery.resourceViewer`).
   - `JOBS_BY_USER` requires `bigquery.jobs.list` and only shows the caller's
     own jobs.
   - In many enterprise sandbox projects, **both** `INFORMATION_SCHEMA.JOBS*`
     views return `403 Access Denied` even when the user can run queries,
     whereas `scripts/gcp_job_monitor.py` (which calls the `jobs.list` /
     `jobs.get` REST API directly) succeeds across all regions at **$0 cost**.
3. **Partition Pruning (`creation_time`):**
   Always filter on `creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL N DAY)`
   to avoid scanning 180 days of metadata.

---

## 1. Recent BigQuery Jobs (`JOBS_BY_USER` / `JOBS_BY_PROJECT`)

```sql
SELECT
  job_id,
  job_type,
  statement_type,
  state,
  user_email,
  creation_time,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) / 1000.0 AS duration_sec,
  ROUND(total_bytes_billed / POW(1024, 3), 4) AS gb_billed,
  total_slot_ms,
  error_result.reason AS error_reason,
  error_result.message AS error_message,
  SUBSTR(query, 1, 200) AS query_preview
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY
  creation_time DESC
LIMIT 25;
```

*(If `JOBS_BY_PROJECT` fails with `Access Denied`, replace `JOBS_BY_PROJECT`
with `JOBS_BY_USER` and remove `user_email` filtering, or run
`scripts/gcp_job_monitor.py --action=bq_list`.)*

---

## 2. Most Expensive Jobs (On-Demand Bytes Billed & Est. USD)

On-demand pricing is approximately **$6.25 per TiB (`POW(1024, 4)` bytes)** in
most regions. For capacity/edition (slot) workloads, rank by `total_slot_ms`
instead.

```sql
SELECT
  job_id,
  user_email,
  statement_type,
  creation_time,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) / 1000.0 AS duration_sec,
  ROUND(total_bytes_billed / POW(1024, 3), 2) AS gib_billed,
  ROUND((total_bytes_billed / POW(1024, 4)) * 6.25, 4) AS est_on_demand_usd,
  total_slot_ms,
  ROUND(total_slot_ms / 1000.0 / 3600.0, 4) AS slot_hours,
  cache_hit,
  SUBSTR(query, 1, 200) AS query_preview
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
ORDER BY
  total_bytes_billed DESC,
  total_slot_ms DESC
LIMIT 20;
```

---

## 3. Slowest / Longest-Running Jobs

Separating `total_slot_ms / NULLIF(TIMESTAMP_DIFF(end_time, start_time, MILLISECOND), 0)`
(`avg_slots`) helps distinguish queries that waited on slot contention or single-thread
skew (low `avg_slots`, high `duration_sec`) from massively parallel heavy queries
(high `avg_slots`, high `duration_sec`).

```sql
SELECT
  job_id,
  user_email,
  state,
  statement_type,
  creation_time,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) / 1000.0 AS elapsed_sec,
  total_slot_ms,
  ROUND(
    SAFE_DIVIDE(
      total_slot_ms,
      TIMESTAMP_DIFF(end_time, start_time, MILLISECOND)
    ),
    2
  ) AS avg_parallel_slots,
  ROUND(total_bytes_billed / POW(1024, 3), 2) AS gib_billed,
  error_result.message AS error_message,
  SUBSTR(query, 1, 200) AS query_preview
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY
  elapsed_sec DESC
LIMIT 20;
```

---

## 4. Deep-Dive on a Specific Job ID (Stages, Timeline & Referenced Tables)

```sql
SELECT
  job_id,
  user_email,
  state,
  statement_type,
  creation_time,
  start_time,
  end_time,
  TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) / 1000.0 AS elapsed_sec,
  total_bytes_processed,
  total_bytes_billed,
  total_slot_ms,
  bi_engine_statistics.bi_engine_mode,
   error_result,
  referenced_tables,
  job_stages,
  timeline,
  query
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND job_id = @job_id;
```

---

## 5. Cost & Slot Attribution by User & Reservation (`bq_summary` SQL Equivalent)

```sql
SELECT
  user_email,
  COALESCE(edition, 'ON_DEMAND') AS edition,
  COALESCE(reservation_id, '(none)') AS reservation_id,
  COUNT(*) AS total_jobs,
  COUNTIF(error_result IS NULL) AS succeeded_jobs,
  COUNTIF(error_result IS NOT NULL) AS failed_jobs,
  ROUND(SUM(total_bytes_billed) / POW(1024, 3), 2) AS total_gib_billed,
  ROUND(
    SUM(IF(reservation_id IS NULL, total_bytes_billed, 0)) / POW(1024, 4) * 6.25,
    4
  ) AS est_on_demand_usd,
  ROUND(SUM(total_slot_ms) / 1000.0 / 3600.0, 4) AS total_slot_hours
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY
  user_email,
  edition,
  reservation_id
ORDER BY
  total_gib_billed DESC,
  total_slot_hours DESC;
```

---

## 6. Failure Triage & Top Error Reasons

```sql
SELECT
  error_result.reason AS error_reason,
  error_result.message AS sample_message,
  COUNT(*) AS failure_count,
  ARRAY_AGG(job_id ORDER BY creation_time DESC LIMIT 3) AS sample_job_ids
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND error_result IS NOT NULL
GROUP BY
  error_reason,
  sample_message
ORDER BY
  failure_count DESC
LIMIT 20;
```

---

## 7. Most Queried / Highest-Cost Tables (`bq_hot_tables` SQL Equivalent)

```sql
SELECT
  CONCAT(rt.project_id, '.', rt.dataset_id, '.', rt.table_id) AS full_table_id,
  COUNT(DISTINCT job_id) AS query_count,
  COUNT(DISTINCT user_email) AS distinct_users,
  ROUND(SUM(total_bytes_billed) / POW(1024, 3), 2) AS total_gib_billed,
  ROUND((SUM(total_bytes_billed) / POW(1024, 4)) * 6.25, 4) AS est_on_demand_usd,
  ROUND(SUM(total_slot_ms) / 1000.0, 2) AS total_slot_sec
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT,
  UNNEST(referenced_tables) AS rt
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND state = 'DONE'
  AND error_result IS NULL
GROUP BY
  full_table_id
ORDER BY
  total_gib_billed DESC,
  total_slot_sec DESC
LIMIT 20;
```

---

## 8. Slot Reservations, Capacity Commitments & Assignments (`bq_reservations` SQL Equivalent)

```sql
SELECT
  reservation_name,
  edition,
  slot_capacity AS baseline_slots,
  autoscale.current_slots AS autoscale_current_slots,
  autoscale.max_slots AS autoscale_max_slots,
  ignore_idle_slots
FROM
  `region-us`.INFORMATION_SCHEMA.RESERVATIONS;
```

---

## 9. Time-Series Slot Contention (`JOBS_TIMELINE_BY_PROJECT`)

Use `INFORMATION_SCHEMA.JOBS_TIMELINE_BY_PROJECT` (1-second granularity) to
answer questions like *"What time of day did slot usage spike?"* or *"Were jobs
queued waiting for slots at 2pm?"*:

```sql
SELECT
  TIMESTAMP_TRUNC(period_start, MINUTE) AS minute_bucket,
  reservation_id,
  ROUND(SUM(period_slot_ms) / 1000.0 / 60.0, 2) AS avg_slots_used,
  MAX(total_Slot_ms) AS peak_period_slot_ms,
  MAX(pending_units) AS max_pending_work_units,
  COUNT(DISTINCT job_id) AS active_jobs
FROM
  `region-us`.INFORMATION_SCHEMA.JOBS_TIMELINE_BY_PROJECT
WHERE
  job_creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
  AND period_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
GROUP BY
  minute_bucket,
  reservation_id
ORDER BY
  avg_slots_used DESC
LIMIT 30;
```

---

## 10. Dataset & Table Storage Cost Analysis (`TABLE_STORAGE`)

Use `INFORMATION_SCHEMA.TABLE_STORAGE` to answer admin questions about active vs.
long-term logical and physical storage bytes or time-travel/fail-safe overhead:

```sql
SELECT
  table_schema AS dataset_name,
  COUNT(*) AS table_count,
  ROUND(SUM(total_logical_bytes) / POW(1024, 3), 2) AS total_logical_gib,
  ROUND(SUM(active_logical_bytes) / POW(1024, 3), 2) AS active_logical_gib,
  ROUND(SUM(long_term_logical_bytes) / POW(1024, 3), 2) AS long_term_logical_gib,
  ROUND(SUM(total_physical_bytes) / POW(1024, 3), 2) AS total_physical_gib,
  ROUND(SUM(time_travel_physical_bytes) / POW(1024, 3), 2) AS time_travel_physical_gib
FROM
  `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
WHERE
  deleted = FALSE
GROUP BY
  dataset_name
ORDER BY
  total_logical_gib DESC
LIMIT 20;
```
