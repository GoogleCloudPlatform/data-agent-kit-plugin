<!-- disableFinding(LINE_OVER_80) -->

# Phase 3 — Validate & Repair (`references/validate.md`)

Every context set must pass **Tier-1 structural & SQL validation** and be
checked for **Tier-2 semantic coherence** before you present the Gate 2 review
or run `kcmd push`.

--------------------------------------------------------------------------------

## Step 3.1 — Run `kcmd push --dry-run` and each engine's compile check

In a `kcmd` workspace (`catalog.yaml` present), `kcmd push --dry-run` parses the
OKF v0.2 `.md` files and `bundle/_links.yaml` and shows what a push would do,
**without publishing any changes**. It is not a full validation: it may check
only entries and links that changed since the last pull or push (an unchanged
workspace reports "nothing to push"), it checks a new context set only locally,
and it doesn't check orphans, inline links, or whether the published set changed
since your pull (`references/navigate.md` §3). The Tier-1 checklist in Step 3.2
is what covers the whole bundle.

```bash
# 1. Check what a push would do, without publishing
kcmd push --dry-run

# 2. Compile-check each sample SQL query in a table page's `queries` aspect (Step 3.3)
bq query --dry_run --use_legacy_sql=false "<SQL>"   # BigQuery; other engines: references/source_engines.md
```

*(If authoring a standalone local OKF bundle without `catalog.yaml`, verify the
Tier-1 structural checklist in Step 3.2 directly across `bundle/` and
`bundle/_links.yaml`. In either case, links may also live in page frontmatter
under `links` / `extra.links` / `x-kcmd.links`; check both places.)*

--------------------------------------------------------------------------------

## Step 3.2 — Tier-1 structural issues (auto-repair before Gate 2, except on read-only export)

Tier-1 issues are mechanical/structural defects. When authoring, importing, or
editing a bundle, **fix all Tier-1 issues automatically** before presenting your
review to the user.

-   **Read-only export / pull-only exception:** When the user asked only to
    export or download a remote context set locally without edits, **do not
    auto-rewrite** the pulled files — only **report** any Tier-1/Tier-2 defects
    in your closing summary so the local export stays faithful to Knowledge
    Catalog.
-   **Respect non-concept & custom pages:** Each row below applies only to the
    page type it names:
    -   **Reserved & untyped files (OKF v0.2 §3.1, §§8–9):** An untyped
        `bundle/index.md` (frontmatter at most the optional `okf_version: "0.2"`
        key and **no** `type:` or `extra:`), subdirectory `index.md`, and
        `log.md` are reserved non-concept files — **never** flag them as orphans
        or missing `type:`, and **never** add `type:` to `bundle/index.md`
        alongside `bundle/agents.md` (if `bundle/index.md` is an unused empty
        stub, you may remove it).
    -   **Pulled / custom pages:** A pulled `Context Overlay` page is not a
        defect for missing `resource:` or Table Context sections, and an
        imported OKF `Attested Computation` page kept in a user's as-is layout
        is valid (`references/kc_constructs/SUBSKILL.md` §2). Note also that for
        nested folders (`documents/<slug>.md`,
        `assets/<engine>/<container>/<table>.md`), `kcmd` (`conceptToEntry`)
        defaults `parentEntry` from the parent path segment when
        `extra.resource.parent` is omitted, whereas top-level `assets.md` and
        `documents.md` require `extra.resource.parent: agents`.

Tier-1 defects, how to detect each, and how to fix it:

-   **Missing progressive-disclosure index (default layout only)**
    -   **How to detect it:** When using the default progressive-disclosure
        layout (not a custom user directory structure kept as-is), missing
        `bundle/agents.md`, `bundle/assets.md`, `bundle/documents.md`, or a
        container index `bundle/assets/<engine>/<container>.md`
    -   **How to fix it in `bundle/`:** Create `bundle/agents.md`
        (`type: Context Set` or `type: Knowledge Base Root`), `bundle/assets.md`
        (`extra.resource.parent: agents`), `bundle/documents.md`
        (`extra.resource.parent: agents`), and each container index
        `bundle/assets/<engine>/<container>.md` (e.g.
        `bundle/assets/bigquery/<project>/<dataset>.md`;
        `type: Knowledge Base Index`, `extra.resource.parent: assets`; do not
        create `assets/<engine>.md` or intermediate index pages). Skip this rule
        when the user chose to keep their own OKF directory structure as-is.
