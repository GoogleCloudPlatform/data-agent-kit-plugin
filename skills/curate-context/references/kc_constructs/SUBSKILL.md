<!-- disableFinding(LINE_OVER_80) -->

# Knowledge Catalog Constructs in OKF v0.2 (`references/kc_constructs/SUBSKILL.md`)

A Knowledge Catalog **context set** is an entry group (`type: context-set`)
whose entries and links are authored on disk as **Open Knowledge Format (OKF
v0.2)** markdown files directly under `bundle/`.

Read `references/kc_constructs/output_contract.md` alongside this file for exact
frontmatter and body templates.

--------------------------------------------------------------------------------

## 1. Bundle directory layout & entry IDs

Let:

-   `<CS_ID>` = context set entry group ID (e.g., `retail-orders-context`)
-   `<PROJECT>` = GCP project hosting the context set (e.g., `my-gcp-project`)
-   `<LOCATION>` = entry group location, confirmed by the user (see
    `references/plan.md` Step 1.4 for proposing a default).

`kcmd` maps `bundle/<entry-id>.md` **directly** to
`projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CS_ID>/entries/<entry-id>`.
The context-set scope (`<PROJECT>.<LOCATION>.<CS_ID>`) lives only in
`catalog.yaml` — **do not** prefix paths inside `bundle/` with
`<CS_ID>/<PROJECT>/<LOCATION>/`, so the bundle stays portable across
environments (`dev` → `qa` → `prod`).

### Default Progressive Disclosure Hierarchy (never forced over a user's OKF directory structure)

When authoring a new context set from scratch (or when a user chooses to fit our
opinionated layout), data agents that consume it traverse the context set
top-down starting at `agents`. BigQuery is shown; other engines use
`assets/<engine>/<container path>/` the same way
(`references/source_engines.md`), and one bundle can hold several engines:

```
bundle/
├── index.md                                                # optional untyped OKF v0.2 index (never a KC entry when agents.md exists)
├── agents.md                                               # entry ID: agents (type: Context Set or Knowledge Base Root, no parent)
├── assets.md                                               # entry ID: assets (type: Knowledge Base Index, extra.resource.parent: agents)
├── assets/
│   └── bigquery/
│       └── <bq_project>/
│           ├── <dataset>.md                                # entry ID: assets/bigquery/<bq_project>/<dataset> (type: Knowledge Base Index, extra.resource.parent: assets)
│           └── <dataset>/
│               └── <table>.md                              # entry ID: assets/bigquery/<bq_project>/<dataset>/<table> (type: Table Context, extra.resource.parent: assets/bigquery/<bq_project>/<dataset>)
├── documents.md                                            # entry ID: documents (type: Knowledge Base Index, extra.resource.parent: agents)
├── documents/
│   └── <slug>.md (or concepts/<slug>.md, learnings/<slug>.md) # entry ID: documents/<slug>, documents/concepts/<slug>, or documents/learnings/<slug> (type: Knowledge Base / Concept / Learning)
└── _links.yaml                                             # EntryLinks: reference (source system entry), related (index->child, concept<->table, joined tables), definition (@dataplex)
```

> **Respecting user OKF directory structures & reserved files:**
>
> -   Never force a user to convert their OKF bundle into the
>     progressive-disclosure layout above. When importing an existing OKF bundle
>     or working with a user's own directory layout, ask in the Gate 1 plan
>     whether they want to (1) apply our progressive-disclosure layout
>     (recommended) or (2) keep and push their OKF bundle in its current
>     directory structure as-is.
> -   **Compact spine by default; intermediate index pages when needed:**
>     -   **Small new context sets (default):** Skip single-child pass-through
>         directories (`assets/<engine>.md`, `assets/<engine>/<project>.md`) so
>         data agents reach tables in fewer hops — create only the container
>         index page (e.g. `assets/bigquery/<bq_project>/<dataset>.md`) and set
>         its `extra.resource.parent: assets`.
>     -   **High fan-out, shared database context, or project-level assets:**
>         Add intermediate `Knowledge Base Index` pages (`assets/<engine>.md`,
>         `assets/<engine>/<project>.md`, or `.../<database>.md` above
>         `<schema>.md`) when `assets.md` would otherwise list more than ~10
>         containers across multiple engines, projects, or schemas, when
>         multiple schemas share database- or instance-wide rules, or when
>         `<project>` or `<engine>` is itself the deepest container (e.g.
>         `@pubsub` topics or `@storage` buckets). Chain `extra.resource.parent`
>         through each index page that exists.
>     -   **Pulled or imported bundles:** Always preserve existing intermediate
>         index pages and `parent` chains (for example sets created by Managed
>         Enrichment or `kcmd init`; `parentEntry` is immutable in Knowledge
>         Catalog once created).
> -   **`bundle/index.md`, `log.md`, and non-concept files (OKF v0.2 §3.1,
>     §§8–9):** `kcmd init --format okf` scaffolds `bundle/index.md`. When
>     `bundle/agents.md` exists, `kcmd` automatically skips an untyped
>     `bundle/index.md` (OKF v0.2 index files carry no frontmatter except an
>     optional bundle-root `okf_version: "0.2"`, §§8, 12 — **no** `type:` or
>     `extra:`). Keep `bundle/index.md` untyped or remove an empty stub
>     `bundle/index.md` if unused — **never** put `type:` on `bundle/index.md`
>     alongside `bundle/agents.md`. Subdirectory `index.md` files and
>     append-only `log.md` files (`YYYY-MM-DD` date headings) have no
>     frontmatter and are never KC concept entries. Every other `.md` file in
>     the bundle is a concept and needs `type:` (§3.1), so keep repo-level
>     non-concept `.md` files (`README.md`, `CONTRIBUTING.md`) outside `bundle/`
>     when pushing with `kcmd`.

