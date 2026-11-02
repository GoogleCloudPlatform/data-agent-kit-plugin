# Resource Contention Queries

Telemetry and SQL queries for diagnosing slot contention, tracking per-minute
and window-averaged concurrency timelines, comparing degraded vs baseline
timeframes, detecting noisy neighbor workload variance, and analyzing pending
job backlogs.

## Table of Contents

-   [Per-Minute Project Slot Usage, Concurrency & Queue Timeline](#per-minute-project-slot-usage-concurrency-queue-timeline)
    (Lines 17-48)
-   [Reservation Maximum Utilization & Slot Saturation Timeline (1-Second Resolution)](#reservation-maximum-utilization-slot-saturation-timeline-1-second-resolution)
    (Lines 49-250)
-   [Slot Contention & Queue Latency Diagnosis](#slot-contention-queue-latency-diagnosis)
    (Lines 251-280)

## Per-Minute Project Slot Usage, Concurrency & Queue Timeline

Groups by 1-minute buckets (`MINUTE`) to track concurrency, per project job
queue length, slot usage over time.

```sql
SELECT
  TIMESTAMP_TRUNC(period_start, MINUTE) AS window_minute,
  project_id AS resource_owner_project_id,
  reservation_id,
  ROUND(SUM(period_slot_ms) / 1000.0 / 60.0, 1) AS slot_usage,
  ROUND(COUNT(*) / 60.0, 1) AS job_concurrency,
  ROUND(COUNTIF(state = 'PENDING') / 60.0, 1) AS project_queue_length,
FROM
  `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.JOBS_TIMELINE_BY_PROJECT
WHERE
  job_creation_time
    BETWEEN TIMESTAMP_SUB(TIMESTAMP('{target_start_timestamp}'), INTERVAL 2 DAY)
    AND TIMESTAMP('{target_end_timestamp}')
  AND period_start
    BETWEEN TIMESTAMP('{target_start_timestamp}')
    AND TIMESTAMP('{target_end_timestamp}')
  AND (statement_type != 'SCRIPT' OR statement_type IS NULL)
GROUP BY
  window_minute,
  resource_owner_project_id,
  reservation_id
ORDER BY
  window_minute DESC,
  slot_usage DESC;
```

## Reservation Maximum Utilization & Slot Saturation Timeline (1-Second Resolution)

Evaluates true reservation slot saturation by expanding reservation capacity and
job slot consumption to 1-second resolution. Evaluates the time-average
percentage of time a reservation spent at maximum capacity (> 95%), accounting
for primary vs. failover baseline slots, scaling mode headroom, and borrowed
idle slots.

```sql
WITH
  reservation_timeline_raw AS (
    SELECT
      max_slots,
      slots_assigned,
      autoscale,
      ignore_idle_slots,
      per_second_details,
      period_start,
      edition,
      project_id AS admin_project_id,
      reservation_id,
      scaling_mode,
      is_creation_region
    FROM
      `{admin_project_id}`.`region-{region}`.INFORMATION_SCHEMA.RESERVATIONS_TIMELINE_BY_PROJECT
    WHERE
      period_start
      BETWEEN TIMESTAMP('{target_start_timestamp}')
      AND TIMESTAMP('{target_end_timestamp}')
  ),
  reservation_per_second AS (
    SELECT
      s.start_time AS period_start,
      edition,
      admin_project_id,
      reservation_id,
      scaling_mode,
      ignore_idle_slots,
      -- Primary region baseline & autoscale headroom
      IF(is_creation_region, IFNULL(s.slots_assigned, 0), 0) AS baseline_slots,
      IF(
        is_creation_region,
        IF(
          scaling_mode IN ('ALL_SLOTS', 'AUTOSCALE_ONLY'),
          IFNULL(max_slots, 0) - IFNULL(s.slots_assigned, 0),
          0),
        0) AS max_slots_exclude_baseline,
      -- Failover secondary region baseline & autoscale headroom
      IF(NOT is_creation_region, IFNULL(s.slots_assigned, 0), 0) AS failover_baseline_slots,
      IF(
        NOT is_creation_region,
        IF(
          scaling_mode IN ('ALL_SLOTS', 'AUTOSCALE_ONLY'),
          IFNULL(max_slots, 0) - IFNULL(s.slots_assigned, 0),
          0),
        0) AS failover_max_slots_exclude_baseline,
      IFNULL(s.autoscale_current_slots, 0) AS autoscale_current_slots,
      IFNULL(s.autoscale_max_slots, 0) AS autoscale_max_slots,
      IFNULL(s.borrowed_slots, 0) AS borrowed_slots
    FROM
      reservation_timeline_raw,
      UNNEST(
        IF(
          ARRAY_LENGTH(per_second_details) > 0,
          ARRAY(
            SELECT AS STRUCT
              s.start_time,
              s.autoscale_current_slots,
              s.autoscale_max_slots,
              s.slots_assigned,
              s.borrowed_slots
            FROM
              UNNEST(per_second_details) AS s
          ),
          ARRAY(
            SELECT AS STRUCT
              s AS start_time,
              autoscale.current_slots AS autoscale_current_slots,
              autoscale.max_slots AS autoscale_max_slots,
              slots_assigned AS slots_assigned,
              0 AS borrowed_slots
            FROM
              UNNEST(
                GENERATE_TIMESTAMP_ARRAY(
                  period_start,
                  TIMESTAMP_ADD(period_start, INTERVAL 59 SECOND),
                  INTERVAL 1 SECOND)) AS s
          ))) AS s
  ),
  jobs_per_second AS (
    SELECT
      TIMESTAMP_TRUNC(period_start, SECOND) AS period_start,
      reservation_id,
      SUM(period_slot_ms) / 1000.0 AS used_slots,
      COUNT(*) AS job_concurrency,
      COUNTIF(state = 'PENDING') AS queued_job_concurrency,
      COUNT(DISTINCT project_id) AS project_concurrency
    FROM
      `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.JOBS_TIMELINE_BY_ORGANIZATION
    WHERE
      job_creation_time
        BETWEEN TIMESTAMP_SUB(TIMESTAMP('{target_start_timestamp}'), INTERVAL 2 DAY)
        AND TIMESTAMP('{target_end_timestamp}')
      AND period_start
        BETWEEN TIMESTAMP('{target_start_timestamp}')
        AND TIMESTAMP('{target_end_timestamp}')
      AND (statement_type != 'SCRIPT' OR statement_type IS NULL)
    GROUP BY
      period_start,
      reservation_id
  ),
  reservation_job_joined AS (
    SELECT
      r.period_start,
      r.reservation_id,
      r.edition,
      r.scaling_mode,
      r.ignore_idle_slots,
      r.baseline_slots,
      r.failover_baseline_slots,
      r.autoscale_max_slots,
      r.max_slots_exclude_baseline,
      r.failover_max_slots_exclude_baseline,
      r.autoscale_current_slots,
      r.borrowed_slots AS idle_slots,
      IFNULL(j.used_slots, 0) AS total_slot_usage,
      IFNULL(j.job_concurrency, 0) AS job_concurrency,
      IFNULL(j.queued_job_concurrency, 0) AS queued_job_concurrency,
      IFNULL(j.project_concurrency, 0) AS project_concurrency,
      -- Total maximum slot capacity ceiling across baseline, autoscale, and failover
      (
        r.baseline_slots
        + r.failover_baseline_slots
        + r.autoscale_max_slots
        + r.max_slots_exclude_baseline
        + r.failover_max_slots_exclude_baseline) AS total_max_capacity,
      -- Attribution of used slots across baseline, autoscale, and idle pools
      GREATEST(
        LEAST(
          r.baseline_slots + r.failover_baseline_slots, IFNULL(j.used_slots, 0) - r.borrowed_slots),
        0) AS baseline_used_slots,
      LEAST(
        GREATEST(
          IFNULL(j.used_slots, 0)
            - r.borrowed_slots
            - (r.baseline_slots + r.failover_baseline_slots),
          0),
        r.autoscale_current_slots) AS autoscaled_used_slots
    FROM
      reservation_per_second r
    LEFT JOIN
      jobs_per_second j
      USING (period_start, reservation_id)
  ),
  second_level_metrics AS (
    SELECT
      period_start,
      reservation_id,
      edition,
      scaling_mode,
      ignore_idle_slots,
      total_slot_usage,
      baseline_slots + failover_baseline_slots AS total_baseline_capacity,
      total_max_capacity,
      idle_slots,
      baseline_used_slots,
      autoscaled_used_slots,
      job_concurrency,
      queued_job_concurrency,
      project_concurrency,
      -- Saturation Indicator: True when active slot usage exceeds 95% of total maximum capacity
      IF(
        SAFE_DIVIDE(
          idle_slots + baseline_used_slots + autoscaled_used_slots,
          total_max_capacity)
          > 0.95,
        1,
        0) AS is_max_utilization
    FROM
      reservation_job_joined
  )
SELECT
  TIMESTAMP_TRUNC(period_start, MINUTE) AS window_minute,
  reservation_id,
  -- Time-average percentage of seconds spent at max capacity (> 95%) during the minute
  ROUND(AVG(is_max_utilization) * 100, 1) AS pct_time_at_max_utilization,
  ROUND(SUM(total_slot_usage) / 60, 1) AS avg_slot_usage,
  ROUND(AVG(total_baseline_capacity), 1) AS avg_baseline_capacity,
  ROUND(AVG(total_max_capacity), 1) AS avg_max_capacity,
  ROUND(AVG(idle_slots), 1) AS avg_borrowed_idle_slots,
  ROUND(AVG(queued_job_concurrency), 1) AS avg_queued_jobs,
  ROUND(AVG(job_concurrency), 1) AS avg_job_concurrency
FROM
  second_level_metrics
GROUP BY
  window_minute,
  reservation_id
ORDER BY
  window_minute DESC,
  pct_time_at_max_utilization DESC;
```

## Slot Contention & Queue Latency Diagnosis

Identify completed queries that experienced excessive queuing latency between
`creation_time` and `start_time` due to lack of available slots.

```sql
SELECT
  job_id,
  user_email,
  creation_time,
  start_time,
  TIMESTAMP_DIFF(start_time, creation_time, SECOND) AS queue_latency_sec,
  TIMESTAMP_DIFF(end_time, start_time, SECOND) AS execution_duration_sec,
  total_slot_ms,
  reservation_id,
  (
    SELECT LOGICAL_OR(slot_contention)
    FROM UNNEST(query_info.performance_insights.stage_performance_standalone_insights)
  ) AS has_slot_contention
FROM
  `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 DAY)
  AND state = 'DONE'
  AND (statement_type != 'SCRIPT' OR statement_type IS NULL)
  AND TIMESTAMP_DIFF(start_time, creation_time, SECOND) > 5
ORDER BY
  queue_latency_sec DESC
LIMIT 50;
```
