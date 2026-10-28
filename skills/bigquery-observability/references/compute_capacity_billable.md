# Billable Capacity Compute (Slots & Commitments)

## Table of Contents

-   [Edition Billable Slots Timeline](#edition-billable-slots-timeline) (Lines
    8-204)

## Edition Billable Slots Timeline

Commitments are purchased at the Edition level, but baseline and autoscaled
slots are assigned at the reservation level. To calculate billable slot hours
across 1-Year/3-Year commitments, uncovered baseline PAYG, and dynamic
autoscaling, join `CAPACITY_COMMITMENT_CHANGES_BY_PROJECT` and
`RESERVATIONS_TIMELINE`:

```googlesql
WITH
  commitments_with_next_plan AS (
    SELECT
      *,
      IFNULL(
        LEAD(commitment_plan)
          OVER (
            PARTITION BY capacity_commitment_id
            ORDER BY change_timestamp ASC
          ),
        commitment_plan) AS next_plan,
      IFNULL(
        LEAD(change_timestamp)
          OVER (
            PARTITION BY capacity_commitment_id
            ORDER BY change_timestamp ASC
          ),
        change_timestamp) AS next_plan_change_timestamp
    FROM
      `{admin_project_id}`.`region-{region}`.INFORMATION_SCHEMA.CAPACITY_COMMITMENT_CHANGES_BY_PROJECT
  ),
  capacity_changes_with_migration_delete AS (
    SELECT
      next_plan_change_timestamp AS change_timestamp,
      project_id,
      project_number,
      capacity_commitment_id,
      commitment_plan,
      state,
      slot_count,
      'DELETE' AS action,
      commitment_start_time,
      commitment_end_time,
      failure_status,
      renewal_plan,
      user_email,
      edition,
      is_flat_rate
    FROM
      commitments_with_next_plan
    WHERE
      commitment_plan <> next_plan
    UNION ALL
    SELECT
      *
    FROM
      `{admin_project_id}`.`region-{region}`.INFORMATION_SCHEMA.CAPACITY_COMMITMENT_CHANGES_BY_PROJECT
  ),
  capacity_commitment_slot_data AS (
    SELECT
      change_timestamp,
      capacity_commitment_id,
      commitment_plan,
      CASE
        WHEN action = "CREATE" OR action = "UPDATE"
          THEN
            IFNULL(
              IF(
                LAG(action)
                  OVER (
                    PARTITION BY capacity_commitment_id
                    ORDER BY change_timestamp ASC, action ASC
                  )
                  IN UNNEST(['CREATE', 'UPDATE']),
                slot_count - LAG(slot_count)
                  OVER (
                    PARTITION BY capacity_commitment_id
                    ORDER BY change_timestamp ASC, action ASC
                  ),
                slot_count),
              slot_count)
        ELSE
          IF(
            LAG(action)
              OVER (
                PARTITION BY capacity_commitment_id
                ORDER BY change_timestamp ASC, action ASC
              )
              IN UNNEST(['CREATE', 'UPDATE']),
            -1 * slot_count,
            0)
        END AS slot_count_delta
    FROM
      capacity_changes_with_migration_delete
    WHERE
      state = "ACTIVE"
      AND edition = '{edition}'
      AND change_timestamp <= TIMESTAMP('{end_timestamp}')
  ),
  running_total_commitments AS (
    SELECT
      change_timestamp,
      SUM(IF(commitment_plan = 'ANNUAL', slot_count_delta, 0))
        OVER (
          ORDER BY change_timestamp
          RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS capacity_slot_annual,
      SUM(IF(commitment_plan = 'THREE_YEAR', slot_count_delta, 0))
        OVER (
          ORDER BY change_timestamp
          RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS capacity_slot_three_year,
      SUM(slot_count_delta)
        OVER (
          ORDER BY change_timestamp
          RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS capacity_slot_total
    FROM
      capacity_commitment_slot_data
  ),
  distinct_commitments AS (
    SELECT
      change_timestamp,
      MAX(capacity_slot_annual) AS capacity_slot_annual,
      MAX(capacity_slot_three_year) AS capacity_slot_three_year,
      MAX(capacity_slot_total) AS capacity_slot_total
    FROM
      running_total_commitments
    GROUP BY
      change_timestamp
  ),
  distinct_commitments_with_next AS (
    SELECT
      change_timestamp,
      IFNULL(
        LEAD(change_timestamp) OVER (ORDER BY change_timestamp ASC),
        CURRENT_TIMESTAMP()) AS next_change_timestamp,
      capacity_slot_annual,
      capacity_slot_three_year,
      capacity_slot_total
    FROM
      distinct_commitments
  ),
  reservation_period_slices AS (
    SELECT
      period_start,
      SUM(IF(is_creation_region, slot_capacity, 0)) AS total_baseline_slots,
      SUM(period_autoscale_slot_seconds) AS total_autoscale_slot_seconds
    FROM
      `{admin_project_id}`.`region-{region}`.INFORMATION_SCHEMA.RESERVATIONS_TIMELINE
    WHERE
      period_start >= TIMESTAMP('{start_timestamp}')
      AND period_start < TIMESTAMP('{end_timestamp}')
      AND edition = '{edition}'
    GROUP BY
      period_start
  ),
  edition_billable_slots_cte AS (
    SELECT
      r.period_start,
      IFNULL(c.capacity_slot_annual, 0) AS committed_slots_annual,
      IFNULL(c.capacity_slot_three_year, 0) AS committed_slots_three_year,
      r.total_baseline_slots,
      IF(
        r.total_baseline_slots - IFNULL(c.capacity_slot_total, 0) > 0,
        r.total_baseline_slots - IFNULL(c.capacity_slot_total, 0),
        0) AS uncovered_baseline_slots,
      r.total_autoscale_slot_seconds
    FROM
      reservation_period_slices r
    LEFT JOIN
      distinct_commitments_with_next c
      ON
        r.period_start >= c.change_timestamp
        AND r.period_start < c.next_change_timestamp
  )

-- Replace this SELECT with your specific troubleshooting aggregation, for example:
SELECT
  '{region}' AS region,
  '{edition}' AS edition,
  SUM(committed_slots_annual * 60) / 3600.0
    AS billable_committed_annual_slot_hours,
  SUM(committed_slots_three_year * 60) / 3600.0
    AS billable_committed_three_year_slot_hours,
  SUM(uncovered_baseline_slots * 60) / 3600.0
    AS billable_uncovered_baseline_slot_hours,
  SUM(total_autoscale_slot_seconds) / 3600.0
    AS billable_autoscaled_payg_slot_hours,
  SUM(
    (committed_slots_annual * 60)
    + (committed_slots_three_year * 60)
    + (uncovered_baseline_slots * 60)
    + total_autoscale_slot_seconds)
    / 3600.0 AS total_billable_slot_hours
FROM
  edition_billable_slots_cte;
```
