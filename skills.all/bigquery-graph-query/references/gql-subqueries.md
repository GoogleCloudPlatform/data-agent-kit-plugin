# GQL Subquery Limitations

Load this reference when a query uses a subquery — i.e. an `EXISTS`, `IN`,
`LIKE`, `VALUE`, or `ARRAY` block enclosed in braces `{}`. BigQuery GQL has
critical limitations and syntax differences from standard GoogleSQL that you
**MUST** follow.

## Mandatory Graph Name Specification

In BigQuery Graph, unlike standard GoogleSQL, you **MUST** specify the graph
name within the subquery block. If the outer query uses `GRAPH
<project>.<dataset>.<graph>`, the internal subquery must also explicitly
re-declare it.

```sql
MATCH (n1)
WHERE EXISTS {
  -- REQUIRED: You must re-specify the graph name here
  GRAPH <project>.<dataset>.<graph>
  MATCH (n2)
  WHERE n1 = n2
  RETURN 1 as one
}
```

Failure to include the graph name in the subquery will result in a job-server
error.

## The WHERE vs. FILTER Rule

Certain types of subqueries **throw errors when used inside a `WHERE` clause**
because BigQuery's query planner cannot decorrelate them if they act as join
predicates.

For the following subquery types, you **CANNOT** use the `WHERE` clause. You
**MUST** use the `FILTER` clause instead: `EXISTS`, `IN`, `LIKE`, and `LIKE
ANY/SOME/ALL` subqueries.

**INCORRECT (will throw error):**

```sql
MATCH (p:Person) WHERE EXISTS {
  GRAPH <project>.<dataset>.<graph>
  MATCH (p)-[:Owns]->(:Account)
}
```

**CORRECT:**

```sql
MATCH (p:Person) FILTER EXISTS {
  GRAPH <project>.<dataset>.<graph>
  MATCH (p)-[:Owns]->(:Account)
}
```

## Supported Subquery Types and Correlations

-   **`ARRAY` Subquery**: Fully Supported. Evaluates the query block and returns
    an array of the results.
-   **`VALUE` Subquery**: Partially Supported. Evaluates the internal query and
    returns a single scalar value. **Limitation**: `VALUE` subqueries throw
    errors when correlated variables from the outer block are referenced inside
    the `VALUE` subquery.
-   **`EXISTS`, `IN`, `LIKE` Subqueries**: Partially Supported. **Limitation**:
    Throw errors when correlated variables are used. Throw errors when used in
    `WHERE` filter (Must use `FILTER`).
