# Materialized Views

Guidance for deciding when to propose a BigQuery materialized view and how to
write the `CREATE MATERIALIZED VIEW` statement. Propose the DDL to the user and
let them run it; never run it yourself.

## Table of Contents

-   [When to Propose a Materialized View](#when-to-propose-a-materialized-view)
    (Lines 18-24)
-   [Smart Tuning Requirements](#smart-tuning-requirements) (Lines 26-49)
-   [Partition Alignment, Clustering & Proposing the DDL](#partition-alignment-clustering-proposing-the-ddl)
    (Lines 51-87)
-   [Verifying the View](#verifying-the-view) (Lines 89-97)
-   [Telemetry & Data Retrieval Reference](#telemetry-data-retrieval-reference)
    (Lines 99-111)

## When to Propose a Materialized View

Propose a materialized view when queries repeatedly run the same aggregations,
filters, or joins over large base tables (for example, dashboards that query the
same summary metrics). A materialized view precomputes and stores aggregated
results and automatically combines them with incremental changes in the base
tables.

## Smart Tuning Requirements

BigQuery automatically rewrites queries against the base tables to read a
materialized view (smart tuning), so users don't need to change their queries. A
query is rewritten only if the view:

*   Belongs to the same project as one of its base tables or the project that
    the query runs in.
*   Uses the same set of base tables as the query.
*   Includes all columns that the query reads. For example, a query that reads a
    column the view doesn't include is not rewritten. If the view outputs
    `CAST(sold_datetime AS DATE)`, a query that filters on `sold_datetime`
    itself is not rewritten either.
*   Includes all rows that the query reads. For example, a query is not
    rewritten if it reads dates outside the view's `WHERE` range, or adds a more
    restrictive filter on a column that the view filters on but doesn't output.

Smart tuning isn't supported for materialized views that:

*   Reference logical views.
*   Use `UNION ALL` or `LEFT OUTER JOIN`.
*   Are non-incremental (`allow_non_incremental_definition = true`). Users must
    query these views directly.
*   Reference tables with change data capture (CDC) enabled.

## Partition Alignment, Clustering & Proposing the DDL

Base the view definition on the query patterns against the base tables, so that
it serves a broad set of queries rather than one query. For example, if users
often filter on `user_id` or `department`, group by (and optionally cluster on)
those columns instead of adding a filter such as `user_id = 123` to the view.
For date filters, omit narrow date filters or use a date range that covers all
ranges the queries read.

For partitioning and clustering:

*   **Partition alignment:** If the base table is partitioned, partition the
    view on the same partitioning column to reduce refresh and query cost. For
    time-based partitioning, the granularity must match the base table, and a
    truncation function applied to the partitioning column must be at least as
    granular as the base table's partitioning. For integer-range partitioning,
    the range must match exactly. A view over a non-partitioned base table can't
    be partitioned.
*   **Clustering:** Cluster on output columns that queries filter on. Aggregate
    output columns can't be clustering columns.

For a base table partitioned by `DATE(event_ts)`:

```sql
CREATE MATERIALIZED VIEW `{project_id}.{dataset_id}.{view_name}`
  PARTITION BY DATE(event_day)
  CLUSTER BY service_name
AS (
  SELECT
    TIMESTAMP_TRUNC(event_ts, DAY) AS event_day,
    service_name,
    COUNT(*) AS request_count,
    SUM(bytes_sent) AS total_bytes_sent
  FROM `{project_id}.{dataset_id}.{table_id}`
  GROUP BY event_day, service_name
);
```

## Verifying the View

Check that the view appears in `materialized_view_statistics` with `chosen` set
to `TRUE`, or that the query plan contains a `READ {view_name}` step. If
`chosen` is `FALSE`, read `rejected_reason` (for example, `NO_DATA` means the
view hasn't refreshed yet, and `COST` means another source was estimated to be
cheaper). If the view is not listed at all, the query shape doesn't match the
view; compare it with [Smart Tuning Requirements](#smart-tuning-requirements).
If many views are considered, the list might be incomplete.

## Telemetry & Data Retrieval Reference

If the `bigquery-observability` skill is available in your workspace, refer to
its telemetry references for the query templates. All decision rules and DDL
templates are self-contained within this guide. Without that skill, check
`materialized_view_statistics` in the region-qualified `INFORMATION_SCHEMA.JOBS`
view.

*   **Rewrite Usage:** See the `bigquery-observability` skill
    (`references/job_performance_queries.md`, section "Materialized View Rewrite
    Usage"). For a single job, `bq show --format=prettyjson
    --location={location} -j {project_id}:{job_id}` returns
    `statistics.query.materializedViewStatistics`.