--------------------------------------------------------------------------------

## 2. How the KC construct types & OKF v0.2 metadata map to files

-   **1. Root Router (`agents`) & Progressive-Disclosure Indexes** (`assets`,
    `documents`, `assets/<engine>/<container>`)
    -   **Entry ID pattern:** `agents` (`type: Context Set` or
        `type: Knowledge Base Root`); `assets`, `documents`,
        `assets/<engine>/<container>` (`type: Knowledge Base Index`)
    -   **OKF Frontmatter `type:` (`document.type` slug):** `type: Context Set`
        (`context-set`; default for new context sets) or
        `type: Knowledge Base Root` (`knowledge-base-root`) on `agents`;
        `type: Knowledge Base Index` (`knowledge-base-index`) on
        category/dataset indexes
    -   **Required Frontmatter & Body:** `title`, `description`,
        `extra.resource.parent` set to the nearest existing ancestor index
        (except on `agents`; container indexes default to
        `extra.resource.parent: assets`, or point to an intermediate
        engine/project/database index when one exists), plus a Markdown
        **Contents** table linking to every child entry
        (`[Title](/<child-id>.md)` or relative `./`/`../` link).
-   **2. Table Context Document** (and non-`/tables/` asset context pages)
    -   **Entry ID pattern:** `assets/<engine>/<container>/<table>` for
        `/tables/<name>` entries (e.g.
        `assets/bigquery/<bq_project>/<dataset>/<table>`), or
        `assets/<engine>/<container>/<collection>/<name>` for non-`/tables/`
        collections such as `models/<m>`, `routines/<r>`, `graphs/<g>`, or
        `views/<v>` (`references/source_engines.md`)
    -   **OKF Frontmatter `type:` (`document.type` slug):**
        `type: Table Context` or `type: Table` (`table-context`; pages written
        by Knowledge Catalog enrichment carry `context-overlay`)
    -   **Required Frontmatter & Body:** `title`, `description`,
        `extra.resource.parent: assets/<engine>/<container>`, `resource:` = the
        table's system entry name in its engine's group
        (`references/source_engines.md`; BigQuery:
        `projects/<BQ_PROJECT>/locations/<bq_location>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>`,
        both `<BQ_PROJECT>`s the table's project, not the context set's;
        `<bq_location>` the dataset's location in lowercase, e.g. `us`, `eu`,
        `us-central1`). Body: the `output_contract.md` §3 sections (Table
        Overview & Grain, Key Columns, Join Relationships, Querying Rules &
        Caveats). Optional concrete representative SQL in
        `extra.aspects."dataplex-types.global.queries"` (`output_contract.md`
        §3).
-   **3. Knowledge Base, Concept & Learning Documents** (business concepts,
    metrics, SOPs, policies, learnings)
    -   **Entry ID pattern:** `documents/<slug>`, `documents/concepts/<slug>`,
        or `documents/learnings/<slug>`
    -   **OKF Frontmatter `type:` (`document.type` slug):**
        `type: Knowledge Base` (`knowledge-base`), `type: Concept` (`concept`),
        or `type: Learning` (`learning`)
    -   **Required Frontmatter & Body:** `title`, `description`,
        `extra.resource.parent: documents` (or `documents/concepts` /
        `documents/learnings` when nested under those index pages). Body:
        authoritative definition, formula/SQL rule, edge cases, source
        citations, and `> **Open question:**` if sources conflict.

