---
name: bigquery-optimization
license: Apache-2.0
metadata:
  version: v1
  publisher: google
description: >-
  Provides workflows to optimize BigQuery environments (capacity planning,
  editions), storage assets (partitioning, clustering, storage lifecycles,
  billing models), and SQL queries. Use when optimizing cost, modeling Edition
  migrations, rightsizing reservations, evaluating logical vs. physical storage,
  designing table partitioning/clustering, generating table DDL, migrating
  unpartitioned tables, managing partition expiration, optimizing individual SQL
  queries, or evaluating acceleration structures (search indexes, materialized
  views, BI Engine).

  Do not use for raw usage reporting (use bigquery-observability), query
  execution plan analysis, error troubleshooting, or diagnosing why a specific
  job was slow (use bigquery-troubleshooting).
---

# BigQuery Optimization Workflow

## Workflows

Determine the optimization focus of the user's request and follow the relevant
workflow:

-   **Telemetry & Observability Baseline:** For direct raw usage telemetry,
    `INFORMATION_SCHEMA` queries, and baseline metric calculations, consult the
    `@skill:bigquery-observability` skill. If the `bigquery-observability`
    companion skill is not available in the active environment, all optimization
    guidelines, DDL templates, and decision models across this skill and its
    reference guides are fully self-contained.
-   **Capacity & Editions Modeling:** Evaluate the cost-efficiency of migrating
    workloads from On-Demand to Editions, as well as rightsizing active Edition
    reservations, baseline commitments, and autoscaling caps.
    *   *Instructions:* Read `references/capacity_planning_editions.md` to
        provide deep links to BigQuery's built-in recommendation UIs (e.g., Slot
        Estimator) and guide the user through UI navigation: 1. navigate to the
        Slot Estimator tab, 2. select 'On-Demand' as the source to analyze
        historical query volume, and 3. review the Cost-Optimized
        Recommendations and Slot Usage Chart.
-   **Table & Storage Optimization:** Optimize storage costs from a billing
    model, physical layout, and lifecycle perspective.
    *   *Billing Architecture:* Read `references/storage_billing_models.md` for
        guidance on evaluating aggregate compression ratios (e.g. >2:1 threshold
        in US) to recommend Physical vs. Logical billing, noting that the
        break-even ratio depends on specific regional rates and custom
        enterprise contracts. When providing `TABLE_STORAGE` queries, always
        scope with `WHERE table_schema = '{dataset_id}'`, use the regional
        dataset view, and warn that 0 rows indicates a region mismatch or lack
        of native tables rather than zero billable usage.
    *   *Partitioning & Clustering Strategy:* Read
        `references/table_partitioning_clustering.md` to generate production DDL
        templates (CREATE TABLE, CTAS migrations for unpartitioned tables, and
        modifying clustering specifications), enforce pruning with
        `require_partition_filter = true`, and manage partition limits (up to
        10,000 partitions/table).
    *   *Lifecycle Management:* Read
        `references/storage_lifecycle_management.md` to pinpoint inactive data
        and define precise Time-to-Live (TTL) partition expirations, dataset
        expirations, and Time Travel window reductions.
    *   *Acceleration Structures:* Read `references/search_indexes.md` to decide
        when to propose a search index for selective lookups over `STRING` or
        `JSON` data, write the `CREATE SEARCH INDEX` DDL, and tell the user how
        to verify index coverage and usage. Read
        `references/materialized_views.md` to decide when to propose a
        materialized view for repeated aggregations or joins over large base
        tables, write the `CREATE MATERIALIZED VIEW` DDL, and tell the user how
        to verify that smart tuning uses it. Read `references/bi_engine.md` to
        decide when to propose BI Engine vs. Materialized Views for BI dashboard
        acceleration, diagnose `PARTIAL` or `DISABLED` BI Engine fallback
        reasons (`bi_engine_statistics`), and combine BI Engine with
        materialized views that pre-join or pre-aggregate the data.
-   **SQL Optimization:** Optimize individual SQL queries to reduce slot-time
    and the amount of data read.
    *   *Instructions:* Follow the instructions in
        `references/sql_optimization.md` to provide recommendations to the user
        on how to rewrite their SQL query to reduce slot-time and the amount of
        data read.

## Execution Guardrails

-   **Terminology & Cost Framing:** Never promise or guarantee "cost-reduction"
    or "reducing expenditure." Always frame recommendations using the
    terminology **"optimizing your bill"** or **"improving cost-efficiency."**
-   **Explicit Scope Framing & Region Resolution:** Always state the target
    `project_id` and `region` at the very top of your response so the user
    immediately knows the exact scope being evaluated. Follow this 3-tier
    resolution hierarchy:
    1.  *Explicit Region:* Use the region specified in the user's prompt (e.g.,
        `europe-west1`).
    2.  *Contextual Region:* Resolve the region from the specific dataset or
        resource mentioned in the context.
    3.  *Unspecified Fallback:* Default to `us` / `region-us`, explicitly state
        that `us` was assumed as the default, and instruct the user to
        substitute their region if their resources reside elsewhere. *Region
        Formatting:* In Cloud Console deep links, use the region identifier
        directly (e.g., `region=us`, `region=europe-west1`). In SQL queries
        against `INFORMATION_SCHEMA`, use the regional dataset qualifier (e.g.,
        `region-us`, `region-europe-west1`).
-   **Zero-Row Result Guard:** If querying `TABLE_STORAGE` with `WHERE
    table_schema = '{dataset_id}'` returns 0 rows, do not proceed with an empty
    or zero-usage evaluation. Treat this as an indicator that the dataset may
    reside in a different region or have no native tables; stop and prompt the
    user to confirm the dataset's regional location.
-   **Populate Concrete Parameters:** When generating URLs and SQL queries,
    always substitute known `project_id` and `region` values directly into the
    code and links. Never leave literal `{project_id}` or `{location}`
    placeholders for the user to manually edit.
-   **No Autonomous Purchasing or Financial Mutations:** Never provide the user
    with executable scripts (e.g., `gcloud` or `bq` shell commands like `bq
    update --storage_billing_model=...`) designed to autonomously purchase
    annual commitments, alter edition tier bindings, or mutate storage billing
    models. Always guide the user to execute commitment purchases, reservation
    changes, and storage billing model updates manually via the Cloud Console
    UI.
