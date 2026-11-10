<!-- disableFinding(LINE_OVER_80) -->

# OKF v0.2 Output Contract (`references/kc_constructs/output_contract.md`)

Use these exact templates when creating or editing files under `bundle/`.

Every concept file lives directly at `bundle/<entry-id>.md` (`kcmd` maps
`bundle/<entry-id>.md` directly to
`projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CS_ID>/entries/<entry-id>`
using `catalog.yaml` — never prefix `bundle/` paths with
`<CS_ID>/<PROJECT>/<LOCATION>/`).

-   **Bundle-root `bundle/index.md` (OKF v0.2 §8, §12):**
    `kcmd init --format okf` scaffolds `bundle/index.md`. When
    `bundle/agents.md` exists, `kcmd` automatically skips an untyped
    `bundle/index.md`. You may either keep `bundle/index.md` untyped (index
    files carry no frontmatter except an optional bundle-root
    `okf_version: "0.2"` — **never** `type:` or `extra:`) or remove an empty
    stub `bundle/index.md` if unused.
-   **Markdown links (OKF v0.2 §6):** Both root-relative `/path.md` (resolved
    from `bundle/`) and file-relative `./rel.md` / `../rel.md` links are valid
    in OKF v0.2.

--------------------------------------------------------------------------------

## 1. Root Router Page: `bundle/agents.md`

Entry ID: `agents` (no `extra.resource.parent`; `type: Context Set` slugifies to
`dataplex-types.global.document.data.type: context-set`, and
`type: Knowledge Base Root` slugifies to `knowledge-base-root`).

```markdown
---
type: Context Set
title: "<Context Set Display Name>"
description: "<50-1,024 chars: what questions this context set answers, naming its core tables and key metrics/concepts from the plan, so Knowledge Catalog Search can match it.>"
---
# <Context Set Display Name>

<1-2 sentence scope summary grounded in the user's sources.>

<When the set covers more than one table: 1-3 sentences on how the tables relate (join keys and
cardinality, e.g. "`<table_a>.<fk>` → `<table_b>.<pk>`, many-to-one").>

## Contents

| Entry | Summary |
| :--- | :--- |
| [Data Assets](/assets.md) | Curated source containers (datasets, databases) and table context documents |
| [Business Documents & Concepts](/documents.md) | Authoritative metric definitions, policies, and domain rules |
```

> The Summary cells in these index templates are examples: write one line on
> what each linked index actually lists in this context set.
>
> The root `description:` and `title:` become the context set's search metadata.
> Write a specific description: name the main tables (by table name) and the key
> metrics, concepts or policies the set covers, and the kinds of questions it
> answers, using only facts from the plan's sources. Never use a generic line
> such as "Entry point for data agents…" or repeat only the title. When you edit
> or extend an existing context set, update the description if the change adds
> or removes a core table or concept.

--------------------------------------------------------------------------------

## 2. Category & Dataset Hierarchy Indexes

Templates show BigQuery. For another engine, swap
`bigquery/<bq_project>/<dataset>` for `<engine>/<container path>`, the
`resource:` / `target` entry name, and `sqlDialect` per
`references/source_engines.md`; one bundle can mix engines.

> **Compact spine by default (`SUBSKILL.md` §1).** On small new context sets,
> skip single-child pass-through directories (`assets/<engine>.md`,
> `assets/<engine>/<project>.md`) so container index pages (e.g.
> `assets/bigquery/<bq_project>/<dataset>.md`) set
> `extra.resource.parent: assets` and are listed directly in `assets.md`. Add
> intermediate `Knowledge Base Index` pages when `assets.md` would exceed ~10
> containers, when documenting shared database/instance context across schemas,
> or when `<project>`/`<engine>` is itself the container, and always preserve
> existing intermediate index pages on pulled or imported bundles (or custom OKF
> layouts kept as-is).
>
> **Documents-only / policy-only context sets (zero tables):** When a context
> set is built purely from policy or domain documents with no database tables,
> omit `bundle/assets.md` and `bundle/assets/` altogether; author only
> `bundle/agents.md` (linking only
> `[Business Documents & Concepts](/documents.md)`), `bundle/documents.md`
> (`extra.resource.parent: agents`), the document pages under
> `bundle/documents/`, and `bundle/_links.yaml` (`related` links from `agents`
> to `documents` and from `documents` to each document page).

