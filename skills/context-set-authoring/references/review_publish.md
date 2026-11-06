<!-- disableFinding(LINE_OVER_80) -->

# Phase 4 — Review & Publish (`references/review_publish.md`)

Publishing writes your local `bundle/` changes to the remote Knowledge Catalog
entry group via `kcmd push`. **Never run `kcmd push` (without `--dry-run`)
without first presenting the Gate 2 Review and receiving the user's explicit
confirmation in the next turn.**

--------------------------------------------------------------------------------

## Local-Only Authoring & Read-Only Export Closing Summary (no remote push)

When the workflow is **local-only** (standalone OKF v0.2 bundle or local
in-place edits with no remote push requested) or a **read-only export**
(`kcmd init` + `kcmd pull` to download a remote context set locally without
edits):

1.  Do **not** run `kcmd push` (and on a read-only export, do not auto-rewrite
    pulled files).
2.  Present a concise **3-line local closing summary** in plain product
    language:
    -   **Files ready under `bundle/`** (entry and `EntryLink` counts written,
        updated, or downloaded, plus `catalog.yaml` if initialized).
    -   **Validation / findings status** (Tier-1 structural & SQL compile-check
        status, or any reported defects/conflicts found in a pulled export).
    -   **Next step:** confirm that nothing was published to Knowledge Catalog
        and the local `bundle/` is ready for git check-in or further edits.

--------------------------------------------------------------------------------

## Step 4.1 — Prepare the pre-push validation state (remote mode)

Before presenting the Gate 2 Review, run:

```bash
# 1. Check what a push would do, without publishing
kcmd push --dry-run

# 2. Verify each sample SQL query compiles via its engine's compile check
bq query --dry_run --use_legacy_sql=false "<SQL>"   # BigQuery; other engines: references/source_engines.md
```

Verify that:

-   `kcmd push --dry-run` reports `0` errors, and its planned changes match what
    you intended.
-   Your own Tier-1 check (`references/validate.md` Step 3.2) over the whole
    bundle finds no orphans, dangling `extra.resource.parent` / path-field /
    inline links, dangling or cross-location `bundle/_links.yaml` endpoints, or
    typed `bundle/index.md` collisions alongside `bundle/agents.md`. The dry run
    doesn't check all of these.
-   All sample SQL queries pass their engine's compile check (`0` SQL/schema
    errors), or you report why it couldn't run.
-   For targeted edits, only the requested entry (and any explicitly requested
    links) were modified or added under `bundle/` — no unrelated entries were
    touched or reformatted.

--------------------------------------------------------------------------------

## Step 4.2 — Present the Gate 2 Review Summary and STOP

Present a concise, scannable review summary in **strict plain product language**
(SKILL.md §5 — always refer to the product as **Knowledge Catalog**, never
**Dataplex**, and **never** include literal command strings or flags like
`kcmd push --dry-run`, `kcmd push`, `--dry-run`, or engine commands such as
`bq query --dry_run` in your Gate 2 reply; refer to them as *"catalog publish
preview"*, *"bundle validation"*, and *"<engine> compile check"*, e.g.
*"BigQuery compile check"*) containing:

1.  **Validation Status:**
    -   **Bundle check:** passed or failed, with the entry and link counts you
        counted and what you checked (structure, links, hierarchy), plus the
        publish preview's result (0 errors, and which entries it actually
        checked if it checked only the changed ones).
    -   Sample queries: compile-check status for each query (naming its engine),
        plus an offer to run a bounded live execution test if the user hasn't
        answered that yet.
2.  **Change Summary (files under `bundle/`):**
    -   **Added entries:** list each new entry ID, its OKF `type`, `title`, and
        file path under `bundle/`.
    -   **Modified entries:** list each modified entry ID and a 1-line summary
        of what changed.
    -   **Deleted entries:** list any deleted entry IDs.
    -   **SQL queries:** list the queries added, changed, or kept in each table
        page's `queries` aspect, with one line each on what it computes.
    -   **Entry links:** list added/modified/deleted links (`type` —
        `reference`, `related` including index-to-child and concept/table links,
        or `definition` — and endpoints), plus any cross-location external links
        omitted on a regional context set.
    -   **Other writes** the publish preview lists outside the context set's own
        entry group, if any.
3.  **Tier-2 Findings / Open Questions / Ripple Effects:**
    -   Any unresolved source conflicts (with both definitions cited).
    -   Any downstream ripple effects on other documents or sample queries
        discovered when inspecting cross-references in `bundle/`.
    -   Any out-of-scope items that were declined (e.g., certification, access
        settings, glossary term writes).
4.  **Note on local files:** publishing may rewrite local pages (see
    `references/navigate.md` §3); suggest committing or backing up the workspace
    first.

End with a direct question, for example:

> *"Shall I publish these changes to Knowledge Catalog now?"*

**Stop your turn here.** Do **not** run `kcmd push` (without `--dry-run`) in the
same turn as authoring or reviewing.

--------------------------------------------------------------------------------

## Step 4.3 — Publish after user approval

Push only on an unambiguous approval of this review ("publish", "push it", "go
ahead and publish"). Approving the plan, or a reply that asks to see something
("show me the diff", "stage it"), is not push approval: re-present the review
and stop. Once the user approves:

1.  Run it in the foreground and wait for it to finish (never in the background,
    and never end the turn while it is still running):

    ```bash
    kcmd push
    ```

    Wait for its final `RESULT:` line before running any other command (don't
    inspect or edit the workspace while a push is still in flight). If the push
    fails or its output reveals issues, any change to `bundle/` needs a new
    `kcmd push --dry-run`, a new Gate 2 review, and a new approval before you
    push again. If it stops because the published context set changed since your
    pull, follow `references/navigate.md` §4; never use `--force`.
2.  **Verify the published context set in Knowledge Catalog:** After `kcmd push`
    succeeds, verify that the published context set and its entries are live in
    Knowledge Catalog by looking up the context set's root entry (`lookup_entry`
    / `search_entries` via the Knowledge Catalog MCP on
    `projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CONTEXT_SET_ID>/entries/agents`,
    or `gcloud dataplex entries list --project=<PROJECT> --location=<LOCATION>
    --entry-group=<CONTEXT_SET_ID>`). Certification stays out of scope.
3.  Report the result (published or the error, in plain words), the published
    context set
    (`projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CONTEXT_SET_ID>`), a
    summary of pushed entries and links, the Knowledge Catalog post-push
    verification status, any other writes the output lists, and which local
    files the push rewrote (for example links moved from `_links.yaml` into page
    frontmatter).
