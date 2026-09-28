---
name: bigquery-graph-query
license: Apache-2.0
metadata:
  version: v2
  publisher: google
description: >-
  Provides guidelines and best practices for querying BigQuery property graphs and semantic graphs: native GQL (Graph Query Language) pattern matching, multi-hop and variable-length paths, aggregation, top-N, path extraction, output formatting (graph visualization with TO_JSON vs tabular), GRAPH_TABLE relational SQL integration, and semantic graph querying via the GRAPH_EXPAND TVF with starting-node view selection and AGG() measures. Also covers hybrid semantic search, combining `VECTOR_SEARCH` candidate generation with graph traversal when a node carries an embedding-backed property. Use when querying graph topology, node/edge connections, paths, or semantic measures over an existing BigQuery graph. Don't use for Cypher or non-BigQuery graph databases, or for creating/modifying a graph schema.
---

# BigQuery Graph Query Guidelines

You are querying a BigQuery property graph or semantic graph. You **MUST
exclusively use the BigQuery GoogleSQL GQL and SQL standards**. **NEVER, under
any circumstances, generate or consider Cypher queries.** Follow the
instructions below exactly rather than relying on general graph-query knowledge.

## Query Paradigm Decision Guide

Before writing any query, determine whether you are querying a **Property
Graph** or a **Semantic Graph**:

-   **Property Graph (topology, paths, connections)**:
    -   **Schema in Context**: `<property_graph>` DDL / node & edge tables.
    -   **Target Query Engine / Mechanism**: **Native GQL** (`GRAPH ... MATCH
        ... RETURN`) by default; `GRAPH_TABLE` if joining relational tables.
-   **Semantic Graph (business metrics, dimensions, measures)**:
    -   **Schema in Context**: `<semantic_graph start_node="X">` flattened
        views.
    -   **Target Query Engine / Mechanism**: **`GRAPH_EXPAND` TVF** with
        `start_node => "X"` and `AGG()` measures.
-   **Semantic Graph Fallback (unqueryable entity / cyclic path)**:
    -   **Schema in Context**: Node has no `<semantic_graph start_node="X">`
        view.
    -   **Target Query Engine / Mechanism**: **Native GQL fallback** via
        `GRAPH_TABLE` over the `<property_graph>` with manual SQL aggregations.

--------------------------------------------------------------------------------

## Reference Files (rarely needed — do NOT load for standard queries)

**This document is self-sufficient for the vast majority of questions**,
including matching, multi-hop and variable-length paths, filtering,
**aggregation / grouping / top-N**, existence checks, output formatting, and
`GRAPH_EXPAND` queries. For these, generate the query directly from the rules
below — do **not** open the companion files.

Only read a companion file when the query genuinely needs one of these
**uncommon** capabilities:

-   **Joining graph results with a separate relational (non-graph) table**, or
    passing values from an outer SQL table into the graph scope (parameterized
    `GRAPH_TABLE`):
    [graph-table-and-sql-integration.md](references/graph-table-and-sql-integration.md)
-   **Advanced element-identity functions** (`SOURCE_NODE_ID`,
    `DESTINATION_NODE_ID`, `ELEMENT_ID`, `LABELS`), or deep **performance
    tuning** of a slow/large traversal beyond the optimization rules in this
    core:
    [gql-advanced-functions-and-perf.md](references/gql-advanced-functions-and-perf.md)
-   **Correlated-subquery edge cases** beyond the WHERE-vs-FILTER rule below
    (e.g. `VALUE`/`ARRAY` subquery correlation limits):
    [gql-subqueries.md](references/gql-subqueries.md)
-   **Hybrid semantic + graph search**, when the question is conceptual rather
    than key-based **and** a node has an embedding-backed property, so
    candidates must come from `VECTOR_SEARCH` before traversal (embedding calls
    bill per invocation — do not open this otherwise):
    [hybrid-vector-graph-search.md](references/hybrid-vector-graph-search.md)

If none of the above clearly applies, this core document is sufficient.

--------------------------------------------------------------------------------

## PART 1: Property Graph Querying (Native GQL)

### Pre-generation Checklist

Before generating any GQL, you MUST:

1.  **Identify Output Intent**: Determine if the user intends to **visualize a
    graph network** (requires `TO_JSON()`) or **view tabular data** (requires
    specific properties).
2.  **Verify Language Standard**: Confirm the query will use **BigQuery
    GoogleSQL GQL**. NEVER use Cypher.

### Core Directives

