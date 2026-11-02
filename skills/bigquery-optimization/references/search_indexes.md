# Search Indexes

Guidance for deciding when to propose a BigQuery search index and how to write
the `CREATE SEARCH INDEX` statement. Propose the DDL to the user and let them
run it; never run it yourself.

## Table of Contents

-   [When to Propose a Search Index](#when-to-propose-a-search-index) (Lines
    16-33)
-   [Proposing the DDL](#proposing-the-ddl) (Lines 35-70)
-   [Verifying the Index](#verifying-the-index) (Lines 72-82)
-   [Telemetry & Data Retrieval Reference](#telemetry-data-retrieval-reference)
    (Lines 84-99)

## When to Propose a Search Index

Propose a search index when all of the following are true:

*   Queries repeatedly look up specific values (for example, an IP address, an
    ID, or an error code) in `STRING` or `JSON` data. Searches work best when
    they return few results.
*   The table is at least 10 GB. Search indexes are designed for large tables:
    an index on a table smaller than 10 GB is not populated, and queries don't
    use it (`IndexUnusedReason` code `BASE_TABLE_TOO_SMALL`).
*   The lookups use the `SEARCH` function, or can be rewritten to use `SEARCH`.
    Because `SEARCH` matches tokens rather than substrings, its results can
    differ from `REGEXP_CONTAINS` or `LIKE '%term%'` (wrap exact tokens
    containing delimiters in backticks, such as ``'`req-7f3a9c`'``, and confirm
    with the user). For `REGEXP_CONTAINS` or `LIKE '%term%'` filters, propose
    the index together with the `SEARCH` rewrite from the rule "Use SEARCH on
    columns with a search index" in [sql_optimization.md](sql_optimization.md),
    to apply once the index's `coverage_percentage` is above 0.

## Proposing the DDL

Index only the `STRING` or `JSON` columns that queries search:

```sql
CREATE
  SEARCH INDEX {index_name}
ON `{project_id}.{dataset_id}.{table_id}`({column_1}, {column_2});
```

Or index all `STRING` and `JSON` data in the table:

```sql
CREATE
  SEARCH INDEX {index_name}
ON `{project_id}.{dataset_id}.{table_id}`(ALL COLUMNS);
```

Analyzer option (`analyzer`):

*   `LOG_ANALYZER` (default) works well for machine-generated logs and has rules
    for tokens such as IP addresses and emails. `NO_OP_ANALYZER` matches
    pre-processed data exactly. `PATTERN_ANALYZER` extracts tokens with a
    regular expression. With a non-default analyzer, queries must pass the same
    analyzer to `SEARCH` (for example, `SEARCH(email, 'kim', analyzer =>
    'NO_OP_ANALYZER')`).

For example:

```sql
CREATE
  SEARCH INDEX {index_name}
ON
  `{project_id}.{dataset_id}.{table_id}`(ALL COLUMNS)
  OPTIONS (analyzer = 'NO_OP_ANALYZER');
```

## Verifying the Index

Every search index proposal must tell the user how to verify it, in two steps:

1.  **Coverage, before relying on the index:** Check that `index_status` is
    `ACTIVE` and `coverage_percentage` is above 0. A `coverage_percentage` of 0
    means the index is not usable in a `SEARCH` query, even if some data has
    already been indexed.
2.  **Usage, after queries run:** Check that `index_usage_mode` is `FULLY_USED`
    or `PARTIALLY_USED`. For `UNUSED` or `PARTIALLY_USED`, read the
    `index_unused_reasons` codes (for example, `BASE_TABLE_TOO_SMALL`).

## Telemetry & Data Retrieval Reference

If the `bigquery-observability` skill is available in your workspace, refer to
its telemetry references for the query templates. All decision rules and DDL
templates are self-contained within this guide. Without that skill, check
`index_status` and `coverage_percentage` in the dataset-qualified
`INFORMATION_SCHEMA.SEARCH_INDEXES` view, and `search_statistics` in the
region-qualified `INFORMATION_SCHEMA.JOBS` view.

*   **Index Coverage:** See the `bigquery-observability` skill
    (`references/storage_footprints.md`, section "Search Index Coverage Query").
*   **Index Usage:** See the `bigquery-observability` skill
    (`references/job_performance_queries.md`, section "Search Index Usage") for
    `search_statistics.index_usage_mode` and `index_unused_reasons`. For a
    single job, `bq show --format=prettyjson --location={location} -j
    {project_id}:{job_id}` returns `statistics.query.searchStatistics`.
