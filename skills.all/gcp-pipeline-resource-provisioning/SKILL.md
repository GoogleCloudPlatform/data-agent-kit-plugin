---
name: gcp-pipeline-resource-provisioning
description: |
  Automates declarative resource creation and provisioning for data pipelines, supporting BigQuery, Dataform, Dataproc, BigQuery Data Transfer Service (DTS), and other resources. It manages environment-specific configurations (dev, staging, prod) through a deployment.yaml file.
  Use when:
  - Modifying or creating deployment.yaml for deployment settings.
  - Resolving environment-specific variables (e.g., Project IDs, Regions) for deployment.
  - Provisioning supported infrastructure like BigQuery datasets/tables, Dataform resources, or DTS resources via deployment.yaml.
  Do not use when:
  - Resources already exist.
  - Managing resources not supported by `gcloud beta orchestration-pipelines resource-types list`.
  - Managing general cloud infrastructure (VMs, networks, Kubernetes, IAM policies), which are better suited for Terraform.
  - Infrastructure spans multiple cloud providers (AWS, Azure, etc.).
  - Already uses Terraform for the target resources.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

## How to use this skill

Create or update existing `deployment.yaml` file and deploy resources. All
configuration files MUST be maintained together in the repository root.

### Mandatory labels

> [!IMPORTANT]
>
> Whenever you generate resource definitions in `deployment.yaml`, you **MUST**
> directly populate the `datacloud` label under `definition.labels` for every
> resource to track the source of creation. Determine the value based on your
> current IDE environment:
>
> -   For Antigravity, set `datacloud: "antigravity"`
> -   For VS Code, set `datacloud: "vscode"`
> -   For any other environment, set `datacloud: "other"`
>
> Do not use a variable substitution for this label; hardcode the appropriate
> string value directly into each resource definition (e.g., replacing
> `__REQUIRED_LABEL__` placeholders).
>
> **Special rule for BigQuery DTS Ingestion:** Whenever you generate a
> `bigquerydatatransfer.transferConfig` in `deployment.yaml`, you **MUST** also
> explicitly define its target destination `bigquery.dataset` in the same file
> and apply the `datacloud` label to it. You must do this even if the dataset
> already exists, to ensure the destination dataset's labels are patched and
> updated.

### Step 1: Supported Resource Types

The framework supports deploying various GCP resources. To see the comprehensive
list of supported resource types, run the following command:

```
gcloud beta orchestration-pipelines resource-types list
```

Refer to: references/gcp-pipeline-resource-provisioning_spec.md to understand
the template for `deployment.yaml`.

### Step 2: Discover Environment Parameters

Before generating configurations, discover the actual values for the target
project, region, environment, and commit SHA.

> [!TIP]
>
> If `deployment.yaml` already exists in the repository root, prioritize
> extracting `project` and `region` from the target environment configuration
> (e.g., `dev`).

1.  **Project ID**:

    ```bash
    gcloud config get project
    ```

2.  **Project Number**:

    ```bash
    gcloud projects describe $(gcloud config get project) --format="value(projectNumber)"
    ```

3.  **Region**:

    ```bash
    gcloud config get-value compute/region
    ```

4.  **Commit SHA**:

    ```bash
    git rev-parse HEAD
    ```

5.  **Environment Name**: If initialization is needed, you MUST ask the user for
    the environment name. If the user does not provide it, use **dev** as the
    default.

> [!TIP]
>
> Use these commands to replace placeholders like `YOUR_PROJECT_ID` with actual
> values. Always remove associated comments that start with TODO once replaced.

### Step 3: Generate or update deployment.yaml

Create or update `deployment.yaml` in the repository root. This file maps
supported environments (**dev**, **stage**, **prod**) to their specific
configurations and resources.

> [!TIP]
>
> **Use the Reference Spec**: The agent can use the
> **`references/gcp_pipeline_resource_provisioning_spec.md`** file as a
> template. It includes sample definitions for select supported resource types.
> Copy and adapt the required resource blocks into the `deployment.yaml`. Use
> `gcloud beta orchestration-pipelines resource-types list` when needed.

> [!IMPORTANT]
>
> **Handling Secrets & Privacy (CRITICAL)**: NEVER hardcode plain-text secrets
> in `deployment.yaml`.
>
> -   **Sensitive Data (Secrets):** Sensitive information such as passwords, API
>     keys, and other sensitive information MUST be stored in Secret Manager and
>     declared in the `secrets:` block of `deployment.yaml`.
> -   **Non-Sensitive Data (Variables):** General configuration (e.g., dataset
>     names, table IDs, regions) could be declared in the `variables:` block.
> -   **Substitution via `{{ VAR }}`:** Both `variables:` and `secrets:` MUST be
>     used as `{{ VARIABLE_NAME }}` substitutions in resource definitions.
> -   **No Creation**: The agent MUST NOT use the framework to *create* new
>     secrets. If `gcloud` indicates the secret does not exist, the agent MUST
>     ask the user to create it manually and then re-verify.
> -   **Reference Only Policy**: The agent's role is strictly limited to
>     *referencing* existing secrets. The agent MUST NEVER read, print, or
>     inspect the values of secrets.
> -   **Safe Deployment**: The actual value injection happens during deployment
>     execution. The agent only provides the reference.
> -   **Manual Secret Management**: Advise the user to manage secret payloads
>     and versions manually.

### Step 4: Validation

The agent MUST validate the `deployment.yaml` before generating the deployment
script. This ensures the configuration is syntactically correct and all
variables are resolvable.

```
gcloud beta orchestration-pipelines validate --environment=<ENV_NAME>
```

### Step 5: Deployment

Run the following command to deploy the resources to the target environment.

```
gcloud beta orchestration-pipelines deploy --environment=<ENV_NAME> --local
```

> [!NOTE]
>
> If a new transfer is being created, make sure to NOT remove the DTS transfer
> resource from `deployment.yaml` after it completes the run.

## Definition of Done

-   `deployment.yaml` exists in the repository root with actual discovered
    values (no placeholders) and correct resource definitions.
-   The agent runs the deployment command to perform the deployment, and it
    executes successfully (exit code 0).