### `bundle/assets.md` (Entry ID: `assets`, `extra.resource.parent: agents`)

```markdown
---
type: Knowledge Base Index
title: "Data Assets"
description: "Source datasets/databases and table context documents in this context set."
extra:
  resource:
    parent: agents
---
# Data Assets

| Entry | Summary |
| :--- | :--- |
| [<bq_project>.<dataset>](/assets/bigquery/<bq_project>/<dataset>.md) | Dataset `<bq_project>.<dataset>` |
```

### `bundle/assets/bigquery/<bq_project>/<dataset>.md` (Entry ID: `assets/bigquery/<bq_project>/<dataset>`, `extra.resource.parent: assets`)

```markdown
---
type: Knowledge Base Index
title: "Dataset: <bq_project>.<dataset>"
description: "Curated tables in <bq_project>.<dataset>."
extra:
  resource:
    parent: assets
---
# Dataset: `<bq_project>.<dataset>`

| Entry | Summary |
| :--- | :--- |
| [<table>](/assets/bigquery/<bq_project>/<dataset>/<table>.md) | <1-line grain and purpose of table> |
```

### `bundle/documents.md` (Entry ID: `documents`, `extra.resource.parent: agents`)

```markdown
---
type: Knowledge Base Index
title: "Business Documents & Concepts"
description: "Domain definitions, metric rules, and operating procedures."
extra:
  resource:
    parent: agents
---
# Business Documents & Concepts

| Entry | Summary |
| :--- | :--- |
| [<Concept Title>](/documents/<slug>.md) | <1-line summary of the concept or policy> |
```

*(If you group concepts under `documents/concepts/<slug>.md`, also create the
sibling index `bundle/documents/concepts.md` with
`extra.resource.parent: documents` and list it in `documents.md`.)*

--------------------------------------------------------------------------------

## 3. Table Context Document: `bundle/assets/bigquery/<bq_project>/<dataset>/<table>.md`

Entry ID: `assets/bigquery/<bq_project>/<dataset>/<table>`

```markdown
---
type: Table Context
title: "<bq_project>.<dataset>.<table>"
description: "<1-sentence summary of the table's grain and business role>"
resource: "projects/<BQ_PROJECT>/locations/<bq_location>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>"
tags:
  - bigquery                                # the table's engine
  - table-context
sources:                                    # OKF v0.2 provenance (§5.1): add or update it when the page's content comes from named files/URLs
  - id: <source-slug>
    resource: <URL, /bundle-path, or scope descriptor>
    title: "<Source Title>"
extra:
  resource:
    parent: assets/bigquery/<bq_project>/<dataset>
  aspects:                                  # only when the plan includes sample queries for this table
    dataplex-types.global.queries:
      userManaged: true
      queries:
        - description: "<What it computes and the business rules it applies, citing the source. Use the literal values the source gives.>"
          sql: |-
            SELECT ...
            FROM `<bq_project>.<dataset>.<table>`
            WHERE <filter_column> = <literal value from the source>
          source: USER
          sqlDialect: GOOGLE_SQL            # engine's value; omit for PostgreSQL/MySQL (source_engines.md)
---
# `<bq_project>.<dataset>.<table>`

## Table Overview & Grain
- **Physical Table:** `<bq_project>.<dataset>.<table>`
- **Primary Key / Grain:** `<primary_key_column(s)>` - one row per <grain from schema/docs>.

## Key Columns & Business Semantics

| Column | Type | Business Meaning & Rules |
| :--- | :--- | :--- |
| `<col_1>` | `<TYPE>` | <The column's catalog/schema description copied verbatim, or what a user doc says about it> |
| `<col_2>` | `<TYPE>` | No description in source. |
| `<col_3>` | `<TYPE>` | No description in source. Observed values (aggregate query): `a`, `b`. |

## Join Relationships
- <Joins to [`<other_table>`](/assets/bigquery/<bq_project>/<dataset>/<other_table>.md) on
  `<table>.<fk> = <other_table>.<pk>` (<cardinality>). Only between tables in this context set, and
  only when a description, document, or query you ran establishes the keys; otherwise omit.>

## Querying Rules & Caveats
- <Only filters, partition pruning columns, soft-delete flags, or NULL handling that a source states
  (cite it, e.g. via `[^<source-slug>]` footnote or inline doc section). Omit this section if no source states any.>
- **Related Concepts:** [`<Concept Title>`](/documents/<slug>.md)
```

