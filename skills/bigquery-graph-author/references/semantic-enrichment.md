# Semantic Enrichment — decided in the plan, landed in the first DDL

Semantics — **measures** (numbers to add up) and **dimensions** (categories to
slice by) — are decided in the readable plan (the plan station) and landed in
the same `CREATE PROPERTY GRAPH` statement as the structure (the compose
station). The graph is composed once — no semantics-only rerun — for two
reasons:

-   **Semantics change the structure.** Any column a `MEASURE` aggregates must
    also be declared as an ordinary property in the same `PROPERTIES` list
    (syntax: ddl/ddl-reference.md §4A).
-   **There is no semantics-only edit.** `CREATE OR REPLACE` replaces the whole
    definition; every element you fail to re-declare is silently dropped, with
    the statement returning success. See the caution at the end of this file.

## The plan station — the semantics decision

The plan always closes the semantics question. Never leave it open for later.

### When to propose

Put semantic proposals in the plan when any of these holds: **the user asked**
("I want revenue per category", "make the amount columns aggregatable"); **the
document declares them** (the discovery station collected metrics, buckets and
business definitions from an attached document or model); or **the schema
warrants suggesting them** (the screening below turns up columns that are
plainly measures, or categories a business user would obviously slice by).

When none holds, the plan carries one explicit line — **"No semantics apply to
this graph."** — so the reader sees the question was asked and answered, not
skipped. One approval covers structure and semantics: the user reads one plan,
says yes once, and nothing semantic is deferred to after the build.

### Source badges

Every semantic row in the plan carries a provenance badge. Two badges face the
user:

| Badge      | Means                        | Typical origin                   |
| ---------- | ---------------------------- | -------------------------------- |
| `declared` | someone stated it, outside   | the attached document, a         |
:            : your own reasoning           : semantic model, a table or       :
:            :                              : column description               :
| `inferred` | you produced it from context | a data-shape measurement, or     |
:            :                              : domain knowledge about this kind :
:            :                              : of business                      :

Internally, note which kind of inference each `inferred` item is —
**data-shape** (you measured the data and the shape implies it) or **domain**
(knowledge about this kind of business, not this data) — and keep the confidence
ordering `declared > data-shape > domain`. Three rules attach:

-   **The badge says where an item came from, not how good it is.**
-   **Never promote.** A domain hunch that a data check is merely consistent
    with is still domain; only a measurement that *established* it makes it
    data-shape — then cite the measurement.
-   **A `declared` item still gets checked against the data.** The document says
    `status` has four values; the data says six. The document's word is a claim,
    not evidence — the same rule the relationship-verification station applies
    to relationships.

### How many at once

Lead with the few you are most sure of: three to five items, `declared` first,
then the data-shape items you actually measured. Hold the domain-sourced ideas
back to a named count — "I have 6 more suggestions from e-commerce convention;
say the word" — and run a second round after the first lands, not in the same
message. **List every declared item as its own row — never abbreviate the
declared list with "etc."**; an item that never appears as a row can never be
approved. **An ambiguous reply is a question, not a yes** — ask which ones.

### Confirmation is required

**Nothing inferred lands without the user's confirmation** — not the obvious
ones, not the ones the document implied, not the one you need to make another
one work. Confirmation means: the item was a row in the plan the user approved.
Two corollaries: **a confirmed item may not grow on the way in** (confirmed
`age_group` with four buckets lands with four; a fifth is a new proposal), and
**a confirmation does not carry to the neighbour** (yes to `age_group` is not
yes to `income_band`, however alike they look).

### The proposal rows

Each measure is a row:

Measure       | Expression                 | Sits on                       | Why that table                                | Source                  | Read-back
------------- | -------------------------- | ----------------------------- | --------------------------------------------- | ----------------------- | ---------
`total_sales` | `MEASURE(SUM(sale_price))` | `order_items` (edge `Bought`) | its rows are the sales — the grain rule below | `inferred` (data-shape) | readable via `GRAPH_EXPAND` — or the multi-root warning from the read-back limitations below, stated here, not after approval

Each dimension is a row:

| Dimension   | Bound to      | Derivation  | Why they would | Source     |
:             :               :             : want it        :            :
| ----------- | ------------- | ----------- | -------------- | ---------- |
| `age_group` | `users.age` → | the `CASE`, | makes "revenue | `inferred` |
:             : node `Cust`   : verbatim    : by age band"   : (domain)   :
:             :               :             : askable; `age` :            :
:             :               :             : alone groups   :            :
:             :               :             : into 60        :            :
:             :               :             : buckets nobody :            :
:             :               :             : reads          :            :

