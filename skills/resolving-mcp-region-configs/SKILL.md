---
name: resolving-mcp-region-configs
description: >-
  Runs a mandatory Step 0 pre-flight check for regional Google Cloud MCP servers
  (Dataproc dak-spark and Composer dak-composer) before using regional MCP tools
  or falling back to CLI commands. Use whenever a task involves Dataproc
  clusters, Spark batches, jobs, or sessions, or Cloud Composer / Managed
  Airflow environments, DAGs, or tasks, and expected mcp__*__dataproc__* or
  mcp__*__composer__* tools are missing (ToolSearch/deferred tools) or fail on a
  malformed host. Inspects live Data Agent Kit plugin MCP configs (mcp.json,
  .claude-plugin/mcp.json, mcp_config.json) across Claude Code, Codex CLI, and
  Antigravity CLI for unreplaced $GCP_REGION, ${region}, or ${REGION}
  placeholders and delegates setup to @skill:dak-setup while prohibiting manual
  config edits. Do NOT use when regional MCP endpoints already contain a valid
  region, when regional MCP tools already work, or for non-regional services.
license: Apache-2.0
metadata:
  version: v6
  publisher: google
---

# Regional MCP Server Configuration

## Mandatory Step 0 Pre-Flight Check

> [!IMPORTANT] **Pre-Flight Check Before Using Dataproc / Composer / Regional
> Services or Falling Back to CLI**: Whenever a task involves a regional Google
> Cloud service (e.g. Dataproc clusters, Spark batches, jobs, or sessions; Cloud
> Composer environments, DAGs, or Airflow tasks): 1. **Check for MCP tools
> first**: Before executing any `gcloud dataproc`, `gcloud composer`, or CLI
> commands, check whether the expected `mcp__*__<service>__*` tools (e.g.
> `mcp__*__dataproc__*`, `mcp__*__composer__*`) are registered in the current
> environment (`ToolSearch` or deferred tools). 2. **If tools are missing or
> calls fail/hang on a malformed host**: Do **NOT** immediately fall back to
> `gcloud`/`bq` CLI. Inspect the live MCP configuration files (below) for
> unreplaced `$GCP_REGION`, `${region}`, or `${REGION}` placeholders. 3. **If
> the region placeholder is already replaced with a valid region (e.g.
> `us-central1`)**: This skill does not apply — proceed normally with the task.

Some Google Cloud MCP servers are region-scoped (e.g. Dataproc:
`https://dataproc-$GCP_REGION.googleapis.com/mcp`, Composer:
`https://composer.$GCP_REGION.rep.googleapis.com/mcp`). If the region
placeholder was never filled in, the server fails to connect **silently** — it
registers zero tools, with no error and no placeholder string visible anywhere
to notice. Treat a missing `mcp__*__<service>__*` tool as the trigger, not just
a failed call — that's the most common way this skill gets skipped in favor of a
`gcloud`/`bq` fallback.

## When to use

-   User asks to use a regional service (e.g. "list dataproc clusters", "list
    composer environments", "why did my DAG fail"), and the matching `mcp__*`
    tools aren't present — check `ToolSearch` or the deferred-tools listing
    first — or a call to one fails/hangs on a malformed host.
-   Then inspect the live config (below) for `$GCP_REGION`, `${region}`, or
    `${REGION}`. If found, run the procedure. If the region is already set, this
    skill doesn't apply — investigate normally instead.

### Supported services

Each regional GCP service maps to an MCP server key in the config file and an
exact service name in `@skill:dak-setup`:

-   **Dataproc / Spark**: MCP server `dak-spark` (enabled as `Apache Spark` in
    `@skill:dak-setup`).
-   **Cloud Composer / Airflow**: MCP server `dak-composer` (enabled as
    `Apache Airflow` in `@skill:dak-setup`).

## Locating the live config

Inspect the runtime Data Agent Kit plugin MCP config file (read-only —
hand-editing `mcp.json`, `.claude-plugin/mcp.json`, or `mcp_config.json` to
replace region placeholders is **PROHIBITED**):

-   **Claude Code**:
    `~/.claude/plugins/cache/<marketplace>/dak/<version>/.claude-plugin/mcp.json`
    (get `<marketplace>`/`<version>` from
    `~/.claude/plugins/installed_plugins.json`) or `./.claude-plugin/mcp.json`.
-   **Codex CLI**:
    `~/.codex/plugins/cache/<marketplace>/dak/<version>/mcp.json` or
    `./mcp.json`.
-   **Antigravity CLI**:
    `~/.gemini/config/plugins/{dak,data-agent-kit-plugin}/mcp_config.json` or
    `./mcp_config.json`.
-   **IDE-global MCP configs (not managed by `@skill:dak-setup`)**:
    `~/.gemini/config/mcp_config.json` and
    `~/.gemini/antigravity/mcp_config.json` are managed by the Data Cloud IDE
    extension settings rather than `@skill:dak-setup`.

## Procedure

> [!CAUTION] **Manual Placeholder Edits Are PROHIBITED**: You MUST NOT hand-edit
> `mcp.json`, `.claude-plugin/mcp.json`, or `mcp_config.json` (or instruct the
> user to manually edit them) to replace `$GCP_REGION`, `${region}`, or
> `${REGION}`. `@skill:dak-setup` owns plugin configuration and overwrites
> manual edits on sync.

1.  You MUST NOT call the regional MCP tools yet — they will not be available
    until configuration and restart complete.
2.  You MUST inspect the live config file(s) above (read-only) for `dak-spark`
    and `dak-composer` URLs containing `$GCP_REGION`, `${region}`, or
    `${REGION}`:
    -   **If all regional server URLs already contain a concrete region** (e.g.
        `us-central1`): stop using this skill and troubleshoot the task
        normally.
    -   **If the placeholder appears only in an IDE-global config**
        (`~/.gemini/config/mcp_config.json` or
        `~/.gemini/antigravity/mcp_config.json`): do **NOT** invoke
        `@skill:dak-setup`; tell the user to set their GCP project and region in
        the Data Cloud IDE extension settings.
3.  **If an unreplaced placeholder is present in a live Data Agent Kit plugin
    MCP config**, you MUST immediately invoke and follow `@skill:dak-setup` to
    configure the plugin:
    -   During `@skill:dak-setup`, ensure `Apache Spark` (for Dataproc /
        `dak-spark`) and/or `Apache Airflow` (for Composer / `dak-composer`) is
        included in the enabled services without dropping any previously enabled
        services, and verify `@skill:dak-setup` reports that the plugin has been
        configured.
    -   **If direct execution of `@skill:dak-setup` is blocked** (for example,
        inside Codex CLI's default read-only sandbox), instruct the user to run
        the setup skill directly:
        -   **Claude Code or Antigravity CLI**: run `/dak:dak-setup` (or
            `/dak-setup` for Antigravity Marketplace installs).
        -   **Codex CLI**: restart Codex with `codex -s danger-full-access` and
            run `$dak:dak-setup`.
4.  You MUST tell the user that an agent restart is required after setup
    completes — MCP connections load once at startup and do not hot-reload
    mid-session. Restarting does **not** lose the conversation:

    -   **Claude Code**: `claude --resume` (or `--continue`)
    -   **Codex**: `codex resume --last` (or `codex resume` for a picker)
    -   **Antigravity**: use its resume/history picker if available
