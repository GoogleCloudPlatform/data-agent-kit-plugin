<!-- disableFinding(LINE_OVER_80) -->

# Phase 1 — Discover & Plan (`references/plan.md`)

During Phase 1 you are in **read-only mode**. Do **not** run `kcmd init` (except to inspect an
existing remote context set, Rule C), do **not** create or modify any file under `bundle/`, and do
**not** run `kcmd push`.

---

## Step 1.0 — Inspect the local workspace FIRST (before any `kcmd` call)

Before running any `kcmd` command, inspect the current working directory (and any directory named in
the prompt):

- If `.md` files already exist locally (in `./`, `bundle/`, or `okf_bundle/`):
  - **Local edit / repair request** (user asks to update a definition, add a template, fix orphans,
    or edit the local context set without asking to pull from or push to a remote KC entry group):
    read only the relevant local `.md` files and `_links.yaml`. **Do not run `kcmd init`, `kcmd
    pull`, or `kcmd push`.**
  - **Targeted edit (`t10` / `t20`):** Read the target concept file first. If changing a definition,
    column filter, or threshold, search `bundle/` (e.g., `grep -rn "<entry-id-or-concept>" bundle/`)
    to find every entry, query template, and `_links.yaml` item that references it so you can list
    **ripple effects** before or alongside the edit.
- If no local OKF files exist yet:
  - Check whether the user gave a remote context-set scope (`PROJECT.LOCATION.CONTEXT_SET_ID`) or
    asked for a local standalone OKF bundle.
  - **If the user did NOT specify which layout they want**, include an explicit **Layout Choice**
    question in your Gate 1 plan:
    1. **Standalone Progressive-Disclosure OKF Bundle** (`bundle/agents.md`, `bundle/assets.md`,
       `bundle/documents.md`, `bundle/assets/bigquery/<p>/<d>/<table>.md`,
       `bundle/documents/<slug>.md`, `bundle/query-templates/<slug>.md`, `bundle/_links.yaml`) —
       local markdown files ready for GDA consumption or git check-in without requiring a remote
       Knowledge Catalog entry group.
    2. **kcmd-Synced Workspace** (`catalog.yaml` +
       `bundle/<context-set-id>/<project>/<location>/...`) — bound to a remote Knowledge Catalog
       entry group (`PROJECT.LOCATION.CONTEXT_SET_ID`) for `kcmd pull` / `kcmd push`.

---

## Step 1.1 — Check grounding and inputs

Inspect what the user gave you:

1. **Zero context provided?**
   If the user asks to create a context set from scratch (e.g., *"Create a customer-360 context set"*
   or *"Set up a finance context set with standard SaaS metrics, don't ask questions"*) without
   naming any tables, datasets, local files, or existing context-set IDs:
   - **Stop immediately.** Do not search randomly and do not invent tables or definitions.
   - Ask the user for:
     1. The BigQuery project/dataset/tables (or a search term + project to look up in KC).
     2. Any local documents, SOPs, glossary notes, or example SQL queries.
     3. The target context set scope (`PROJECT.LOCATION.CONTEXT_SET_ID`) or whether they want a
        local-only OKF bundle.
   - **End your turn.**

2. **Local files or existing `okf_bundle/` / `bundle/`?**
   Read all local `.md`, `.sql`, `.yaml`, or `.txt` files the user referenced (or that sit in the
   working directory).
   - If the workspace already has an `okf_bundle/` (seed bundle, or any folder the user points at)
     that needs to be imported into a context set, read every file in it so your plan accounts for
     every concept, table, and query template. The plan must map each bundle file to its entry,
     list what you'll add on top, and ask whether to **convert to KC's layout** or **keep the
     bundle's folders as-is** (even when the remote `PROJECT.LOCATION.CONTEXT_SET_ID` is given).

---

## Step 1.2 — Discover entries in Knowledge Catalog (only when remote assets/scope are involved)

Follow these discovery rules strictly:

### Rule A — Exact BigQuery table IDs given (`project.dataset.table`)
If the user provides **exact** `project.dataset.table` IDs and says those are the tables to use:

- Fetch each table's `@bigquery` entry (or BigQuery schema) directly by its resource name:
  ```
  projects/<PROJECT>/locations/<LOCATION>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BQ_PROJECT>/datasets/<DATASET>/tables/<TABLE>
  ```
  *(Note: BigQuery dataset location such as `US` or `EU` is used in the `@bigquery` entry path:
  `projects/<BQ_PROJECT>/locations/US/entryGroups/@bigquery/entries/...`)*
- **Do NOT run broad catalog searches for tables when exact table IDs were already given.**
- Only search Knowledge Catalog if you also need to check for existing `@dataplex` glossary terms
  (`type=projects/dataplex-types/locations/global/entryTypes/glossary-term ...`).

