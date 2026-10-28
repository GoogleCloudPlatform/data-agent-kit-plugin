---
name: resolving-mcp-region-configs
description: >-
  Mandatory Step 0 pre-flight check for regional Google Cloud MCP servers (e.g. Dataproc, Dataform) before using MCP tools or falling back to gcloud/bq CLI.
  Use whenever interacting with Dataproc clusters, Spark batches, jobs, sessions, Dataform repositories, workspaces, workflow invocations, or regional GCP resources.
  Fixes regional MCP servers whose endpoint URL still has an unreplaced $GCP_REGION / ${REGION} placeholder across Claude Code, Codex, and Antigravity.
  Trigger: an expected mcp__*_{service}_* tool is missing entirely (not just failing), or a call to one fails/hangs on a malformed host. Check via ToolSearch/deferred-tools listing before falling back to gcloud/bq CLI. Asks the user for a region, patches the live MCP config file(s), and tells the user how to restart without losing session context.
license: Apache-2.0
metadata:
  version: v5
  publisher: google
---

# Regional MCP Server Configuration

## Mandatory Step 0 Pre-Flight Check

> [!IMPORTANT] **Pre-Flight Check Before Using Dataproc / Regional Services or
> Falling Back to CLI**: Whenever a task involves a regional Google Cloud
> service (e.g. Dataproc clusters, Spark batches, jobs, or sessions, or Dataform
> repositories and workflow invocations): 1. **Check
> for MCP tools first**: Before executing any `gcloud dataproc`, `gcloud
> dataform`, or other CLI commands,
> check whether the expected `mcp__*__<service>__*` tools (e.g.
> `mcp__*__dataproc__*` or `mcp__*__dataform__*`) are registered in the current
> environment (`ToolSearch`
> or deferred tools). 2. **If tools are missing or calls fail/hang on a
> malformed host**: Do **NOT** immediately fall back to `gcloud`/`bq` CLI.
> Inspect the live MCP configuration files (below) for unreplaced `$GCP_REGION`
> or `${REGION}` placeholders. 3. **If the region
> placeholder is already replaced with a valid region (e.g. `us-central1`)**:
> This skill does not apply — proceed normally with the task.

Some Google Cloud MCP servers are region-scoped (e.g. Dataproc:
`https://dataproc-$GCP_REGION.googleapis.com/mcp`, Dataform:
`https://dataform.$GCP_REGION.rep.googleapis.com/mcp`). If the region
placeholder was never filled in, the server fails to connect **silently** — it
registers zero tools, with no error and no placeholder string visible anywhere
to notice. Treat a missing `mcp__*__<service>__*` tool as the trigger, not just
a failed call — that's the most common way this skill gets skipped in favor of a
`gcloud`/`bq` fallback.

## When to use

-   User asks to use a regional service (e.g. "list dataproc clusters", "list
    dataform repositories"), and the matching `mcp__*` tools aren't present —
    check `ToolSearch` or the deferred-tools listing first — or a call to one
    fails/hangs on a malformed host.
-   Then inspect the live config (below) for `$GCP_REGION` or
    `${REGION}`. If found, run the procedure. If the region is
    already set, this skill doesn't apply — investigate normally instead.

### Supported services

- **Dataproc**
  - MCP server: `dak-spark`
  - Endpoint template: `https://dataproc-$GCP_REGION.googleapis.com/mcp`
- **Dataform**
  - MCP server: `dak-dataform`
  - Endpoint template: `https://dataform.$GCP_REGION.rep.googleapis.com/mcp`

The templates differ in shape: Dataproc uses a `dataproc-<region>` hostname
prefix, while Dataform uses a regional endpoint (`dataform.<region>.rep`).
Substitute only the placeholder — keep the rest of each URL exactly as-is.

## Locating the live config

The file actually loaded at runtime is under the plugin's install/cache path,
not just any workspace copy — edit that one (and the source copy, best-effort,
so the fix survives a reinstall):

-   **Claude Code**:
    `~/.claude/plugins/cache/<marketplace>/dak/<version>/.claude-plugin/mcp.json`
    (get `<marketplace>`/`<version>` from
    `~/.claude/plugins/installed_plugins.json`). Also check
    `./.claude-plugin/mcp.json` and `claude_desktop_config.json`.
-   **Codex**: `~/.codex/plugins/cache/<marketplace>/dak/<version>/mcp.json`.
-   **Antigravity**: `./mcp_config.json` or
    `~/.gemini/antigravity/mcp_config.json`.

## Procedure

1.  You MUST NOT call the regional tools yet — there likely aren't any to call.
2.  You MUST scan the config file(s) above for **every** supported regional
    server that still contains `$GCP_REGION` or `${REGION}`, not only the one
    the current task needs — they share the same placeholder.
3.  You MUST ask the user for their GCP region (e.g. `us-central1`). You MUST
    NOT guess. If more than one server is affected, ask once whether to use the
    same region for all of them or a different region per service.
4.  You MUST edit the placeholder to the chosen region in each affected
    server's URL in the config file(s) above.
5.  You MUST tell the user which servers were updated and to restart — MCP
    connections load once at startup and won't hot-reload mid-session.
    Restarting does **not** lose the conversation:

    -   **Claude Code**: `claude --resume` (or `--continue`)
    -   **Codex**: `codex resume --last` (or `codex resume` for a picker)
    -   **Antigravity**: use its resume/history picker if available
