<!-- disableFinding(LINE_OVER_80) -->

# Working with `kcmd` (`references/navigate.md`)

This workflow uses exactly three `kcmd` commands: `init`, `pull`, and `push`.
All authoring happens by editing OKF v0.2 files under `bundle/` directly.

--------------------------------------------------------------------------------

## 1. Workspace files on disk

After `kcmd init --entry-group <P>.<L>.<ID> --format okf` (and `kcmd pull` if
`init` didn't already populate `bundle/` for an existing context set), the
directory contains:

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
-   `kcmd` maps `bundle/<entry-id>.md` directly to
    `projects/<PROJECT>/locations/<LOCATION>/entryGroups/<CONTEXT_SET_ID>/entries/<entry-id>`.
    Never nest files under `bundle/<id>/<project>/<location>/` when authoring
    new bundles (though if a pre-pulled workspace on disk already uses an older
    directory layout, keep its existing paths intact on targeted edits).
-   Keep repo-level non-concept `.md` files (`README.md`, `CONTRIBUTING.md`)
    outside `bundle/` so `kcmd` scans only bundle files (in OKF v0.2 every `.md`
    file in the bundle other than `index.md` / `log.md` is a concept and needs
    `type:`, §3.1).
-   **Never edit `catalog.yaml` (or a `.kcmd/` folder, if present) by hand.**
    Re-running `kcmd init` for the same scope keeps existing keys and comments
    in `catalog.yaml`.
-   **Publishing an existing local OKF folder in place (one copy by default):**
    when the user's own OKF folder (whatever its name) is what they want to
    publish, its pages become the workspace's bundle; keep editing those files.
    `kcmd` reads pages from `<workspace>/bundle/`, so for a folder `<folder>`
    with another name (after Gate 1):
    1.  Keep `<folder>` unlinked while running
        `kcmd init --entry-group <P>.<L>.<ID> --format okf` so `kcmd init`'s
        scaffolded `bundle/` stub doesn't create a nested `bundle/<basename>`
        link and any auto-pull on an existing remote context set lands in the
        temporary `bundle/` first (reconcile or merge pulled pages if needed
        without overwriting local `<folder>` files prior to Gate 2).
    2.  Remove only the newly scaffolded stub `bundle/` directory (never user
        files), then create a directory link `bundle -> <folder>` next to
        `catalog.yaml` (`ln -s <folder> bundle` on macOS/Linux;
        `mklink /J bundle <folder>` directory junction on Windows, which works
        without elevated privileges). `kcmd` reads and writes through the link.
        Converting to the progressive-disclosure layout restructures `<folder>`
        in place (moves, new index pages, deletions; `SKILL.md` §4). Make a
        separate copy only if the user explicitly asks.

--------------------------------------------------------------------------------

## 2. Commands

-   `kcmd init --entry-group <P>.<L>.<ID> --format okf`
    -   **Purpose:** Create (or update) `catalog.yaml` for the context set with
        `layout: okf` (if `bundle/` is still empty afterwards for an existing
        context set, run `kcmd pull`)
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
-   **The entry group is created as a context set on the first push.**
    `kcmd init` and the dry run don't create anything in Knowledge Catalog. When
    the context set doesn't exist yet, the first `kcmd push` creates the entry
    group with type `context-set`, which can't change afterwards. Never create
    the entry group yourself (for example with
    `gcloud dataplex entry-groups create`); let the first push create it.
-   **Read every note in the output.** If `kcmd pull` or `kcmd init` reports
    lookups that failed (for example a quota error), the local links may be
    incomplete: tell the user, and don't publish link deletions that come from
    that pull. A real push may also update the overview on the context set's own
    catalog search entry (in the system `@dataplex` entry group) so search shows
    the root page's summary; the dry run doesn't list it. Say so in every Gate 2
    review, and report any other write `kcmd push` lists outside the context
    set's own entry group in the post-push report.
-   **Scale & quota limits (surface to the user on large context sets):**
    `kcmd push` reconciles entries and entry links (`bundle/_links.yaml`)
    against the remote entry group (check the `kcmd push --dry-run` summary when
    removing a local `.md` file, since some `kcmd` versions only create or
    update entries present in `bundle/` without deleting removed remote
    entries). When authoring or publishing a large context set (100+ entries or
    200+ links), let the user know that Knowledge Catalog enforces regional
    per-user per-minute read/write quotas on Entry Links (~400 read RPM and ~200
    write RPM on the standard tier, 150–500 RPM across tiers), and keep
    `bundle/_links.yaml` focused on high-signal links (`reference`,
    `definition`, and primary `related` edges) rather than dense all-pairs
    links.

## 4. When kcmd fails or refuses

Report the error in plain words and stop; never edit `.kcmd/` or `catalog.yaml`,
and never retry with `--force`.

-   **Reads return 403 right after the first push of a new context set:** access
    to a new context set can take a minute or two to take effect. Wait a minute
    and retry the pull or lookup, for up to about three minutes, before
    reporting a failure.
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
-   **Someone else published since your pull** (the user mentions a teammate's
    changes, the dry run would delete or update entries you didn't touch and the
    user wants the published version, or a future kcmd stops the push for it):
    kcmd 0.2.3 doesn't detect this itself, so don't push. Tell the user which
    entries differ, then, with their approval:
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