1.  **Default Query Construction (Standalone GQL)**: Write standalone GQL
    queries using the `RETURN` statement natively (`GRAPH ... MATCH ...
    RETURN`). This natively supports aggregation, grouping, and top-N (see
    below). **Only** use the `GRAPH_TABLE` table-valued function when you must
    join graph results with a separate relational table (see the SQL-integration
    reference).
2.  **Keyword Escaping**: You **MUST** enforce backticks around any reserved SQL
    and GQL keywords used as identifiers (e.g., `order`, `begin`, `path` used as
    column, label, or variable names).
3.  **Strictly Follow Graph Schema**: All labels (e.g., `:Person`, `:Account`)
    and properties (e.g., `n.id`, `e.amount`) used in the query MUST match the
    provided graph schema. Do NOT guess or hallucinate schema elements.
4.  **Result Uniqueness**: Use `DISTINCT` in your `RETURN`/`COLUMNS` clause when
    the user prompt implies they want unique results.
5.  **Graph Path Variables**: When a query involves "paths", "path traversal",
    "path finding", or finding relationships between nodes, you **MUST** assign
    the matched pattern to a path variable (e.g., `MATCH p = ...`).

### Basic Query Construction

A GQL query names the graph, then chains clauses that pipe a "working table"
from one to the next: `MATCH`, `LET` (define a variable/alias), `FILTER` (filter
intermediate results — this is the GQL clause, used between clauses instead of a
trailing `WHERE`), `WITH` (project/sort/group into the next scope), `ORDER BY` /
`LIMIT` / `OFFSET`, and `RETURN` (project the final output).

```sql
GRAPH <project>.<dataset>.<graph>
MATCH (src:Account)-[t:Transfers]->(dst:Account)
LET transfer_amount = t.amount
FILTER transfer_amount > 1000
WITH src, dst, transfer_amount
ORDER BY transfer_amount DESC
LIMIT 50
RETURN src.id AS source, dst.id AS destination, transfer_amount
```

**Chaining with `NEXT`:** Compose multiple linear statements into one compound
query with the `NEXT` keyword — the results of the statement before `NEXT` pipe
into the statement after it.

### Aggregation, Grouping, and Top-N (native standalone GQL)

**You do NOT need `GRAPH_TABLE` for aggregation, grouping, counts, sums,
averages, "how many", "most/least", or "top N".** Standalone GQL handles these
natively — this covers the majority of analytical questions:

-   **Aggregate functions** go directly in `RETURN` (or `WITH`): `COUNT(*)`,
    `COUNT(DISTINCT x)`, `SUM(e.amount)`, `AVG(...)`, `MIN`/`MAX`.
-   **Implicit GROUP BY**: any non-aggregated expressions in `RETURN`/`WITH`
    become the grouping keys automatically (like standard GQL grouping). There
    is no separate `GROUP BY` clause in standalone GQL — group by listing the
    key columns alongside the aggregate.
-   **Top-N / ranking**: add `ORDER BY <agg> DESC` then `LIMIT <n>`.

```sql
-- "Which 3 entities filed the most filings?" (grouping + top-N, no GRAPH_TABLE)
GRAPH <project>.<dataset>.<graph>
MATCH (e:Entity)-[:Filed]->(f:Filing)
RETURN e.name AS entity, COUNT(f) AS filing_count
ORDER BY filing_count DESC
LIMIT 3
```

```sql
-- "Total transferred out per account" (grouped aggregate)
GRAPH <project>.<dataset>.<graph>
MATCH (src:Account)-[t:Transfers]->(:Account)
RETURN src.id AS account, SUM(t.amount) AS total_out
ORDER BY total_out DESC
```

Use `GRAPH_TABLE` (load the SQL-integration reference) **only** when you must
`JOIN` graph output with a separate relational table or feed outer-table values
into the graph scope.

### Existence Checks and Subqueries (essentials)

For "entities that have / do not have a relationship", "at least one", "where
there exists ..." questions, use a subquery. Two rules prevent the common errors
(load the subqueries reference only for `VALUE`/`ARRAY` correlation edge cases):

1.  **Use `FILTER`, not `WHERE`, for `EXISTS` / `IN` / `LIKE` subqueries.**
    These throw errors inside a `WHERE` clause.
2.  **Re-declare the graph name inside the subquery block.** A subquery `{ ...
    }` must repeat `GRAPH <project>.<dataset>.<graph>` even though the outer
    query already declared it.

```sql
GRAPH <project>.<dataset>.<graph>
MATCH (p:Person)
FILTER EXISTS {
  GRAPH <project>.<dataset>.<graph>
  MATCH (p)-[:Owns]->(:Account)
}
RETURN p.name
```

