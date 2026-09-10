# Data Agent Kit Starter Pack

> [!NOTE]
> This extension is currently in beta (pre-v1.0), and may see breaking changes until the first stable release (v1.0).

This plugin provides a specialized suite of skills and MCP tools for data engineers and database practitioners working on Google Cloud. It acts as an expert assistant, allowing you to use natural language prompts in your preferred coding agent to architect complex data pipelines, transform data with dbt, write Spark and BigQuery SQL notebooks, create and troubleshoot Dataflow pipelines, and orchestrate end-to-end workflows across the Google Cloud data ecosystem (BigQuery, Spanner, BigLake, Dataproc, etc.).

> [!IMPORTANT]
> **We Want Your Feedback!**
> Please share your thoughts with us by opening an issue on GitHub. Your input is invaluable and helps us improve the project for everyone.

## Contents

- [Why Use the Data Agent Kit Starter Pack?](#why-use-the-data-agent-kit-starter-pack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Security Reminder: Agent Environment Hardening](#security-reminder-agent-environment-hardening)

## Why Use the Data Agent Kit Starter Pack?

* **Seamless Workflow:** Bring Google Cloud data engineering expertise directly into your terminal or IDE via Gemini CLI, Claude Code, or Codex.
* **End-to-End Data Pipelines:** Effortlessly generate code that reads raw data from Cloud Storage, processes it with Spark, Dataflow or BigQuery, transforms it through medallion architectures (bronze, silver, gold) using dbt, and exports it to serving layers like Spanner.
* **Ecosystem Integration:** Work across boundaries—generate BigLake Iceberg catalog tables, train BigQuery ML models (XGBoost, KMEANS), and create interactive Streamlit dashboards or LookML models, all from natural language.
* **Workflow Orchestration:** Automatically create and schedule orchestration pipelines that tie your notebooks and dbt models together into robust, scheduled jobs.

## Prerequisites

Ensure you have the following installed:
* **Node.js and npm** (Latest version recommended)
* **Google Cloud SDK (gcloud CLI):** [Install and initialize](https://cloud.google.com/sdk/docs/install) the gcloud CLI and ensure [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc) are configured.
* One of the following coding agents:
    * Antigravity CLI
    * [Gemini CLI](https://github.com/google-gemini/gemini-cli) (v0.6.0+)
    * [Claude Code](https://code.claude.com/docs)
    * Codex CLI
* **(Optional) IDE Extension:** [Google Cloud Data Agent Kit](https://docs.cloud.google.com/data-cloud-extension/vs-code/install).

## Getting Started

<!-- {x-release-please-start-version} -->

### Installation

Choose the installation method for your preferred coding agent. Run the commands in terminal

<details>
<summary><b>Antigravity CLI</b></summary>

Install the plugin directly from GitHub:
```bash
agy plugin install https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack
```
</details>

<details>
<summary><b>Gemini CLI and Gemini Code Assist</b></summary>

Install the extension directly from GitHub:
```bash
gemini extensions install https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack --ref 0.10.1
```
</details>

<details>
<summary><b>Claude Code</b></summary>

Run the `claude` command to start the agent, then follow these steps:

1. **Install the plugin:**
```bash
/plugin install data-agent-kit-starter-pack@claude-plugins-official
```
</details>

<details>
<summary><b>Codex</b></summary>

#### Option 1: Marketplace Installation (Recommended)

Codex utilizes a marketplace system for plugins. Install the Data Agent Kit Starter Pack marketplace to access the plugin:

```bash
# Step 1. Add marketplace
codex plugin marketplace add https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack

# Step 2. Add the plugin
codex plugin add dak@data-agent-kit-starter-pack-marketplace
```

#### Option 2: Script Installation (Alternative)

1. **Run the installation script in your terminal:**

**macOS / Linux:**
```bash
CODEX_TAG="0.10.1"; curl -sSL https://raw.githubusercontent.com/gemini-cli-extensions/data-agent-kit-starter-pack/$CODEX_TAG/codex-install.sh | bash -s -- $CODEX_TAG
```

**Windows:**
```powershell
$env:CODEX_TAG="0.10.1"; irm "https://raw.githubusercontent.com/gemini-cli-extensions/data-agent-kit-starter-pack/$env:CODEX_TAG/codex-install.ps1" | iex
```

2. **Install the plugin in Codex:**

Start the Codex agent (`codex`), then run:
```bash
/plugins
```
Use the interactive options to install the plugin with the name `Data Agent Kit Starter Pack`.
</details>

<details>
<summary><b>Any Agent Plugins–compatible client</b></summary>

This repository is a valid [Agent Plugins](https://github.com/agentplugins/agent-plugins-spec) (v1) plugin. Any [compatible client](https://agent-plugins.org/compatible-clients) (VS Code, Cursor, GitHub Copilot, Codex, Kiro, …) can install it directly using its own built-in plugin command — skills and MCP servers included — by pointing at this repository:
```
https://github.com/gemini-cli-extensions/data-agent-kit-starter-pack
```
See your agent's documentation for its exact install command.
</details>

### Configuration

This extension brings a suite of specialized **Skills** and **MCP toolboxes**. While skills are ready to use upon installation, you **must** configure the MCP toolboxes and authenticate with Google Cloud for them to start successfully.

> [!NOTE]
> If you use Gemini CLI, Claude Code, or Codex in your IDE (e.g., via VS Code extensions), they share the same underlying configuration and MCP servers as the CLI agents.

#### 1. Authenticate with Google Cloud
The MCP toolboxes require an active authenticated session to interact with your resources. Run the following commands in your terminal:
```bash
gcloud auth login
gcloud auth application-default login
```

#### 2. Update Agent Configuration
You must configure the MCP toolboxes in your agent's configuration files for them to start successfully. After updating, you must restart the agent.

To verify your configuration:
* Run the `/mcp` command to check the status of available MCP servers.
* Ask your agent "What skills are available?" to view the list of active skills.

<details>
<summary><b>Antigravity CLI</b></summary>

Edit the configuration file:
`~/.gemini/antigravity-cli/plugins/data-agent-kit-starter-pack/mcp_config.json`
</details>

<details>
<summary><b>Gemini CLI and Gemini Code Assist</b></summary>

Edit the configuration file:
`~/.gemini/extensions/data-agent-kit-starter-pack/gemini-extension.json`
</details>

<details>
<summary><b>Claude Code</b></summary>

Edit the configuration file:
`~/.claude/plugins/cache/claude-plugins-official/data-agent-kit-starter-pack/0.10.1/.claude-mcp.json`
</details>

<details>
<summary><b>Codex</b></summary>

1. Edit the configuration file:
`~/.codex/plugins/cache/data-agent-kit-starter-pack-marketplace/dak/0.10.1/.mcp.json`

2. Restart Codex.
</details>

<!-- {x-release-please-end} -->
<!-- github-release-force: 0.10.1 -->

## Usage Examples

Interact with your coding agent using natural language prompts to perform complex data engineering tasks:

* **Data Ingestion & Processing:**
  * "Create a Spark notebook that reads raw fraud transaction data from gs://fin-clearing-west1/raw, deduplicates records, and writes hourly partitions to a BigLake Iceberg catalog table."
  * "Create a BigQuery SQL notebook that drops an existing table and writes deduplicated transaction data from GCS."
* **Data Transformation (dbt):**
  * "Create a dbt pipeline to transform bronze_transactions into silver and gold tables, standardizing timestamps and joining with identity tables."
* **Machine Learning & Serving:**
  * "Train a robust XGBoost model using BigQuery ML on the gold_transactions table to identify potential fraud."
  * "Generate an inference notebook to batch-process new partitions and write flagged transactions into a Cloud Spanner table for high-availability access."
* **Analysis & Visualization:**
  * "Generate a complete View for my BigQuery tables to show YoY revenue growth, then generate a LookML model and an interactive Streamlit dashboard prototype."
* **Orchestration:**
  * "Create an orchestration pipeline that first runs the dedup notebook, then the dbt pipeline, and finally the model training and inference notebooks. Schedule it to run every Monday morning."


## Troubleshooting

Use `gemini --debug` to enable debugging.

Common issues:

* **Plugin Not Found:** Ensure you have restarted your agent (e.g., Gemini CLI or Codex) after installation.
* **Authentication Errors:** Many GCP skills require an active authenticated session. Ensure you have run `gcloud auth login` and `gcloud auth application-default login` on your machine. See [Set up Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) for more information.
* **"failed to find default credentials: google: could not find default credentials."**: Ensure Application Default Credentials (ADC) are available in your environment.
* **MCP Connection Issues:** Update the MCP server configurations such as project, region etc. needed by MCP toolboxes in order to connect successfully to them.
* **"✖ Error during discovery for server: MCP error -32000: Connection closed"**: The connection could not be established. Ensure your configuration is correctly set in the agent's configuration file.
* **"✖ MCP ERROR: Error: spawn .../toolbox ENOENT"**: The Toolbox binary did not download correctly. Ensure you are using Gemini CLI v0.6.0+.
* **"cannot execute binary file"**: The Toolbox binary did not download correctly. Ensure the correct binary for your OS/Architecture has been downloaded.

## Security Reminder: Agent Environment Hardening

Your agent can execute tools and commands on your behalf. Protect your Google
Cloud resources by enforcing **The Principle of Least Privilege** across all
CLIs, MCP servers and other resources available to your agents.

*   **Service Accounts:** Use
    [service accounts](https://cloud.google.com/docs/authentication/use-service-account-impersonation)
    instead of end user credentials to access Google Cloud resources.
*   **Limited Permissions:** Assign roles with
    [limited permissions](https://cloud.google.com/iam/docs/roles-overview)
    to the service account that you're using for authentication.
*   **Principal Access Boundaries:** Prevent unwanted cross-org agent access by
    using
    [Principal Access Boundary policies](https://cloud.google.com/iam/docs/principal-access-boundary-policies#use-case-one-project)
    to scope your agent to projects you intend it to access.
*   [Include a condition in the policy binding](https://cloud.google.com/iam/docs/principal-access-boundary-policies#use-case-one-project)
    to ensure that the policy only applies to the service accounts that you
    intend to restrict.

You can read more
[here](https://docs.cloud.google.com/data-cloud-extension/vs-code/prompt-injection-risk)
on how to mitigate prompt injection attacks with Google Cloud MCP.

## Usage Statistics

The Data Agent Kit collects usage statistics (such as when the skills and
MCP tools included in this kit are used) to improve the reliability and
performance of the tool. No user code, file contents, or application data
values are collected.

### Opting Out

You can opt out of usage statistics collection at any time using one of the
following methods:

#### 1. Environment Variable
Set the `DO_NOT_TRACK` environment variable to `1` in your environment:
```bash
export DO_NOT_TRACK=1
```

#### 2. Configuration File
Create or update your configuration file at `~/.data_agent_kit/config.json` to
disable collection:
```json
{
  "enableTelemetry": false
}
```