### Rule B — Loose table names or topic description given
If the user names tables loosely (e.g., *"the orders and customers tables in project X"*, or *"our
revenue tables"*):

- Search Knowledge Catalog scoped to the target `<PROJECT>` to find candidate tables and glossary
  terms.
- Inspect every candidate table's full schema, row/column descriptions, and timestamps/deprecation
  notes.
- **Lookalike / duplicate table check:** Whenever discovery returns multiple similar tables (e.g.,
  `orders` vs `orders_v2` vs `orders_legacy` vs `stg_orders`), **flag all lookalike candidates** in
  your plan, compare their schemas/descriptions, state which one you recommend (and why), and ask
  the user to confirm before authoring.

### Rule C — Existing remote context set
If the user references an existing remote context set (`PROJECT.LOCATION.CONTEXT_SET_ID`) and
`catalog.yaml` is not yet initialized locally, you may run `kcmd init --entry-group
<PROJECT>.<LOCATION>.<CONTEXT_SET_ID> --format okf` followed by `kcmd pull` (or read the existing `bundle/` if
already pulled) to read the current state. This only writes the local workspace; it does not change
Knowledge Catalog.

---

## Step 1.3 — Cross-check sources for conflicts & gaps

Before drafting the plan, compare all sources (user prompt, local SOP/markdown files, `@bigquery`
schemas, `@dataplex` glossary terms, and existing `bundle/` entries):

1. **Source conflicts:** Does Document A define a metric/filter/threshold differently from Document
   B, the user prompt, or a SQL query? (e.g., `status = 'COMPLETED'` vs `status IN ('COMPLETED', 'SHIPPED')`,
   or 30-day vs 90-day churn window, or gross vs net revenue).
   - **Never pick a winner.** List both definitions with their exact source citations (`file:line`
     or entry ID) in a **Conflicts & Open Questions** section of the plan.
2. **Schema mismatches:** Does a source doc or SQL query reference a column or table that does not
   exist in the `@bigquery` schema? Flag it explicitly.
3. **Out-of-scope requests:** Did the user ask to certify entries, create new `@dataplex` glossary
   terms, modify `@bigquery` entries directly, or build an OSI-G model? Note clearly in the plan
   which items are declined and what in-scope alternative you will build (e.g., linking to existing
   `@dataplex` terms or authoring a `Knowledge Base` concept doc inside the context set).

---

## Step 1.4 — Present the Gate 1 Plan and STOP

Keep the plan concise: counts and **one line per item** (table, page, template, link). Do **not**
paste full schemas, full SQL, or whole pages into the plan; list query templates by their question
plus a one-line description of what they compute.

Format your response clearly with these sections:

1. **Target Context Set & Layout:**
   - If remote scope given: `PROJECT.LOCATION.CONTEXT_SET_ID`, display name, description, and OKF
     bundle root (`bundle/<context-set-id>/<project>/<location>/`). If the user gave a project and ID
     but no location, use the BigQuery datasets' location (e.g., `us`), not `global`, and say so.
   - If no remote scope given: propose the target `bundle/` structure and **ask the user whether
     they want (a) a standalone local progressive-disclosure OKF bundle or (b) a remote-synced
     `kcmd` workspace (`catalog.yaml` + `PROJECT.LOCATION.CONTEXT_SET_ID`)**.
2. **Discovered Assets & Lookalikes:**
   - Tables inspected (`@bigquery` resource path + key columns).
   - Any lookalike/duplicate tables found and which one is recommended.
   - Any existing `@dataplex` glossary terms found to link via `definition`.
3. **Planned OKF Files (`bundle/`):**
   - **Top-level router & category indexes:** `agents.md`, `assets.md`, `documents.md` (and
     project/dataset hierarchy indexes `assets/bigquery/<project>.md`,
     `assets/bigquery/<project>/<dataset>.md`).
   - **Table Context docs:** `assets/bigquery/<project>/<dataset>/<table>.md` (with `resource:`
     pointing to the `@bigquery` entry, grain, column semantics, and caveats).
   - **Knowledge Base concept docs:** `documents/<slug>.md` or `documents/concepts/<slug>.md`
     (business rules, metric definitions, policies — each cited to its source).
   - **Query Templates:** `query-templates/<slug>.md` (natural-language question `title`, `intent`,
     `parameters`, and `sql` block).
   - **Entry Links (`bundle/_links.yaml`):** `related` links (each table-context doc to its
     `@bigquery` source entry; templates to the tables/docs they use; concept docs to the pages they
     govern; tables that are commonly joined), and `definition` links only from a page to an
     **existing** `@dataplex` glossary term. Join keys and cardinality go in the table-context body text, never in a
     `schema-join` link.
4. **Conflicts, Declined Out-of-Scope Items & Open Questions:**
   - Any contradictions between sources (both sides cited).
   - Any out-of-scope requests declined (certification, `@dataplex` glossary writes, OSI-G).
   - Whether the user wants an opt-in sampled live test of each query template (one run with its
     base tables under `TABLESAMPLE SYSTEM (1 PERCENT)`) in addition to `bq query --dry_run`.

End with a clear prompt asking the user to approve the plan (and answer any open questions) before
you write any files. **Stop your turn here.**