### Graph Pattern Matching

Node patterns use parentheses `()`; edge patterns use square brackets `[]`
connected with arrows for direction. The BigQuery-specific rules:

#### Node Patterns

-   `MATCH (p:Person|Account)`: the `|` label expression matches nodes that have
    **either** label (OR). You **cannot** use `&` in a label expression.
-   `MATCH (p:Person {id: 1})`: property-filter shorthand.
-   `MATCH (p:Person WHERE p.age > 18)`: inline `WHERE` condition on properties.

#### Edge Patterns

-   `MATCH (a)-[e:Transfers]->(b)`: directed edge (preferred).
-   `MATCH (a)-[e:Transfers {amount: 50}]->(b)`: edge with a property filter.
-   `MATCH (a)-[e:Transfers]-(b)`: undirected (any direction) — **avoid**;
    specify explicit direction for better performance.

#### Pattern Joins

A complex pattern is one or more path patterns separated by commas `,`. If two
comma-separated patterns **share a variable**, BigQuery performs an **equijoin**
on it; if they share none, the result is a **cross join**.

```sql
GRAPH <project>.<dataset>.<graph>
MATCH (src:Account)-[t1:Transfers]->(interm:Account),
      (interm)<-[:Owns]-(p:Person)
RETURN src.id AS account_id, p.name AS owner_name
```

#### Variable-Length Paths and Quantifiers

Find multi-hop connections by appending a quantifier to an edge pattern. **This
syntax differs from Cypher — use the BigQuery form:**

-   `{m, n}`: repeat the edge pattern between `m` and `n` times, e.g.
    `-[e:Transfers]->{1,3}`.
-   **Group Variables**: when an edge variable is quantified (e.g., `e` in
    `-[e:Transfers]->{1,3}`), `e` becomes a **group variable** — an array of the
    matched edges in the path. Interact with it using array functions
    (`ARRAY_LENGTH(e)`) or horizontal aggregation (`SUM(e.amount)`).

#### Path Search Prefixes

Variable-length paths can produce exponential combinations and repeating paths.
Constrain the search between each source/destination pair with a prefix placed
immediately before the path pattern:

-   `ANY`: exactly one arbitrary matching path per unique source/destination
    pair.
-   `ANY SHORTEST`: a single path with the minimum number of edges (hops).
-   `ANY CHEAPEST`: a single path with the minimum total cost, aggregating
    `COST` expressions defined on the edges.

```sql
GRAPH <project>.<dataset>.<graph>
MATCH ANY SHORTEST
  (a:Account {id: 123})-[e:Transferred]->{1,3}(b:Account {id: 456})
RETURN e
```

### Path Extraction Functions

When an entire path is bound to a variable (`MATCH p = (...)`), extract metadata
and elements from it:

-   `PATH_FIRST(p)` / `PATH_LAST(p)`: the starting / terminal node of path `p`.
-   `PATH_LENGTH(p)`: an `INT64` count of the edge hops in path `p`.
-   `NODES(p)` / `EDGES(p)`: an array of the node / edge elements, ordered by
    their sequence in the path.

```sql
GRAPH <project>.<dataset>.<graph>
MATCH p = (a:Account)-[t:Transfers]->{1,3}(b:Account)
RETURN PATH_LENGTH(p) AS hops, TO_JSON(NODES(p)) AS path_nodes
```

For `SOURCE_NODE_ID`, `DESTINATION_NODE_ID`, `ELEMENT_ID`, and `LABELS`, load
the advanced-functions reference.

### Output Formatting: Visualization vs. Tabular

Strictly distinguish **graph visualization** intent from **tabular data** intent
when constructing the `RETURN`/`COLUMNS` clause.

#### 1. Graph Visualization Intent

Use when the user wants to see relationships, paths, topology, networks,
connectivity, or entire entities (nodes/edges) as a whole. **Triggers**:
"visualize", "show the graph", "network", "connections", "find the path",
"relationship between X and Y".

-   **Default to `TO_JSON()`**: unless specific properties (e.g., `n.name`) or
    path metrics (e.g., `PATH_LENGTH(p)`) are explicitly requested, you **MUST**
    wrap all graph topology outputs (nodes, edges, and path variables) in
    `TO_JSON()` so the graphing UI receives full JSON objects.
-   **Limit**: always append `LIMIT 500` unless the user requests a different
    number, to avoid overwhelming the UI.

