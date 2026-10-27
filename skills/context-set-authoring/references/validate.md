<!-- disableFinding(LINE_OVER_80) -->

# Phase 3 — Validate & Repair (`references/validate.md`)

Every context set must pass **Tier-1 structural & SQL validation** and be checked for **Tier-2
semantic coherence** before you present the Gate 2 review or run `kcmd push`.

---

## Step 3.1 — Run `kcmd push --dry-run` and BigQuery dry-run

In a `kcmd` workspace (`catalog.yaml` present), `kcmd push --dry-run` parses all OKF `.md`
files and `bundle/_links.yaml`, validates entry and link schemas, and reports problems **without
publishing any changes**:

```bash
# 1. Validate OKF bundle structure, entries, and links without publishing
kcmd push --dry-run

# 2. Dry-run each SQL query template with sample parameter values substituted
bq query --dry_run --use_legacy_sql=false "<SQL with @param replaced by sampleValues[0]>"
```

*(If authoring a standalone local OKF bundle without `catalog.yaml`, verify the Tier-1 structural
checklist in Step 3.2 directly across `bundle/` and `bundle/_links.yaml`.)*

---

## Step 3.2 — Tier-1 structural issues (auto-repair before Gate 2)

Tier-1 issues are mechanical/structural defects. **Fix all Tier-1 issues automatically** before
presenting your review to the user:

| Tier-1 Defect | How to detect it | How to fix it in `bundle/` |
| :--- | :--- | :--- |
| **Missing progressive-disclosure index** | Missing `agents.md`, `assets.md`, `documents.md`, or intermediate `assets/bigquery/<project>.md` / `<dataset>.md` | Create `agents.md`, `assets.md`, `documents.md` (`type: Knowledge Base Index`) and intermediate `assets/bigquery/<project>.md` and `assets/bigquery/<project>/<dataset>.md` with `parent` chain and Contents tables. |
| **Orphan entry** (not reachable from `agents.md` or any link) | Concept `.md` file in `bundle/` is not linked from any index Contents table or `bundle/_links.yaml` | Add a row for `<id>` in its parent index's Markdown Contents table (`[Title](/<ns>/<p>/<l>/<id>.md)`), set `parent:` in its frontmatter, and/or add an appropriate link in `bundle/_links.yaml`. |
| **Dangling `parent` or inline link** | `parent:` or `[Label](/path.md)` points to a non-existent `.md` file in `bundle/` | Fix the typo in the target ID/path so it points to an existing concept `.md` file in `bundle/`, or remove the reference if the target entry was intentionally deleted. |
| **Dangling `bundle/_links.yaml` endpoint** | `kcmd push --dry-run` errors or `source` / `target` / `entries` references a missing local entry ID | Update the `source` / `target` / `entries` in `bundle/_links.yaml` (or frontmatter `extra.links`) to the valid entry ID, or remove the stale link. |
| **Missing required Query Template fields** | `type: Query Template` file is missing `title`, distinct `description` (`intent`), ` ```sql ` block, or `parameters` for `@param` | Ensure every `type: Query Template` file has `title`, `description` (distinct from `title`), a ` ```sql ` code fence, and for every `@param` in SQL a matching `parameters:` item with `name`, `type` (`STRING`, `INT64`, `DATE`, etc.), and non-empty `sampleValues: ["..."]`. |
| **`?` positional placeholders in SQL** | SQL block uses `?` instead of `@param_name` | Replace `?` with named BigQuery `@param_name` parameters and declare each in `parameters:`. |
| **Ungrounded column meaning** | A Key Columns cell describes a column that has no description in the `@bigquery` schema and no mention in a user doc | Replace the cell with `No description in source.` (optionally followed by values observed with an aggregate query you ran). |
| **Table-context missing `resource:`** | `type: Table Context` file has no `resource:` frontmatter field | Add `resource: projects/<P>/locations/<L>/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<BP>/datasets/<D>/tables/<T>` to frontmatter. |

Treat every `kcmd push --dry-run` warning about links (for example "definition TARGET should be a
glossary-term entry") as an error to fix before Gate 2: on a first push the entry group doesn't exist
yet, so Knowledge Catalog can't validate links remotely and the dry-run may still print `RESULT: OK`.

After fixing any Tier-1 issue, re-run `kcmd push --dry-run` (and `bq query --dry_run`) until all
checks pass with zero errors.

---

## Step 3.3 — SQL query template verification

1. **Static & BigQuery dry-run check (always run):**
   For each `type: Query Template` file under `query-templates/`, substitute each `@param`'s first
   `sampleValues` entry and run a BigQuery dry-run (`bq query --dry_run --use_legacy_sql=false`, or
   the host environment's BigQuery dry-run tool) and verify that every referenced table and column
   exists in the `@bigquery` schemas.
   - If a template fails dry-run because of a column typo, bad table name, or invalid SQL syntax,
     fix the SQL in `bundle/.../query-templates/<slug>.md` and re-run the dry-run check.
2. **Live execution check (ask the user):**
   Dry-run proves the SQL compiles against the schema, **not** that the business logic returns
   sensible rows. In your Gate 2 review summary, report the dry-run pass and **ask the user** if
   they would like you to run a sampled live test: run each template once with the sample parameter
   values and its base tables under `TABLESAMPLE SYSTEM (1 PERCENT)` (never a bare `LIMIT` on a base
   table). Zero rows means inconclusive, not a failure. Skip this if the user declined it.

---

## Step 3.4 — Tier-2 semantic & ripple-effect checks (surface to user)

Tier-2 issues involve **business meaning** and must **never** be silently guessed:

1. **Ripple effects on targeted edits:**
   When the user changes a metric definition, filter, status code, or join key in one concept doc
   (e.g., changing `documents/concepts/active-customer.md` from 90 days to 60 days, or changing what
   counts as `revenue`):
   - Search `bundle/` (`grep -rn "<changed-entry-id-or-concept>" bundle/`) and inspect
     `bundle/_links.yaml` to find every other concept doc, table-context doc, and query template
     that links to or mentions that concept/column/threshold.
   - In your response, **explicitly list every downstream entry/query template** that may now be
     out of sync (with its entry ID and the specific line/SQL filter affected), and ask whether the
     user wants those updated too (or if only the target file should be changed).

2. **Conflicting business definitions across files:**
   If an existing bundle or multi-file workspace has two entries or source documents that define the
   same metric, threshold, or join rule differently:
   - Do **not** silently overwrite one with the other.
   - Keep/add a visible `> **Conflict / Open question:**` note citing both sources, and surface the
     conflict prominently in your review summary so the user can decide which definition wins.
