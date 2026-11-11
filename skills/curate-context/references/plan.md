<!-- disableFinding(LINE_OVER_80) -->

# Phase 1 — Discover & Plan (`references/plan.md`)

During Phase 1 you are in **read-only mode**. Do **not** run `kcmd init` (except
to inspect an existing remote context set, Rule C), do **not** create or modify
any file under `bundle/`, and do **not** run `kcmd push`.

--------------------------------------------------------------------------------

## Step 1.0 — Check `kcmd` availability & inspect the local workspace FIRST

1.  **If the request targets a remote Knowledge Catalog context set (or mentions
    `kcmd`), resolve `kcmd` safely before anything else** (`SKILL.md` Step 0):
    check `kcmd --version` on `PATH` first, then
    `"$HOME/.local/bin/kcmd" --version`, and save whichever command succeeded
    for every later `kcmd` call. Never prepend `$PWD` to `PATH` or auto-run
    `./bq`, `./gcloud`, or `./kcmd` from `$PWD` (only use a workspace wrapper if
    the user named it in this conversation or confirms after you show its path
    and first few lines, including `#!`, alongside your Gate 1 plan). If `kcmd`
    is missing, state at the top of your reply that it isn't installed and
    nothing was created/published yet, give safe `@google-cloud/kcmd` install
    guidance (never unscoped `kcmd`), and present the Gate 1 plan asking whether
    to install `@google-cloud/kcmd` alongside approving the plan.
2.  Before running any `kcmd` command, inspect the current working directory
    (and any directory named in the prompt):

-   If OKF `.md` files already exist locally (in `./`, `bundle/`, or any folder
    the user names):
    -   **Local edit / repair request** (user asks to update a definition, add a
        sample query, fix orphans, or edit the local context set without asking
        to pull from or push to a remote KC entry group): read only the relevant
        local `.md` files and their links (`_links.yaml` and page frontmatter
        `extra.links` / `x-kcmd.links`). **Do not run `kcmd init`, `kcmd pull`,
        or `kcmd push`.** Gate 1 still applies: present a short edit plan (Step
        1.4) before changing any file.
    -   **Targeted single-entry or definition edit:** Read the target concept
        file first. If changing a definition, column filter, or threshold,
        search `bundle/` (or the active in-place `<okf_folder>/` using your host
        search tool or `grep -rn "<entry-id-or-concept>" bundle/`) to find every
        entry, sample query, and link that references it so you can list
        **ripple effects** before or alongside the edit.