-   **Generic or missing root `description:`**
    -   **How to detect it:** `bundle/agents.md` has no `description:`, one
        under 50 or over 1,024 characters, or a generic one that names no core
        table, metric or concept (e.g. "Entry point for data agents…" or only
        the title)
    -   **How to fix it in `bundle/`:** Rewrite it from the plan's sources to
        name the main tables and key metrics/concepts and the questions the set
        answers.
-   **Orphan entry or disconnected KC Graph index**
    -   **How to detect it:** A concept `.md` file (`type:` present; never
        untyped `index.md` or `log.md`) is not linked from any index Contents
        table or `bundle/_links.yaml`, or an index page in the default layout
        lacks `related` `EntryLinks` to its child entries
    -   **How to fix it in `bundle/`:** Add a row for `<id>` in its parent
        index's Markdown Contents table (`[Title](/<id>.md)` or relative
        `./`/`../` link), set `extra.resource.parent` in its frontmatter (except
        on `agents` and `query-template` entries), and add `related`
        `EntryLinks` in `bundle/_links.yaml` connecting each index (`agents`,
        `assets`, `<container>`, `documents`) to its child entries plus concept
        docs to governing tables.
-   **Dangling `extra.resource.parent`, path field, or inline link**
    -   **How to detect it:** `extra.resource.parent` (or `x-kcmd.parentEntry`),
        an in-bundle frontmatter path field (OKF v0.2 §6.2:
        `sources[].resource`, `computation`, `executor.resource`,
        `attester.resource`), or a Markdown link (`[Label](/path.md)` from
        `bundle/` root or `[Label](../rel.md)` from the file's directory) misses
    -   **How to fix it in `bundle/`:** Fix the typo in `extra.resource.parent`,
        the path field, or the Markdown link so it resolves to an existing file
        in `bundle/` (`/path` from the bundle root, relative paths from the
        containing file's directory, OKF v0.2 §6), or remove the reference if
        the target entry was intentionally deleted.
-   **Dangling or cross-location `bundle/_links.yaml` endpoint**
    -   **How to detect it:** `kcmd push --dry-run` errors, `source` / `target`
        / `entries` references a missing local entry ID, or an external
        system-entry (any engine) / regional `@dataplex` target has a different
        location from a regional context set
    -   **How to fix it in `bundle/`:** Update `source` / `target` / `entries`
        in `bundle/_links.yaml` (or frontmatter `extra.links`) to the valid
        entry ID; if a table or regional glossary term is in a different
        location from a regional context set, keep `resource:` on the
        `Table Context` page, omit the cross-location `EntryLink` from
        `bundle/_links.yaml`, and note it in Gate 2.
-   **Invalid representative query, or a new query template**
    -   **How to detect it:** A query in `dataplex-types.global.queries` is
        missing `description`, `sql`, `source`, or `userManaged: true`, has a
        `sqlDialect` outside its enum (or none on a GoogleSQL query;
        `references/source_engines.md`), or contains `@param` / `?` / `$1`
        placeholders; an existing `query-template` parameter `type` is not one
        of `BOOLEAN`, `NUMBER`, `STRING`, `BYTES`, `DATETIME`, `TIMESTAMP`,
        `GEOSPATIAL`, `STRUCT`, `RANGE`; or the bundle has a new
        `type: Query Template` page or `query-context/templates/` file that you
        wrote
    -   **How to fix it in `bundle/`:** Fix the query per `output_contract.md`
        §3 (literal values only), and map any invalid `query-template` parameter
        `type` to one of the 9 valid enum values (`output_contract.md` §5). Move
        the SQL of any new query-template page into the main table page's
        `queries` aspect with literal values and delete the template page; leave
        query-template entries that were already in a pulled context set (and
        `Attested Computation` pages in an as-is OKF bundle) untouched.
-   **Ungrounded column meaning, or invented `stale_after` / certification**
    -   **How to detect it:** A Key Columns cell describes a column that has no
        description in the source schema and no user doc defining what it is; or
        a page invents an ungrounded `stale_after` date or
        `dataplex-types.global.certification` aspect
    -   **How to fix it in `bundle/`:** Replace ungrounded column cells with
        `No description in source.` (optionally followed by observed aggregate
        values or quoted doc usage, e.g.
        `Used in <METRIC>: <quoted expression> (<doc> §<section>).`); remove any
        ungrounded `stale_after` or fabricated `certification` aspect while
        preserving genuine upstream OKF metadata (`sources`, `verified`,
        `generated`, `status`, and any unknown or extension keys, OKF v0.2
        §4.1).
-   **Table-context missing `resource:`**
    -   **How to detect it:** `type: Table Context` file has no `resource:`
        frontmatter field
    -   **How to fix it in `bundle/`:** Add `resource:` with the table's system
        entry name per `references/source_engines.md` (BigQuery:
        `projects/<BQ_PROJECT>/locations/<bq_location>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<D>/tables/<T>`;
        table's project, lowercase location) to frontmatter.

Treat every `kcmd push --dry-run` warning about links (for example "definition
TARGET should be a glossary-term entry") as an error to fix before Gate 2: on a
first push the entry group doesn't exist yet, and links to entries the push
would create are often skipped, so Knowledge Catalog can't validate them
remotely and the dry-run may still print `RESULT: OK`.

After fixing any Tier-1 issue, re-run `kcmd push --dry-run` (and the engine
compile checks) until both report zero errors, and re-check the Tier-1 defect
list yourself.

--------------------------------------------------------------------------------

## Step 3.3 — SQL query verification

1.  **Static & engine compile check (always run):**
    -   For each **representative query** in a table page's `queries` aspect,
        run its engine's cost-free compile check on the literal `sql`
        (`references/source_engines.md`; BigQuery:
        `bq query --dry_run --use_legacy_sql=false "<SQL>"` or the host
        environment's BigQuery dry-run tool) and verify that every referenced
        table and column exists in the source schemas. A query reads only tables
        its engine can reach (e.g. BigQuery can read BigLake tables); don't add
        cross-engine joins no source gives.
    -   If a query fails the check because of a column typo, bad table name, or
        invalid SQL syntax, fix its SQL and re-run the check.
    -   If the check can't run at all (CLI error, no credentials, offline, no
        connection to the database, or no check for that engine), don't work
        around authentication. Report "<engine> compile check: not run" with the
        one-line reason in the Gate 2 review, and never present a manual schema
        comparison as a compile check.
2.  **Live execution & profiling check (ask the user for query live tests):**
    The compile check proves the SQL compiles against the schema, **not** that
    the business logic returns sensible rows. In your Gate 2 review summary,
    report the compile-check pass and **ask the user** if they would like you to
    run a bounded live execution check of each query (aggregate or bounded
    `LIMIT` queries per `references/source_engines.md`, after the compile check,
    never copying sensitive PII into the context set or chat). Skip live
    execution if the user declined it.

--------------------------------------------------------------------------------

## Step 3.4 — Tier-2 semantic & ripple-effect checks (surface to user)

Tier-2 issues involve **business meaning** and must **never** be silently
guessed:

1.  **Ripple effects on targeted edits:** When the user changes a metric
    definition, filter, status code, or join key in one concept doc (e.g.,
    changing `documents/concepts/active-customer.md` from 90 days to 60 days, or
    changing what counts as `revenue`):

    -   Search `bundle/` (or the active in-place `<okf_folder>/`, e.g.,
        `grep -rn "<changed-entry-id-or-concept>" bundle/`) and inspect the
        links (`bundle/_links.yaml` or `<okf_folder>/_links.yaml`, and page
        frontmatter `links` / `extra.links` / `x-kcmd.links`) to find every
        other concept doc, table-context doc, and sample query that links to or
        mentions that concept/column/threshold.
    -   In your response, **explicitly list every downstream entry and sample
        query** that may now be out of sync (with its entry ID and the specific
        line/SQL filter affected), and ask whether the user wants those updated
        too (or if only the target file should be changed).

2.  **Conflicting business definitions across files:** If an existing bundle or
    multi-file workspace has two entries or source documents that define the
    same metric, threshold, or join rule differently:

    -   Do **not** silently overwrite one with the other.
    -   Keep/add a visible `> **Conflict / Open question:**` note citing both
        sources, and surface the conflict prominently in your review summary so
        the user can decide which definition wins.