**Bound to** is the exact table, column and element alias (`users.age` →
`Cust`). **Derivation** is the expression, written out, cut points included —
with no basis for the cut points, offer two candidate schemes. **Why they would
want it** is the question it makes askable, in their words. **Read-back**
carries any shape or billing limitation from the read-back limitations below,
before approval, not after.

### Descriptions and synonyms ride along

Every proposed measure and derived dimension also carries its `OPTIONS` metadata
in the proposal: a one-line `description`, and `synonyms` when the business has
other names for it ("revenue" / "sales"). These are part of the semantic layer,
not decoration — natural-language interfaces downstream read them. They land in
the same `CREATE PROPERTY GRAPH` statement (syntax: ddl/ddl-reference.md §4B for
properties, §4C for node/edge labels). A description that comes from the catalog
or the document keeps badge `declared`; one you wrote is `inferred`, confirmed
like any other semantic row.

### Read-back limitations — state them in the proposal

Two constructs read a landed graph, and they limit what a proposal row may
promise (mechanics: ddl/feature-parity.md §2–§3):

| The question           | The construct            | What limits it           |
| ---------------------- | ------------------------ | ------------------------ |
| *Does the graph answer | GQL `MATCH` with the     | needs an Enterprise or   |
: questions?*            : aggregation written out  : Enterprise Plus          :
:                        : over ordinary columns    : reservation; **cannot    :
:                        :                          : see a `MEASURE` at all** :
| *Does this `MEASURE`   | `GRAPH_EXPAND` + `AGG()` | needs a **single-root    |
: return its number?*    :                          : tree topology** (works   :
:                        :                          : on on-demand pricing —   :
:                        :                          : no reservation required) :

What that means for a proposal row:

-   **A multi-root graph is currently incompatible with the `GRAPH_EXPAND` TVF**
    — its measures can be defined but not read back through it. Building and
    `MATCH`-querying a multi-root graph is fully supported; only this read path
    is affected. Never bend a real graph into one root to make a measure
    readable; state the limitation in the row and let the user choose. A measure
    delivered unreadable is allowed; delivered unreadable *silently* is not.
-   **Dimensions read back through `MATCH` like any ordinary property** — only
    measures are hidden from GQL. `GRAPH_EXPAND` output columns are
    **alias-derived, not label-derived** (`<element alias>_<property>`; worked
    example 3).
-   **When one read path is blocked**, the read-back entry says which figure the
    user will get instead (`MATCH` with the aggregation written out, plain SQL,
    or `not read back`, reason named) — never a plain-SQL number presented as a
    `GRAPH_TABLE` or `GRAPH_EXPAND` result.

### Screening — which numeric columns are measures

A numeric type is not a metric — meaning decides. Read the column and table
descriptions from the discovery station first: a line like "line-item sale
price, USD" settles additivity and enters as `declared`. Never compose a
description's content from its name: a field you did not read is `not read`, an
empty one is `empty` — both stated explicitly, then fall back to the inferred
tiers. When nothing is declared, say so.

Rule these out before proposing anything: **anything used as a key** (every
column in a `KEY`, `SOURCE KEY` or `DESTINATION KEY`, and any id-shaped name);
**codes stored as numbers** (status codes, postal codes, year and month parts,
version numbers, latitude/longitude); **ratios computed upstream** (the ratio
rule below).

Per-entity attributes (`age`, a rating, a catalog price on a dimension row) are
not excluded — they take the aggregate that fits their meaning:
`MEASURE(AVG(age))` is valid; a `SUM` over them is what makes no sense. Propose
them with the fitting aggregate.

One screening query separates the ids from the rest, per candidate column:

```sql
SELECT
  COUNT(*)              AS rows_total,
  COUNT(DISTINCT <col>) AS distinct_values,
  MIN(<col>) AS min_v, MAX(<col>) AS max_v,
  COUNTIF(<col> < 0)    AS negatives
FROM `<project>.<dataset>.<table>`;
```

Read it this way: `distinct_values = rows_total` with `max_v` close to the row
count is a dense surrogate key, never a metric. A dense integer range far
narrower than the row count, sized like another table, is a foreign key.
Non-integer values over a wide range are the real candidates.