> Copy real column descriptions verbatim. For every column with no description
> in the schema and no definition in a user doc, write
> `No description in source.` (optionally followed by values observed from an
> aggregate query you ran, or a quoted, cited formula or filter where a doc uses
> the column without defining it). Never paraphrase a column name into a meaning
> (never `"The <qualifier> of the <noun>"` for a column named
> `<noun>_<qualifier>`).

### SQL queries (`dataplex-types.global.queries` aspect)

All SQL the skill authors goes in the **`queries` aspect** of `Table Context`
pages:

-   **When to use:** For metric/KPI queries and concrete, grounded example
    queries taken from query history, user-provided SQL, golden/pinned queries,
    or source documentation. Never invent queries out of thin air.
-   **Where:** On the `Table Context` page of the main (fact) table it queries,
    under `extra.aspects` as shown above. Never put the aspect on the source
    system entry (`@bigquery` or any other engine's).
-   **Fields:** Each item has `description`, `sql`, `source: USER`, and the
    engine's `sqlDialect` (`GOOGLE_SQL` for BigQuery and GoogleSQL-dialect
    Spanner; omitted for PostgreSQL/MySQL, which the enum lacks — name the
    dialect in `description`); the aspect has `userManaged: true` so Knowledge
    Catalog doesn't overwrite it.
-   **SQL:** Concrete and executable in the table's engine and dialect with
    literal values (no `@param`, `?`, or `$1` placeholders), reading only tables
    that engine can reach, checked with the engine's cost-free compile check.
-   **Existing queries:** When editing a pulled page that already has a
    `queries` aspect, keep every existing item (including `source: AGENT` ones)
    unless the plan says to change it.
-   **No query templates yet:** Don't create `query-template` entries or
    `query-context/templates/` pages (§5).

--------------------------------------------------------------------------------

## 4. Knowledge Base, Concept & Learning Document: `bundle/documents/<slug>.md`

Entry ID: `documents/<slug>`, `documents/concepts/<slug>` (with
`extra.resource.parent: documents/concepts`), or `documents/learnings/<slug>`
(with `extra.resource.parent: documents/learnings`). Use `type: Knowledge Base`
(or `type: Concept` / `type: Learning`).

Optional OKF v0.2 provenance, trust, and lifecycle keys (`sources` with required
`resource` per item, `usage_window`, `generated: { by, at }`,
`verified: [{ by, at }]` or `{ by, at }`, `status: draft | stable | deprecated`,
and an ISO 8601 `stale_after` carrying an explicit UTC offset like `...Z` when
known) may appear in frontmatter; preserve all existing keys when editing or
importing, including unknown or extension keys verbatim (OKF v0.2 §4.1).

