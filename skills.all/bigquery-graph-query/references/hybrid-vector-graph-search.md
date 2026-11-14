# Hybrid Semantic + Graph Search

Load this reference only when the question is **conceptual** — it describes what
the user means rather than naming an ID or literal — **and** a node has an
embedding-backed property.

Semantic search supplies candidate nodes; the graph constrains them. The search
targets the node's **underlying source table** — `VECTOR_SEARCH` takes a
`TABLE`, and GQL has no vector-distance syntax inside `MATCH`.

## Choosing the Column to Search

Always use `VECTOR_SEARCH`; what changes is the column you name and the
`query_value`. **Never** guess a model name or an embedding column — if you
cannot confirm a row from the schema, you are on the last row.

Corpus                          | `column_to_search`  | `query_value`
:------------------------------ | :------------------ | :-------------------
autonomous embedding generation | the source text col | the query string
precomputed `ARRAY<FLOAT64>`    | the embedding col   | `AI.EMBED(…).result`
an existing node                | the embedding col   | that node's vector
no embeddings                   | —                   | none — plain GQL

The string form requires autonomous embedding generation; against a plain text
column it fails with `No generation expression found for the column_to_search`.

If no row applies, or a deployment blocks reading the node table, answer with
plain GQL and lexical predicates. **Never** embed the node table on the fly, and
do not lecture the user about the missing capability.

## Basic Structure

Candidate generation goes in its own CTE — never inlined as an `IN` subquery,
which discards `distance`. Join it to `GRAPH_TABLE` and order by `distance`. Use
`distance_type => 'COSINE'` for text; the default is `EUCLIDEAN`.

```sql
WITH candidates AS (
  SELECT base.artifact_id AS artifact_id, distance
  FROM VECTOR_SEARCH(
    TABLE `<project>.<dataset>.<node_table>`,
    'description',  -- source text column; autonomous embeddings enabled
    query_value => 'precipitation fouling during crystallization',
    top_k => 50,
    distance_type => 'COSINE')
)
SELECT g.artifact_id, g.experiment_id, c.distance
FROM candidates AS c
JOIN GRAPH_TABLE(
    `<project>.<dataset>.<graph>`
    MATCH (a:Artifact)-[:Informs]->(e:Experiment)
    COLUMNS (a.artifact_id AS artifact_id, e.experiment_id AS experiment_id)
) AS g
  ON g.artifact_id = c.artifact_id
ORDER BY c.distance
LIMIT 10
```

## Swapping the Candidate CTE

Only the CTE changes for the other rows; the `GRAPH_TABLE` join is identical.

**Precomputed vectors.** Name the embedding column and build the query vector
with the `AI.EMBED` scalar — no `MODEL` entity needed. Exactly one of `endpoint`
or `model` is required; `connection_id` is optional. Set `RETRIEVAL_QUERY`:
corpora use `RETRIEVAL_DOCUMENT`, and matching both sides degrades ranking.

**Match the endpoint to the stored vectors.** `INFORMATION_SCHEMA` does not
record which model produced a precomputed column, so take the endpoint from the
column description, agent config or the user; if you cannot, do not embed. A
dimension mismatch errors; a same-dimension mismatch silently returns nonsense.

```sql
  FROM VECTOR_SEARCH(
    TABLE `<project>.<dataset>.<node_table>`,
    'description_embedding',
    query_value => AI.EMBED(
      'solvent selection for scale-up',
      endpoint => 'text-embedding-005',
      task_type => 'RETRIEVAL_QUERY').result,
    top_k => 50,
    distance_type => 'COSINE')
```

**An existing node as the query.** Nothing to embed — pass the node's stored
vector. Exclude the seed in the base-table query so it does not consume a
`top_k` slot.

```sql
  FROM VECTOR_SEARCH(
    (SELECT molecule_id, profile_embedding
     FROM `<project>.<dataset>.<node_table>`
     WHERE molecule_id != 'GSK035A'),
    'profile_embedding',
    query_value => (
      SELECT profile_embedding
      FROM `<project>.<dataset>.<node_table>`
      WHERE molecule_id = 'GSK035A'),
    top_k => 50,
    distance_type => 'COSINE')
```

## Rules

-   **Retrieve wide, cut late**: set `top_k` to `MAX(50, 3 × requested_limit)`
    before the join and apply the requested `LIMIT` after it. A `top_k` equal to
    the rows wanted often returns nothing once the traversal filters. If the
    result is still short, retry once with a larger `top_k`.
-   **Pre-filter in the base-table query**, not an outer `WHERE`: `top_k`
    applies first, so a post-filter silently returns fewer rows than requested.
    Only `SELECT`, `FROM` and `WHERE` are allowed there, and you must not filter
    on the embedding column.
-   **Keep exact identifiers exact**: put a named ID in the graph `WHERE` or the
    pre-filter, and pass only the conceptual remainder as search text.
-   **Deduplicate fan-out**: use `ANY SHORTEST` on quantified traversals, or
    `SELECT DISTINCT` when projecting only node properties.
-   **Return provenance**: join document/page columns when the schema has them.
