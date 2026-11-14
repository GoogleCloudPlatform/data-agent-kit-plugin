# GRAPH_TABLE Syntax and SQL Integration

Load this reference only when a query must **join graph results with a separate
relational (non-graph) table**, or feed values from an outer SQL table into the
graph scope. For plain aggregation / grouping / counts / top-N over graph
matches, do NOT use `GRAPH_TABLE` — standalone GQL (`GRAPH ... MATCH ... RETURN
... ORDER BY ... LIMIT`) handles those natively, as described in the core skill.

The `GRAPH_TABLE` table-valued function is the mechanism for integrating
property graph queries with standard SQL operations in BigQuery when they cross
the graph/relational boundary.

## When to Use GRAPH_TABLE

You **SHOULD** use `GRAPH_TABLE()` only when your query must cross the
graph/relational boundary. Use it for:

-   **Relational Joins**: Joining graph query results with relational tables or
    other `GRAPH_TABLE` calls.
-   **Passing outer values in**: parameterized `GRAPH_TABLE` that references a
    column from an earlier table in the SQL `FROM` clause.
-   **SQL-side post-processing**: applying standard SQL clauses (`GROUP BY`,
    `HAVING`, window functions, pagination) *on top of* a relational join with
    graph output. (For aggregation over graph matches alone, use standalone
    GQL.)

## Basic Syntax

The basic structure of a `GRAPH_TABLE` query involves specifying the graph name,
the GQL statements, and a `COLUMNS` clause to define the output relational
schema.

```sql
SELECT
  src_account_id,
  COUNT(*) AS transfer_count,
  SUM(amount) AS total_transfer_volume
FROM GRAPH_TABLE(
    <project>.<dataset>.<graph>
    MATCH (src:Account)-[t:Transfers]->(dst:Account)
    WHERE src.is_blocked = true
    COLUMNS (src.id AS src_account_id, t.amount AS amount)
)
GROUP BY src_account_id
HAVING total_transfer_volume > 10000
ORDER BY total_transfer_volume DESC
```

## The COLUMNS Clause

The `COLUMNS` clause is mandatory if you want to explicitly define the returned
table's schema.

-   **Explicit Projection**: It limits the output to only the specified
    expressions from the graph query scope.
-   **Anonymous Columns**: You *must* alias any expressions in the `COLUMNS`
    clause if they generate an anonymous column (e.g., `COLUMNS (t.amount * 2 AS
    doubled_amount)`).
-   **Default Behavior**: If the `COLUMNS` clause is entirely omitted,
    `GRAPH_TABLE` returns all graph pattern variables present in the query
    scope.
-   **Aggregations**: You can include standard SQL aggregate functions directly
    within the `COLUMNS` clause to perform grouping and aggregation across the
    rows of the resulting graph matches.

## Joins with Relational Tables

You can join the result of `GRAPH_TABLE` with other standard BigQuery tables or
even other `GRAPH_TABLE` results using standard SQL semantics (e.g., `JOIN`,
`LEFT JOIN`).

To make a `GRAPH_TABLE` aware of variables from an earlier table in the `FROM`
clause, you can use parameterized `GRAPH_TABLE`. In the example below, `a.id`
from the `Accounts` table is passed into the `GRAPH_TABLE` scope:

```sql
SELECT
  a.name,
  g.total_amount
FROM Accounts AS a
JOIN GRAPH_TABLE(
    <project>.<dataset>.<graph>
    MATCH (src:Account {id: a.id})-[t:Transfers]->(dst:Account)
    COLUMNS (SUM(t.amount) AS total_amount)
) AS g
```
