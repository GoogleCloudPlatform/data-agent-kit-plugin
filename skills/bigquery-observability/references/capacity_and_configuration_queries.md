# Capacity & Configuration Queries

Telemetry and SQL queries for evaluating reservation slot capacity, monitoring
autoscaling behavior and headroom saturation, inspecting capacity commitments
and assignments, and auditing configuration changes.

## Table of Contents

-   [Reservation Slot Capacity & Autoscaling Saturation Timeline (1-Second Resolution)](#reservation-slot-capacity-autoscaling-saturation-timeline-1-second-resolution)
    (Lines 14-168)
-   [Auditing Reservation & Assignment Configuration Changes](#auditing-reservation-assignment-configuration-changes)
    (Lines 169-189)

## Reservation Slot Capacity & Autoscaling Saturation Timeline (1-Second Resolution)

Tracks second-by-second baseline capacity, active autoscaling slots, and maximum
capacity ceilings. Accurately calculates baseline and autoscale slots by
accounting for:

-   **Primary vs Failover Regions (`is_creation_region`)**: Distinguishes
    primary baseline from disaster-recovery secondary region baseline.
-   **Predictable Scaling Modes (`scaling_mode`)**: When `scaling_mode IN
    ('ALL_SLOTS', 'AUTOSCALE_ONLY')`, `max_slots` includes baseline slots, so
    autoscale max is `max_slots - slots_assigned`.
-   **Per-Second Telemetry (`per_second_details`)**: Unnests second-level
    records or expands minute intervals across 60 seconds.
-   **Autoscale Saturation**: Detects when autoscaling reached its maximum
    capacity headroom (`autoscale_current_slots >= total_autoscale_max`).

```sql
WITH
  reservation_timeline_raw AS (
    SELECT
      period_start,
      project_id AS admin_project_id,
      reservation_name,
      reservation_id,
      edition,
      scaling_mode,
      is_creation_region,
      ignore_idle_slots,
      slots_assigned,
      max_slots,
      autoscale,
      per_second_details
    FROM
      `{admin_project_id}`.`region-{region}`.INFORMATION_SCHEMA.RESERVATIONS_TIMELINE_BY_PROJECT
    WHERE
      period_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
      AND reservation_name = '{reservation_name}'
  ),
  reservation_per_second AS (
    SELECT
      s.start_time AS second_timestamp,
      TIMESTAMP_TRUNC(period_start, MINUTE) AS window_minute,
      reservation_name,
      reservation_id,
      edition,
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
  capacity_metrics_per_second AS (
    SELECT
      second_timestamp,
      window_minute,
      reservation_name,
      edition,
      scaling_mode,
      -- Total baseline capacity across primary and failover regions
      (baseline_slots + failover_baseline_slots) AS total_baseline_capacity,
      -- Total maximum autoscale (excluding baseline)
      (autoscale_max_slots + max_slots_exclude_baseline + failover_max_slots_exclude_baseline)
        AS total_autoscale_max,
      -- Total ceiling capacity across baseline and autoscale
      (
        baseline_slots
        + failover_baseline_slots
        + autoscale_max_slots
        + max_slots_exclude_baseline
        + failover_max_slots_exclude_baseline) AS total_max_capacity,
      autoscale_current_slots,
      borrowed_slots AS idle_slots,
      -- Saturation Indicator: True when autoscale is maxed out
      IF(
        (autoscale_max_slots + max_slots_exclude_baseline + failover_max_slots_exclude_baseline) > 0
          AND autoscale_current_slots
            >= (
              autoscale_max_slots
              + max_slots_exclude_baseline
              + failover_max_slots_exclude_baseline),
        1,
        0) AS is_autoscale_saturated
    FROM
      reservation_per_second
  )
SELECT
  window_minute,
  reservation_name,
  edition,
  scaling_mode,
  ROUND(AVG(total_baseline_capacity), 1) AS avg_baseline_slots,
  ROUND(AVG(autoscale_current_slots), 1) AS avg_autoscale_slots,
  ROUND(AVG(total_autoscale_max), 1) AS avg_total_autoscale_max,
  ROUND(AVG(total_max_capacity), 1) AS avg_total_max_capacity,
  ROUND(AVG(idle_slots), 1) AS avg_borrowed_idle_slots,
  -- Percentage of seconds in the minute where autoscaling was saturated at max
  ROUND(AVG(is_autoscale_saturated) * 100, 1) AS pct_time_autoscale_saturated
FROM
  capacity_metrics_per_second
GROUP BY
  window_minute,
  reservation_name,
  edition,
  scaling_mode
ORDER BY
  window_minute DESC;
```

## Auditing Reservation & Assignment Configuration Changes

Audit historical modifications across reservation configurations, assignments,
and capacity commitments (e.g., `RESERVATION_CHANGES_BY_PROJECT`,
`ASSIGNMENT_CHANGES_BY_PROJECT`, `CAPACITY_COMMITMENT_CHANGES_BY_PROJECT`).

```sql
SELECT
  change_timestamp,
  action,
  reservation_name,
  slot_capacity AS new_slot_capacity,
  autoscale.max_slots AS new_autoscale_max_slots,
  user_email
FROM
  `{admin_project_id}`.`region-{region}`.INFORMATION_SCHEMA.RESERVATION_CHANGES_BY_PROJECT
WHERE
  change_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
ORDER BY
  change_timestamp DESC;
```
