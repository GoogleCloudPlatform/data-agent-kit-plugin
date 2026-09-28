---
name: enforcing-resource-attribution
description: |
  Enforces resource attribution for CLI commands. Use this skill whenever you are running `bq` or `gcloud` commands via `run_command`. It ensures mandatory labeling for supported `bq` operations while avoiding invalid flags on read-only commands.
license: Apache-2.0
metadata:
  version: v6
  publisher: google
---

# Resource Attribution Enforcement

To track resources created or manipulated by AI agents, you **MUST** ensure
that standard CLI commands are tagged with appropriate attribution labels
under relevant conditions.

## Applicability

You should apply these attribution labels **ONLY** under the following
conditions:
1.  **DAK Tooling**: You are executing Python scripts, running MCP tools, or
    following workflows provided by the **Data Agent Kit**.
2.  **Domain Relevance**: You are operating on BigQuery datasets, GCS
    buckets, or Analytics infrastructure (including **Spark**,
    **Dataproc**, or Serverless Spark) intended for data preparation,
    deduplication, or analysis.

### 🚫 When to Omit
Do **NOT** apply these labels if you are running generic administrative
commands or working on infrastructure completely unrelated to Data Cloud /
Analytics (e.g., managing Compute Engines for web apps, setting up standard
IAM policies, etc.).

Do **NOT** apply `--label` flags to commands that do not accept labels, as the `--label` flag is unsupported by these specific `bq` subcommands. These include:
- `bq show`
- `bq ls`
- `bq version`
- `bq rm`
- `bq cancel`
- `bq head`

## BigQuery CLI (`bq`)

You **MUST** apply `--label key:value` **ONLY** to subcommands that accept job or resource labels (`bq query`, `bq load`, `bq extract`, `bq mk`, `bq update`, and `bq cp`).

-   **Flag Form**: `--label key:value`
-   **Mandatory Label**: `datacloud:<ide>`
-   **Deduction Rule**: Substitute `<ide>` with your actual environment/client
    (e.g., `vscode`, `antigravity`, `codex`, `cursor`, `cloud-shell`,
    `workstation`, `gemini-cli`, `claude`).
    *   Use `cloud-shell` for GCP Cloud Shell.
    *   Use `workstation` for GCP Cloud Workstations.
    If you cannot determine your environment, use `ai-agent`. Note that
    BigQuery labels **cannot** contain dots or spaces.

### Examples

#### Query Example
**Incorrect**:
```bash
bq query --use_legacy_sql=false "SELECT 1"
```

**Correct** (assuming you are running in VS Code):
```bash
bq query --use_legacy_sql=false --label datacloud:vscode "SELECT 1"
```

#### Copy Example
**Incorrect**:
```bash
bq cp dataset1.table1 dataset2.table1_copy
```

**Correct** (assuming you are running in Antigravity):
```bash
bq cp --label datacloud:antigravity dataset1.table1 dataset2.table1_copy
```

---

## Google Cloud SDK (`gcloud`)

Whenever you execute any `gcloud` command via `run_command`, you **MUST**
prepend the command with the `CLOUDSDK_METRICS_ENVIRONMENT` environment
variable to ensure proper resource attribution.

-   **Environment Variable**: prepend commands using the append form. It keeps
    any attribution another tool or skill already set on the same variable and
    adds the DAK tag after it, so both values reach the metrics pipeline:

    ```bash
    CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.<ide>"
    ```

-   **Deduction Rule**: Substitute `<ide>` with your actual environment/client
    (e.g., `vscode`, `antigravity`, `codex`, `cursor`, `cloud-shell`,
    `workstation`, `gemini-cli`, `claude`).
    *   Use `cloud-shell` for GCP Cloud Shell.
    *   Use `workstation` for GCP Cloud Workstations.
    If you cannot determine your environment, use `ai-agent`. Note that
    values must use dots (e.g., `datacloud.vscode`), not colons.

### Examples

**Incorrect**:
```bash
gcloud compute disks create my-disk --size=10GB
```

**Correct** (assuming you are running in VS Code):
```bash
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.vscode" gcloud compute disks create my-disk --size=10GB
```

> [!IMPORTANT]
>
> This applies to **ALL** `gcloud` commands, whether they are read-only
> (`gcloud ... list`) or mutations (`gcloud ... create`).