-   If the user asks only to **export / download** an existing remote context
    set to a local folder without edits: confirm the destination folder and
    target context set in a brief Gate 1 plan; after approval, run `kcmd init`
    (and `kcmd pull` only if `init` didn't already populate `bundle/`), report
    any Tier-1/Tier-2 defects without rewriting pulled files, and present the
    local-only closing summary (`references/review_publish.md`).
-   If no local OKF files exist yet:
    -   Check whether the user gave a remote context-set scope
        (`PROJECT.LOCATION.CONTEXT_SET_ID`) or asked for a local standalone OKF
        bundle.
    -   **If the user didn't say**, ask the local-only-or-publishable question
        from `SKILL.md` §4 in your Gate 1 plan.

--------------------------------------------------------------------------------

## Step 1.1 — Check grounding and inputs

Inspect what the user gave you:

1.  **Zero context provided?** If the user asks to create a context set from
    scratch (e.g., *"Create a context set for our sales data"* or *"Set up a
    context set with standard metrics, don't ask questions"*) without naming any
    tables, datasets, local files, or existing context-set IDs:

    -   **Stop immediately.** Do not search randomly and do not invent tables or
        definitions.
    -   Ask the user for:
        1.  The tables to cover in any engine, e.g. BigQuery
            project/dataset/tables or Spanner instance/database/tables (or a
            search term + project to look up in KC).
        2.  Any local documents, SOPs, glossary notes, or example SQL queries.
        3.  The project, location, and name for the context set, or whether they
            want local files only.
    -   **End your turn.**

    **Exception, existing context set named by topic but not by ID:** If the
    user asks to pull, review, or edit an existing context set and gives a
    project (or a topic) but not its ID, look it up before asking: search
    Knowledge Catalog (`search_entries` first; otherwise list the project's
    entry groups in the source tables' locations, their multi-region (`us` or
    `eu`), and `global` with
    `gcloud dataplex entry-groups list --project=<PROJECT> --location=<LOC>`)
    and show the matches in plain language for the user to pick before running
    `kcmd init` or `kcmd pull`. Ask for the ID only if the lookup finds nothing
    or can't run.

2.  **Local files or an existing OKF bundle?** Read all local `.md`, `.sql`,
    `.yaml`, or `.txt` files the user referenced (or that sit in the working
    directory).

    -   If the workspace already has an OKF v0.2 bundle (any folder the user
        points at, or any folder holding `.md` pages with `type:` frontmatter,
        an `index.md`, or a `_links.yaml`, whatever its name) that needs to be
        imported into a context set, read every file in it AND inspect any
        schema/source files the user provided (or read each table's schema per
        `references/source_engines.md`) so your plan accounts for every concept,
        table, column, and SQL query. The plan must:
        -   Map each bundle file to its entry and preserve upstream OKF v0.2
            provenance, trust, lifecycle, and extension frontmatter keys plus
            body caveats / `[^id]` footnotes verbatim (see
            `references/kc_constructs/SUBSKILL.md` §2 for how SQL pages,
            `Attested Computation` pages, and upstream frontmatter are handled).
        -   Say that the import works on the user's folder in place (one copy by
            default; see `SKILL.md` §4 and `references/navigate.md` §1): if the
            folder isn't named `bundle/`, run `kcmd init` first, remove only the
            scaffolded stub `bundle/` folder, and link `bundle -> <folder>`
            (`ln -s` on macOS/Linux; `mklink /J` on Windows) rather than copying
            or renaming it; make a separate copy only if the user explicitly
            asks. For option 1 below, list every page move, rename, and
            deletion.
        -   List what you propose adding on top, and **always ask whether the
            user wants to (1) convert to our progressive-disclosure layout
            (recommended) or (2) keep and push the OKF bundle in its current
            directory structure as-is** (recommend option 1, never force it; if
            they pick option 2, preserve their `Attested Computation` pages,
            frontmatter, and assets intact).

--------------------------------------------------------------------------------

## Step 1.2 — Discover entries in Knowledge Catalog (only when remote assets/scope are involved)

Follow these discovery rules strictly:

### Rule A — Exact table IDs given (e.g. BigQuery `project.dataset.table`)

If the user provides **exact** table IDs or resource names in any engine and
says those are the tables to use:

-   Fetch each table's system entry directly by its entry name, built from the
    engine's row in `references/source_engines.md`. BigQuery example:

    ```
    projects/<BQ_PROJECT>/locations/<bq_location>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>
    ```

    *(Both `<BQ_PROJECT>`s are the table's project, not the context set's;
    `<bq_location>` is the dataset's location in lowercase, e.g. `us` for a `US`
    dataset. Other engines follow the same pattern with their own group,
    resource name, and location. Use the same name for the table page's
    `resource:`.)*
-   When the Knowledge Catalog MCP is available, inspect existing Knowledge
    Catalog resource entries to inform context set authoring: call
    `lookup_entry` on each table's entry name to read its full schema, column
    descriptions, existing `overview` / `queries` aspects, and location (if the
    location isn't known yet, read it per `references/source_engines.md` or run
    a single scoped `search_entries` call to obtain the full entry name).
-   **Do NOT run broad catalog searches for tables when exact table IDs were
    already given.**
-   Search Knowledge Catalog (`search_entries`) for relevant `@dataplex`
    glossary terms
    (`type=projects/dataplex-types/locations/global/entryTypes/glossary-term ...`)
    or related domain catalog entries when needed to ground business definitions
    and `definition` links.

### Rule B — Loose table names or topic description given

