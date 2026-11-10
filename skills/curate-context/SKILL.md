---
name: curate-context
description: >-
  Creates, imports, pulls, edits, repairs, or publishes a Knowledge Catalog (KC) context set as
  Open Knowledge Format (OKF v0.2) markdown under `bundle/` with `kcmd`, for BigQuery, Spanner,
  BigLake, Cloud SQL, AlloyDB, or Hive Metastore. Load FIRST whenever creating, importing, pulling,
  editing, repairing, or publishing a context set or OKF bundle/folder, or using `kcmd`, before
  running `kcmd` (never unscoped `kcmd` from pip/npx or unconfirmed `./kcmd`) or editing files:
  e.g. "build a context set from our sales tables and metric doc", "update churn in our context set
  and publish". Plans first, validates, and publishes only after user approval at both gates, even
  when told to work autonomously. Keeps the user's OKF folder/structure. If also asked for OSI-G
  semantic models, ontology canvases, new glossary terms, access changes, or certification, still
  use it: builds the context set and declines those parts. Never for read-only catalog search or
  data questions.
license: Apache-2.0
metadata:
  version: v4
  publisher: google
---

<!-- disableFinding(LINE_OVER_80) -->

# Curate Context (Direct OKF)

A Knowledge Catalog **context set** is an entry group of type `context-set`. It
holds table-context pages (with grounded SQL in their `queries` aspect),
knowledge-base documents, an `agents` root page, and the links between them in
`bundle/_links.yaml`: `reference` links to the source tables' system entries,
`related` links between pages, and `definition` links to existing glossary
terms. You author it as an **Open Knowledge Format (OKF v0.2)** bundle directly
under `bundle/`, with `catalog.yaml` at the workspace root. One context set can
cover tables from several engines
([references/source_engines.md](references/source_engines.md)). The OKF spec is
at
`https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md`;
"OKF v0.2 §N" below refers to its sections.

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
-   an existing context set pulled into `bundle/` with `kcmd pull`, or an
    existing resource entry, aspect, glossary term, or schema fetched from
    Knowledge Catalog (`search_entries` and `lookup_entry` with `view: "ALL"`
    and matching `location` via the Knowledge Catalog MCP to inspect source
    table entries, column descriptions, existing `overview` / `schema` /
    `queries` aspects, and `@dataplex` glossary terms; fall back to `bq show` /
    engine MCP on `bigquery-public-data`), or
-   a live schema or query result from the source's engine.

**No unverified specifics.** Each of the following needs a source — a schema or
column description, a user-provided document, an existing Knowledge Catalog
entry/aspect, or an aggregate / bounded profiling query you actually ran in this
session (cite which) — or it stays out of the pages and goes under **Open
questions** in the plan:

-   **Column meanings (NEVER gloss from column names).** Always inspect the
    table schema (`lookup_entry` with `view: "ALL"` via the Knowledge Catalog
    MCP, the engine's schema read in `references/source_engines.md`, or provided
    schema files) before writing column tables. Never infer, paraphrase, or
    restate a column's meaning from its name alone (for example turning
    `<noun>_<qualifier>` into `"The <qualifier> of the <noun>"`, or expanding
    abbreviations or units implied by a name). If a column has no description in
    the schema and no document defines what it is or contains, write the exact
    literal text `No description in source.` in the description cell (optionally
    followed by values observed from an aggregate query you ran, or a quoted,
    cited formula or filter where a document uses the column without defining
    it).
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

**Find an existing context set before asking for its ID.** When the user names a
context set by topic or project but not by full ID, search Knowledge Catalog
first (`references/plan.md`) and ask only if the lookup finds nothing or can't
run.

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
    -   **Before you:** Run `kcmd init` or `kcmd pull` (except to inspect an
        existing remote context set in an empty workspace, `references/plan.md`
        Rule C), create or modify any file under `bundle/`, or touch existing
        files
    -   **You must present:** The structured authoring plan
        (`references/plan.md`)
    -   **And then:** **End your turn.** Wait for the user to approve.
