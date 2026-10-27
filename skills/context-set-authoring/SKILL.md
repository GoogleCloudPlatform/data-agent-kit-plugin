---
name: context-set-authoring
description: |
  Build or edit a Knowledge Catalog (KC) context set by authoring Open Knowledge Format (OKF v0.2)
  markdown files directly under `bundle/` (links in `bundle/_links.yaml`). Use for any task that
  creates, imports, pulls, edits, repairs or publishes a context set (BigQuery, Spanner, BigLake,
  Cloud SQL or AlloyDB sources), or that involves `kcmd`:
  e.g. "create a context set from our revenue tables and the finance SOP", start one from an
  existing OKF bundle, "add a sample query for Q". Plans first, validates with
  `kcmd push --dry-run` (and the engine's compile check for SQL), and pushes only after user approval; ends
  its turn after the plan and after the review, even when told to work autonomously. Respects and
  pushes the user's own OKF directory structure when requested rather than forcing a layout. If the
  request also asks for OSI-G semantic models, new glossary terms or certification, still use it:
  it builds the context set and declines those parts. Not for read-only catalog or data questions.
license: Apache-2.0
metadata:
  version: v3
  publisher: google
---

<!-- disableFinding(LINE_OVER_80) -->

# Context Set Authoring (Direct OKF)

Author or update a Knowledge Catalog **context set**: an entry group
(`type: context-set`) of table-context documents (with grounded representative
SQL queries in their `queries` aspect), knowledge-base documents, an `agents`
router root (`type: Context Set` or `type: Knowledge Base Root`, normalized to
`dataplex-types.global.document.data.type: context-set`), and the `EntryLinks`
between them in `bundle/_links.yaml` (`reference` links to source tables' system
entries such as `@bigquery` or `@spanner`, `related` links connecting index
pages to child entries plus concept docs to governing tables and joined tables,
and `definition` links to existing `@dataplex` glossary terms), represented on
disk as an **Open Knowledge Format (OKF v0.2)** bundle directly under `bundle/`
(`catalog.yaml` at the workspace root). One context set can cover tables from
several engines (`references/source_engines.md`).

Instead of calling per-entry CLI subcommands to author each entry one by one,
you **write and edit the OKF `.md` files and `bundle/_links.yaml` directly**,
validate with `kcmd push --dry-run` (plus the engine's cost-free compile check
for SQL queries, e.g. `bq query --dry_run` for BigQuery), and publish with
`kcmd push` after user approval.

**SQL goes in the table page's `queries` aspect only (`output_contract.md`
§3):**

-   Put every SQL query you author (metric/KPI queries and concrete examples
    from user-provided SQL, golden/pinned queries, or docs) in the
    `dataplex-types.global.queries` aspect of the `Table Context` page of the
    main table it queries (`userManaged: true`, `source: USER`, and the engine's
    `sqlDialect`, e.g. `GOOGLE_SQL` for BigQuery), as concrete, executable SQL
    in that engine's dialect with literal values, checked with the engine's
    cost-free compile check (`references/source_engines.md`). Keep the source's
    filters and literal values as written.
-   **Query templates are not authored yet.** Don't create `query-template`
    entries, `query-context/templates/` pages, or `@param` placeholders. If the
    user asks for a query template or gives `@param` SQL, say in one line in the
    Gate 1 plan that query-template entries aren't authored yet, and offer the
    query with literal values in the table page's `queries` aspect instead (use
    the sample values they gave, or ask for them).
-   Leave existing `query-template` / `query-templates/` entries in a pulled
    context set untouched, unless the user asks to change them or approves a
    ripple fix in the plan; then edit only the affected SQL or text in place
    (`references/kc_constructs/SUBSKILL.md`, "Pages you didn't write").

--------------------------------------------------------------------------------

## Non-negotiable guardrails

### 1. Grounding — never invent business knowledge

Every fact you write into a document, table description, column note, join, or
SQL query must come from:

-   a source the user provided in this session (files on disk, text in the
    prompt, an OKF bundle),
