---
name: context-set-authoring
description: |
  Build or edit a Knowledge Catalog (KC) context set by authoring Open Knowledge Format (OKF v0.2)
  markdown files directly under `bundle/` (links in `bundle/_links.yaml`). Use for any task that
  creates, imports, pulls, edits, repairs or publishes a context set, or that involves `kcmd`:
  e.g. "create a context set from our revenue tables and the finance SOP", start one from an
  existing OKF bundle, "add a query template for Q". Plans first, validates with
  `kcmd push --dry-run` (and BigQuery dry-run for SQL templates), and pushes only after the user
  approves; it ends its turn after the plan and after the review, even when told to work
  autonomously. If the request also asks for OSI-G semantic models, new glossary terms or
  certification, still use it: it builds the context set and declines those parts. Not for
  read-only questions about data or catalog metadata.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

<!-- disableFinding(LINE_OVER_80) -->
# Context Set Authoring (Direct OKF)

Author or update a Knowledge Catalog **context set**: an entry group (`type: context-set`) of
table-context documents, knowledge-base documents, query templates, an `agents` index, and the
links between them, represented on disk as an **Open Knowledge Format (OKF v0.2)** bundle under
`bundle/` (`catalog.yaml` at the workspace root).

Instead of calling per-entry CLI subcommands to author each entry one by one, you **write and edit
the OKF `.md` files and `bundle/_links.yaml` directly**, validate with `kcmd push --dry-run`
(plus `bq query --dry_run` for query templates), and publish with `kcmd push` after user approval.

---

## Non-negotiable guardrails

### 1. Grounding — never invent business knowledge

Every fact you write into a document, table description, column note, join, or query template must
come from:

- a source the user provided in this session (files on disk, text in the prompt, an OKF bundle),
- an existing context set pulled into `bundle/` with `kcmd pull`, or an entry or schema fetched
  from Knowledge Catalog / BigQuery, or
- a live BigQuery schema/query result.

**No unverified specifics.** Each of the following needs a source — a schema or column description,
a user-provided document, or an aggregate / `TABLESAMPLE` query you actually ran in this session
(cite which) — or it stays out of the pages and goes under **Open questions** in the plan:

- **Column meanings.** If a column has no description in the schema or the user's docs, don't gloss
  it from its name; write "No description in source." (type only) or ask.
- **Value sets, thresholds, and cutoffs** (e.g. `status` ∈ {active, closed}, `duration_minutes > 0`,
  "over 24 hours").
- **Prescriptive rules and edge-case interpretations** ("should filter / exclude / cap / sum …",
  "zero durations are aborted checkouts", "depots should be excluded"). Don't add general
  "data-quality best practice" that no source states, and don't explain why values are NULL, zero,
  or unusual ("indicates…", "reflects…") unless a source says so.
- **Gaps in a source's categorization.** When a document's rule doesn't cover every value (e.g. it
  defines "Walk Up" and "…Membership…" but not other subscriber types), list the uncovered case as
  an **Open question** in the plan; don't add an `ELSE 'Other'` bucket or a default unless the source
  defines one.
- **Joins and references** to any table that isn't one of the context set's inputs, and join keys
  between inputs that no description, document, or query you ran establishes.
- **Filters and parameters inside query templates.** A template only applies filters, thresholds
  (`HAVING`, minimum counts), and parameters that the user asked for or a source states; don't add
  defensive `WHERE`/`HAVING` clauses or extra knobs.