**The screening rules out ids; it does not pick the aggregate** — a column fit
for `SUM`, one fit only for `AVG`, and a plain attribute can profile
identically; only the column's meaning decides which aggregate, if any, fits.
State your reasoning in the proposal row and let the user overrule you.

### Grain — the table a measure sits on decides whether the number is right

A measure belongs on the table whose rows *are* the thing being measured — on
any other table a traversal inflates the aggregate by the fan-out factor, with
no error (worked example 1 below). Revenue, quantity and line counts belong on
the transaction (edge) table; entity counts and averages of entity attributes
belong on the node. `AGG()` groups over the defining table's `KEY`, so each row
counts once no matter how expansion fans it out.

### Ratios are not sums

A rate — return rate, conversion rate, discount rate — cannot be a summed
column, and averaging a per-row ratio does not give the overall one. Build the
numerator as a derived 0/1 property (`IF(returned_at IS NULL, 0, 1) AS
is_returned` in the `PROPERTIES` list) and let the query average it:
`AVG(is_returned)` over any grouping is that group's rate, on the right
denominator. If numerator and denominator live on different tables, no property
can express it — say so and hand the user the SQL instead.

### Proposals that are really something else

A relabelled key is not a dimension — a nicer name on `user_id` gives a
high-cardinality grouping column and no meaning. A derivation that needs a join
is a relationship — it goes through the structural part of the plan as an edge
and a property, not into a `CASE`. A ratio is a measure question (above). A
status recoding is a dimension only if the mapping is stated: `status IN
('Cancelled','Returned') AS churn_signal` is a business claim, `domain` at best
— run the distinct-values query and print the value set; a status you never saw
cannot be mapped, an invented value cannot be found.

## Landing — handled by the compose station, reported back here

Confirmed semantic rows land in the same `CREATE PROPERTY GRAPH` statement as
the structure — one statement, dry-run, approve, execute — governed by the
journey's compose and execute stations. Syntax and worked DDL:
ddl/ddl-reference.md §4 (measures: §4A; derived dimension columns: §4D). This
file decides and outlines the semantics; it does not assemble DDL.

**After landing — the trace.** In the message that reports the build, one line
per confirmed item: what it landed as, what it is bound to, what was read back
(or `not read back` and why — the limitations above). Then two checkable
statements: **every landed item traces to a row in the approved plan** — a
semantic item in the DDL not on that list is silent enrichment, a defect even
when the item is good; name it and remove it. And **every confirmed item
landed** — or the ones that did not, with the reason.

## Worked examples (thelook_ecommerce)

1.  **Wrong grain inflates silently** — `SUM(retail_price)` over `Customer ->
    Bought -> Product` returned 10,788,871; over `products` alone, 1,724,491 —
    **6.3x too high, no error, no warning**.
2.  **Grain lock in action** — grouping orders by status, `COUNT(Ord_order_id)`
    returned 105 (each order repeated per line item); `AGG(Ord_order_count)`
    returned 74, matching plain SQL's `COUNT(DISTINCT order_id)`.
3.  **Alias, not label** — on a graph with aliases and labels deliberately
    different, `AGG(ItemAlias_m_item)` returned its number while
    `AGG(ItemLabel_m_item)` failed with `Unrecognized name` — and BigQuery's own
    hint spells out the alias.

## Caution — semantics after the build (out of the happy path)

In this journey semantics never arrive late: they are decided in the plan and
composed into the first DDL. If you are adding semantics to a graph that already
exists: **there is no incremental ALTER. The only write is `CREATE OR REPLACE`,
and it replaces the entire definition: every element you do not re-declare —
node table, edge table, alias, key, label, property — is deleted, and the
statement returns success with zero warnings.**

The safe procedure, condensed:

1.  Read the stored definition — the baseline your statement must reproduce
    element by element:

    ```sql
    SELECT property_graph_name, ddl
    FROM `<dataset>.INFORMATION_SCHEMA.PROPERTY_GRAPHS`
    WHERE property_graph_name = '<graph>';
    ```

2.  Execute that text plus the confirmed additions — nothing else added, dropped
    or renamed. Do not rediscover the dataset. A new measure's column must also
    join the `PROPERTIES` list, so even "just add a measure" touches structure.

3.  State the diff in the proposal and the closing report: which elements gained
    what, and that every other element is byte-for-byte the graph they already
    had. The approval prompt states explicitly that this **REPLACES the existing
    graph `<name>`**. Anything wrong with the existing design is a finding to
    raise, never a correction to fold quietly into an "update".
