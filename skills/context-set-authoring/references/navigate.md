<!-- disableFinding(LINE_OVER_80) -->

# Working with `kcmd` (`references/navigate.md`)

This workflow uses exactly three `kcmd` commands: `init`, `pull`, and `push`.
All authoring happens by editing OKF v0.2 files under `bundle/` directly.

--------------------------------------------------------------------------------

## 1. Workspace files on disk

After `kcmd init --entry-group <P>.<L>.<ID> --format okf` (and `kcmd pull` for
an existing context set), the directory contains:

```
<workspace>/
├── catalog.yaml               # Workspace manifest (scope + layout: okf). Do not edit by hand.
└── bundle/                    # Portable OKF v0.2 markdown bundle (EDIT FILES HERE; no <id>/<p>/<l>/ prefix)
    ├── index.md               # Optional untyped OKF v0.2 index (frontmatter at most okf_version: "0.2"; keep untyped or remove stub; NEVER add type: alongside agents.md)
    ├── _links.yaml            # EntryLinks (reference -> source system entry, e.g. @bigquery, related -> index/child + concept/table + joined tables, definition -> @dataplex)
    ├── agents.md              # Entry ID: agents (type: Context Set or Knowledge Base Root)
    ├── assets.md              # Entry ID: assets (extra.resource.parent: agents)
    ├── documents.md           # Entry ID: documents (extra.resource.parent: agents)
    ├── assets/<engine>/<container>.md          # e.g. assets/bigquery/<bq_project>/<dataset>.md
    ├── assets/<engine>/<container>/<table>.md  # e.g. assets/spanner/<project>/<instance>/<database>/<table>.md
    └── documents/<slug>.md
```

`catalog.yaml` looks like:

```yaml
scope: entryGroup.<PROJECT>.<LOCATION>.<CONTEXT_SET_ID>
layout: okf
```

-   `kcmd init --format okf` writes `layout: okf`; `kcmd pull` and `kcmd push`
    read `layout:` from `catalog.yaml` and take no `--format` flag.
-   `kcmd` (`OkfLayout`) maps `bundle/<entry-id>.md` directly to
    `projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CONTEXT_SET_ID>/entries/<entry-id>`.
    Never nest files under `bundle/<id>/<project>/<location>/` when authoring
    new bundles (though if a pre-pulled workspace on disk already uses an older
    directory layout, keep its existing paths intact on targeted edits).
-   Keep repo-level non-concept `.md` files (`README.md`, `CONTRIBUTING.md`)
    outside `bundle/` so `kcmd` scans only bundle files (in OKF v0.2 every `.md`
    file in the bundle other than `index.md` / `log.md` is a concept and needs
    `type:`, §3.1).
-   **Never edit `catalog.yaml` (or `.kcmd/` if present in older setups) by
    hand.** Re-running `kcmd init` for the same scope keeps existing keys and
    comments in `catalog.yaml`.
-   **Publishing an existing local OKF folder in place:** when the user's own
    OKF folder (whatever its name) is what they want to publish, run `kcmd init`
    for the context set from that folder (after Gate 1) so its pages are the
    workspace's bundle, and keep editing those files. Don't copy the pages into
    a separate `bundle/` unless the user asks. If `kcmd init` reports it can't
    use the folder as-is (for example it expects pages under `bundle/`), stop
    and ask before moving files.

--------------------------------------------------------------------------------

## 2. Commands

-   `kcmd init --entry-group <P>.<L>.<ID> --format okf`
    -   **Purpose:** Create (or update) `catalog.yaml` for the context set with
        `layout: okf`; for an existing context set some kcmd versions also pull
        it
    -   **When to run:** **Only after Gate 1 approval**, or before `kcmd pull`
        when inspecting an existing remote context set
-   `kcmd pull`
    -   **Purpose:** Pull remote entries & links into `bundle/`
    -   **When to run:** During discovery (or read-only export), when
        `kcmd init` did not already pull
-   `kcmd push --dry-run`
    -   **Purpose:** Parse the bundle and check what would be published (see the
        limits below) without publishing
    -   **When to run:** After authoring/editing, before Gate 2