-   an existing context set pulled into `bundle/` with `kcmd pull`, or a 1P
    resource entry, aspect, glossary term, or schema fetched from Knowledge
    Catalog (`search_entries` and `lookup_entry` via the Knowledge Catalog MCP
    to inspect source table entries in any engine's system entry group, column
    descriptions, existing `overview` / `schema` / `queries` aspects, and
    `@dataplex` glossary terms to inform context set authoring), or
-   a live schema or query result from the source's engine.

**No unverified specifics.** Each of the following needs a source — a schema or
column description, a user-provided document, a 1P Knowledge Catalog
entry/aspect, or an aggregate / bounded profiling query you actually ran in this
session (cite which) — or it stays out of the pages and goes under **Open
questions** in the plan:

-   **Column meanings (NEVER gloss from column names).** Always inspect the
    table schema (`lookup_entry` via the Knowledge Catalog MCP when additional
    entry/column metadata is needed, the engine's schema read in
    `references/source_engines.md`, or provided schema files) before writing
    column tables. If a column has an empty or missing description in the schema
    and no user-provided document defines it, you **must** write the exact
    literal text `No description in source.` in the description cell (optionally
    followed by values observed from an aggregate or bounded profiling query you
    ran). **Never** infer, paraphrase, or restate a column's meaning from its
    column name (never turn `<noun>_<qualifier>` into
    `"The <qualifier> of the <noun>"`, and never expand abbreviations or units
    implied by a name). **A column appearing in a doc's formula, filter, or SQL
    is not a definition of it.** If a doc only uses the column (e.g.
    `<METRIC> = <col_a> <= <col_b> AND <col_c> = <col_d>`), the cell is
    `No description in source.` followed by how the doc uses it, quoted and
    cited (`No description in source. Used in <METRIC>: <col_c> = <col_d> (<doc>
    §<section>).`). Only text in the doc that says what the column *is* or
    *contains* counts as a description. Before writing each table page, check
    every non-verbatim cell against this rule.
-   **Value sets, thresholds, and cutoffs** (allowed values of a status or
    category column, numeric lower/upper bounds, time windows).
