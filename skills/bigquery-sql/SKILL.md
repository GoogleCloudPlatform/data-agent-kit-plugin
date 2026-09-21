---
name: bigquery-sql
license: Apache-2.0
metadata:
  version: v2
  publisher: google
description: >-
  Provides BigQuery SQL query optimization techniques, execution best practices, and performance tuning rules for high-efficiency querying. Use when optimizing BigQuery SQL queries, reducing query costs, or designing performant SQL transformations.
---

# BigQuery SQL Optimization

Performance and efficiency guidelines for BigQuery SQL queries. Includes rules
for column pruning, predicate pushdown, join optimization, and materialization
strategies.

## SQL Optimization Rules

> [!TIP] Always include a **"Summary of Optimizations"** section listing only
> the optimizations applied.

### Always Apply (Automatic)

-   **Column Pruning**: Remove unnecessary columns from all query stages.
-   **Common Subexpression Reuse**: Factor out identical expressions to avoid
    redundant computation.
-   **Predicate Pushdown**: Apply `WHERE` filters as early as possible.
-   **Early Aggregation**: Perform `GROUP BY` before joins when possible.
-   **Intermediate Materialization**: Choose `VIEW` vs `TABLE` for intermediate
    nodes based on efficiency.

#### Intermediate Node Strategy

-   **`VIEW`**: Small datasets or simple transformations.
-   **`TABLE`**: Large datasets, expensive computations, or nodes reused
    multiple times.

### Always Rewrite (Mandatory)

-   **`WHERE <col> IN (SELECT ...)`**: Replace With `WHERE EXISTS (SELECT 1 FROM
    ...)`
-   **`WHERE (SELECT COUNT(*) ...) > 0`**: Replace With `WHERE EXISTS (SELECT 1
    FROM ...)`

### Propose with Confirmation (Conditional)

-   **`UNION` → `UNION ALL`**: Faster (skips deduplication), but permits
    duplicate rows.
-   **`COUNT(DISTINCT)` → `APPROX_COUNT_DISTINCT`**: Faster and lower memory,
    but approximate.
