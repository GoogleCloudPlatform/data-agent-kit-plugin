# Graph Verification

This file walks through how a created graph can be verified by running GQL /
semantic SQL queries against the graph.

## 1. The quick smoke check — one query to confirm the graph answers (start here)

One query after a build: confirm the graph can answer, not exhaustively verify
it. Pick any relationship that actually landed and run a one-hop count through
GQL `MATCH` with explicit aggregation, forcing a real endpoint join, then
cross-check the same count in plain SQL.

```sql
SELECT
  COUNT(*)                   AS true_edges,
  COUNTIF(src_probe IS NULL) AS src_probe_nulls,
  COUNTIF(dst_probe IS NULL) AS dst_probe_nulls
FROM GRAPH_TABLE(
  <dataset>.<graph>
  MATCH (s:<SourceLabel>)-[e:<EdgeLabel>]->(d:<DestLabel>)
  RETURN s.<src_probe_col> AS src_probe, d.<dst_probe_col> AS dst_probe
);
```

Bare `COUNT(*)` over an unconsumed `RETURN` column does **not** work — the
planner prunes the join unless the outer aggregate actually reads the projected
value, so `COUNTIF(... IS NULL)` is what forces it (the consumed-endpoint
method). The probe columns must be real node properties — not the node's `KEY`
column, and not a column that also exists on the edge table — or the planner can
satisfy them without joining at all.

```sql
SELECT COUNT(*) AS true_edges
FROM `<edge_table>`        AS ed
JOIN `<source_node_table>` AS s ON ed.<source_key> = s.<source_node_key>
JOIN `<dest_node_table>`   AS d ON ed.<dest_key>   = d.<dest_node_key>;
```

**Judgment**: the two counts must agree digit for digit. Agreement is a pass —
say so in one line: the graph answers. A mismatch is a finding, not noise —
report it explicitly, name which side looks wrong if you know, and never average
or quietly prefer one number.

## 2. The optional full suite

The full verification suite checks the created graph against
`INFORMATION_SCHEMA` and GQL / semantic SQL queries (where applicable), and
produces a full report for the user. Every check here is a query you run
yourself.

### 2.1 Confirm it is registered, then count each edge type

```sql
SELECT property_graph_name FROM `<dataset>.INFORMATION_SCHEMA.PROPERTY_GRAPHS`;
```

**A naive `COUNT(*)` over a `GRAPH_TABLE` match returns the edge table's raw row
count, not the number of edges whose endpoints actually exist.** Run the same
consumed-endpoint query from the smoke check (§1) above (its probe-column rules
apply), once per edge label, with probe columns chosen for that label's node
types.

**Judgment**: cross-check each result with the same plain-SQL join shown above.
The two methods should agree; a disagreement is itself a finding and must be
reported, not averaged.

### 2.2 Reconcile against the raw edge table

```sql
SELECT COUNT(*) AS raw_rows FROM `<edge_table>`;
```

Put `true_edges` and `raw_rows` side by side for every edge type. When they
differ, **name the cause** — expired foreign keys, a resolution rate short of
100%, a filter applied upstream — and report both numbers with the cause.

### 2.3 Check every node type is reachable

An **orphan node table** — declared, full of rows, referenced by no edge — is
legal DDL and produces an island in the graph. No error message will ever report
it. Check it two ways, both free:

**Against the DDL that landed** (query it via `INFORMATION_SCHEMA` as above,
reading `ddl` instead of just the name): every node alias must appear in at
least one `SOURCE KEY ... REFERENCES` or `DESTINATION KEY ... REFERENCES`. Write
the per-alias result down — node alias, then the edge aliases that reference it
— before writing anything else. An alias you did not name is an alias you did
not check.

**Against the counts you already have**: a node label can be wired up in the DDL
and still be unreachable if every edge type touching it counted zero above — for
each label, at least one incident edge type must have `true_edges > 0`. A label
whose every incident edge came back zero is an orphan in practice, needing the
same explanation as one the DDL never wired.

Do not test this with an unlabeled undirected match (`MATCH (n:<Label>)-[e]-()`)
— the planner fans out across every edge type in both directions and does not
return in practical time on a large graph, where the two passes above answer
instantly. Instead, run one real multi-hop traversal that returns actual rows
(for example user → order → product), labeled and directed, with a small
`LIMIT`, so "traversable" is demonstrated rather than assumed.

### 2.4 Reconcile against the approved plan

Every element in the plan the user approved must appear in the landed DDL, and
every element in the landed DDL must trace back to that plan or be flagged as an
admitted addition. Tick the approved node/edge list off against the DDL you
pulled above.