If the prompt gives **no sources at all** (no table IDs, no context-set ID, no local files, no
domain details) or asks you to invent schemas and KPIs ("make up standard definitions", "don't ask
me questions"): **stop immediately**. Write nothing, do not run `kcmd init`, and ask the user for:

1. Which BigQuery tables or datasets to cover (or a topic to search for in Knowledge Catalog).
2. Any source documents, SOPs, metric definitions, or SQL queries they have.
3. The target `PROJECT.LOCATION.CONTEXT_SET_ID` (and display name).

When sources **disagree** (e.g., two docs define a metric differently, or a doc contradicts the
physical schema): **never silently pick one**. Surface both versions with exact citations in the
plan and in a `> **Open question:**` callout in the concept doc, and ask the user which is
authoritative.

### 2. Two hard gates — stop and wait for user approval

| Gate | Before you... | You must present... | And then... |
| :--- | :--- | :--- | :--- |
| **Gate 1 — Plan approval** | Run `kcmd init`, create/modify any file under `bundle/` or `catalog.yaml`, or touch existing files | The structured authoring plan (`references/plan.md`) | **End your turn.** Wait for the user to approve. |
| **Gate 2 — Push approval** | Run `kcmd push` (without `--dry-run`) | Validation results (`kcmd push --dry-run`, template dry-run status), summary of added/modified/deleted entries and links, and any Tier-2 findings (`references/review_publish.md`) | **End your turn.** Wait for the user to approve pushing. |

**"Don't wait for approval" / "just build and push it" prompts do NOT override Gate 1 or Gate 2.**
Even when the user says *"go ahead and build it without waiting"* or *"push it right away"*:

- If no `bundle/` exists yet (new context set): present the **Gate 1 Plan** and **end your turn**
  without writing any files.
- If a workspace with `bundle/` already exists on disk and the user asks to edit/repair and push
  immediately: you may apply the local edits to `bundle/` and run `kcmd push --dry-run`,
  then present the **Gate 2 Review** and **end your turn** without running `kcmd push`.

### 3. Scope boundaries — decline out-of-scope actions

A context set only writes entries and entry links **inside its own entry group** (`type:
context-set`). If the user asks for any of the following, **explicitly decline** that part (explain
why) while still helping with the in-scope context-set work:

- **Certifying** the context set or any entry (certification is a governance/steward action in the
  console/IAM, not performed by this authoring workflow).
- **Creating or modifying Dataplex Business Glossary terms** in `@dataplex` (you can *link* to
  existing `@dataplex` glossary terms via `definition` links, or create a `Knowledge Base` concept
  doc *inside* the context set, but never write to `@dataplex`).
- **Modifying `@bigquery` system entries directly** (no aspects on source tables or columns; instead,
  create a `Table Context` doc inside the context set that points its `resource:` frontmatter at the
  `@bigquery` entry).
- **Adding `schema-join` links between source tables** (describe join keys in the `Table Context`
  body text and connect related entries with `related` links instead).
- **Authoring OSI-G semantic models** (out of scope for OKF context sets).

**Sampled reads only.** Any BigQuery query that reads table rows (profiling, checking values, or
the opt-in live test of a query template) must sample its base tables with
`TABLESAMPLE SYSTEM (1 PERCENT)` or return aggregates only. Never run a bare `SELECT ... LIMIT` on a
base table, and never copy sensitive values (PII, secrets) into the context set or the chat.
`bq query --dry_run` and schema reads (`bq show --schema`) are always fine.

### 4. Local OKF-first default — never touch remote KC unless asked

- **Local files first:** Before running any `kcmd` command, check the current working directory (and
  any path the user mentioned) for existing `.md` files, `bundle/`, `okf_bundle/`, or
  `catalog.yaml`.
- **Edit in place with no remote calls:** If local OKF `.md` files already exist and the user asks
  to edit, add, or fix entries locally (without mentioning a remote `PROJECT.LOCATION.ID` or asking
  to pull/push), **edit the local `.md` files directly** and verify structural integrity across
  `bundle/` (`references/validate.md`). Do **not** run `kcmd init`, `kcmd pull`, or `kcmd push`.
- **Importing an existing OKF bundle (e.g. `okf_bundle/` or a folder the user names) into a context
  set, including a named remote one:** in the Gate 1 plan, map each bundle file to the entry it
  becomes, list what you'll add on top (index pages, `related` links), and **ask whether to convert
  the bundle to KC's progressive-disclosure layout or keep its folders as-is**. Keep the bundle's own
  wording; only append sections the plan names.
- **Ask which layout when creating a new context set without a remote scope:** If no local OKF files
  exist and the user has not specified whether they want a standalone local OKF bundle or a
  remote-backed `kcmd` workspace, **ask in your Gate 1 plan**:
  1. **Progressive-disclosure OKF bundle** (`agents.md`, `assets.md`, `documents.md`,
     `assets/bigquery/<p>/<d>/<table>.md`, `documents/<slug>.md`, `query-templates/<slug>.md`,
     `_links.yaml` — default for local authoring and GDA consumption), or
  2. **kcmd-synced workspace** (`catalog.yaml` + `bundle/<context-set-id>/<project>/<location>/...`
     for syncing with a remote Knowledge Catalog entry group).

---

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
  │    • Check Tier-1 OKF hierarchy, frontmatter, and `_links.yaml`     │
  │    • Dry-run SQL query templates via `bq query --dry_run`           │
  │    • Run `kcmd push --dry-run` to validate entries and links        │
  └──────────────────────────────────┬──────────────────────────────────┘
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 4. REVIEW & PUBLISH                     references/review_publish.md│
  │    • Local-only mode: present validation summary & changed files    │
  │    • Remote mode: present `kcmd push --dry-run` summary ──► STOP    │
  │    • Only after explicit push approval: run `kcmd push`             │
  └─────────────────────────────────────────────────────────────────────┘
```

### Which reference to load

1. **Always read `references/plan.md` first** when starting a new context set, importing an OKF
   bundle, or planning an edit.
2. **Read `references/kc_constructs/SUBSKILL.md` and `references/kc_constructs/output_contract.md`**
   before writing or editing any file under `bundle/` (exact OKF v0.2 frontmatter, progressive
   disclosure hierarchy, `[Title](/path.md)` link syntax, and `bundle/_links.yaml` format).
3. **Read `references/validate.md`** when running Tier-1 / Tier-2 validation or repairing an
   existing bundle.
4. **Read `references/review_publish.md`** before presenting the Gate 2 review or running
   `kcmd push`.
5. **Read `references/navigate.md`** when you need `kcmd init` / `pull` / `push` details or the
   workspace layout.

---

## Quick command reference

Only three `kcmd` commands are used by this workflow: `init`, `pull`, and `push`. `--format okf` is
only passed to `kcmd init` (it writes `layout: okf` to `catalog.yaml`); `kcmd pull` and `kcmd push`
read the layout from `catalog.yaml`. Never edit
`catalog.yaml` by hand.

```bash
# Workspace setup (ONLY after Gate 1 approval, or to inspect an existing remote context set)
kcmd init --entry-group <PROJECT>.<LOCATION>.<CONTEXT_SET_ID> --format okf   # writes `layout: okf` to catalog.yaml
kcmd pull                      # pull the remote context set into bundle/

# Validation (run after authoring/editing bundle/, before Gate 2)
kcmd push --dry-run
bq query --dry_run --use_legacy_sql=false "<SQL with sample parameter values>"

# Publish (ONLY after Gate 2 approval)
kcmd push
```