### OKF v0.2 Provenance, Trust, Lifecycle & Extensions (SPEC §§4.1, 5, 7)

All OKF v0.2 frontmatter families are supported and preserved losslessly by
`kcmd`:

-   **Provenance (`sources` & `usage_window`, §5.1):** `sources:` is a list of
    `{ id, resource, title, author, usage_count, last_modified }` entries with
    optional sibling `usage_window: { from, to }`. Attribute individual claims
    in the body with Markdown footnotes matching `sources[].id` (e.g.
    `[^rev-policy]` with `[^rev-policy]: Revenue recognition policy`), never a
    `# Citations` body list.
-   **Trust (`generated` & `verified`, §§5.2–5.3, §7):** `generated: { by, at }`
    and `verified:` as either a list `[{ by, at }]` or a single mapping
    `{ by, at }` (treated as a one-element list). Actors use
    `<producer>/<version>` (tools/agents), `human:<id>`, or `process:<id>`;
    `verified` by a `human:` actor gives human-reviewed, by non-`human:` actors
    only gives machine-confirmed, and no `verified` means unverified.
-   **Lifecycle & freshness (`status`, `stale_after`, §§5.4–5.5):**
    `status: draft | stable | deprecated` (default `stable`; never fabricate a
    `dataplex-types.global.certification` aspect) and an optional ISO 8601
    `stale_after` instant (**omit if unknown — never invent a review date**).
-   **Extensions (§4.1):** Preserve any unknown or extension keys (including
    upstream values or keys this skill doesn't recognize) verbatim at any level
    without re-serializing unchanged values.

**SQL queries go in the `queries` aspect only:**

-   Put every SQL query you author (metric/KPI queries and concrete examples
    from user-provided SQL, golden/pinned queries, or docs) in the **`queries`
    aspect** of the main table's `Table Context` page, with literal values
    (`output_contract.md` §3). Never invent queries out of thin air.
-   Don't author `query-template` entries or `query-context/templates/` pages
    yet. If the user asks for a query template or gives `@param` SQL, say so in
    the Gate 1 plan and offer the literal-value query in the `queries` aspect
    instead.

### Pages you didn't write, `Attested Computation`, & existing structures

A pulled context set or an imported bundle can contain pages that don't follow
these templates: for example `type: Context Overlay` pages (table descriptions
written by an enrichment agent, often with their own sections and no
`resource:`), an `agents` page of `type: Knowledge Base` or
`type: Knowledge Base Index`, legacy `assets/bigquery/<p>` (or other engine)
index pages or a pre-pulled `<cs_id>/<project>/<location>/` directory prefix,
existing `query-templates/<slug>` or `query-context/templates/<slug>` entries,
OKF v0.2 `type: Attested Computation` concepts (§10), or a user bundle with its
own folder hierarchy.

-   **Keep existing structures intact on edits:** Keep each existing page's file
    path, `type:`, frontmatter keys (`extra.resource.parent`, `x-kcmd`, etc.),
    parent chain, and section structure. On a targeted edit, follow the sections
    and folder structure the set already has; don't convert a `Context Overlay`
    page to a `Table Context` template, move pre-pulled paths, or add
    `resource:`, `title`, or `description` unless the user asked. Leave pages
    you aren't changing byte-for-byte as they are (no reformatting,
    re-indenting, or re-ordering of frontmatter), especially certified or
    `verified` pages.
-   Leave pulled `query-template` / `query-templates/` entries untouched unless
    the user asks to change them or approves a ripple fix in the plan; then edit
    only the affected SQL or text in place, keeping the page's `type:` and
    aspect structure (`output_contract.md` §5). Never move them or create new
    ones.
-   **Importing OKF `type: Attested Computation` concepts (OKF v0.2 §10):** An
    imported OKF v0.2 bundle may include `Attested Computation` pages
    (`runtime`, optional `parameters: [{ name, type, required }]`, inline
    `# Computation` fenced SQL or `computation:` file path, `executor`,
    `attester`):
    -   If the user chooses our **progressive-disclosure KC layout** (option 1):
        place concrete executable SQL in the main `Table Context` page's
        `queries` aspect. If `@param` or dbt `{{ var(...) }}` placeholders are
        present, note in one line at Gate 1 that `query-template` entries aren't
        authored yet and offer the SQL with literal sample values in the
        `queries` aspect while keeping narrative metric/concept docs and
        provenance.
    -   If the user chooses to **keep their OKF directory structure as-is**
        (option 2): preserve their `Attested Computation` pages, frontmatter
        (`runtime`, `parameters`, `computation`, `executor`, `attester`), code
        fences, and referenced non-`.md` assets (`references/...`) intact.