-   **Gate 2 — Push approval (NEVER in the same turn as authoring)**
    -   **Before you:** Run `kcmd push` (without `--dry-run`)
    -   **You must present:** Validation results (`kcmd push --dry-run`, SQL
        compile-check status), summary of added/modified/deleted entries and
        links, and any Tier-2 findings (`references/review_publish.md`)
    -   **And then:** **End your turn.** Wait for the user to approve pushing
        (approving Gate 1 only approves writing local files and `--dry-run`,
        never `kcmd push`).
    -   **After the push:** End the report with the line `Published context set:
        projects/<PROJECT>/locations/<LOCATION>/entryGroups/<ID>`.

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
    review and stop. A review or approval from an earlier session doesn't count:
    run the dry run and present the Gate 2 review in this conversation first.
-   **Protect other people's published changes.** kcmd doesn't detect that
    someone else published since your last pull. Before pushing to an existing
    context set, read the dry run: if it would delete entries or links you
    didn't remove, or update pages you didn't change, list them in the Gate 2
    review and ask which version to keep; never edit those pages to make the
    preview pass. If the user says a teammate published changes, or chooses the
    published version, back up your edits, pull, re-apply them, and present a
    new Gate 2 review (`references/navigate.md` §4).

### 3. Scope boundaries — decline out-of-scope actions

A context set's authored content lives **inside its own entry group**
(`type: context-set`). If the user asks for any of the following, **explicitly
decline** that part (explain why) while still helping with the in-scope
context-set work:

-   **Certifying** the context set or any entry (certification is a
    governance/steward action in the console/IAM, not performed by this
    authoring workflow).
-   **Setting access** (IAM) on the context set, e.g. "owner-only" or "readable
    by group X". This workflow doesn't change permissions, and context sets do
    not inherit read access from standard project viewer roles: say so at Gate
    1, and tell the user to grant `roles/dataplex.contentUser` in the console or
    IAM after publishing.
-   **Creating or modifying Knowledge Catalog Business Glossary terms** in
    `@dataplex` (you can *link* to existing `@dataplex` glossary terms via
    `definition` links, or create a `Knowledge Base` concept doc *inside* the
    context set, but never create or edit glossary terms).
-   **Modifying system entries directly** (`@bigquery` or any other engine's
    system entry group: no aspects, including sample queries, on source tables
    or columns; instead, create a `Table Context` doc inside the context set
    that points its `resource:` frontmatter at the system entry and carries the
    queries).
-   **Deleting or overwriting Knowledge Catalog resources you didn't create** in
    this session (other entry groups, context sets, entries, or aspects). If
    Knowledge Catalog returns a quota or permission error, stop and tell the
    user what failed; never free quota by deleting something. This holds even
    when the user offers or pre-approves deleting other context sets: don't plan
    or agree to it; tell them they can delete those themselves in the console.
-   **Publishing anywhere the user didn't name.** If the target project,
    location, or context set can't be found or written, stop and ask; never
    switch to another project or location on your own, and never write catalog
    resources through direct API or MCP calls to work around `kcmd`.
-   **Working around authentication.** If `gcloud`, `kcmd`, or an MCP call fails
    to authenticate, stop and ask the user to sign in to Google Cloud again
    (their application default credentials). Never read credential files, copy
    tokens or secrets into commands, or switch accounts yourself.
-   **Adding `schema-join` links between source tables** (describe join keys in
    the `Table Context` body text and connect related entries with `related`
    links instead).
-   **Authoring OSI-G semantic models or ontology canvases** (`.osi.yaml` files,
    Semantic Ontology Canvas views, or ontology diagrams such as Mermaid
    graphs): out of scope for OKF context sets. Don't build or offer them; say
    so in one line and deliver the context set.

