# Advanced Element Functions & Query Optimization

Load this reference for (a) the advanced element-inspection functions below, or
(b) tuning a slow / large-fan-out traversal.

## Element Traversal and Inspection Functions

These functions operate on individual node or edge element variables:

-   `DESTINATION_NODE_ID(e)`: Retrieves the unique internal string identifier of
    an edge `e`'s destination node.
-   `SOURCE_NODE_ID(e)`: Retrieves the unique internal string identifier of an
    edge `e`'s source node.
-   `ELEMENT_ID(x)`: Returns the unique internal identifier for the given node
    or edge `x`.
-   `LABELS(x)`: Returns an array of string labels bound to a node or edge
    element `x`.

## Query Optimization and Best Practices

Performance is a key consideration for highly connected BigQuery graphs. Adhere
to these principles whenever writing GQL statements to ensure optimal execution.

### 1. Start Traversals From Low-Cardinality Nodes

Always write your path traversals so they originate from the lowest cardinality
nodes (the most specific entities). This drastically reduces the intermediate
result set sizes and speeds up execution, especially for variable-length
traversals.

-   **Example**: Instead of starting from a highly active `Account` node and
    traversing backwards to find the owner, start with the specific `Person`
    node and traverse forward.
-   **Filter Early**: Push specific properties (e.g., `Account {id: 7}`) as
    early as possible in your `MATCH` clause to prune the search space
    immediately.

### 2. Specify Labels Explicitly

You must explicitly provide node and edge labels when they are known (e.g.,
`(a:Account)-[:Transfers]->(b:Account)`).

While BigQuery attempts to infer labels from query usage, if inference fails or
labels are omitted, the engine is forced to perform full table scans over
multiple distinct underlying node/edge tables.

### 3. Avoid Bi-directional Graph Traversals

BigQuery Graph schema physical implementations are directional. You should
always specify a source and destination node for an edge (using `->` or `<-`).

Although query pattern syntax allows for bidirectional or undirected path
traversal (`(node)-[edge]-(node)`), doing so incurs a severe implicit
performance penalty.

If you need to find an edge between two specific nodes regardless of direction,
**DO NOT** use a bidirectional pattern. Instead, use explicit directional
traversals combined with `UNION ALL`:

**GOOD:**

```sql
GRAPH <project>.<dataset>.<graph>
MATCH (a1:Account {id:10})-[t:Transfer]->(a2:Account {id: 20})
RETURN t
UNION ALL
MATCH (a2:Account {id: 20})-[t:Transfer]->(a1:Account {id: 10})
RETURN t
```

### 4. Prefer Single MATCH Statements

When possible without sacrificing readability or violating logic intent, prefer
composing a single comprehensive `MATCH` statement over chaining multiple
individual `MATCH` statements. A single statement allows the query optimizer a
wider global view of the graph pattern, often leading to better execution plans.