**A dropped element — approved but not landed — is reported first**, before any
other number in this stage: say the graph does not match what the user approved,
and offer to add it back. An element in the DDL **not** in the approved plan is
scope creep: name it and say where it came in. If the user named specific tables
up front (prompt or document), confirm each landed and say so first in the
closing message — this catches "we scoped to three things and delivered two."

### 2.5 Check every metric against plain SQL

Only if semantics were confirmed. Compute each metric through the graph and
straight off the base tables, and print the two side by side.

Three rules:

-   **`AGG()` over the measure, via `GRAPH_EXPAND`, is the only read that
    verifies the measure.** Summing the underlying column — by `MATCH`, plain
    SQL, or anything else — measures the column, not the measure, and agrees
    with the base-table figure whether or not the measure works.
-   **If the read path errors, print the error verbatim and mark that metric
    `unreadable`** — not `verified`, not silently dropped; falling back to
    summing the plain column claims a working measure where one errored on
    contact. On a multi-root graph the error `The graph must have a single root
    node table` is expected: say so in the plan, don't discover it here.
-   **Never write "verified" about a query that did not run.** One row per
    measure, each carrying the exact `GRAPH_EXPAND` column read. A measure not
    read back gets `not read back` in its `GRAPH_EXPAND` cell — never a number
    carried over from the plain-SQL cell, never the word "match".

```sql
SELECT Product_category  AS category,
       AGG(Item_revenue) AS revenue
FROM   GRAPH_EXPAND("<dataset>.<graph>")
GROUP BY category;
```

```sql
SELECT p.category AS category,
       SUM(oi.sale_price) AS revenue
FROM      `<dataset>.order_items` AS oi
JOIN      `<dataset>.products`    AS p ON oi.product_id = p.id
GROUP BY category;
```

They must agree digit for digit, on a grouping with several groups — a single
grand total can match by luck when a fan-out cancels out. A disagreement is
almost always the metric defined on the wrong table. Report the comparison,
never the `GRAPH_EXPAND` figure alone.

**If the measure sits on a non-root (parent) table, the plain-SQL side must
manage the grain explicitly.** The example above is safe because the measure
column lives on the lowest-grain fact table; joining a *parent* table down to a
child grain fans each parent row out once per child row, and a straight `SUM`
then overcounts by exactly that fan-out — the two sides disagree even when the
measure is right (`COUNT`-style checks can still agree by luck; `SUM` will not).
Collapse to the parent's own grain in a pre-aggregating subquery — `SELECT
DISTINCT` on its primary key plus the columns you need — then aggregate:

```sql
-- measure column on products (a parent of order_items): collapse to the
-- parent's grain first, then aggregate
SELECT s.category, SUM(s.retail_price) AS catalog_value
FROM (SELECT DISTINCT p.id, p.category, p.retail_price
      FROM `<dataset>.products`    AS p
      JOIN `<dataset>.order_items` AS oi ON oi.product_id = p.id) AS s
GROUP BY s.category;
```

### 2.6 Write the numbers down

Your closing report must contain, in the message to the user:

1.  the graph name and dataset it landed in;
2.  per node label: row count, and whether any edge reaches it;
3.  per edge label: `true_edges`, `raw_rows`, the gap's cause, the count method
    (named as the consumed-endpoint method), and the cross-check;
4.  per metric: name, table, `AGG()` value, and the plain-SQL figure it was
    checked against — one line each, none omitted or merged;
5.  if semantics were confirmed: one row per item — landed-as, bound-to,
    read-back-or-why-not — plus: every landed item traces to a confirmed
    proposal, and every confirmed item landed;
6.  if the user named specific tables (prompt or document): each one's fate;
7.  the discovery-station inventory reconciliation, closed against what landed:
    total object count, and every object as *node*, *edge*, *both*, or *excluded
    — with the reason*; `undecided` is not permitted here, and the two counts
    must match and both be printed;
8.  anything you could not verify, and why.

If a number is missing, the stage is not done. Do not substitute a reassuring
sentence for a count you did not take.

**On the last item, "none" is a claim, and it is the one most often false — do
not write it, nor "all verified" or "100% verified", unless every count, edge
figure, and measure in the report traces to a query you ran in this
conversation.** Before writing it, name the query whose result licenses each
check you are asserting passed. If any line came from the plan rather than the
landed graph — an incident-edge column filled in from memory, an edge listed
because it was proposed — that line is the unverified item, named here.
