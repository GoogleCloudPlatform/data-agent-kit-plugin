# Storage: Logical & Physical Pricing (Bytes Stored)

## Table of Contents

-   [Storage Snapshot & Billing Model Comparison Query](#storage-snapshot-billing-model-comparison-query)
    (Lines 18-107)
-   [Dataset Storage Configuration Query](#dataset-storage-configuration-query)
    (Lines 108-127)
-   [Partition Level Aging & Storage Query](#partition-level-aging-storage-query)
    (Lines 128-146)
-   [Daily Storage Usage Timeline (Time-Integral Conversion)](#daily-storage-usage-timeline-time-integral-conversion)
    (Lines 147-175)
-   [Table Partitioning, Clustering & Filter Enforcement Audit](#table-partitioning-clustering-filter-enforcement-audit)
    (Lines 176-238)
-   [Search Index Coverage Query](#search-index-coverage-query) (Lines 239-262)
-   [Placeholder Definitions](#placeholder-definitions) (Lines 263-268)

## Storage Snapshot & Billing Model Comparison Query

> [!NOTE] The `DECLARE` parameters in the query below reflect default US
> multi-region list pricing ($/GiB/month). Because BigQuery storage pricing
> varies across regions (e.g., non-US regions such as `europe-west1` or
> `asia-northeast1`), verify the current rates for your specific region at
> [BigQuery Storage Pricing](https://cloud.google.com/bigquery/pricing#storage)
> and update the `DECLARE` rates before running.

```googlesql
-- Default pricing parameters below reflect US multi-region standard list rates ($/GiB/month).
-- IMPORTANT: Storage rates vary by region (e.g., non-US regions).
-- Verify and update these DECLARE variables for your specific region before executing.
-- Reference: https://cloud.google.com/bigquery/pricing#storage
DECLARE active_logical_gib_price FLOAT64 DEFAULT 0.02;
DECLARE long_term_logical_gib_price FLOAT64 DEFAULT 0.01;
DECLARE active_physical_gib_price FLOAT64 DEFAULT 0.04;
DECLARE long_term_physical_gib_price FLOAT64 DEFAULT 0.02;

WITH
  storage_sizes AS (
    SELECT
      table_schema AS dataset_name,
      -- Logical
      SUM(IF(deleted = FALSE, active_logical_bytes, 0)) / POWER(1024, 3)
        AS active_logical_gib,
      SUM(IF(deleted = FALSE, long_term_logical_bytes, 0)) / POWER(1024, 3)
        AS long_term_logical_gib,
      -- Physical
      SUM(active_physical_bytes) / POWER(1024, 3) AS active_physical_gib,
      SUM(active_physical_bytes - time_travel_physical_bytes) / POWER(1024, 3)
        AS active_no_tt_physical_gib,
      SUM(long_term_physical_bytes) / POWER(1024, 3)
        AS long_term_physical_gib,
      -- Restorable physical (Time Travel & Fail-Safe)
      SUM(time_travel_physical_bytes) / POWER(1024, 3)
        AS time_travel_physical_gib,
      SUM(fail_safe_physical_bytes) / POWER(1024, 3)
        AS fail_safe_physical_gib
    FROM
      `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.TABLE_STORAGE_BY_PROJECT
    WHERE
      total_physical_bytes + fail_safe_physical_bytes > 0
      AND table_type = 'BASE TABLE'
    GROUP BY
      1
  )
SELECT
  '{region}' AS region,
  dataset_name,
  ROUND(active_logical_gib, 2) AS active_logical_gib,
  ROUND(long_term_logical_gib, 2) AS long_term_logical_gib,
  ROUND(active_physical_gib, 2) AS active_physical_gib,
  ROUND(long_term_physical_gib, 2) AS long_term_physical_gib,
  ROUND(time_travel_physical_gib, 2) AS time_travel_physical_gib,
  ROUND(fail_safe_physical_gib, 2) AS fail_safe_physical_gib,
  -- Compression Ratios
  ROUND(
    SAFE_DIVIDE(active_logical_gib, active_no_tt_physical_gib), 2) AS active_compression_ratio,
  ROUND(
    SAFE_DIVIDE(long_term_logical_gib, long_term_physical_gib), 2) AS long_term_compression_ratio,
  -- Forecast Costs
  ROUND(
    active_logical_gib * active_logical_gib_price, 2) AS forecast_active_logical_cost,
  ROUND(
    long_term_logical_gib * long_term_logical_gib_price, 2) AS forecast_long_term_logical_cost,
  ROUND(
    (active_no_tt_physical_gib + time_travel_physical_gib + fail_safe_physical_gib)
      * active_physical_gib_price,
    2) AS forecast_active_physical_cost,
  ROUND(
    long_term_physical_gib * long_term_physical_gib_price, 2) AS forecast_long_term_physical_cost,
  -- Total Cost Delta (Positive = Physical is cheaper; Negative = Logical is cheaper)
  ROUND(
    (
      (active_logical_gib * active_logical_gib_price)
      + (long_term_logical_gib * long_term_logical_gib_price))
      - (
        (
          active_no_tt_physical_gib
          + time_travel_physical_gib
          + fail_safe_physical_gib)
          * active_physical_gib_price
        + (long_term_physical_gib * long_term_physical_gib_price)),
    2) AS forecast_total_cost_difference
FROM
  storage_sizes
ORDER BY(forecast_active_logical_cost + forecast_active_physical_cost) DESC;
```

## Dataset Storage Configuration Query

Inspect dataset lifecycle parameters (`storage_billing_model`,
`max_time_travel_hours`, `default_partition_expiration_days`):

```googlesql
SELECT
  schema_name AS dataset_name,
  option_name,
  option_value
FROM
  `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.SCHEMATA_OPTIONS
WHERE
  option_name IN (
    'storage_billing_model',
    'max_time_travel_hours',
    'default_partition_expiration_days',
    'default_table_expiration_days');
```

## Partition Level Aging & Storage Query

Inspect partition-level storage and modification timestamps to identify mature
unpartitioned tables or historical partitions:

```googlesql
SELECT
  table_name,
  partition_id,
  last_modified_time,
  ROUND(total_logical_bytes / POWER(1024, 3), 2) AS total_logical_gib
FROM
  `{project_id}`.`{dataset_id}`.INFORMATION_SCHEMA.PARTITIONS
WHERE
  table_name = '{table_name}'
ORDER BY
  partition_id DESC;
```

## Daily Storage Usage Timeline (Time-Integral Conversion)

Convert cumulative `MiB * seconds` storage metrics from
`TABLE_STORAGE_USAGE_TIMELINE` to daily average GiB:

```googlesql
SELECT
  usage_date,
  table_schema AS dataset_name,
  -- Logical average daily GiB: (MiB * seconds / 86400 seconds) / 1024 MiB_per_GiB
  ROUND(SUM(billable_total_logical_usage) / 86400 / 1024, 2) AS avg_daily_logical_gib,
  ROUND(SUM(billable_active_logical_usage) / 86400 / 1024, 2) AS avg_daily_active_logical_gib,
  ROUND(SUM(billable_long_term_logical_usage) / 86400 / 1024, 2) AS avg_daily_long_term_logical_gib,
  -- Physical average daily GiB: (MiB * seconds / 86400 seconds) / 1024 MiB_per_GiB
  ROUND(SUM(billable_total_physical_usage) / 86400 / 1024, 2) AS avg_daily_physical_gib,
  ROUND(SUM(billable_active_physical_usage) / 86400 / 1024, 2) AS avg_daily_active_physical_gib,
  ROUND(SUM(billable_long_term_physical_usage) / 86400 / 1024, 2)
    AS avg_daily_long_term_physical_gib
FROM
  `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.TABLE_STORAGE_USAGE_TIMELINE
WHERE
  usage_date >= DATE_SUB(CURRENT_DATE('PST8PDT'), INTERVAL 7 DAY)
GROUP BY
  1, 2
ORDER BY
  usage_date DESC,
  avg_daily_logical_gib DESC;
```

## Table Partitioning, Clustering & Filter Enforcement Audit

Verify whether referenced tables have `DATE`, `TIMESTAMP`, `DATETIME`, or
`INT64` integer-range partitioning (`is_partitioning_column = 'YES'` and
`data_type`), which high-cardinality filtering and grouping columns are in the
`CLUSTER BY` key (`clustering_ordinal_position`), and whether
`require_partition_filter` is enabled in `INFORMATION_SCHEMA.TABLE_OPTIONS`.
Tables where `partitioning_column IS NULL` are unpartitioned (`DATE` /
`TIMESTAMP` / `DATETIME` indicate time-unit partitioning; `INT64` indicates
integer-range partitioning via `RANGE_BUCKET`), and tables where
`clustering_columns IS NULL` lack clustering on high-cardinality filtering and
grouping columns (`WHERE` and `GROUP BY`). `TABLES`, `COLUMNS`, and
`TABLE_OPTIONS` support dataset (`{dataset_id}`) or regional (`region-{region}`)
scoping.

```googlesql
-- Verify whether referenced tables have DATE, TIMESTAMP, DATETIME, or INT64
-- integer-range partitioning, high-cardinality clustering columns, and
-- require_partition_filter enabled:
SELECT
  c.table_schema AS dataset_id,
  c.table_name,
  MAX(IF(c.is_partitioning_column = 'YES', c.column_name, NULL))
    AS partitioning_column,
  MAX(IF(c.is_partitioning_column = 'YES', c.data_type, NULL))
    AS partitioning_data_type,
  CASE MAX(IF(c.is_partitioning_column = 'YES', c.data_type, NULL))
    WHEN 'DATE' THEN 'DATE partitioning'
    WHEN 'TIMESTAMP' THEN 'TIMESTAMP partitioning'
    WHEN 'DATETIME' THEN 'DATETIME partitioning'
    WHEN 'INT64' THEN 'INT64 integer-range partitioning'
    ELSE 'UNPARTITIONED'
    END AS partitioning_type,
  STRING_AGG(
    IF(c.clustering_ordinal_position IS NOT NULL, c.column_name, NULL),
    ', '
    ORDER BY c.clustering_ordinal_position)
    AS clustering_columns,  -- High-cardinality filtering and grouping columns in CLUSTER BY
  COALESCE(MAX(opt.option_value), 'false') AS require_partition_filter
FROM
  `{project_id}`.`{dataset_id}`.INFORMATION_SCHEMA.COLUMNS AS c
INNER JOIN
  `{project_id}`.`{dataset_id}`.INFORMATION_SCHEMA.TABLES AS t
  ON
    c.table_catalog = t.table_catalog
    AND c.table_schema = t.table_schema
    AND c.table_name = t.table_name
LEFT JOIN
  `{project_id}`.`{dataset_id}`.INFORMATION_SCHEMA.TABLE_OPTIONS AS opt
  ON
    c.table_catalog = opt.table_catalog
    AND c.table_schema = opt.table_schema
    AND c.table_name = opt.table_name
    AND opt.option_name = 'require_partition_filter'
WHERE
  t.table_type = 'BASE TABLE'
GROUP BY
  c.table_schema,
  c.table_name
ORDER BY
  c.table_name;
```

## Search Index Coverage Query

Inspect search index status, coverage, backlog, and storage for a dataset. A
`coverage_percentage` of 0 means the index is not usable in a `SEARCH` query,
even if some data has already been indexed. An index on a base table smaller
than 10 GB is not populated, so its `coverage_percentage` stays 0.

```googlesql
SELECT
  table_name,
  index_name,
  index_status,
  coverage_percentage,
  unindexed_row_count,
  ROUND(total_logical_bytes / POWER(1024, 3), 2) AS index_logical_gib,
  analyzer,
  last_refresh_time,
  ddl
FROM
  `{project_id}`.`{dataset_id}`.INFORMATION_SCHEMA.SEARCH_INDEXES
ORDER BY
  coverage_percentage ASC;
```

## Placeholder Definitions

-   **`{project_id}`**: Google Cloud project ID.
-   **`{region}`**: Storage region (e.g. `us`, `europe-west1`).
-   **`{dataset_id}`**: Dataset name/schema containing the table.
-   **`{table_name}`**: Table name to inspect.
