<!-- disableFinding(LINE_OVER_80) -->

# Working with `kcmd` (`references/navigate.md`)

This workflow uses exactly three `kcmd` commands: `init`, `pull`, and `push`. All authoring happens by
editing OKF v0.2 files under `bundle/` directly.

---

## 1. Workspace files on disk

After `kcmd init --entry-group <P>.<L>.<ID> --format okf` (and `kcmd pull` for an existing context set), the
directory contains:

```
<workspace>/
├── catalog.yaml               # Workspace manifest (scope + layout). Do not edit by hand.
├── .kcmd/                     # Internal base snapshot & config (DO NOT edit .kcmd/ directly)
└── bundle/                    # Authoritative OKF v0.2 markdown bundle (EDIT FILES HERE)
    ├── index.md               # Auto-generated root directory index
    ├── _links.yaml            # Authorable entry links (definition, related)
    └── <id>/<project>/<location>/
        ├── agents.md
        ├── assets.md
        ├── documents.md
        ├── assets/bigquery/<bq_project>/<dataset>/<table>.md
        ├── documents/<slug>.md
        └── query-templates/<slug>.md
```

`catalog.yaml` looks like:

```yaml
scope: entryGroup.<PROJECT>.<LOCATION>.<CONTEXT_SET_ID>
layout: okf
```

- `kcmd init --format okf` writes `layout: okf`; `kcmd pull` and `kcmd push` read `layout:` from
  `catalog.yaml` and take no `--format` flag.
- **Never edit `catalog.yaml` or `.kcmd/` by hand.** Re-running `kcmd init` for the same scope keeps
  existing keys and comments in `catalog.yaml`.

---

## 2. Commands

| Command | Purpose | When to run |
| :--- | :--- | :--- |
| `kcmd init --entry-group <P>.<L>.<ID> --format okf` | Create (or update) `catalog.yaml` for the context set with `layout: okf` | **Only after Gate 1 approval**, or before `kcmd pull` when inspecting an existing remote context set |
| `kcmd pull` | Pull remote entries & links into `bundle/` | Safe during discovery when inspecting an existing remote context set |
| `kcmd push --dry-run` | Validate all entries and links parsed from `bundle/` without publishing | After authoring/editing, before Gate 2 |
| `kcmd push` | Publish added/modified/removed entries and links to Knowledge Catalog | **Only after Gate 2 approval** |
