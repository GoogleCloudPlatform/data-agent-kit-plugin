<!-- disableFinding(LINE_OVER_80) -->

# Phase 4 — Review & Publish (`references/review_publish.md`)

Publishing writes your local `bundle/` changes to the remote Knowledge Catalog entry group via
`kcmd push`. **Never run `kcmd push` (without `--dry-run`) without first presenting the Gate 2
Review and receiving the user's explicit confirmation in the next turn.**

---

## Step 4.1 — Prepare the pre-push validation state

Before presenting the Gate 2 Review, run:

```bash
# 1. Validate the OKF bundle, entries, and links without publishing
kcmd push --dry-run

# 2. Verify SQL query templates compile via BigQuery dry-run
bq query --dry_run --use_legacy_sql=false "<SQL with sample parameter values>"
```

Verify that:

- `kcmd push --dry-run` succeeds with `0` errors (no orphans, no dangling links).
- All query templates pass BigQuery dry-run (`0` SQL/schema errors).
- For targeted edits (`t10`), only the requested entry (and any explicitly requested links) were
  modified or added under `bundle/` — no unrelated entries were touched or reformatted.

---

## Step 4.2 — Present the Gate 2 Review Summary and STOP

Present a concise, scannable review summary containing:

1. **Validation Status:**
   - `kcmd push --dry-run`: PASS (entry count, link count, progressive-disclosure hierarchy
     verified).
   - Query templates: BigQuery dry-run status for each query template, plus an offer to run a sampled
     live test (`TABLESAMPLE SYSTEM (1 PERCENT)`) if the user hasn't answered that yet.
2. **Change Summary (files under `bundle/`):**
   - **Added entries:** list each new entry ID, its OKF `type`, `title`, and file path under
     `bundle/`.
   - **Modified entries:** list each modified entry ID and a 1-line summary of what changed.
   - **Deleted entries:** list any deleted entry IDs.
   - **Entry links (`bundle/_links.yaml`):** list added/modified/deleted links (`type`, `source` →
     `target`).
3. **Tier-2 Findings / Open Questions / Ripple Effects:**
   - Any unresolved source conflicts (with both definitions cited).
   - Any downstream ripple effects on other documents or query templates discovered when inspecting
     cross-references in `bundle/`.
   - Any out-of-scope items that were declined (e.g., certification, `@dataplex` glossary writes).

End with a direct question, for example:
> *"Should I run `kcmd push` now to publish this context set to Knowledge Catalog?"*

**Stop your turn here.** Do **not** run `kcmd push` (without `--dry-run`) in the same turn as
authoring or reviewing.

---

## Step 4.3 — Publish after user approval

Once the user replies approving the push:

1. Run it in the foreground and wait for it to finish (never in the background, and never end the
   turn while it is still running):
   ```bash
   kcmd push
   ```
   Wait for its final `RESULT:` line before running any other command (don't inspect or edit the
   workspace while a push is still in flight). If the push fails or its output reveals issues, any
   change to `bundle/` needs a new `kcmd push --dry-run`, a new Gate 2 review, and a new approval
   before you push again.
2. Report the result (`RESULT: OK` or the error), the published context set resource name
   (`projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CONTEXT_SET_ID>`) and summary of pushed
   entries and links.
