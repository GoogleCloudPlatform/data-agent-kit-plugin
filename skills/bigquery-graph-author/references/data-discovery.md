# Data discovery — the discovery station, data side

The data side of **the discovery station — understand the sources**: tables,
keys, join history from INFORMATION_SCHEMA and the catalog. Runs on every
request, including dataset-only ones. Everything found here is a *candidate*:
every relationship still goes through the checks in
`relationship-verification.md` (the relationship-verification station) before it
may appear in a proposal — every edge carries data-side evidence, never a
document's or a catalog's word alone.

### 1.1 Datasets: answer from a live listing, never from memory

If the user asks what datasets exist, pull a live listing — query
`INFORMATION_SCHEMA.SCHEMATA`, or use your platform's dataset-listing tool if
one is available — and answer from what it returns. **A listing sees the current
project only**: when the user mentions another project's dataset, take the name
from them — absence from the listing is not evidence it does not exist. If the
user names a dataset and nothing else, assume they wish to use any and all base
tables in it and say so.

### 1.2 Close the roster — every object, no type filter

Never treat a schema-listing tool's output (whatever tool lists tables and
columns on your platform) as the full object list — pull the roster with the
query below. **`BASE TABLE` is not a synonym for "table"** — `VIEW`,
`MATERIALIZED VIEW`, `CLONE`, `SNAPSHOT` and `EXTERNAL` are all queryable and
none is automatically out of scope.

Pull the roster yourself, once per dataset, with the following SQL query, before
anything is modelled:

```sql
SELECT table_name, table_type
FROM `<project>.<dataset>`.INFORMATION_SCHEMA.TABLES
ORDER BY table_type, table_name;
```

**Do not add a `WHERE table_type = ...` clause.** If you are unable to execute
the SQL query, say you cannot close the roster, label the schema-listing tool's
output as an unverified subset, and carry that caveat forward.

Then agree the scope, by type, explicitly — show type counts, state what you
include and leave out and why, and let the user overrule. Defaults: base tables,
clones and snapshots in; views and materialized views in as element tables, but
say which (a view over tables you also model separately duplicates edges);
external tables in, warning that key checks on them can be slow. An exclusion is
a stated decision, never a quiet filter.

Carry a disposition roster in which **every row of the query result appears
exactly once** — node / edge / both / excluded / undecided, one line of why.
Closure rule: `objects returned` = `node + edge + both + excluded + undecided`;
state both numbers, and if they differ you have lost an object — find it before
going on. `undecided` is acceptable mid-conversation; leaving an object
unmentioned is not — never lump leftovers together as "and the rest".

Where the schema-listing tool returned fewer objects than the query did, that
gap is a finding: name the missing objects, say the schema channel skipped them,
and fetch their columns via `INFORMATION_SCHEMA.COLUMNS`.

### 1.3 Read the catalog for structure — not for relationships

The catalog is **Knowledge Catalog** (KC) — one *entry* per BigQuery table
carrying schema, human-written descriptions, and usage information; all metadata
*about* your source tables, none of it a substitute for querying them. Once per
dataset, right after the roster:

1.  Call `search_entries` once for the whole dataset (not one call per table) to
    resolve every table to its catalog resource name, then `lookup_context` once
    with the full resolved list. Never call `lookup_context` with a bare table
    name — it rejects that.
2.  Read `technical_metadata` as your first read of the schema and
    `business_descriptions` for context. Read `operational_metadata` too, but
    **never as the ground for a relationship** — it can disagree with your own
    direct read of job history (1.4), which decides every time;
    `operational_metadata` is only a cross-check.
3.  Per segment (*schema* and *business descriptions* only): populated = usable
    — use it, without also calling the matching direct-source tool for the same
    fact (once per source). Empty, not enabled, or errored = not usable — schema
    falls back to the schema listing (§1.2); business descriptions have no
    fallback, say so and move on. State every fallback, never silent.
4.  If a KC call errors or times out, report the failure (never fabricate a
    substitute) and fall back as above. A KC outage should never block the
    workflow.
5.  Do not call `search_aspect_types` on your own initiative — catalog-wide
    discovery is not this job. `lookup_entry` on a user-named table is fine.

**Table and column descriptions arrive with the schema — read them, and take
your semantics from there first**, before you infer anything about what a column
*means*.

