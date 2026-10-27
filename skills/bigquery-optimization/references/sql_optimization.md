# BigQuery SQL Optimization

Guidance for optimizing the user's SQL by applying a list of optimization rules.
Apply any of the rules listed below to the provided SQL. If none of the rules
apply, tell the user that their query is already optimal. Only consult the list
of rules in the subsections in this file.

> [!TIP] Always include a **"Summary of Optimizations"** section listing only
> the optimizations applied.

## Table of Contents

-   [SQL optimization rules for reducing slot-time](#sql-optimization-rules-for-reducing-slot-time)
    (Lines 52-588)
    -   [Materialize a CTE with temporary tables](#materialize-a-cte-with-temporary-tables)
        (Lines 54-94)
    -   [Order multiple temporary tables or variables in reference order](#order-multiple-temporary-tables-or-variables-in-reference-order)
        (Lines 96-161)
    -   [Add DISTINCT to semijoin subqueries](#add-distinct-to-semijoin-subqueries)
        (Lines 163-209)
    -   [Replace REGEXP_CONTAINS with LIKE](#replace-regexp_contains-with-like)
        (Lines 211-229)
    -   [Use SEARCH on columns with a search index](#use-search-on-columns-with-a-search-index)
        (Lines 231-279)
    -   [In a WHERE clause, use a BETWEEN expression instead of the EXTRACT function](#in-a-where-clause-use-a-between-expression-instead-of-the-extract-function)
        (Lines 281-314)
    -   [Add a LIMIT clause to an ORDER BY clause](#add-a-limit-clause-to-an-order-by-clause)
        (Lines 316-346)
    -   [Remove an ORDER BY clause from a CREATE TABLE statement](#remove-an-order-by-clause-from-a-create-table-statement)
        (Lines 348-378)
    -   [Compare date columns to DATE literals, not string casts](#compare-date-columns-to-date-literals-not-string-casts)
        (Lines 380-410)
    -   [Add a null filter to a NOT IN subquery](#add-a-null-filter-to-a-not-in-subquery)
        (Lines 412-441)
    -   [Replace a WHERE IN OR IN clause with LEFT JOINs](#replace-a-where-in-or-in-clause-with-left-joins)
        (Lines 443-479)
    -   [Replace exact aggregates with approximate aggregates](#replace-exact-aggregates-with-approximate-aggregates)
        (Lines 481-510)
    -   [Pre-aggregate join inputs before joining](#pre-aggregate-join-inputs-before-joining)
        (Lines 512-588)
-   [SQL optimization rules for reducing amount of data](#sql-optimization-rules-for-reducing-amount-of-data)
    (Lines 590-837)
    -   [Replace `SELECT *` with a specific column list](#replace-select-with-a-specific-column-list)
        (Lines 592-629)
    -   [Check the query filters on the partitioned column](#check-the-query-filters-on-the-partitioned-column)
        (Lines 631-837)
        -   [Fetching table schemas from BigQuery](#fetching-table-schemas-from-bigquery)
            (Lines 793-821)
        -   [Validating a rewrite with a dry run](#validating-a-rewrite-with-a-dry-run)
            (Lines 823-837)

## SQL optimization rules for reducing slot-time

### Materialize a CTE with temporary tables

If there is a CTE clause that is referenced multiple times, suggest
materializing it into a temporary table by wrapping the CTE clause in a `CREATE
TEMP TABLE AS` statement.

Rationale: CTE clauses are evaluated every time a query references them;
materializing a CTE into a temporary table means that it will only be evaluated
once.

Here is an example of a query where multiple CTEs are referenced multiple times:

```sql
WITH t1 AS (SELECT a0 FROM a),
     t2 AS (SELECT x.a0 FROM t1, t1 x),
     t3 AS (SELECT x.a0 FROM t2, t2 x),
     t4 AS (SELECT x.a0 FROM t3, t3 x)
SELECT
  a0,
  COUNT(*)
FROM
  t4
GROUP BY
  1;
```

Here is how the rewritten query should look:

```sql
CREATE TEMP TABLE t1 AS (SELECT a0 FROM a);
CREATE TEMP TABLE t2 AS (SELECT x.a0 FROM t1, t1 x);
CREATE TEMP TABLE t3 AS (SELECT x.a0 FROM t2, t2 x);
CREATE TEMP TABLE t4 AS (SELECT x.a0 FROM t3, t3 x);
SELECT
  a0,
  COUNT(*)
FROM
  t4
GROUP BY
  1;
```

### Order multiple temporary tables or variables in reference order

When applying the rules for materializing CTEs into temporary tables (see
subsection "Materialize a CTE with temporary tables") or declaring variables
(see rule 3.b. in the subsection "Check the query filters on the partitioned
column"), order them in the order that they are referenced in the query.
Temporary tables and variables must come before other temporary tables or
variables that reference them.

Example of a query with a temporary table and a variable that is out of order:

```sql
DECLARE last_order_date DEFAULT (
  SELECT
    max(date)
  FROM
    quantity_sold_per_day
);

CREATE TEMP TABLE quantity_sold_per_day AS (
  SELECT
    EXTRACT(DATE from timestamp) AS date,
    SUM(quantity) as total_quantity
  FROM
    orders
  GROUP BY 1
);

SELECT
  timestamp,
  order_id,
  quantity
FROM
  orders
WHERE
  timestamp >= last_order_date;
```

Here is the corrected order of the temporary table and variable:

```sql
CREATE TEMP TABLE quantity_sold_per_day AS (
  SELECT
    EXTRACT(DATE from timestamp) AS date,
    SUM(quantity) as total_quantity
  FROM
    orders
  GROUP BY 1
);

DECLARE last_order_date DEFAULT (
  SELECT
    max(date)
  FROM
    quantity_sold_per_day
);

SELECT
  timestamp,
  order_id,
  quantity
FROM
  orders
WHERE
  timestamp >= last_order_date;
```

### Add DISTINCT to semijoin subqueries

If the query contains a semijoin, rewrite the subquery to have a DISTINCT clause
only if the subquery does not have a GROUP BY clause. If the subquery has a
GROUP BY clause, then the subquery should remain as is. If the subquery does not
have a GROUP BY clause, then the subquery should be rewritten to have a DISTINCT
clause.

Rationale: `DISTINCT` in the semijoin subquery reduces the amount of data to
check for in the `IN` clause.

Here is an example of a query with a semijoin whose subquery does not have a
GROUP BY clause:

```sql
SELECT
  t1.a0
FROM
  test.a t1
WHERE
  t1.a2 IN (SELECT t2.a2 FROM test.a t2);
```

Here is the query rewritten with a DISTINCT clause:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  t1.a2 IN (SELECT DISTINCT t2.a2 FROM test.a t2);
```

Here is an example of a query with a semijoin whose subquery has a GROUP BY
clause and should not be rewritten:

```sql
SELECT
  t1.a0
FROM
  test.a t1
WHERE
  t1.a2 IN (SELECT t2.a2, count(*) FROM test.a t2 group by 1);
```

This query should not be rewritten since the subquery has an aggregation.

### Replace REGEXP_CONTAINS with LIKE

If the query contains the function `REGEXP_CONTAINS` where the regular
expression uses wildcards, rewrite the query to use the `LIKE` operator instead.

Rationale: `LIKE` is more performant than `REGEXP_CONTAINS`.

Examples of valid rewrites:

*   `REGEXP_CONTAINS(a, '.*abc.*')` should be rewritten as `a LIKE '%abc%'`
*   `REGEXP_CONTAINS(a, '^abc.*')` should be rewritten as `a LIKE 'abc%'`
*   `REGEXP_CONTAINS(a, '.*abc$')` should be rewritten as `a LIKE '%abc'`
*   `REGEXP_CONTAINS(a, '.*abc.*def.*')` should be rewritten as `a LIKE
    '%abc%def%'`

Example of where `REGEXP_CONTAINS` should not be rewritten:

*   `REGEXP_CONTAINS(a, 'abc')` should not be rewritten as `a LIKE '%abc%'`
    since the query does not contain any wildcards.

### Use SEARCH on columns with a search index

If the query filters a column with `REGEXP_CONTAINS` or `LIKE '%term%'` and the
column is covered by an `ACTIVE` search index with a `coverage_percentage` above
0 (the user confirms, or `INFORMATION_SCHEMA.SEARCH_INDEXES` shows the column or
`ALL COLUMNS` in `ddl`), suggest rewriting the filter to use the `SEARCH`
function. If no index exists, propose the rewrite only together with an index
proposal, to apply once coverage is above 0. Do not rewrite `=`, `IN`, `LIKE
'prefix%'`, `STARTS_WITH`, or `ENDS_WITH` comparisons with string literals;
BigQuery can already use the search index for them.

`SEARCH` matches tokens, not substrings. With the default `LOG_ANALYZER` it is
case-insensitive, and `SEARCH(a, '192.0.2.1')` matches any row that contains the
tokens `192`, `0`, `2`, and `1` in any order; enclose the term in backticks for
an exact match. If the index uses a non-default analyzer, pass the same analyzer
to `SEARCH`. Because the results can differ from the original filter, propose it
and wait for the user to confirm before applying; do not include it in an
otherwise-automatic rewrite. For when to create an index, see
[search_indexes.md](search_indexes.md).

Rationale: A search index lets BigQuery skip base table data that doesn't
contain the search tokens, which reduces bytes processed and slot time. Savings
are largest when the matching rows are a small fraction of the table.

Here is an example of a query that filters an indexed column with `LIKE`:

```sql
SELECT
  Level,
  Source,
  Message
FROM
  my_dataset.Logs
WHERE
  Message LIKE '%94.60.64.181%';
```

Here is the rewritten query with `SEARCH`:

```sql
SELECT
  Level,
  Source,
  Message
FROM
  my_dataset.Logs
WHERE
  SEARCH(Message, '`94.60.64.181`');
```

### In a WHERE clause, use a BETWEEN expression instead of the EXTRACT function

If the column is a `DATE` type: rewrite filter expressions of the form
`EXTRACT(YEAR FROM date_column) = 2024` to `date_column BETWEEN '2024-01-01' AND
'2024-12-31'`.

If the column is a `TIMESTAMP` type: rewrite filter expressions of the form
`EXTRACT(YEAR FROM timestamp_column) = 2024` to `timestamp_column >= '2024-01-01
00:00:00' AND timestamp_column < '2025-01-01 00:00:00'`.

Rationale: BigQuery can statically evaluate `BETWEEN` expressions; it cannot
statically evaluate functions applied to columns.

Example of a query with a date filter expression:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  EXTRACT(YEAR FROM t1.a2) = 2024;
```

Here is the query rewritten with a date filter expression:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  t1.a2 BETWEEN '2024-01-01' AND '2024-12-31';
```

### Add a LIMIT clause to an ORDER BY clause

If a query has an `ORDER BY` clause without a `LIMIT` clause, suggest adding a
`LIMIT` clause.

Rationale: In vast majority of cases, users do not need the full results of an
`ORDER BY` clause; `LIMIT` improves the performance of the `ORDER BY` clause.

Example of a query with an `ORDER BY` clause without a `LIMIT` clause:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
ORDER BY
  t1.a2;
```

Here is the example query rewritten with a `LIMIT` clause:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
ORDER BY
  t1.a2
LIMIT
  1000;
```

### Remove an ORDER BY clause from a CREATE TABLE statement

If a query is a `CREATE TABLE` or `CREATE OR REPLACE TABLE` statement, remove an
`ORDER BY` clause if it has one.

Rationale: When writing to a table, BigQuery will order the data as needed,
making the `ORDER BY` unnecessary.

Here is an example of a query with a `CREATE OR REPLACE TABLE` statement with an
`ORDER BY` clause:

```sql
CREATE OR REPLACE TABLE test.a AS (
  SELECT
    t1.a0
  FROM
    test.b AS t1
  ORDER BY t1.a2
);
```

Here is the query rewritten with the `ORDER BY` clause removed:

```sql
CREATE OR REPLACE TABLE test.a AS (
  SELECT
    t1.a0
  FROM
    test.b AS t1
);
```

### Compare date columns to DATE literals, not string casts

Rewrite filter expressions of the form `CAST(date_column AS STRING) =
'2025-01-15'` to `date_column = DATE('2025-01-15')`.

Rationale: BigQuery can statically evaluate comparisons against the column
unless the column has a function applied to it.

Example of a query with a date filter expression that casts a `DATE` column to a
string:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  CAST(DATE(date_column) AS STRING) = '2025-01-15';
```

Here is the query rewritten with a date filter expression that does not cast the
`DATE` column but instead casts the string literal to a `DATE`:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  date_column = DATE('2025-01-15');
```

### Add a null filter to a NOT IN subquery

Rewrite subqueries within `NOT IN` clauses to add a `WHERE` clause that excludes
nulls.

Rationale: It allows BigQuery to use the more performant anti-hash join instead
of the slower left outer hash join.

Here is an example of a query with a subquery in a `NOT IN` clause:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  t1.a2 NOT IN (SELECT t2.a2 FROM test.b AS t2);
```

Here is the rewritten query that adds a `WHERE` clause to exclude nulls in the
`NOT IN` subquery:

```sql
SELECT
  t1.a0
FROM
  test.a AS t1
WHERE
  t1.a2 NOT IN (SELECT t2.a2 FROM test.b AS t2 WHERE t2.a2 IS NOT NULL);
```

### Replace a WHERE IN OR IN clause with LEFT JOINs

If the query contains a `WHERE ... IN (...) OR ... IN (...)` clause, which is an
expression that follows this pattern: `columnA IN (subqueryX) OR columnB in
(subqueryY)`, then rewrite the query to use `LEFT JOIN` clauses.

Rationale: `WHERE ... IN (...) OR ... IN (...)` uses a cross product join, which
can be significantly more expensive than `LEFT JOIN`s.

Example of a query with a `WHERE` clause that has two `IN` clauses:

```sql
SELECT
  t1.a0,
  t1.a1
FROM
  test.a AS t1
WHERE
  t1.a2 IN (SELECT t2.a2 FROM test.b AS t2)
  OR t1.a3 IN (SELECT t3.a3 FROM test.c AS t3);
```

Here is the rewritten query with `LEFT JOIN` clauses:

```sql
SELECT
  t1.a0,
  t1.a1
FROM
  test.a AS t1
LEFT JOIN (SELECT DISTINCT a2 FROM test.b) AS t2
  ON t1.a2 = t2.a2
LEFT JOIN (SELECT DISTINCT a3 FROM test.c) AS t3
  ON t1.a3 = t3.a3
WHERE
  t2.a2 IS NOT NULL OR t3.a3 IS NOT NULL;
```

### Replace exact aggregates with approximate aggregates

If the query contains the expression `COUNT(DISTINCT ...)`, suggest rewriting to
use `APPROX_COUNT_DISTINCT(...)`.

This changes exact counts to approximate ones. Propose it and wait for the user
to confirm before applying; do not include it in an otherwise-automatic rewrite.

Rationale: Approximate aggregates are significantly more efficient than exact
aggregates, however at the cost of precision. As a general rule of thumb, large
aggregations should use approximate aggregates, and small aggregations should
use exact aggregates.

Here is an example of a query with a `COUNT(DISTINCT ...)` expression:

```sql
SELECT
  COUNT(DISTINCT t1.a0)
FROM
  test.a AS t1;
```

Here is the rewritten query with `APPROX_COUNT_DISTINCT`:

```sql
SELECT
  APPROX_COUNT_DISTINCT(t1.a0)
FROM
  test.a AS t1;
```

### Pre-aggregate join inputs before joining

If a `WITH` CTE joins a detail table to a parent table without aggregating and
the outer query immediately aggregates (`GROUP BY`) that CTE's rows by the join
key, rewrite the CTE to pre-aggregate the detail table by the join key before
joining to the parent table in the outer query, and place the largest table
first (leftmost) in the `JOIN` clause. Only apply this rule when the query has a
`WITH` CTE that performs an unaggregated `JOIN` followed by an outer `GROUP BY`;
do not apply it to flat queries without a join CTE or to queries that already
aggregate in a semijoin (`WHERE ... IN (SELECT ... GROUP BY ...)`).

Rationale: Reducing data with `GROUP BY` before a `JOIN` avoids shuffling and
multiplying detail rows across the join stage (`records_written >> records_read`
and `shuffle_output_bytes_spilled > 0` in `job_stages`), reducing both slot-time
and shuffle memory usage. When diagnosing a Cartesian join explosion, also
inspect the `JOIN` clauses for unintentional `CROSS JOIN`s, missing `ON`
conditions, or non-selective join predicates (duplicate keys on both sides), and
filter out `NULL` or skewed dummy keys (e.g., `WHERE customer_id IS NOT NULL AND
customer_id != 'GUEST'`) before joining.

Here is an example of a query that joins `comments` and `users` before
aggregating:

```sql
WITH
  users_posts AS (
    SELECT
      u.display_name,
      u.reputation,
      c.score,
      c.text,
      c.user_id
    FROM
      `my_dataset.comments` AS c
    JOIN
      `my_dataset.users` AS u
      ON c.user_id = u.id
  )
SELECT
  display_name,
  reputation,
  AVG(score) AS avg_score,
  COUNT(text) AS comments_count
FROM
  users_posts
GROUP BY
  display_name,
  reputation,
  user_id;
```

Here is the rewritten query that pre-aggregates `comments` by `user_id` before
joining to `users`:

```sql
WITH
  comments_by_user AS (
    SELECT
      user_id,
      AVG(score) AS avg_score,
      COUNT(text) AS comments_count
    FROM
      `my_dataset.comments`
    GROUP BY
      user_id
  )
SELECT
  u.display_name,
  u.reputation,
  c.avg_score,
  c.comments_count
FROM
  comments_by_user AS c
JOIN
  `my_dataset.users` AS u
  ON c.user_id = u.id;
```

## SQL optimization rules for reducing amount of data

### Replace `SELECT *` with a specific column list

If the query contains a `SELECT *`, tell the user to rewrite to select only the
columns needed. Only suggest this for the top-level `SELECT` in the main query
or in `CREATE TEMP TABLE` statements. Do not suggest this for subqueries in
`WITH` and `WHERE` clauses.

Rationale: Selecting only the necessary columns reduces the amount of data that
BigQuery needs to read and process. `SELECT *` in subqueries do not necessarily
increase the amount of data read, as BigQuery can prune the columns in the
subquery.

Example of a query with a top-level `SELECT *` for which the user should specify
a column list:

```sql
SELECT
  *
FROM
  test;
```

Example of a query with a subquery that has `SELECT *`, which should not need to
be rewritten:

```sql
SELECT
  orders.order_id,
  SUM(orders.quantity) as total_quantity
FROM
  orders
WHERE EXISTS (
    SELECT *
    FROM line_items
    WHERE orders.order_id = line_items.order_id
  )
GROUP BY 1;
```

### Check the query filters on the partitioned column

Check the given query on how it filters (either a `WHERE` clause in a `SELECT`
statement or `ON` clause in a `JOIN` statement) on the partitioned column.

Steps to follow:

1.  Find all referred tables in `SELECT` or `JOIN` statements. If the query does
    not specify the project ID, use the project ID from the context.

    Example 1 where the referred tables follow the format `DATASET.TABLE` and do
    not specify the project ID:

    ```sql
    SELECT
      COUNT(o_orderkey)
    FROM
      my_dataset.orders
    INNER JOIN
      my_dataset.customers
      ON (o_custkey = c_custkey)
    ```

    Assuming that the project ID from the context is `my-project-id`, the
    referred tables in Example 1 are:

    -   `my-project-id.my_dataset.orders`
    -   `my-project-id.my_dataset.customers`

    Example 2 where the referred tables follow the format
    `PROJECT_ID.DATASET.TABLE`:

    ```sql
    SELECT
      COUNT(o_orderkey)
    FROM
      `my-project-id.my_dataset.orders`
    INNER JOIN
      `my-project-id.my_dataset.customers`
      ON (o_custkey = c_custkey)
    ```

    The referred tables in Example 2 are:

    -   `my-project-id.my_dataset.orders`
    -   `my-project-id.my_dataset.customers`

2.  Fetch the table schema from BigQuery for each referred table and get the
    partitioned column for each table if it exists.

    In the JSON output, use the field
    `partitionDefinition.partitionedColumn.field`. Note that this field is
    repeated, but in practice only one field is populated when the table is
    partitioned.

3.  For each table with a partitioned column, check the following rules:

    a. Ensure that the query contains a filter condition for the partitioned
    column for each table reference. If there is no filter condition for the
    partitioned column and the table has a partitioned column, tell the user.

    Rationale: If a table is partitioned, queries should leverage the
    partitioning to reduce the amount of data to read.

    Note that if the table's schema specifies that the partition filter is
    required (as specified in the field `requirePartitionFilter`), then no
    filter condition will cause the query to return an error.

    Example of query that does *not* have a filter condition on a partitioned
    column `o_orderdate` for table reference `my_dataset.orders`:

    ```sql
    SELECT
      COUNT(o_orderkey)
    FROM
      my_dataset.orders
    INNER JOIN
      my_dataset.customers
      ON (o_custkey = c_custkey)
    ```

    Example suggested improvement to show users:

    ```sql
    SELECT
      COUNT(o_orderkey)
    FROM
      my_dataset.orders
    INNER JOIN
      my_dataset.customers
      ON (o_custkey = c_custkey)
    WHERE
      -- Ask the user to provide the start and end dates.
      o_orderdate BETWEEN @start_date AND @end_date
    ```

    b. If the filter condition for the partitioned column is dynamic
    (specifically, a scalar subquery or a column-dependent aggregation), rewrite
    the query so that the filter condition is in a variable.

    Example of a query with a dynamic filter condition that is doing an
    aggregation on a partitioned column:

    ```sql
    SELECT o_orderstatus, o_orderdate
      FROM `my_dataset.orders`
    WHERE
      o_orderdate = (
        SELECT max(o_orderdate) FROM `my_dataset.orders`
      );
    ```

    Here is the query rewritten so that the filter condition is in a variable:

    ```sql
    DECLARE max_order_date DATE DEFAULT (
      SELECT max(o_orderdate) FROM `my_dataset.orders`
    );
    SELECT o_orderstatus, o_orderdate
    FROM `my_dataset.orders`
    WHERE
      o_orderdate = max_order_date;
    ```

    Note that the variable `max_order_date` still scans the entire table,
    however the full scan is still more efficient than the original query. If
    the table is configured with `require_partition_filter = true`, then the
    user needs to add an additional filter condition within the variable
    `max_order_date`.

    c. Isolate the partitioned column from unsupported functions and arithmetic
    expressions. BigQuery prunes partitions when the `WHERE` filter compares the
    partitioned column (or a documented pruning-supported built-in function on
    the partitioned column, such as `DATE(ts_col)`, `EXTRACT(DATE FROM ts_col)`,
    `CAST(ts_col AS DATE)`, `DATE_TRUNC`, or `TIMESTAMP_TRUNC` with constant
    arguments) against a constant expression. Wrapping the partitioned column in
    an unsupported function (such as `FORMAT_DATE` or `EXTRACT(MONTH FROM
    ts_col)`) or applying arithmetic to the partitioned column (such as
    `ts_col + INTERVAL 1 DAY > CURRENT_TIMESTAMP()`) prevents partition pruning.
    Rewrite the filter to isolate the partitioned column on one side of the
    comparison:

    ```sql
    -- Unpruned (arithmetic on the partitioned column):
    SELECT
      order_id,
      total_amount
    FROM
      `my_dataset.orders`
    WHERE
      order_timestamp + INTERVAL 1 DAY > CURRENT_TIMESTAMP();

    -- Rewritten to isolate the partitioned column for partition pruning:
    SELECT
      order_id,
      total_amount
    FROM
      `my_dataset.orders`
    WHERE
      order_timestamp > CURRENT_TIMESTAMP() - INTERVAL 1 DAY;
    ```

#### Fetching table schemas from BigQuery

Use the following shell command to fetch the table schema from BigQuery:

-   If the query specifies the project ID:

    ```bash
    bq show --format=prettyjson PROJECT_ID:DATASET.TABLE
    ```

    For example, given this table reference: `my_project:my_dataset.orders`, run
    the command:

    ```bash
    bq show --format=prettyjson my_project:my_dataset.orders
    ```

-   If the query does not specify the project ID:

    ```bash
    bq show --format=prettyjson DATASET.TABLE
    ```

    For example, given this table reference: `my_dataset.orders`, run the
    command:

    ```bash
    bq show --format=prettyjson my_dataset.orders
    ```

#### Validating a rewrite with a dry run

After rewriting a query to add partition filters or replace `SELECT *` with
explicit columns, instruct the user to validate the estimated bytes processed
before executing the query using a dry run:

```bash
bq query --use_legacy_sql=false --dry_run "{sql_query}"
```

A dry run validates SQL syntax and returns the deterministic
`totalBytesProcessed` estimate after partition pruning and column pruning
without running the query or incurring compute charges. Note that block-pruning
savings from clustered columns are determined dynamically during execution and
are not reflected in the dry-run upper bound.
