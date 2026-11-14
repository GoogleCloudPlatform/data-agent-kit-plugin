# Relationship verification — the relationship-verification station

This file covers **the relationship-verification station — verify relationships
against the data**, which runs on every request. **Every inferred key and every
inferred relationship must be checked against the data before it appears in a
design proposal** — whatever its source badge in `data-discovery.md` says. Even
a level 1 declared constraint gets the join-resolution check, because a declared
constraint in BigQuery is not enforced.

**Evidence strength does not substitute for measurement.** A level 2 job-history
`ON` predicate says someone once joined those columns — nothing about what
fraction resolves today, or whether the column points at more than one parent;
levels 3–5 say even less. All of levels 2–5 go through the checks below: the
source badge records where the *idea* came from, the number measured here
records whether it *holds*.

These checks are cheap — BigQuery bills by column. Keep them cheap: name only
the columns you need, never `SELECT *`, never `ORDER BY` a check. **And gate the
exception**: light reads and small checks run without asking, but when a check's
dry-run or byte estimate comes back large, quote it to the user first — expected
scan size, run in full / sample / skip — and run only on their word.

### 2.1 Is the key really a key?

For each table where there is no key column, for each candidate key column:

```sql
SELECT
  COUNT(*)                   AS rows_total,
  COUNT(DISTINCT <key_col>)  AS distinct_values,
  COUNTIF(<key_col> IS NULL) AS null_values
FROM `<project>.<dataset>.<table>`;
```

Usable only when `distinct_values = rows_total` and `null_values = 0`. If not:
find a different column, use a composite key, or drop the table from the node
list — never build on a key you just watched fail.

### 2.2 What fraction of the relationship actually resolves?

For each candidate relationship, measure the share of edge rows that find a
matching node:

```sql
SELECT
  COUNT(*)                                                    AS edge_rows,
  COUNTIF(e.<fk_col> IS NULL)                                 AS fk_null,
  COUNTIF(n.<key_col> IS NOT NULL)                            AS resolved,
  ROUND(SAFE_DIVIDE(100 * COUNTIF(n.<key_col> IS NOT NULL), COUNT(*)), 2) AS resolved_pct
FROM      `<project>.<dataset>.<edge_table>` AS e
LEFT JOIN `<project>.<dataset>.<node_table>` AS n
       ON e.<fk_col> = n.<key_col>;
```

`LEFT JOIN` is mandatory — `INNER JOIN` cannot show what failed to resolve.

Report `resolved_pct` for every relationship, as a number, in the exploration
record and proposal. **100% is the only result needing no explanation.** A
self-referencing relationship (data-discovery.md §1.4's single-table combo)
checks the same way — one physical table aliased twice, child column against its
own key.

Same column name and same type do not imply shared values — only the measured
query decides.

### 2.3 Anything under 100% is a question you must answer

A rate below 100% is neither "fine" nor "broken" — it is evidence that something
specific is going on, and the design depends on which. Never average it away or
call it "mostly fine"; name the cause before proceeding.

**An exact 0% is its own case — suspect your wiring before the data.** A low
percentage usually means the data disagrees; a precise zero usually means the
test is mis-wired. Rule out wrong column pair, mismatched types (the join
compares silently and returns nothing), and wrong table first; only then is a
zero a finding about the data.

The usual causes, and what each means for the build:

-   **The column points at more than one table (polymorphic foreign key).** Ids
    from two or more parents with nothing marking which — common, invisible in
    the schema, and invisible to the catalog too, since `technical_metadata`
    mirrors that same schema. Build it as two edge projections — 2.4.
-   **You sliced the data and cut the other side.** A time window of one table
    without its partners shreds referential integrity. Slice every table on the
    same key, not the same date, or state the loss and accept it deliberately.
-   **Current-state dimension, historical facts.** Retired products, deleted
    users: the parent row is simply gone. Nothing is broken; the graph is just
    smaller than the fact table. Say by how much.
-   **Dirty or optional data.** Nulls, sentinel values, legacy ids. Quantify it
    rather than asserting it.
-   **Two id generations in one namespace.** Ids that do not overlap, wholly or
    partially. Sample unmatched values from each side; differing *shapes* (UUIDs
    against integers) settle it in one look.

To spot a polymorphic column, probe unresolved rows against the other parent:

```sql
SELECT
  COUNT(*)                       AS unresolved_rows,
  COUNTIF(b.<key_b> IS NOT NULL) AS also_found_in_b
FROM      `<project>.<dataset>.<edge_table>` AS e
LEFT JOIN `<project>.<dataset>.<node_a>`     AS a ON e.<fk_col> = a.<key_a>
LEFT JOIN `<project>.<dataset>.<node_b>`     AS b ON e.<fk_col> = b.<key_b>
WHERE e.<fk_col> IS NOT NULL AND a.<key_a> IS NULL;
```

A high `also_found_in_b` means the column is polymorphic; a near-zero one rules
it out and sends you to the other explanations.

### 2.4 Pattern: a polymorphic column becomes two edge projections

When one column points at two parents, do not pick one and lose the rest, and do
not invent a discriminator column that isn't there. Declare the **same physical
table twice**, under two aliases, with two destinations and two labels — rows
that don't match a given destination drop out of that projection, so each
carries its own half and nothing is double-counted:

```sql
EDGE TABLES (
  my_dataset.comments AS CommentsOnQuestions
    KEY (id)
    SOURCE KEY (user_id) REFERENCES Users (id)
    DESTINATION KEY (post_id) REFERENCES Questions (id)
    LABEL CommentedOnQuestion,
  my_dataset.comments AS CommentsOnAnswers
    KEY (id)
    SOURCE KEY (user_id) REFERENCES Users (id)
    DESTINATION KEY (post_id) REFERENCES Answers (id)
    LABEL CommentedOnAnswer
)
```

The same trick covers one table serving as two differently-directed edges, and a
table serving as **both a node and an edge** — register it under one alias in
`NODE TABLES` and another in `EDGE TABLES` (distinct names; the documented way a
table serves as both). That dual registration is required whenever other tables'
foreign keys point *at* a table you classified as an edge: `REFERENCES` takes an
element alias, an edge is not a valid target, so without a node alias those
relationships quietly do not get built — no error, just missing edges. Before
settling the roster, check every table's foreign keys against your edge
classifications and say what the check found.

A polymorphic column is a reporting event, not just a build decision: it becomes
two rows in the proposal's relationship list, and the probe query that
identified it goes into the evidence appendix like any other measurement.
