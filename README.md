# Data Agent Kit

Data Agent Kit is a **free** plugin that connects your coding agent to 15+
Google Data Cloud services, including BigQuery, Cloud Storage, Spanner,
AlloyDB, Managed Service for Apache Spark, and Knowledge Catalog.

Spend your time on insights, not boilerplate. Describe a data task in plain
language, and watch your agent handle the heavy lifting for you: writing SQL
queries, building notebooks, generating pipeline code, setting up ML workflows,
and more.

> [!IMPORTANT]
> This repository contains the Data Agent Kit **plugin** for coding agents:
> Antigravity CLI, Claude Code, Codex CLI, and any
> [Agent Plugins](https://github.com/agentplugins/agent-plugins-spec)–compatible
> client.
>
> If you use an IDE, install the Data Agent Kit **extension** instead. If you
> use **Visual Studio Code**, install Data Agent Kit from the
> [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=GoogleCloudTools.datacloud).
> If you use another VS Code-based IDE, such as **Antigravity IDE** or **Cursor**,
> search for "Data Agent Kit" in your IDE's Extensions panel and install it from
> there.

## Prerequisites

- A supported coding agent: Antigravity CLI, Claude Code, Codex CLI, or another Agent Plugins–compatible client.

- **Node.js** (latest LTS recommended).

- **Google Cloud CLI (`gcloud`)**, installed and authenticated:
  1. [Install the gcloud CLI](https://cloud.google.com/sdk/docs/install).
  2. Log in with your Google Cloud account:

     ```bash
     gcloud auth login
     ```

  3. Log in to
     [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc):

     ```bash
     gcloud auth application-default login
     ```

## Installation

<!-- {x-release-please-start-version} -->

<details>
<summary><b>Antigravity CLI</b></summary>

```bash
agy plugin install https://github.com/GoogleCloudPlatform/data-agent-kit-plugin
```

</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude plugin install data-agent-kit-starter-pack@claude-plugins-official
```

</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
codex plugin marketplace add GoogleCloudPlatform/data-agent-kit-plugin
codex plugin add dak@dak-marketplace
```

</details>

<details>
<summary><b>Any Agent Plugins–compatible client</b></summary>

Point your client's plugin install command at this repository:

```text
https://github.com/GoogleCloudPlatform/data-agent-kit-plugin
```

See your agent's documentation for the exact command.

</details>

## Configuration

<details>
<summary><b>Antigravity CLI and Claude Code</b></summary>

Provide any prompt to your agent and it will walk you through configuring
Data Agent Kit.

Alternatively, you can manually invoke the Data Agent Kit setup skill:

```text
/dak:dak-setup
```

Restart your agent when prompted to complete the setup.
</details>

<details>
<summary><b>Codex CLI</b></summary>
Codex runs with a sandbox by default that prevents Data Agent Kit from
configuring itself. Temporarily disable the sandbox to allow setup:

```bash
codex -s danger-full-access
```

Invoke the Data Agent Kit setup skill:

```text
$dak:dak-setup
```

Restart your agent when prompted to complete the setup. You can now use Codex
normally with the sandbox enabled.
</details>

<!-- {x-release-please-end} -->
<!-- github-release-force: 0.11.0 -->

## Features and Common Uses

- **Data engineering:** Build pipelines that turn source data into
  analysis-ready tables, with quality checks along the way. Develop
  transformations with dbt or Dataform, schedule workflows with Managed Service
  for Apache Airflow, and debug failed runs by tracing execution logs and code.
- **Data science:** Develop experiments in Jupyter notebooks on local Python or
  remote Managed Service for Apache Spark kernels. Prepare features from
  BigQuery, train models with BigQuery ML, and schedule batch inference.
- **Data analysis:** Explore data across BigQuery, AlloyDB, and Cloud SQL. Find
  datasets with Knowledge Catalog, guided by data quality metrics and lineage,
  then build visualizations or reusable data models.

## Example Prompts

- "Create a PySpark notebook to train a distributed Random Forest model on the
BigQuery table `my_transactions`
- "Find datasets about customer orders in Knowledge Catalog and show their
  lineage"
- "Create an Airflow DAG that runs the dedup notebook, the dbt pipeline, and
  model training every Monday morning.
- "My last Dataflow job failed. Find the root cause in the logs and propose a
  fix"

## Troubleshooting

If you see `could not find default credentials` or other auth errors, ensure you
are logged into gcloud.

Exit your agent, run `gcloud auth login` followed by
`gcloud auth application-default login`, then restart your agent.

## Security

Your agent can run tools and commands on your behalf. Apply the **principle of
least privilege** to every CLI, MCP server, and resource it can access:

- Use
  [service account impersonation](https://cloud.google.com/docs/authentication/use-service-account-impersonation)
  instead of end-user credentials.
- Grant the service account only the
  [roles it needs](https://cloud.google.com/iam/docs/roles-overview).
- Use
  [Principal Access Boundary policies](https://cloud.google.com/iam/docs/principal-access-boundary-policies#use-case-one-project)
  with a condition in the policy binding to restrict your agent's service
  accounts to intended projects.

Learn how to
[mitigate prompt injection risks](https://docs.cloud.google.com/data-cloud-extension/vs-code/prompt-injection-risk)
with Google Cloud MCP.

## Usage Statistics

Data Agent Kit collects usage statistics (such as when included skills and MCP
tools are used) to improve reliability and performance. No user code, file
contents, or application data values are collected.

To opt out, either set `DO_NOT_TRACK=1` in your environment:

```bash
export DO_NOT_TRACK=1
```

Or create or update `~/.data_agent_kit/config.json`:

```json
{
  "enableTelemetry": false
}
```

## Feedback

We want your feedback! Please [open an issue](issues/new) to report bugs,
file feature requests, or ask questions.

## Resources

- [Data Agent Kit homepage](https://cloud.google.com/products/data-agent-kit)
- [Data Agent Kit documentation](https://docs.cloud.google.com/data-agent-kit)