```sql
GRAPH <project>.<dataset>.<graph>
MATCH p = (:Person)-[:Knows]->(:Person)
RETURN TO_JSON(p) AS full_path
LIMIT 500
```

#### 2. Tabular or Chart Intent

Use when the user focuses on specific attributes, statistics, or metrics.
**Triggers**: "what is the name", "list", "how many", "count", "average", "top
10", "aggregate". Return ONLY the required properties or aggregates; **do NOT**
use `TO_JSON()`.

-   **Example**: `RETURN account.id, SUM(t.amount) AS total_transfer`

### Query Optimization

Apply these principles to every traversal (detailed rationale and the
bidirectional `UNION ALL` example are in the advanced-functions/performance
reference):

1.  **Start from low-cardinality nodes** and push specific property filters
    (e.g., `Account {id: 7}`) as early as possible in `MATCH` to prune the
    search space.
2.  **Specify labels explicitly** on nodes and edges — omitting known labels
    forces full scans over the underlying node/edge tables.
3.  **Avoid bidirectional/undirected traversals** (`(a)-[e]-(b)`) — they carry a
    severe performance penalty. Use explicit `->`/`<-`; to match either
    direction between two nodes, `UNION ALL` two directed queries.
4.  **Prefer a single comprehensive `MATCH`** over chaining several `MATCH`
    statements, giving the optimizer a wider global view of the pattern.

--------------------------------------------------------------------------------

## PART 2: Semantic Graph Querying (GRAPH_EXPAND TVF)

### 1. Query the Flattened View with `GRAPH_EXPAND`

Always query a semantic graph through the `GRAPH_EXPAND` table-valued function
(TVF); never as a table.

-   A graph exposes one or more flattened views, one per **starting node**. In
    your context each view is a separate `<semantic_graph start_node="X">` block
    whose `<ddl>` describes the columns of that specific view. Pick the block
    that fits the question (see Rule 2) and query it by passing the graph name
    **and** the starting node as a **named argument**:

    ```sql
    SELECT ...
    FROM GRAPH_EXPAND("project_id.dataset_id.property_graph_id",
                      start_node => "X")
    WHERE ...
    ```

    The starting node MUST be passed by name (`start_node => "X"`, matching a
    `start_node` value from the context); a positional second argument is
    invalid.

-   **CRITICAL RULE:** The semantic graph is NOT a regular table, even though
    its schema is presented using `CREATE TABLE`. You **MUST NEVER** query it
    directly as a table (e.g., `FROM my_project.my_dataset.my_graph`).

-   **CRITICAL FALLBACK RULE:** If a `GRAPH_EXPAND` query fails (e.g., syntax
    errors or system limits), **DO NOT** fall back to querying the graph or its
    source tables as standard tables. Doing so causes a critical `NOT_FOUND`
    error.

### 2. Choosing the Starting Node (Avoid Under-counting)

Each starting-node view is produced by joining **outward from that node**, and
it keeps exactly one row per entity reachable from the starting node. Entities
that are **not reachable from the starting node are dropped from the view** — so
the wrong starting node silently under-counts.

-   **Rule:** To aggregate a measure `M` that is defined on node `N` (its column
    is named `N_<measure>`, e.g. `Department_total_budget`), use `start_node =>
    "N"`. You may then `GROUP BY` or filter on `N` and on any node reachable
    from `N` (e.g. a parent entity). Do **not** start from a finer-grained node,
    which would drop rows of `N` that have no finer-grained children.

-   **Worked example.** For "total budget per college", where the schema has
    `Department_total_budget INT64 OPTIONS(is_measure=TRUE, ...)`:

    ```sql
    -- CORRECT: start from Department (the measure's node), then group by college.
    SELECT College_college_name, AGG(Department_total_budget) AS budget
    FROM GRAPH_EXPAND("proj.ds.school_graph", start_node => "Department")
    GROUP BY College_college_name;
    ```

    Starting from a finer node such as `Course` would omit any department that
    has no courses, so its budget would vanish from the total — a silent
    under-count. Always root at the node that owns the measure.

-   **One fact per query.** Prefer answering with a single starting node. If a
    question needs measures that live on different nodes and **no single view
    can hold them all without dropping rows** (e.g. a budget measure on
    `Department` and a count measure on `Course`), compute each with its own
    `start_node` in a separate query and combine the results (e.g. join on the
    shared grouping key).

### 3. When No Starting Node Fits — Fall Back to GQL