-   `kcmd push`
    -   **Purpose:** Publish added/modified/removed entries and links to
        Knowledge Catalog
    -   **When to run:** **Only after Gate 2 approval**

Don't use any other `kcmd` subcommand (for example `export`, `entry`, `link`, or
`status`), even if `kcmd --help` lists it, and never pass a `--force` flag
yourself: the forced forms of `pull` and `push` each discard someone's work.

--------------------------------------------------------------------------------

## 3. What kcmd does and doesn't check or change

-   **The dry run is not a full validation.** Depending on the kcmd version, it
    checks only the entries and links that changed since the last pull or push
    (an unchanged workspace reports "nothing to push"), checks a brand-new
    context set only locally, skips some link checks, and never checks for
    orphan pages, inline links to missing pages, or whether someone else changed
    the published context set since your pull. Your Tier-1 checklist
    (`references/validate.md` Step 3.2) covers the whole bundle; report the two
    separately.
-   **Links and local file rendering across `kcmd` versions.** `kcmd` reads and
    writes `bundle/_links.yaml` (and also reads frontmatter `links` /
    `extra.links` / `x-kcmd.links`); some versions may re-render pages, scaffold
    `index.md`, or move links into page frontmatter (`extra.links`) and delete
    `_links.yaml` on push/pull. Always check both `_links.yaml` and page
    frontmatter when reading an existing bundle, use the target's title as link
    text when you can, and suggest the user commit or back up the workspace
    before publishing.
-   **Read every note in the output.** If `kcmd pull` or `kcmd init` reports
    lookups that failed (for example a quota error), the local links may be
    incomplete: tell the user, and don't publish link deletions that come from
    that pull. If `kcmd push` lists a write outside the context set's own entry
    group (for example an overview on its catalog search entry), include it in
    the Gate 2 review or the post-push report.
-   **Batching, scale & quota limits (surface to the user on large context
    sets):** `kcmd push` automatically splits entry creates, updates, and
    deletes into `:batchChangeMetadata` chunks of up to **250 entry changes per
    request** (`BATCH_MAX_CHANGES = 250`). Entry links (`bundle/_links.yaml`)
    are reconciled after entry batches via bounded-concurrency
    `:lookupEntryLinks` calls (max 10 links per page) and per-link create,
    delete, or update calls (with automatic retry on HTTP `429`). When authoring
    or publishing a large context set (100+ entries or 200+ links), inform the
    user of Knowledge Catalog's regional Entry Links per-minute read/write
    quotas (~300–600 RPM depending on project quota tier) and keep
    `bundle/_links.yaml` focused on high-signal links (`reference`,
    `definition`, and primary `related` edges) rather than dense all-pairs
    links.

## 4. When kcmd fails or refuses

Report the error in plain words and stop; never edit `.kcmd/` or `catalog.yaml`,
and never retry with `--force`.

-   **`init` or `pull` fails on some entries** (for example an entry ID kcmd
    can't store as a file): nothing usable was downloaded; tell the user which
    entries blocked it.
-   **kcmd treats published entries as new** (for example the dry run plans to
    create entries that already exist, reports "already exists" / "exists
    remotely but is new locally", or `pull` refuses over unpushed changes you
    didn't make). If local snapshot state is missing or stale (e.g. in an older
    `kcmd` setup after a fresh git clone), don't push or force anything: ask the
    user to let you run `kcmd init` for the same context set in a new empty
    directory, then carry the clone's intended edits over to the freshly pulled
    pages and continue from Gate 2 there.
-   **`push` stops because the published context set changed since your pull:**
    nothing was published. Tell the user which entries changed remotely, then,
    with their approval:
    1.  Copy every page you changed or added to a backup outside `bundle/`.
    2.  Undo your changes in `bundle/` (restore those pages to their state after
        the last pull, from version control if the workspace has it, otherwise
        by reversing your own edits; remove pages you added), so kcmd sees no
        local changes.
    3.  Run `kcmd pull` (no `--force`). It brings in the other editor's changes.
    4.  Re-apply your changes from the backup on top of the pulled pages,
        keeping the other editor's changes; ask the user if both changed the
        same text.
    5.  Run a new dry run and present a new Gate 2 review that names both sets
        of changes.