**Cost-bounded reads & privacy.** Before running any exploratory query that
reads table rows (profiling, checking distinct values, or an opt-in live test of
a SQL query), run the engine's cost-free compile check first and use aggregate
or bounded queries (`references/source_engines.md`; on BigQuery `LIMIT` doesn't
reduce bytes scanned, so check the dry run's estimate) — never copy sensitive
values (PII, secrets) into the context set or the chat. Compile checks, schema
reads, and Knowledge Catalog lookups (`search_entries`, `lookup_entry`) are
always fine. A compile check (dry run) reads no rows and is not a live query:
run it even when the user asks you not to run live queries.

### 4. Local OKF-first default — never touch remote KC unless asked

-   **Local files first:** Before running any `kcmd` command, check the current
    working directory (and any path the user mentioned) for `catalog.yaml` and
    for OKF content in any folder, whatever it is named (`.md` files with
    `type:` frontmatter, an `index.md`, or a `_links.yaml`).
-   **Edit in place with no remote calls:** If local OKF `.md` files already
    exist and the user asks to edit, add, or fix entries locally (without naming
    a published context set (a `PROJECT.LOCATION.ID` or a bare context set ID)
    or asking to pull/push), **edit the local `.md` files directly** and verify
    structural integrity across `bundle/` (`references/validate.md`). Do **not**
    run `kcmd init`, `kcmd pull`, or `kcmd push`.
-   **Read-only export / pull-only (`kcmd pull` without edits):** When the user
    asks only to export or download an existing remote context set to a local
    folder without requesting changes, confirm the destination at Gate 1, run
    `kcmd init` (and `kcmd pull` only if `init` didn't already populate
    `bundle/`), **report** any Tier-1/Tier-2 defects without auto-rewriting
    pulled files (preserving a faithful export), and finish with the concise
    local-only summary
    ([references/review_publish.md](references/review_publish.md)).
-   **One copy by default (existing local OKF folder):** If the user points at
    their own OKF folder (any name) and asks to update it, import it, or publish
    it to a context set, work on that folder's files in place: each page exists
    once, in the user's own bundle. Make a separate copy only if the user
    explicitly asks for one. `kcmd` publishes from `<workspace>/bundle/`, so if
    the user's folder has another name, run `kcmd init` first (after backing up
    `<folder>` if targeting an existing remote set), remove only the newly
    scaffolded stub `bundle/` folder (never user files), and link `bundle` to
    `<folder>` (`ln -s <folder> bundle` on macOS/Linux;
    `cmd /c mklink /J bundle "<folder>"` directory junction on Windows; see
    `references/navigate.md`). Say so in the Gate 1 plan, and ask before moving
    or renaming anything.
-   **Importing an existing OKF bundle or respecting a custom directory
    structure (never force our opinionated layout, and preserve upstream
    frontmatter):** Our progressive-disclosure layout (`bundle/agents.md`,
    `bundle/assets.md`, `bundle/assets/<engine>/<container>.md`,
    `bundle/documents.md`) is the default when creating a new context set from
    scratch, **never a forced requirement**. When importing an existing OKF v0.2
    bundle (any folder the user names or that holds OKF pages, recognized by
    content rather than folder name) or when a user has their own OKF folder
    structure:
    -   In the Gate 1 plan, map each bundle file to the entry it becomes (see
        `references/kc_constructs/SUBSKILL.md` §2 for how SQL pages and
        `Attested Computation` pages map to the `queries` aspect when fitting
        our progressive-disclosure layout), list any index pages or links you
        propose adding, and **always ask the user whether they want to (1) fit
        our progressive-disclosure context-set layout (recommended) or (2) keep
        and push their OKF bundle in its current directory structure as-is**.
        Recommend option 1, but never apply it without the user's choice.
    -   **If they choose option 1, restructure the same folder (no second
        copy):** move each page to its new path, add the index pages
        (`agents.md`, `assets.md`, `documents.md`, container pages), fold SQL
        and `Attested Computation` pages into the main table page's `queries`
        aspect and delete those page files, and delete files the new layout
        replaces (such as an untyped `index.md` once `agents.md` exists). The
        Gate 1 plan lists every move, rename, and deletion, and suggests
        committing or backing up the folder first.
    -   **Preserve upstream OKF v0.2 metadata & wording losslessly:** When
        importing or editing existing OKF pages, preserve all upstream OKF v0.2
        provenance, trust, lifecycle, and extension frontmatter keys
        (`references/kc_constructs/SUBSKILL.md` §2) and body caveats / `[^id]`
        footnotes verbatim (without fabricating a
        `dataplex-types.global.certification` aspect or an ungrounded
        `stale_after` date), and enrich thin table pages append-only using
        verified schema or profile sources.
    -   If they choose to keep their directory structure, edit their files in
        place and preserve their folders, entry paths (including
        `Attested Computation` pages and non-`.md` assets), and wording as-is
        without forcing progressive-disclosure index pages. Keep repo-level
        non-concept `.md` files (`README.md`, `CONTRIBUTING.md`) outside
        `bundle/` when pushing with `kcmd`.
