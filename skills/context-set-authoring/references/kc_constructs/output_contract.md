<!-- disableFinding(LINE_OVER_80) -->

# OKF v0.2 Output Contract (`references/kc_constructs/output_contract.md`)

Use these exact templates when creating or editing files under `bundle/`.

Let `NS` be `<CS_ID>/<PROJECT>/<LOCATION>` (for example,
`retail-orders/my-project/us-central1`). Every concept file lives at `bundle/$NS/<entry-id>.md`
(or directly at `bundle/<entry-id>.md` — `kcmd` accepts both and normalizes paths on `kcmd pull` /
`kcmd push`). Using `bundle/$NS/<entry-id>.md` matches `kcmd pull` output byte-for-byte.

---

## 1. Root Router Index: `bundle/$NS/agents.md`

Entry ID: `agents` (no `parent`).

```markdown
---
type: Knowledge Base Index
title: "<Context Set Display Name> - Agent Router"
description: "Entry point for data agents using the <Context Set Display Name> context set."
---
# <Context Set Display Name>

<1-2 sentence scope summary grounded in the user's sources.>

<When the set covers more than one table: 1-3 sentences on how the tables relate (join keys and
cardinality, e.g. "`trips.start_station_id` → `stations.station_id`, many-to-one").>

## Contents

| Entry | Summary |
| :--- | :--- |
| [Data Assets](/<NS>/assets.md) | Curated BigQuery table context documents and schemas |
| [Business Documents & Concepts](/<NS>/documents.md) | Authoritative metric definitions, policies, and domain rules |

## Query Templates

| Template | Question (`nlQuery`) |
| :--- | :--- |
| [<Template Title>](/<NS>/query-templates/<slug>.md) | <Natural-language question answered by the template> |
```

---

## 2. Category & Hierarchy Indexes

### `bundle/$NS/assets.md` (Entry ID: `assets`, parent: `agents`)

```markdown
---
type: Knowledge Base Index
title: "Data Assets"
description: "BigQuery projects, datasets, and table context documents in this context set."
extra:
  resource:
    parent: <NS>/agents
---
# Data Assets

| Entry | Summary |
| :--- | :--- |
| [<bq_project>](/<NS>/assets/bigquery/<bq_project>.md) | BigQuery project `<bq_project>` |
```

### `bundle/$NS/assets/bigquery/<bq_project>.md` (Entry ID: `assets/bigquery/<bq_project>`, parent: `assets`)

```markdown
---
type: Knowledge Base Index
title: "BigQuery Project: <bq_project>"
description: "Datasets curated from BigQuery project <bq_project>."
extra:
  resource:
    parent: <NS>/assets
---
# BigQuery Project: `<bq_project>`

| Entry | Summary |
| :--- | :--- |
| [<dataset>](/<NS>/assets/bigquery/<bq_project>/<dataset>.md) | Dataset `<bq_project>.<dataset>` |
```

### `bundle/$NS/assets/bigquery/<bq_project>/<dataset>.md` (Entry ID: `assets/bigquery/<bq_project>/<dataset>`, parent: `assets/bigquery/<bq_project>`)

```markdown
---
type: Knowledge Base Index
title: "Dataset: <bq_project>.<dataset>"
description: "Curated tables in <bq_project>.<dataset>."
extra:
  resource:
    parent: <NS>/assets/bigquery/<bq_project>
---
# Dataset: `<bq_project>.<dataset>`

| Entry | Summary |
| :--- | :--- |
| [<table>](/<NS>/assets/bigquery/<bq_project>/<dataset>/<table>.md) | <1-line grain and purpose of table> |
```

### `bundle/$NS/documents.md` (Entry ID: `documents`, parent: `agents`)

```markdown
---
type: Knowledge Base Index
title: "Business Documents & Concepts"
description: "Domain definitions, metric rules, and operating procedures."
extra:
  resource:
    parent: <NS>/agents
---
# Business Documents & Concepts

| Entry | Summary |
| :--- | :--- |
| [<Concept Title>](/<NS>/documents/<slug>.md) | <1-line summary of the concept or policy> |
```

*(If you group concepts under `documents/concepts/<slug>.md`, also create the sibling index
`bundle/$NS/documents/concepts.md` with `parent: <NS>/documents` and list it in `documents.md`.)*

---

## 3. Table Context Document: `bundle/$NS/assets/bigquery/<bq_project>/<dataset>/<table>.md`

Entry ID: `assets/bigquery/<bq_project>/<dataset>/<table>`