```markdown
---
type: Knowledge Base
title: "<Concept or Metric Name>"
description: "<Concise 1-sentence definition>"
tags:
  - concept
sources:                                    # optional OKF v0.2 provenance (§5.1)
  - id: <source-slug>
    resource: <URL, /bundle-path, or scope descriptor>
    title: "<Source Title>"
extra:
  resource:
    parent: documents
---
# <Concept or Metric Name>

## Definition
<Authoritative business definition grounded in the user's source document(s).>[^<source-slug>]

## Calculation / SQL Rule
- **Formula / Filter:** `<exact SQL expression or filter condition>`
- **Governing Tables:** [`<bq_project>.<dataset>.<table>`](/assets/bigquery/<bq_project>/<dataset>/<table>.md)

## Edge Cases & Exclusions
- <Specific inclusions/exclusions from the SOP or metric spec.>

> **Open question (if sources conflict):** <Cite Source A vs Source B verbatim and state that user
> confirmation is required before treating one as canonical.>

[^<source-slug>]: <Source Title>
```

--------------------------------------------------------------------------------

## 5. Query templates & imported `Attested Computation` pages

-   **No new `query-template` entries yet:** Put authored SQL in the main table
    page's `queries` aspect (§3).
-   **Editing existing `query-template` entries in place:** Leave
    `query-template` / `query-templates/` entries in a pulled or seeded context
    set untouched unless the user asks to repair/update them or approves a
    ripple fix in the plan (`SUBSKILL.md`, "Pages you didn't write"); when
    editing one in place, update only the affected SQL or text and keep its
    existing `type:` and aspect structure intact.
-   **Imported OKF `type: Attested Computation` concepts (OKF v0.2 §10):**
    Follow `SUBSKILL.md` §2 (place concrete SQL in the main table page's
    `queries` aspect when fitting the progressive-disclosure layout, or preserve
    the `Attested Computation` pages and assets intact when keeping the user's
    directory structure as-is).

--------------------------------------------------------------------------------

## 6. Entry Links File: `bundle/_links.yaml`

Place `bundle/_links.yaml` at the root of `bundle/` (when editing an existing
bundle, check both `bundle/_links.yaml` and any page frontmatter `links` /
`extra.links` / `x-kcmd.links` and edit links where they currently live;
`SUBSKILL.md` §3B).

-   **Location rule:** follow `SUBSKILL.md` §3 (on a regional context set, omit
    links to targets in other locations and note them at Gate 1 / Gate 2).

```yaml
links:
  # 1. Directed reference link: every Table Context entry -> its same-location source system entry
  #    (BigQuery shown; other engines: references/source_engines.md)
  - type: reference
    source: assets/bigquery/<bq_project>/<dataset>/<table>
    target: "projects/<BQ_PROJECT>/locations/<bq_location>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>"

  # 2. Directed definition link: context-set entry -> EXISTING @dataplex glossary term (only valid target; copy full entry.name verbatim from search_entries / lookup_entry)
  - type: definition
    source: documents/<concept_slug>
    target: "projects/<PROJECT>/locations/<glossary_location>/entryGroups/@dataplex/entries/<GLOSSARY_TERM_ENTRY_ID>"

  # 3a. Undirected related links: index pages <-> child entries (connects the context graph in Knowledge Catalog)
  - type: related
    entries:
      - agents
      - assets
  - type: related
    entries:
      - agents
      - documents
  - type: related
    entries:
      - assets
      - assets/bigquery/<bq_project>/<dataset>
  - type: related
    entries:
      - assets/bigquery/<bq_project>/<dataset>
      - assets/bigquery/<bq_project>/<dataset>/<table>
  - type: related
    entries:
      - documents
      - documents/<concept_slug>

  # 3b. Undirected related links: concept docs <-> governing Table Context pages, and commonly joined tables
  - type: related
    entries:
      - documents/<concept_slug>
      - assets/bigquery/<bq_project>/<dataset>/<table>
  - type: related
    entries:
      - assets/bigquery/<bq_project>/<dataset>/<left_table>
      - assets/bigquery/<bq_project>/<dataset>/<right_table>
```

Do **not** author `schema-join` links: they are out of scope for context sets.
