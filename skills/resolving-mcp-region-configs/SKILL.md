---
name: resolving-mcp-region-configs
description: >-
  Mandatory Step 0 pre-flight check for regional Google Cloud MCP servers (Composer dak-composer and Dataform dak-dataform) before using regional MCP tools or falling back to gcloud/bq CLI.
  Use whenever a task involves Cloud Composer / Managed Airflow environments, DAGs, or tasks, or Dataform repositories, workspaces, compilations, or workflow invocations, and the expected mcp__*__composer__* or mcp__*__dataform__* tools are missing (ToolSearch/deferred tools) or fail on a malformed host.
  Inspects the live Data Agent Kit plugin MCP config (mcp.json, .claude-plugin/mcp.json, mcp_config.json) across Claude Code, Codex CLI, and Antigravity CLI for unreplaced $GCP_REGION, ${region}, or ${REGION} placeholders, and delegates region configuration to @skill:dak-setup instead of editing the config by hand.
  Do NOT use when the regional MCP endpoints already contain a valid region, when the regional MCP tools already work, or for non-regional services.
license: Apache-2.0
metadata:
  version: v8
  publisher: google
---

# Regional MCP Server Configuration

## Mandatory Step 0 Pre-Flight Check

> [!IMPORTANT] **Pre-Flight Check Before Using Composer / Dataform / Regional
> Services or Falling Back to CLI**: Whenever a task involves a regional Google
> Cloud service (e.g. Cloud Composer environments, DAGs, or Airflow tasks;
> Dataform repositories, workspaces, or workflow invocations): 1. **Check for
> MCP tools first**: Before executing any `gcloud composer`, `gcloud dataform`,
> or other CLI commands, check whether the expected `mcp__*__<service>__*` tools
> (e.g. `mcp__*__composer__*`, `mcp__*__dataform__*`) are registered in the
> current environment (`ToolSearch` or deferred tools). 2. **If tools are
> missing or calls fail/hang on a malformed host**: Do **NOT** immediately fall
> back to `gcloud`/`bq` CLI. Inspect the live MCP configuration files (below)
> for unreplaced `$GCP_REGION`, `${region}`, or `${REGION}` placeholders. 3.
> **If the region placeholder is already replaced with a valid region (e.g.
> `us-central1`)**: This skill does not apply — proceed normally with the task.

Some Google Cloud MCP servers are region-scoped (e.g. Composer:
`https://composer.$GCP_REGION.rep.googleapis.com/mcp`, Dataform:
`https://dataform.$GCP_REGION.rep.googleapis.com/mcp`). If the Data Agent Kit
plugin has not been configured with a region, the server fails to connect
**silently** — it registers zero tools, with no error and no placeholder string
visible anywhere to notice. Treat a missing `mcp__*__<service>__*` tool as the
trigger, not just a failed call — that's the most common way this skill gets
skipped in favor of a `gcloud`/`bq` fallback.

## When to use

-   User asks to use a regional service (e.g. "list composer environments", "why
    did my DAG fail", "list dataform repositories"), and the matching `mcp__*`
    tools aren't present — check `ToolSearch` or the deferred-tools listing
    first — or a call to one fails/hangs on a malformed host.
-   Then inspect the live config (below) for `$GCP_REGION`, `${region}`, or
    `${REGION}`. If found, run the procedure. If the region is already set, this
    skill doesn't apply — investigate normally instead.

### Supported services

Each regional MCP server in the config file is enabled through a service in
`@skill:dak-setup`:

-   **Cloud Composer / Airflow**: MCP server `dak-composer`, enabled by the
    `Apache Airflow` service.
-   **Dataform**: MCP server `dak-dataform`, enabled by the `BigQuery` service.

## Locating the live config

Inspect the Data Agent Kit plugin MCP config file that is actually loaded at
runtime (read-only — hand-editing it to replace region placeholders is
**PROHIBITED**):

-   **Claude Code**:
    `~/.claude/plugins/cache/<marketplace>/dak/<version>/.claude-plugin/mcp.json`
    (get `<marketplace>`/`<version>` from
    `~/.claude/plugins/installed_plugins.json`) or `./.claude-plugin/mcp.json`.
-   **Codex CLI**: `~/.codex/plugins/cache/<marketplace>/dak/<version>/mcp.json`
    or `./mcp.json`.
-   **Antigravity CLI**:
    `~/.gemini/config/plugins/<plugin name>/mcp_config.json` (run
    `agy plugin list` for the installed plugin name) or `./mcp_config.json`.
-   **IDE-global MCP configs (not managed by `@skill:dak-setup`)**:
    `~/.gemini/config/mcp_config.json` and
    `~/.gemini/antigravity/mcp_config.json` are managed by the Data Cloud IDE
    extension settings rather than `@skill:dak-setup`.

The plugin's saved configuration (project, region, and services) is in
`~/.config/data-agent-kit/config.json`.

## Procedure

> [!CAUTION] **Manual Placeholder Edits Are PROHIBITED**: You MUST NOT hand-edit
> `mcp.json`, `.claude-plugin/mcp.json`, or `mcp_config.json` (or instruct the
> user to manually edit them) to replace `$GCP_REGION`, `${region}`, or
> `${REGION}`. `@skill:dak-setup` owns the plugin configuration and overwrites
> manual edits every time the agent starts.

1.  You MUST NOT call the regional MCP tools yet — they will not be available
    until configuration and restart complete.
2.  You MUST inspect the live config file(s) above (read-only) for
    `dak-composer` and `dak-dataform` URLs containing `$GCP_REGION`,
    `${region}`, or `${REGION}`:
    -   **If all regional server URLs already contain a concrete region** (e.g.
        `us-central1`): stop using this skill and troubleshoot the task
        normally.
    -   **If the placeholder appears only in an IDE-global config**
        (`~/.gemini/config/mcp_config.json` or
        `~/.gemini/antigravity/mcp_config.json`): do **NOT** invoke
        `@skill:dak-setup`; tell the user to set their GCP project and region in
        the Data Cloud IDE extension settings.
    -   **If `~/.config/data-agent-kit/config.json` already has a non-empty
        `region` and includes the matching service** but the live plugin config
        still has the placeholder: the agent has not been restarted since setup
        ran. Do **NOT** run `@skill:dak-setup` again; go to step 4.
3.  **If an unreplaced placeholder is present in a live Data Agent Kit plugin
    MCP config**, you MUST immediately invoke and follow `@skill:dak-setup` to
    configure the plugin:
    -   During `@skill:dak-setup`, ensure `Apache Airflow` (for Composer /
        `dak-composer`) and/or `BigQuery` (for Dataform / `dak-dataform`) is
        included in the enabled services without dropping any previously enabled
        services (`@skill:dak-setup` replaces the service list rather than
        merging it), and verify `@skill:dak-setup` reports that the plugin has
        been configured.
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
    -   **Antigravity**: `agy --continue` (or `agy -c`)