```markdown
---
type: Table Context
title: "<bq_project>.<dataset>.<table>"
description: "<1-sentence summary of the table's grain and business role>"
resource: "projects/<PROJECT>/locations/<BQ_LOCATION>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>"
tags:
  - bigquery
  - table-context
extra:
  resource:
    parent: <NS>/assets/bigquery/<bq_project>/<dataset>
---
# `<bq_project>.<dataset>.<table>`

## Table Overview & Grain
- **Physical Table:** `<bq_project>.<dataset>.<table>`
- **Primary Key / Grain:** `<primary_key_column(s)>` - one row per <grain from schema/docs>.

## Key Columns & Business Semantics

| Column | Type | Business Meaning & Rules |
| :--- | :--- | :--- |
| `<col_1>` | `<TYPE>` | <The column's @bigquery description copied verbatim, or what a user doc says about it> |
| `<col_2>` | `<TYPE>` | No description in source. |
| `<col_3>` | `<TYPE>` | No description in source. Observed values (aggregate query): `a`, `b`. |

> Copy real column descriptions verbatim. For every column with no description in the schema and
> no mention in a user doc, the cell is literally `No description in source.` (optionally followed by
> values you observed with an aggregate query you ran). Never paraphrase the column name into a
> meaning ("Unique identifier for the station", "Total number of docks").

## Join Relationships
- Joins to [`<other_table>`](/<NS>/assets/bigquery/<bq_project>/<dataset>/<other_table>.md) on
  `<table>.<fk> = <other_table>.<pk>` (<cardinality>). Only between tables in this context set, and
  only when a description, document, or query you ran establishes the keys; otherwise omit.

## Querying Rules & Caveats
- <Only filters, partition pruning columns, soft-delete flags, or NULL handling that a source states
  (cite it). Omit this section if no source states any.>
- **Related Concepts:** [`<Concept Title>`](/<NS>/documents/<slug>.md)
```

---

## 4. Knowledge Base Concept Document: `bundle/$NS/documents/<slug>.md`

Entry ID: `documents/<slug>` (or `documents/concepts/<slug>` with `parent: <NS>/documents/concepts`).

```markdown
---
type: Knowledge Base
title: "<Concept or Metric Name>"
description: "<Concise 1-sentence definition>"
tags:
  - concept
extra:
  resource:
    parent: <NS>/documents
---
# <Concept or Metric Name>

## Definition
<Authoritative business definition grounded in the user's source document(s).>

## Calculation / SQL Rule
- **Formula / Filter:** `<exact SQL expression or filter condition>`
- **Governing Tables:** [`<bq_project>.<dataset>.<table>`](/<NS>/assets/bigquery/<bq_project>/<dataset>/<table>.md)

## Edge Cases & Exclusions
- <Specific inclusions/exclusions from the SOP or metric spec.>

> **Open question (if sources conflict):** <Cite Source A vs Source B verbatim and state that user
> confirmation is required before treating one as canonical.>
```

---

## 5. Query Template: `bundle/$NS/query-templates/<slug>.md`

Entry ID: `query-templates/<slug>` (flat at top level — **no `parent`**).

- `title` maps to `query-template.nlQuery` (the natural-language question).
- `description` maps to `query-template.intent` (how/why the query answers the question — **must
  not** be identical to `title`).
- Parameterized queries **must** use named `@param_name` syntax in SQL (never `?`) and declare every
  `@param_name` under `extra.aspects."dataplex-types.global.query-template".parameters` (or top-level
  `parameters:` in frontmatter — both are supported; `extra.aspects` is canonical after `kcmd`
  round-trip).

```markdown
---
type: Query Template
title: "<Natural-language question a user would ask, e.g., What is monthly net revenue by region?>"
description: "Computes monthly net revenue by region from <table(s)>, applying <business rule/filter>."
tags:
  - query-template
extra:
  aspects:
    dataplex-types.global.query-template:
      intent: "Computes monthly net revenue by region from <table(s)>, applying <business rule/filter>."
      nlQuery: "<Natural-language question a user would ask, e.g., What is monthly net revenue by region?>"
      sourceType: BIGQUERY
      parameters:
        - name: start_date
          type: DATE
          description: "Inclusive start date (YYYY-MM-DD)"
          sampleValues:
            - "2025-01-01"
---
Uses [`<bq_project>.<dataset>.<table>`](/<NS>/assets/bigquery/<bq_project>/<dataset>/<table>.md)
and follows [`<Concept Name>`](/<NS>/documents/<slug>.md).

```sql
SELECT
  ...
FROM `<bq_project>.<dataset>.<table>`
WHERE order_date >= @start_date
```
```

---

## 6. Entry Links File: `bundle/_links.yaml`

Place `bundle/_links.yaml` at the root of `bundle/` (or declare `extra.links` inside individual
`.md` frontmatters; `bundle/_links.yaml` is the cleanest single place to author all links). When
`kcmd push --dry-run` or `kcmd push` runs, `kcmd` merges `bundle/_links.yaml` into the work state.

```yaml
links:
  # 1. Directed definition link: context-set entry -> EXISTING @dataplex glossary term (only valid target)
  - type: definition
    source: documents/<concept_slug>
    target: "projects/<PROJECT>/locations/global/entryGroups/@dataplex/entries/<GLOSSARY_TERM_ENTRY_ID>"

  # A concept doc and the table / template pages it governs: related (never definition)
  - type: related
    entries:
      - documents/<concept_slug>
      - assets/bigquery/<bq_project>/<dataset>/<table>

  # 2. Undirected related link between a Query Template and a Table Context or Document
  - type: related
    entries:
      - query-templates/<slug>
      - assets/bigquery/<bq_project>/<dataset>/<table>

  # Every Table Context entry: related link to its @bigquery source entry (same as its `resource:`)
  - type: related
    entries:
      - assets/bigquery/<bq_project>/<dataset>/<table>
      - "projects/<PROJECT>/locations/<BQ_LOCATION>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>"

  # Two Table Context entries that are commonly joined (join keys live in each table's body text)
  - type: related
    entries:
      - assets/bigquery/<bq_project>/<dataset>/<left_table>
      - assets/bigquery/<bq_project>/<dataset>/<right_table>
```

Do **not** author `schema-join` links: they are out of scope for context sets.