Some nodes are **not `GRAPH_EXPAND`-queryable** — for example a node on a cyclic
or convergent path (a node reachable by two or more paths). Such a node has **no
`<semantic_graph start_node="X">` block** in your context; only the shared
`<property_graph>` describes it. When answering the question requires an entity
or measure that has no starting-node view:

-   **DO NOT** substitute a different starting node to force a `GRAPH_EXPAND`
    query — a view rooted elsewhere drops that entity's rows and silently
    mis-counts (see Rule 2).
-   **DO NOT** query the graph's source tables directly (see Rule 1).
-   **Answer with GQL instead.** Query the `<property_graph>` with Graph Query
    Language, following the property-graph (GQL) guidelines. GQL pattern-matches
    regardless of join cardinality, so it is not restricted to
    `GRAPH_EXPAND`-queryable starting nodes.
-   **Measures are NOT available in GQL.** `is_measure` columns and the `AGG()`
    function exist **only** in the flattened `GRAPH_EXPAND` views, never in GQL.
    When you fall back to GQL you **MUST** write the aggregation yourself with
    standard SQL aggregate functions (`SUM`, `COUNT`, `AVG`, …) over the
    underlying node/edge properties, wrapping the pattern match in
    `GRAPH_TABLE(...)` so it integrates with SQL grouping.
-   **Worked example.** In a graph where `Office` is not queryable (it converges
    on `Company` via both `Division` and `Region`), "total headcount per
    company" cannot use any `GRAPH_EXPAND` view. Match the path in GQL and
    aggregate the raw `headcount` property yourself:

    ```sql
    SELECT company_name, SUM(headcount) AS total_headcount
    FROM GRAPH_TABLE(
      `proj.ds.graph`
      MATCH (o:Office)-[:OfficeToDivision]->(:Division)
            -[:DivisionToCompany]->(c:Company)
      COLUMNS (c.name AS company_name, o.headcount AS headcount)
    )
    GROUP BY company_name;
    ```

-   If the data needed for the aggregation is not exposed as a property in the
    `<property_graph>` either, tell the user the metric cannot be computed for
    that entity rather than guessing.

### 4. Querying Measures with `AGG()`

Columns marked with `is_measure=TRUE` (e.g., `Customer_customer_count INT64
OPTIONS(is_measure=TRUE)`) are measure columns. You **MUST** aggregate them with
the `AGG()` function.

-   **Syntax:** `AGG(<measure_column_name>)`
-   Do not apply `SUM`, `AVG`, `COUNT`, etc. directly to a measure column — use
    `AGG()`, which applies the measure's own aggregation exactly once per key
    even across fan-out joins.
-   **`sql_expression` is informational only.** A measure column may carry
    `OPTIONS(is_measure=TRUE, sql_expression='SUM(budget)')`. The
    `sql_expression` tells you **what** the measure computes so you can pick the
    right one; it is **not** something to reproduce. You **MUST** always
    reference the measure as `AGG(column)`. **NEVER** copy the raw expression or
    the base columns it names (e.g. `SUM(budget)` / `budget`) — those base
    columns are not present in the flattened view.
-   **Example:**

    ```sql
    -- Given Schema:
    -- CREATE TABLE `my_project.my_dataset.my_graph` (
    --   Customer_name STRING,
    --   Customer_total_orders INT64
    --     OPTIONS(is_measure=TRUE, sql_expression='COUNT(order_id)'),
    --   Product_name STRING
    -- );

    SELECT
      Customer_name,
      AGG(Customer_total_orders) AS total_orders
    FROM GRAPH_EXPAND("my_project.my_dataset.my_graph",
                      start_node => "Customer")
    GROUP BY Customer_name;
    ```

### 5. Prefer Measures (AGG) over Standard SQL Aggregations

You **MUST** prioritize using pre-defined measures (columns with
`is_measure=TRUE`) over writing standard SQL aggregations (like `COUNT(DISTINCT
...)`, `SUM`, etc.) whenever a relevant measure is available in the schema.

-   **Context:** Semantic graphs define business logic within measures to ensure
    accuracy and prevent issues like overcounting. Generating aggregations via
    standard SQL bypasses this logic.
-   **Example Scenario:** If the user asks for the "total number of entities",
    and the schema provides an `Entity_id` column as well as a measure column
    `Entity_count INT64 OPTIONS(is_measure=TRUE)`:

    -   **INCORRECT (Standard SQL):**

        ```sql
        SELECT COUNT(DISTINCT Entity_id) AS total_entities ...
        ```

    -   **CORRECT (Measure):**

        ```sql
        SELECT AGG(Entity_count) AS total_entities ...
        ```