-   **Prescriptive rules and edge-case interpretations** ("should filter /
    exclude / cap / sum …", "zero or negative values mean …", "rows of kind X
    should be excluded"). Don't add general "data-quality best practice" that no
    source states, and don't explain why values are NULL, zero, or unusual
    ("indicates…", "reflects…") unless a source says so.
-   **Gaps in a source's categorization.** When a document's rule doesn't cover
    every value (e.g. it defines two of a column's categories but the column has
    others), list the uncovered case as an **Open question** in the plan; don't
    add an `ELSE 'Other'` bucket or a default unless the source defines one.
-   **Joins and references** to any table that isn't one of the context set's
    inputs, and join keys between inputs that no description, document, or query
    you ran establishes.
-   **Filters and values inside SQL queries.** A query only applies filters,
    thresholds (`HAVING`, minimum counts), and example values that the user
    asked for or a source states; don't add defensive `WHERE`/`HAVING` clauses
    or extra knobs.

If the prompt gives **no sources at all** (no table IDs, no context-set ID, no
local files, no domain details) or asks you to invent schemas and KPIs ("make up
standard definitions", "don't ask me questions"): **stop immediately**. Write
nothing, do not run `kcmd init`, and ask the user for:

1.  Which tables or datasets to cover, in any engine (or a topic to search for
    in Knowledge Catalog).
2.  Any source documents, SOPs, metric definitions, or SQL queries they have.
3.  The project, location, and name for the context set (or whether they want
    local files only).

When sources **disagree** (e.g., two docs define a metric differently, or a doc
contradicts the physical schema): **never silently pick one**. Surface both
versions with exact citations in the plan and in a `> **Open question:**`
callout in the concept doc, and ask the user which is authoritative.

### 2. Two hard gates — stop and wait for user approval

-   **Gate 1 — Plan approval**
    -   **Before you:** Run `kcmd init`, create/modify any file under `bundle/`
        or `catalog.yaml`, or touch existing files
    -   **You must present:** The structured authoring plan
        (`references/plan.md`)
    -   **And then:** **End your turn.** Wait for the user to approve.
-   **Gate 2 — Push approval**
    -   **Before you:** Run `kcmd push` (without `--dry-run`)
    -   **You must present:** Validation results (`kcmd push --dry-run`, SQL
        compile-check status), summary of added/modified/deleted entries and
        links, and any Tier-2 findings (`references/review_publish.md`)
    -   **And then:** **End your turn.** Wait for the user to approve pushing.

**"Don't wait for approval" / "just build and push it" prompts do NOT override
Gate 1 or Gate 2.** Even when the user says *"go ahead and build it without
waiting"* or *"push it right away"*, or asks to edit or repair an existing
`bundle/` and publish it after a review:

-   Present the **Gate 1 Plan** (for an edit or repair: the files you'll change,
    ripple effects, and anything you won't change) and **end your turn** without
    writing any files. Skip Gate 1 only when the user has already approved that
    exact list of changes in this conversation.
-   Push only on an unambiguous approval of the Gate 2 review (the user
    explicitly says to publish). Approving the plan, or a reply that asks to
    see, stage, or change something, is not push approval: re-present the Gate 2
    review and stop.

### 3. Scope boundaries — decline out-of-scope actions

A context set's authored content lives **inside its own entry group**
(`type: context-set`). If the user asks for any of the following, **explicitly
decline** that part (explain why) while still helping with the in-scope
context-set work:

-   **Certifying** the context set or any entry (certification is a
    governance/steward action in the console/IAM, not performed by this
    authoring workflow).
-   **Setting access** (IAM) on the context set, e.g. "owner-only" or "readable
    by group X". This workflow doesn't change permissions; a new context set
    gets the access its project grants. Say so in the Gate 1 plan and tell the
    user to set access in the console or IAM after publishing.
-   **Creating or modifying Knowledge Catalog Business Glossary terms** in
    `@dataplex` (you can *link* to existing `@dataplex` glossary terms via
    `definition` links, or create a `Knowledge Base` concept doc *inside* the
    context set, but never create or edit glossary terms).
-   **Modifying system entries directly** (`@bigquery` or any other engine's
    system entry group: no aspects, including sample queries, on source tables
    or columns; instead, create a `Table Context` doc inside the context set
    that points its `resource:` frontmatter at the system entry and carries the
    queries).
-   **Adding `schema-join` links between source tables** (describe join keys in
    the `Table Context` body text and connect related entries with `related`
    links instead).
-   **Authoring OSI-G semantic models** (out of scope for OKF context sets).

**Cost-bounded reads & privacy.** Before running any exploratory query that
reads table rows (profiling, checking distinct values, or an opt-in live test of
a SQL query), run the engine's cost-free compile check first and use aggregate
or bounded `LIMIT` queries (`references/source_engines.md`) — never copy
sensitive values (PII, secrets) into the context set or the chat. Compile
checks, schema reads, and Knowledge Catalog lookups (`search_entries`,
`lookup_entry`) are always fine.

### 4. Local OKF-first default — never touch remote KC unless asked

-   **Local files first:** Before running any `kcmd` command, check the current
    working directory (and any path the user mentioned) for `catalog.yaml` and
    for OKF content in any folder, whatever it is named (`.md` files with
    `type:` frontmatter, an `index.md`, or a `_links.yaml`).
-   **Edit in place with no remote calls:** If local OKF `.md` files already
    exist and the user asks to edit, add, or fix entries locally (without
    mentioning a remote `PROJECT.LOCATION.ID` or asking to pull/push), **edit
    the local `.md` files directly** and verify structural integrity across
    `bundle/` (`references/validate.md`). Do **not** run `kcmd init`,
    `kcmd pull`, or `kcmd push`.
-   **Read-only export / pull-only (`kcmd pull` without edits):** When the user
    asks only to export or download an existing remote context set to a local
    folder without requesting changes, confirm the destination at Gate 1, run
    `kcmd init` + `kcmd pull`, **report** any Tier-1/Tier-2 defects without
    auto-rewriting pulled files (preserving a faithful export), and finish with
    the concise local-only summary (`references/review_publish.md`).
-   **Existing local OKF folder the user wants to publish (edit in place, no
    copies):** If the user points at their own OKF folder (any name) and asks to
    update it and publish it to a context set, plan the edits on that folder's
    files and, after Gate 1, make them in place. Bind that folder to the context
    set as the kcmd workspace (see `references/navigate.md`) instead of copying
    its pages into a second `bundle/`. Only create a copy if the user asks for
    one; if the installed `kcmd` can't publish the folder where it is, say so in
    the plan and ask before moving anything.
-   **Importing an existing OKF bundle or respecting a custom directory
    structure (never force our opinionated layout, and preserve upstream
    frontmatter):** Our progressive-disclosure layout (`bundle/agents.md`,
    `bundle/assets.md`, `bundle/assets/<engine>/<container>.md`,
    `bundle/documents.md`) is the default when creating a new context set from
    scratch, **never a forced requirement**. When importing an existing OKF v0.2
    bundle (any folder the user names or that holds OKF pages, recognized by
    content rather than folder name) or when a user has their own OKF folder
    structure:
    -   In the Gate 1 plan, map each bundle file to the entry it becomes (SQL
        pages and OKF `type: Attested Computation` pages become literal-value
        queries in the relevant table page's `queries` aspect when fitting our
        progressive-disclosure layout — if `@param` or dbt `{{ var(...) }}`
        placeholders are present, note in one line that KC `query-template`
        entries are post-Preview and offer literal sample values in the
        `queries` aspect while keeping narrative metric/concept docs; existing
        `query-template` entries in a pulled bundle stay as they are), list any
        index pages or links you propose adding, and **always ask the user
        whether they want to (1) fit our progressive-disclosure context-set
        layout (recommended) or (2) keep and push their OKF bundle in its
        current directory structure as-is**. Recommend option 1, but never apply
        it without the user's choice.
    -   **Preserve upstream OKF v0.2 metadata & wording losslessly:** When
        importing or editing existing OKF pages, always preserve upstream
        frontmatter keys (`sources:` with credibility signals + `usage_window:`,
        `generated: { by, at }`, `verified:` as `[{ by, at }]` / `{ by, at }`,
        `status: draft | stable | deprecated`, an ISO 8601 `stale_after:`
        without ever inventing one, `tags:`, and any unknown or extension keys
        verbatim at any level, per OKF v0.2 §4.1) and upstream body caveats /
        `[^id]` footnotes verbatim in the `.md` files (while never fabricating a
        `dataplex-types.global.certification` aspect), and enrich thin table
        pages append-only using verified schema/profile sources (never inventing
        column types or meanings).
    -   If they choose to keep their directory structure, preserve their
        folders, entry paths (including `Attested Computation` pages,
        frontmatter `runtime` / `parameters` / `computation` / `executor` /
        `attester`, and non-`.md` assets), and wording as-is and push it without
        forcing progressive-disclosure index pages. Keep repo-level non-concept
        `.md` files (`README.md`, `CONTRIBUTING.md`) outside `bundle/` when
        pushing with `kcmd`.
-   **Ask which workspace mode when creating a new context set without a remote
    scope:** If no local OKF files exist and the user has not specified whether
    they want a standalone local OKF bundle or a remote-backed `kcmd` workspace,
    **ask in your Gate 1 plan**:
    1.  **Progressive-disclosure OKF bundle** (`bundle/agents.md`,
        `bundle/assets.md`, `bundle/documents.md`,
        `bundle/assets/<engine>/<container>.md` and
        `bundle/assets/<engine>/<container>/<table>.md` (e.g.
        `bundle/assets/bigquery/<p>/<d>/<table>.md`),
        `bundle/documents/<slug>.md`, `bundle/_links.yaml`, plus optional
        untyped `bundle/index.md` — default for local authoring and GDA
        consumption, or the user's preferred folder layout), or
    2.  **kcmd-synced workspace** (`catalog.yaml` + the same portable
        `bundle/...` layout for syncing with a remote Knowledge Catalog entry
        group). In the question to the user, call these "(a) local files only"
        and "(b) linked to a Knowledge Catalog context set you can publish to".

### 5. Plain language & product naming in replies (say "Knowledge Catalog", never "Dataplex"; NEVER show internal CLI flags)

Commands, flags, file names like `catalog.yaml`, and placeholders like
`<PROJECT>.<LOCATION>.<CONTEXT_SET_ID>` are for you, **never** for the user.

-   **Product naming — always say "Knowledge Catalog", never "Dataplex":** In
    all user-facing replies, plans, reviews, questions, and authored `.md` body
    prose, refer to the product as **Knowledge Catalog** (and **Knowledge
    Catalog Business Glossary**), **never** **Dataplex** or **Dataplex Universal
    Catalog** — even though underlying APIs, MCP tools, resource URIs
    (`@dataplex`, `dataplex-types.global.*`), IAM roles (`roles/dataplex.*`),
    and `gcloud dataplex` commands contain `dataplex`. Keep `dataplex` strictly
    inside required technical identifiers in OKF YAML/`_links.yaml` (such as
    `dataplex-types.global.queries` or `@dataplex` link target URIs) or literal
    commands/role IDs under the three allowed exceptions below.
-   **Forbidden strings in user-facing replies:** Never include `kcmd init`,
    `kcmd pull`, `kcmd push`, `kcmd push --dry-run`, `--dry-run`,
    `--format okf`, `--entry-group`, engine commands (`bq query --dry_run`,
    `gcloud spanner ...`, `EXPLAIN`), or `<PROJECT>.<LOCATION>.<CONTEXT_SET_ID>`
    in your Gate 1 plan, Gate 2 review, clarifying questions, or status updates.
-   **How to phrase actions instead:** Always use plain product language: say
    *"catalog publish preview"* or *"bundle validation (0 errors)"* instead of
    `kcmd push --dry-run`; say *"BigQuery compile check"* (or *"Spanner compile
    check"*, etc.) or *"cost-free SQL compile check"* instead of the engine
    command; say *"download the context set"* instead of `kcmd init` /
    `kcmd pull`; and say *"publish to Knowledge Catalog"* instead of
    `kcmd push`. Ask for missing target settings as *"which project, location,
    and context set name?"*.
-   **Only three allowed exceptions:** (1) a concrete
    `gcloud dataplex entry-groups add-iam-policy-binding ...` command that the
    user must run themselves to grant reader access, (2) telling the user that
    `kcmd` is not installed and giving the install command for the official
    `@google-cloud/kcmd` npm package (never the unscoped `kcmd`) or their Data
    Agent Kit setup instructions, or (3) answering an explicit user question
    about how the CLI works.

--------------------------------------------------------------------------------

## Workflow overview

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 1. DISCOVER & PLAN (read-only)                  references/plan.md  │
  │    • Inspect local files FIRST (ls / read existing OKF .md files)   │
  │    • Only run kcmd init + pull if a remote context set is named     │
  │    • Check lookalike tables, source conflicts, ripple effects       │
  │    • Present structured plan ──► STOP (Gate 1: wait for approval)   │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 2. AUTHOR OKF DIRECTLY    references/kc_constructs/SUBSKILL.md &    │
  │                           references/kc_constructs/output_contract.md│
  │    • Local OKF or `kcmd init --entry-group <P.L.ID> --format okf`   │
  │    • Write/edit `.md` files & `_links.yaml` directly                │
  │    • For targeted edits: touch ONLY the target file (+ affected)    │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 3. VALIDATE & REPAIR                          references/validate.md│
  │    • Check Tier-1 OKF hierarchy, frontmatter, and links             │
  │    • Compile-check each SQL query in its engine (cost-free)         │
  │    • Run `kcmd push --dry-run` (checks changed entries/links only)  │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 4. REVIEW & PUBLISH                     references/review_publish.md│
  │    • Local-only mode: present validation summary & changed files    │
  │    • Remote mode: present `kcmd push --dry-run` summary ──► STOP    │
  │    • Only after explicit push approval: run `kcmd push`             │
  │    • Verify published entries in Knowledge Catalog                  │
  └─────────────────────────────────────────────────────────────────────┘
```

### Which reference to load

1.  **Always read `references/plan.md` first** when starting a new context set,
    importing an OKF bundle, or planning an edit.
2.  **Read `references/kc_constructs/SUBSKILL.md` and
    `references/kc_constructs/output_contract.md`** before writing or editing
    any file under `bundle/` (exact OKF v0.2 frontmatter, flat `bundle/`
    progressive-disclosure hierarchy, `[Title](/path.md)` and relative link
    syntax, and `bundle/_links.yaml` format).
3.  **Read `references/validate.md`** when running Tier-1 / Tier-2 validation or
    repairing an existing bundle.
4.  **Read `references/review_publish.md`** before presenting the Gate 2 review
    or running `kcmd push`.
5.  **Read `references/navigate.md`** when you need `kcmd init` / `pull` /
    `push` details or the workspace layout.
6.  **Read `references/source_engines.md`** whenever a source table is not in
    BigQuery (or the set mixes engines): system entry group and `resource:`
    form, schema read, compile check, profiling, and `sqlDialect` per engine.

--------------------------------------------------------------------------------

## Quick command reference

Only three `kcmd` commands are used by this workflow: `init`, `pull`, and `push`
(never other subcommands or `--force`). `--format okf` is only passed to
`kcmd init` (it writes `layout: okf` to `catalog.yaml`); `kcmd pull` and
`kcmd push` read the layout from `catalog.yaml`. Never edit `catalog.yaml` by
hand.

**Step 0 — Make sure `kcmd` is available FIRST (before reading files or
planning):** Whenever the request involves creating, importing, pulling, or
publishing a remote Knowledge Catalog context set (or mentions `kcmd`), make
checking for `kcmd` (`test -x ./kcmd || command -v kcmd`) your **very first tool
call** (look only on `PATH` and in the workspace; don't crawl the filesystem for
other copies). If `kcmd` is missing and the user hasn't asked you not to install
software:

1.  **Install the official package from npm.** The Knowledge Catalog CLI is the
    scoped npm package `@google-cloud/kcmd`. If `command -v npm` finds npm, run
    `npm install -g @google-cloud/kcmd`. If that fails because the global folder
    isn't writable (for example as a non-root user), run
    `npm install --prefix "$HOME/.local" -g @google-cloud/kcmd` and call
    `"$HOME/.local/bin/kcmd"` (or put `$HOME/.local/bin` on `PATH` for later
    commands). Check it with `kcmd --version`, then continue.
    -   **Never** run or suggest the unscoped `npm install kcmd`, `npx kcmd`, or
        `pip install kcmd`: the unscoped `kcmd` names on public registries are
        unrelated third-party packages.
2.  **If npm isn't available, the install fails** (for example the package can't
    be found, there's no network, or permission is denied), **or the user
    doesn't want software installed:** don't write a stand-in `./kcmd` script
    and don't call Knowledge Catalog APIs (such as `gcloud dataplex`) directly.
    Instead, **state at the very top of your reply** that the Knowledge Catalog
    CLI (`kcmd`) isn't installed, that `@google-cloud/kcmd` couldn't be
    installed from npm (one line on why), and that nothing has been published
    yet. Give safe install guidance: `npm install -g @google-cloud/kcmd` once
    the package is available, or the user's Data Agent Kit setup instructions
    (building from `toolbox/mdcode` in `GoogleCloudPlatform/knowledge-catalog`),
    and warn them not to install the unscoped `kcmd` package.
3.  **Prepare the Gate 1 plan in the same reply** (grounded in any local files,
    using plain product language without raw `kcmd init` / `kcmd push --dry-run`
    command syntax) so the request stays ready to resume as soon as `kcmd` is
    installed and the user approves the plan. When the user later confirms
    `kcmd` is installed, check again and resume from the approved step without
    asking them to repeat their prompt.

```bash
# Workspace setup (ONLY after Gate 1 approval, or to inspect an existing remote context set)
kcmd init --entry-group <PROJECT>.<LOCATION>.<CONTEXT_SET_ID> --format okf   # writes `layout: okf` to catalog.yaml
kcmd pull                      # only if init didn't already pull the existing context set

# Validation (run after authoring/editing bundle/, before Gate 2)
kcmd push --dry-run
bq query --dry_run --use_legacy_sql=false "<SQL>"   # BigQuery; other engines: references/source_engines.md

# Publish (ONLY after Gate 2 approval)
kcmd push
```