-   Write new table pages as `Table Context`. If a table already has a page of
    another type, edit that page (it also carries the table's `queries` aspect)
    rather than creating a second one with the same entry ID.

--------------------------------------------------------------------------------

## 3. Cross-references and Entry Links

There are two complementary ways entries connect in a context set:

### A. Markdown links & path fields (OKF v0.2 §6)

Both root-relative (`/path.md`, resolved from the `bundle/` root; recommended)
and file-relative (`./other.md`, `../tables/orders.md`, resolved from the
containing file's directory) links are valid in OKF v0.2 (never use
`[[wikilinks]]`):

-   In a **Contents table cell** (in `agents.md`, `assets.md`, `documents.md`,
    `<container>.md`), link to each child entry using its bundle-root path (or
    file-relative path):

    ```markdown
    | [Orders Table](/assets/bigquery/<bq_project>/<dataset>/orders.md) | Order header grain and status rules |
    ```

-   In **prose**, link to another entry in the bundle with
    `[Target Title](/<entry-id>.md)` or a file-relative link
    `[Target Title](../<path>.md)` (using the target page's title as the label).

-   **Frontmatter path fields** (OKF v0.2 §6.2: `resource`,
    `sources[].resource`, `computation`, `executor.resource`,
    `attester.resource`) accept an absolute URL, a `/path` from the `bundle/`
    root, or a relative path from the containing file's directory.

### B. Entry Links in `bundle/_links.yaml` (or frontmatter `extra.links` / `x-kcmd.links`)

Author `EntryLinks` in `bundle/_links.yaml` at the root of `bundle/` (when
reading or editing an existing bundle, check both `bundle/_links.yaml` and any
page frontmatter `links` / `extra.links` / `x-kcmd.links` and edit links where
they currently live):

1.  **`reference` (directed, `source` → `target`):** Connects every
    `Table Context` entry (`source: assets/<engine>/<container>/<table>`) to its
    real source table's system entry in any engine (`target:` its full entry
    name, matching its `resource:` frontmatter; e.g.
    `projects/<BQ_PROJECT>/locations/<bq_location>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>`
    or a `@spanner` / `@biglake` / `@cloudsql` / `@alloydb` /
    `@dataprocmetastore` entry).
2.  **`related` (undirected, `entries: [a, b]`):** Connects:
    -   **Index pages to their child entries** (`agents` ↔ `assets`, `agents` ↔
        `documents`, `assets` ↔ `assets/<engine>/<container>` — or chaining
        through any intermediate engine/project/database index page when present
        — `assets/<engine>/<container>` ↔ `assets/<engine>/<container>/<asset>`,
        `documents` ↔ `documents/<slug>`, plus `documents` ↔
        `documents/concepts` (or `documents/learnings`) and `documents/concepts`
        ↔ `documents/concepts/<slug>` (or `documents/learnings/<slug>`) if
        nested) so the Knowledge Catalog Studio **Explore Context Graph**
        renders a single connected graph, **and**
    -   **Concept docs to the `Table Context` pages they govern**, plus
        **commonly joined `Table Context` entries** to each other.
3.  **`definition` (directed, `source` → `target`):** Connects a context-set
    entry (`documents/<slug>` or `assets/<engine>/.../<table>`) to an
    **existing** Knowledge Catalog Business Glossary (`@dataplex`) term
    (`target` is the glossary term's full resource name). Never point a
    `definition` link at another page in the context set (Knowledge Catalog
    rejects a document as a `definition` target at push time).

> **Location compatibility rule (system-entry & `@dataplex` targets):**
> Knowledge Catalog requires external `EntryLink` targets (any engine's system
> entry, `@dataplex`) on a **regional** context set (e.g. `us-central1`, `us`,
> `eu`) to be in the **same location** (a `global` context set can link to
> entries in any location, and any context set can link to `global` glossary
> terms). If a table or regional glossary term is in a different location from a
> regional context set, keep `resource:` on the `Table Context` page, **omit**
> that cross-location `EntryLink` from `bundle/_links.yaml` so `kcmd push` does
> not fail validation, and note it in the Gate 1 plan and Gate 2 review.
>
> **No `schema-join` links.** Writing `schema-join` links between source tables
> is out of scope for context sets. Record join keys and cardinality as text in
> each `Table Context` doc's **Join Relationships** section, and connect the two
> `Table Context` entries with a `related` link.