**When they are empty, say so — and never compose a description from an aspect's
name alone.** A body not retrieved is `not read`; a body that came back empty is
`empty`; state "the catalog carries no semantic annotation" before moving to
labelled inference.

**What schema access alone cannot see:** BigQuery rejects a foreign key that
references its own table, so a genuine self-referencing relationship carries no
declared constraint anywhere — neither the schema listing nor
`technical_metadata`'s mirror will show it. Job history (1.4) is what surfaces
it.

### 1.4 Job history — the direct channel for every relationship

**Mandatory, not a fallback — and pulled once per project, not once per
dataset.** `JOBS_BY_PROJECT` is a project-level view priced by the project's
entire job history. Run the Layer 1 index once per project, keep the result, and
reuse it for every dataset and every relationship in the session — whether or
not `operational_metadata` came back populated. Layer 2's drill-down calls count
as this one source's single use.

**Layer 1 — the index.** Run the following SQL query once, filling in
`<project>`, `<region>`, `<dataset>`, `<days>`/`<limit>` (90 days / 50 rows is a
sensible default):

```sql
WITH j AS (
  SELECT
    job_id,
    creation_time,
    (SELECT STRING_AGG(DISTINCT rt.table_id, ',' ORDER BY rt.table_id)
     FROM UNNEST(referenced_tables) AS rt
     WHERE rt.dataset_id = '<dataset>') AS table_combo
  FROM `<project>`.`region-<region>`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL <days> DAY)
    AND job_type = 'QUERY'
    AND statement_type = 'SELECT'
    AND state = 'DONE'
    AND error_result IS NULL
    AND EXISTS (SELECT 1 FROM UNNEST(referenced_tables) AS rt
                WHERE rt.dataset_id = '<dataset>')
    AND REGEXP_CONTAINS(UPPER(query), r'\bJOIN\b')
    AND NOT REGEXP_CONTAINS(UPPER(query),
          r'INFORMATION_SCHEMA|PROPERTY GRAPH|GRAPH_TABLE|GRAPH_EXPAND|RESOLVED_PCT')
)
SELECT
  table_combo,
  COUNT(*)          AS query_count,
  MAX(creation_time) AS last_seen
FROM j
WHERE table_combo IS NOT NULL
GROUP BY table_combo
ORDER BY query_count DESC, table_combo
LIMIT <limit>;
```

This returns table *combinations* — an index for deciding what merits a closer
look, never something to cite directly. **Two filters are mandatory — they stop
job history from quoting your own queries back to you as "evidence":**

-   **`statement_type = 'SELECT'` only.** `job_type = 'QUERY'` includes DDL —
    `CREATE PROPERTY GRAPH` is a QUERY job listing every element table in
    `referenced_tables`.
-   **Exclude your own check queries.** The `NOT REGEXP_CONTAINS` clause drops
    `INFORMATION_SCHEMA` jobs, graph traversals, and this skill's own resolution
    checks (which carry `resolved_pct`).

If a combo survives only on jobs indistinguishable from your own, say so and let
the relationship-verification station's measurement carry the relationship
alone.

**A single-table `table_combo` is a self-join candidate — the only channel that
surfaces self-referencing relationships (1.3).** Each one merits a layer-2 look.

**Layer 2 — on demand.** For every single-table combo, and any multi-table combo
the declared keys don't already fully explain, pull the query text:

```sql
SELECT job_id, creation_time, query
FROM `<project>`.`region-<region>`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL <days> DAY)
  AND job_type = 'QUERY'
  AND statement_type = 'SELECT'
  AND state = 'DONE'
  AND error_result IS NULL
  AND REGEXP_CONTAINS(UPPER(query), r'\bJOIN\b')
  AND NOT REGEXP_CONTAINS(UPPER(query),
        r'INFORMATION_SCHEMA|PROPERTY GRAPH|GRAPH_TABLE|GRAPH_EXPAND|RESOLVED_PCT')
  AND (SELECT STRING_AGG(DISTINCT rt.table_id, ',' ORDER BY rt.table_id)
       FROM UNNEST(referenced_tables) AS rt
       WHERE rt.dataset_id = '<dataset>') = '<table_combo>'
ORDER BY creation_time DESC
LIMIT 5;
```