If the user names tables loosely (e.g., *"the orders and customers tables in
project X"*, or *"our revenue tables"*):

-   Search Knowledge Catalog (`search_entries`) scoped to the target `<PROJECT>`
    to find candidate table entries in any engine (`@bigquery`, `@spanner`,
    `@biglake`, `@cloudsql`, `@alloydb`, `@dataprocmetastore`, ...), `@dataplex`
    glossary terms, and related catalog entries, and use that catalog context to
    inform context set authoring.
-   Inspect every candidate table's full schema, row/column descriptions,
    existing `overview` / `queries` aspects, and timestamps/deprecation notes
    (call `lookup_entry` via the Knowledge Catalog MCP).
-   **Lookalike / duplicate table check:** Whenever discovery returns multiple
    similar tables (e.g., `orders` vs `orders_v2` vs `orders_legacy` vs
    `stg_orders`), **flag all lookalike candidates** in your plan, compare their
    schemas/descriptions, state which one you recommend (and why), and ask the
    user to confirm before authoring.

### Rule C — Existing remote context set

If the user references an existing remote context set
(`PROJECT.LOCATION.CONTEXT_SET_ID`) and `catalog.yaml` is not yet initialized
locally, you may run
`kcmd init --entry-group <PROJECT>.<LOCATION>.<CONTEXT_SET_ID> --format okf`,
then `kcmd pull` only if `init` didn't already pull the entries (or read the
existing `bundle/` if already pulled), to read the current state. This only
writes the local workspace; it does not change Knowledge Catalog. Read the notes
`init`/`pull` print (`references/navigate.md` §3–4).

--------------------------------------------------------------------------------

## Step 1.3 — Cross-check sources for conflicts, location rules & gaps

Before drafting the plan, compare all sources (user prompt, local SOP/markdown
files, source table schemas in every engine, `@dataplex` glossary terms, and
existing `bundle/` entries):

1.  **Source conflicts:** Does Document A define a metric/filter/threshold
    differently from Document B, the user prompt, or a SQL query? (e.g.,
    `status = 'COMPLETED'` vs `status IN ('COMPLETED', 'SHIPPED')`, or 30-day vs
    90-day churn window, or gross vs net revenue).
    -   **Never pick a winner.** List both definitions with their exact source
        citations (`file:line` or entry ID) in a **Conflicts & Open Questions**
        section of the plan.
2.  **Schema mismatches:** Does a source doc or SQL query reference a column or
    table that does not exist in the source table's schema? Flag it explicitly.
3.  **Cross-location links:** Apply the location rule in `SUBSKILL.md` §3 and
    call out any cross-location link you'll omit in the plan.
4.  **Out-of-scope requests:** Did the user ask to certify entries, create new
    `@dataplex` glossary terms, modify system entries (`@bigquery` or any
    engine) directly, or build an OSI-G model? Note clearly in the plan which
    items are declined and what in-scope alternative you will build (e.g.,
    linking to existing `@dataplex` terms or authoring a `Knowledge Base`
    concept doc inside the context set).

--------------------------------------------------------------------------------

## Step 1.4 — Present the Gate 1 Plan and STOP

Keep the plan concise: counts and **one line per item** (table, page, query,
link). Do **not** paste full schemas, full SQL, or whole pages into the plan;
list sample queries with a count and a one-line description of what each
computes. **Write strictly in plain product language (`SKILL.md` §5):** always
refer to the product as **Knowledge Catalog** (never **Dataplex**), show names,
titles, and paths, and never include raw CLI commands, flags, or
`<PROJECT>.<LOCATION>.<CONTEXT_SET_ID>` placeholders in the plan.

Format your response clearly with these sections:

