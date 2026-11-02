# BI Engine Acceleration Strategy

Architectural guidelines, eligibility constraints, and remediation workflows for
accelerating BI dashboard queries using BigQuery BI Engine.

## Table of Contents

-   [1. When to Propose BI Engine vs. Materialized Views](#1-when-to-propose-bi-engine-vs-materialized-views)
    (Lines 19-43)
-   [2. BI Engine Capacity & Preferred Tables](#2-bi-engine-capacity-preferred-tables)
    (Lines 45-61)
-   [3. Limitations & Fallback Causes (`PARTIAL` or `DISABLED`)](#3-limitations-fallback-causes-partial-or-disabled)
    (Lines 63-86)
-   [4. Remediating BI Engine Fallback with Materialized Views](#4-remediating-bi-engine-fallback-with-materialized-views)
    (Lines 88-110)
-   [5. Telemetry & Data Retrieval Reference](#5-telemetry-data-retrieval-reference)
    (Lines 112-126)

## 1. When to Propose BI Engine vs. Materialized Views

Use BI Engine and Materialized Views together or independently depending on the
bottleneck:

<!-- mdformat off -->
| Dimension | BigQuery BI Engine | Materialized Views (`CREATE MATERIALIZED VIEW`) | Combined (BI Engine + Materialized View) |
| :--- | :--- | :--- | :--- |
| **Primary Goal** | Accelerate BI dashboard queries from tools such as Looker, Data Studio (formerly Looker Studio), or Tableau. | Precompute and store aggregated results (such as `SUM` and `COUNT`) for queries that repeatedly aggregate large base tables. | Accelerate dashboards over a materialized view that pre-joins or pre-aggregates the data, so the same joins are not performed for each query. |
| **Mechanism** | In-memory analysis service that caches only the queried parts of columns and partitions. | BigQuery automatically adds incremental base-table changes to the view; smart tuning can reroute eligible base-table queries to it. | The materialized view joins and flattens (or pre-aggregates) the data, and BI Engine accelerates queries to the view. |
<!-- mdformat on -->

**Decision Rule:**

*   **Propose BI Engine** when users analyze data with BI tools (such as Looker,
    Data Studio, or Tableau), or when a subset of tables is queried more
    frequently or backs high-visibility dashboards (designate those tables as
    preferred tables).
*   **Propose a Materialized View** when queries repeatedly aggregate or join
    large base tables.
*   **Propose Both Together** when dashboards repeatedly join or aggregate large
    tables: use a materialized view to pre-join or pre-aggregate the data, and
    mark the view and its base tables as preferred tables. If the dashboard only
    displays recent data, also partition the tables by time so that only the
    latest partitions are loaded into memory.

## 2. BI Engine Capacity & Preferred Tables

*   **Capacity & Cost:** You incur costs for the reservation that you create for
    BI Engine capacity.
*   **Configuring BI Engine Reservations & Preferred Tables:**
    *   Never execute CLI scripts to purchase or mutate BI Engine capacity
        reservations autonomously. Guide the user to configure BI Engine
        capacity or **Preferred Tables** in the Google Cloud Console under
        **BigQuery** > **Administration** > **BI Engine**:
        `https://console.cloud.google.com/bigquery/admin/bi-engine?project={project_id}`
    *   **Preferred Tables:** If a subset of tables is queried more frequently
        or backs high-visibility dashboards, designate those tables as preferred
        tables. Queries to all other tables use regular BigQuery slots. Queries
        that access multiple tables (such as a `JOIN`) are only accelerated if
        all tables in the query are in the preferred tables list, and queries to
        materialized views are only accelerated if both the materialized views
        and their base tables are in the preferred tables list.

## 3. Limitations & Fallback Causes (`PARTIAL` or `DISABLED`)

When the project is configured to use BI Engine, `INFORMATION_SCHEMA.JOBS`
reports each query's acceleration status in
`bi_engine_statistics.bi_engine_mode` (`FULL`, `PARTIAL`, or `DISABLED`) and
`bi_engine_statistics.acceleration_mode` (for example, `FULL_INPUT` when all of
the query inputs were accelerated, or `FULL_QUERY` when all of the query was
accelerated). For `PARTIAL` or `DISABLED`,
`bi_engine_statistics.bi_engine_reasons` (`code` and `message`) explains why.
Query stages that BI Engine can't accelerate fall back to standard BigQuery
execution slots without failing the query. Documented limitations include:

*   **Join Limits:** BI Engine accelerates leaf-level subqueries with `INNER`
    and `LEFT OUTER` joins where a large fact table is joined with up to four
    smaller dimension tables. Each dimension table must have fewer than 5
    million rows and be 5 GiB or less (unpartitioned tables) or have referenced
    partitions of 1 GiB or less (partitioned tables).
*   **Unsupported Features:** BI Engine acceleration isn't available for:
    *   Queries that reference wildcard tables
    *   External tables, including BigLake tables
    *   JavaScript UDFs and remote functions
    *   Row-level security
    *   Queries that use `SEARCH` or `VECTOR_SEARCH` functions, or are optimized
        by search indexes or vector indexes

## 4. Remediating BI Engine Fallback with Materialized Views

When diagnostic telemetry (`bi_engine_statistics`) shows a high rate of
`PARTIAL` or `DISABLED` queries on a dashboard workload:

1.  **Inspect `bi_engine_reasons`:** Group `INFORMATION_SCHEMA.JOBS_BY_PROJECT`
    by `bi_engine_statistics.bi_engine_mode` and
    `UNNEST(bi_engine_statistics.bi_engine_reasons)` to identify the exact
    reason code (such as `INPUT_TOO_LARGE`, `UNSUPPORTED_SQL_TEXT`,
    `TABLE_EXCLUDED`, or `INSUFFICIENT_RESERVATION`).
2.  **Offload Heavy Aggregations & Joins to a Materialized View:** If dashboard
    queries repeatedly aggregate or join large base tables:
    *   Create a partitioned, clustered materialized view (see
        [materialized_views.md](materialized_views.md)) that pre-aggregates the
        dashboard dimensions and measures (such as `SUM` and `COUNT`).
    *   Smart tuning can rewrite eligible queries against the base tables to
        read the materialized view. If you use preferred tables, add both the
        materialized view and its base tables so that queries to the view can be
        accelerated.
3.  **Prune Scanned Partitions:** If the dashboard only displays recent data,
    partition the base tables by time and make sure dashboard queries filter on
    the partitioning column, so that only the latest partitions are loaded into
    memory.

## 5. Telemetry & Data Retrieval Reference

If the `bigquery-observability` skill is available in your workspace, refer to
its shared telemetry references for canonical query templates and schema
dictionaries. All architectural rules, eligibility limits, and remediation
workflows are self-contained within this guide.

*   **BI Engine Acceleration Usage & Fallback Reasons:** See the
    `bigquery-observability` skill (`references/job_performance_queries.md`,
    section "BI Engine Acceleration Usage") to query
    `bi_engine_statistics.bi_engine_mode` and
    `UNNEST(bi_engine_statistics.bi_engine_reasons)`.
*   **Jobs Schema (`bi_engine_statistics`):** See the `bigquery-observability`
    skill (`references/schema_compute.md`, section "1. Jobs & Compute Telemetry
    Views") for `INFORMATION_SCHEMA.JOBS` column definitions.