Read the `ON` predicate in the returned text — it turns "these tables keep
appearing together" into a candidate edge with named columns on each side.

### 1.5 Bounding the candidate set

Admit a pair as a candidate only on one of these, and record which:

1.  **A declared constraint** — the FK names both sides. Always admitted.
2.  **A job-history `ON` predicate** (layer 2) — someone really joined those
    columns. Always admitted.
3.  **A catalog-implied relationship** (`operational_metadata`). Admitted.
4.  **A name-and-type match**, only when *all* hold: same data type; at least
    one side is a key or key-like column (the table's `PRIMARY KEY`, unique and
    non-null per a uniqueness check (relationship-verification.md §2.1), or
    named as the other table's name plus an id-suffix — `user_id` → `users`);
    and the match is on the whole column name, not a shared fragment
    (`start_date`/`end_date` and every `*_id` against every other `*_id` are how
    this degenerates into pairing everything with everything).

Anything not meeting 1–4 is not a candidate; say so.

**Test in that order and state a budget** — say up front how many checks you
intend to run (a relationship-verification check costs single-digit MB; a few
dozen is cheap, a few hundred is not), and when you stop, list what you did not
test and why. A candidate you ran out of budget for is a named gap; never leave
one unmentioned. **Never let the roster shrink to "the tables that had
candidates"** — a table with no candidate pair still owes a roster row: "nothing
connects to it" is a real, reportable finding.

### 1.6 Weighing what you found — five levels of credence

When two sources disagree about whether or how tables relate, resolve by
evidence *type*, not by which tool produced it, high to low:

1.  A declared constraint from the schema listing (`primary_key` /
    `foreign_keys`, e.g. via `INFORMATION_SCHEMA.TABLE_CONSTRAINTS`) — a stated
    fact.
2.  Direct query evidence you read yourself — a job-history `ON` predicate
    (layer 2) or a relationship-verification resolution check. An
    `operational_metadata` entry never sits here, even one naming a specific
    query — it is level 3.
3.  Catalog-derived inference — a relationship `lookup_context` implies: a
    query-log pattern (a cross-check against level 2) or one implied from
    structure/naming.
4.  A business description's prose — informative, not itself evidence of a join.
5.  A guess from column naming alone, with nothing backing it.

A higher level wins a conflict, but **state it explicitly** — one sentence
naming both readings and which one grounds the design; never resolve silently.

**Say which is which.** Every edge in a proposal names where it came from.
"Fact" language belongs to level 1 only; levels 2–5 are inferences — say
"inferred" and name the source every time: "per job history"; "per the catalog's
query-log data as a cross-check" (never shortened to plain "per job history",
which is level 2); "per the catalog's description"; "inferred from column
naming". Never blend a declared fact and an inference into one unattributed
sentence.

### 1.7 When the user names specific tables

A named subset filters the output, not the search — Discovery and relationship
verification still run over the whole dataset, because the tables that make a
scoped subgraph connected (junction tables) are usually tables nobody names.
Core rules:

-   **Record the named set verbatim; resolve each name to exactly one base table
    against the actual table list.** Two matches → ask; zero → ask and show what
    exists; never silently substitute the nearest spelling. The resolved set is
    fixed and every member must land in the final graph.
-   **An unnamed table enters only as a bridge with ≥2 named neighbours, and the
    count decides in both directions**: count 1 never admitted however relevant,
    count 2 admitted however peripheral. Count against the fixed named set only,
    never against tables you just admitted — a named set of one admits nothing.
    One intermediate by default; a two-hop chain only anchored at named tables
    on both ends (reportable); never past two without asking.
-   **If admitted tables outnumber named ones, or an admitted table relates to
    nearly everything (event log, audit table), stop and ask** — the turn ends
    on the question, no design presented as settled.
-   **Output a scope ledger: every base table, one row** — `named` / `admitted
    (bridge)` / `excluded` / `named - isolated`; excluded appears as excluded,
    never merely absent; status must agree with the count. An unconnectable
    named table stays as an isolated node, reported — dropping it is the user's
    call. Vague requests ("…and whatever's related") name no table and enlarge
    nothing: show concrete candidates and ask.
-   **A bridge is a candidate until the relationship-verification station
    measures both legs.** A leg near 0% was never a bridge: withdraw it, say so,
    redo the counts without it.