1.  **Target Context Set & Layout:**
    -   If remote scope given: the project, location, context set name, display
        name, description, and where the files will go (directly under
        `bundle/`, with no `<id>/<project>/<location>/` folder prefix). **If the
        location is missing**, propose the source tables' shared location as the
        default and ask the user to confirm it; if the tables are in different
        locations, ask (a `global` context set can link to any location,
        `SUBSKILL.md` §3). This is the one value you may propose.
    -   If no remote scope given: propose the target `bundle/` structure and
        **ask the user whether they want (a) local files only or (b) files
        linked to a Knowledge Catalog context set they can publish to** (and if
        (b), which project, location, and name).
    -   **Never fill in a missing project or context set name yourself.** If the
        user didn't name them, don't propose, pick, or "assume" one in the plan,
        not even as a placeholder: ask for the missing values in one short
        question (with any readers or access the user mentioned) and leave the
        rest of the plan to your next turn. Values found only in source files
        (e.g. the tables' project in a schema file) are not the user's choice of
        target.
2.  **Discovered Assets & Lookalikes:**
    -   Tables inspected (engine, system entry name + key columns).
    -   Any lookalike/duplicate tables found and which one is recommended.
    -   Any existing Knowledge Catalog Business Glossary (`@dataplex`) terms
        found to link via `definition` (call it *Knowledge Catalog Business
        Glossary* to the user, never *Dataplex*).
3.  **Planned OKF Files (`bundle/`):**
    -   **Top-level router & category/dataset indexes (when using our default
        layout):** `bundle/agents.md` (`type: Context Set` or
        `type: Knowledge Base Root`), `bundle/assets.md`, `bundle/documents.md`,
        and container index pages `bundle/assets/<engine>/<container>.md` (e.g.
        `bundle/assets/bigquery/<project>/<dataset>.md`; skip single-child
        pass-through engine/project index pages by default unless fan-out or
        shared database context warrants them, `SUBSKILL.md` §1; keep
        `bundle/index.md` untyped with at most the optional `okf_version: "0.2"`
        key, OKF v0.2 §8, or remove an empty stub). If importing an OKF bundle
        or when the user prefers their own directory structure, ask whether to
        apply this layout (recommended) or keep their current directory
        structure as-is.
    -   **Table Context docs:** `bundle/assets/<engine>/<container>/<table>.md`
        (with `resource:` pointing to the engine's system entry,
        `extra.resource.parent: assets/<engine>/<container>`, grain, column
        semantics, caveats, and optional concrete representative SQL in the
        `queries` aspect).
    -   **Knowledge Base, Concept & Learning docs:**
        `bundle/documents/<slug>.md`, `bundle/documents/concepts/<slug>.md`, or
        `bundle/documents/learnings/<slug>.md` (`type: Knowledge Base`,
        `Concept`, or `Learning`; business rules, metric definitions, policies,
        and learnings — each cited to its source).
    -   **SQL queries (`queries` aspect):** list each query you'll put in a
        table page's `queries` aspect (metric/KPI queries and concrete examples
        from user-provided SQL, pinned/golden queries, docs, or imported
        `Attested Computation` pages), with literal values and a one-line
        description. If the user asked for a query template or gave `@param` /
        parameterized computation SQL, say that query-template entries aren't
        authored yet and offer the literal-value query instead.
    -   **Links (`bundle/_links.yaml`):** directed `reference` links from each
        `Table Context` doc to its same-location source system entry; undirected
        `related` links connecting **(i)** each index page (`agents`, `assets`,
        `<container>`, `documents`) to its child entries for the Knowledge
        Catalog Explore Context Graph and **(ii)** concept docs to the pages
        they govern plus commonly joined `Table Context` pages; and directed
        `definition` links only from a context-set page to an **existing**
        `@dataplex` glossary term (noting any cross-location external links
        omitted on a regional context set). Join keys and cardinality go in the
        table-context body text, never in a `schema-join` link.
4.  **Conflicts, Declined Out-of-Scope Items & Open Questions:**
    -   Any contradictions between sources (both sides cited).
    -   Any out-of-scope requests declined (certification, access settings,
        glossary term writes, OSI-G).
    -   Whether the user wants an opt-in bounded live execution check of each
        sample query in addition to the engine compile check.

End with a clear prompt asking the user to approve the plan (and answer any open
questions) before you write any files. **Stop your turn here.**