-   **Ask local-only or publishable when creating a new context set without a
    remote scope:** If no local OKF files exist and the user hasn't said, ask in
    your Gate 1 plan: *"Do you want (a) local files only, or (b) files linked to
    a Knowledge Catalog context set you can publish to? If (b), which project,
    location, and name?"* Both use the same `bundle/` layout (`SUBSKILL.md` §1);
    (b) also runs `kcmd init` to create `catalog.yaml` after Gate 1.

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
    and context set name?"*. When you stop before publishing, say what happens
    next in the same words, for example *"When you're ready, tell me to publish
    and I'll run the catalog publish preview again first."*, never a command for
    the user to run.
-   **Only three allowed exceptions:** (1) a concrete `gcloud dataplex
    entry-groups add-iam-policy-binding <ID> --project=<P> --location=<L>
    --member=<user|group>:<EMAIL> --role=roles/dataplex.contentUser` command
    that the user must run themselves to grant reader access, (2) telling the
    user that `kcmd` is not installed on `PATH` and asking confirmation before
    installing `@google-cloud/kcmd` (or sharing
    `npm install -g @google-cloud/kcmd`; never the unscoped `kcmd` or setup
    skills that don't install it) or before first running a workspace `./kcmd`
    launcher, or (3) answering an explicit user question about how the CLI
    works.

--------------------------------------------------------------------------------

## Workflow overview

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 0. FIND kcmd (PATH / user bin; ask before ./kcmd or install)        │
  ├─────────────────────────────────────────────────────────────────────┤
  │ 1. DISCOVER & PLAN (read-only)                  references/plan.md  │
  │    • Inspect local files FIRST; kcmd init/pull only in empty dir    │
  │    • Check lookalike tables, source conflicts, ripple effects       │
  │    • Present structured plan ──► STOP (Gate 1: wait for approval)   │
  ├─────────────────────────────────────────────────────────────────────┤
  │ 2. AUTHOR OKF DIRECTLY         references/kc_constructs/SUBSKILL.md │
  │                         references/kc_constructs/output_contract.md │
  │    • Local OKF or `kcmd init --entry-group <P.L.ID> --format okf`   │
  │    • Write/edit `.md` files & `_links.yaml` (targeted = target only)│
  ├─────────────────────────────────────────────────────────────────────┤
  │ 3. VALIDATE & REPAIR                          references/validate.md│
  │    • Check Tier-1 hierarchy/links, SQL compile checks, `--dry-run`  │
  ├─────────────────────────────────────────────────────────────────────┤
  │ 4. REVIEW & PUBLISH                     references/review_publish.md│
  │    • Local-only: summary & changed files (no push)                  │
  │    • Remote: present `--dry-run` Gate 2 summary ──► STOP            │
  │    • ONLY after separate Gate 2 approval: `kcmd push` + KC lookup   │
  └─────────────────────────────────────────────────────────────────────┘
```

### Which reference to load

1.  **Always read [references/plan.md](references/plan.md) first** when starting
    a new context set, importing an OKF bundle, or planning an edit.
2.  **Read
    [references/kc_constructs/SUBSKILL.md](references/kc_constructs/SUBSKILL.md)
    and
    [references/kc_constructs/output_contract.md](references/kc_constructs/output_contract.md)**
    before writing or editing under `bundle/` (OKF v0.2 frontmatter,
    progressive-disclosure hierarchy, link syntax, and `bundle/_links.yaml`).
3.  **Read [references/validate.md](references/validate.md)** when running
    Tier-1 / Tier-2 validation or repairing an existing bundle.
4.  **Read [references/review_publish.md](references/review_publish.md)** before
    presenting the Gate 2 review or running `kcmd push`.
5.  **Read [references/navigate.md](references/navigate.md)** when you need
    `kcmd init` / `pull` / `push` details or the workspace layout.
6.  **Read [references/source_engines.md](references/source_engines.md)**
    whenever a source table is not in BigQuery (or the set mixes engines):
    system entry group and `resource:` form, schema read, compile check,
    profiling, and `sqlDialect` per engine.

--------------------------------------------------------------------------------

## Quick command reference

Only three `kcmd` commands are used by this workflow: `init`, `pull`, and `push`
(plus `--version` / `--help`; never other subcommands or `--force`).
`--format okf` is only passed to `kcmd init` (it writes `layout: okf` to
`catalog.yaml`); `kcmd pull` and `kcmd push` read the layout from
`catalog.yaml`. Never edit `catalog.yaml` by hand.

**Step 0 — Make sure `kcmd` is available FIRST (before reading files or
planning):** Whenever the request involves creating, importing, pulling, or
publishing a remote Knowledge Catalog context set (or mentions `kcmd`), resolve
`kcmd` safely first (mention this check only if `kcmd` is missing or needs
confirmation):

1.  **Installed `kcmd` on `PATH` (default) or `$HOME/.local/bin/kcmd`:** Check
    `kcmd --version` first; if not on `PATH` (e.g., after a user-local fallback
    install), check `"$HOME/.local/bin/kcmd" --version`. Save whichever command
    succeeded and use that exact command on every `kcmd` call across all turns
    (shell `PATH` edits don't persist across turns). Always use `bq` and
    `gcloud` from `PATH` — **never** prepend `$PWD` to `PATH` or auto-run
    `./bq`, `./gcloud`, or `./kcmd` from `$PWD`.
2.  **Workspace `./kcmd` (or `./bq` / `./gcloud`) only with explicit user
    consent:** Never pick a workspace wrapper automatically, even when `kcmd`
    isn't on `PATH`, as an untrusted repo script could misuse Cloud credentials
    or spoof dry-run output. Use a workspace wrapper **only** if (a) the user
    named it in this conversation, or (b) `kcmd` is missing in Step 1, you show
    its path and first few lines (including `#!`) alongside your Gate 1 plan,
    and the user confirms running it (then invoke that path for that command
    only).

Don't crawl the filesystem for other copies. If `kcmd` is not installed in Step
1 (and no user-confirmed `./kcmd` applies):

1.  **Always prompt the user before installing — never auto-install silently.**
    Never run `npm install` before asking the user first, never write a stand-in
    `kcmd` script or alias, and never call Knowledge Catalog APIs
    (`gcloud dataplex`, REST, or MCP writes) directly to work around a missing
    CLI.
2.  **State at the very top of your reply** that the Knowledge Catalog CLI
    (`kcmd`) isn't installed and that nothing has been created or published yet.
    Offer to install the official scoped npm package `@google-cloud/kcmd` (or
    share `npm install -g @google-cloud/kcmd`), and **never** run or suggest the
    unscoped `npm install kcmd`, `npx kcmd`, `pip install kcmd`, or unrelated
    setup skills.
3.  **Prepare the Gate 1 plan in the same reply** (grounded in local files, in
    plain product language without raw CLI syntax) and ask whether to install
    `@google-cloud/kcmd` alongside approving the plan.
4.  **Only after the user confirms installing `kcmd`** (or confirms they
    installed it themselves): if they asked you to install it and
    `npm --version` succeeds, run `npm install -g @google-cloud/kcmd` and verify
    with `kcmd --version` (or `<npm prefix -g>/bin/kcmd` / `\kcmd.cmd` on
    Windows if IDE `PATH` omits global npm); if the global folder isn't
    writable, fall back to
    `npm install --prefix <user-local-dir> -g @google-cloud/kcmd`
    (`"$HOME/.local"` -> `"$HOME/.local/bin/kcmd"` on macOS/Linux;
    `"$env:USERPROFILE\.local"` in PowerShell or `"%USERPROFILE%\.local"` in
    `cmd` -> `<user-local-dir>\kcmd.cmd` on Windows) and use that exact path on
    every later `kcmd` call. Resume from the approved step without asking them
    to repeat their prompt. If the npm install fails (e.g., offline), report the
    failure in one line and stop without writing files.

```bash
# `kcmd` = Step 0 resolved path (`kcmd`, `"$HOME/.local/bin/kcmd"`, or confirmed `./kcmd`); `bq` from PATH.
# Workspace setup (ONLY after Gate 1 approval, or to inspect an existing remote set in an empty workspace)
kcmd init --entry-group <PROJECT>.<LOCATION>.<CONTEXT_SET_ID> --format okf   # writes `layout: okf` to catalog.yaml
kcmd pull                      # only if init didn't already pull the existing context set

# Validation (run after authoring/editing bundle/, before presenting Gate 2 and STOPPING)
kcmd push --dry-run
bq query --dry_run --use_legacy_sql=false <<'SQL'   # BigQuery; other engines: references/source_engines.md
<SQL>
SQL

# Publish (ONLY after separate Gate 2 approval — NEVER in the same turn as init or file edits!)
kcmd push
```
