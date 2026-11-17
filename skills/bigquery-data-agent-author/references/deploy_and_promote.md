# Code-First Repo Layout, Deployment, Promotion, and Rollback

This reference covers steps 4 and 5: managing BigQuery Conversational Analytics
(`DataAgent`) definitions in Git, validating them offline, promoting from
`stagingContext` to `publishedContext`, rolling back via `lastPublishedContext`,
and choosing between the bundled CLI, `v1` REST / Python SDK, and Terraform.

## 1. Recommended Git Repository Layout

Keep structural metadata in JSON, prose rules in a standalone YAML file, and
environment-specific bindings (`project`, `location`, `data_agent_id`, dataset
names, byte caps, monitoring table) in per-environment override files:

```text
agents/
  sales_analyst/
    agent.json
    system_instruction.yaml
    envs/
      dev.json
      staging.json
      prod.json
```

### `agents/sales_analyst/agent.json`

```json
{
  "displayName": "Commerce Revenue Analyst ({{env_label}})",
  "description": "Answers net revenue and customer-segment questions on commerce_mart.",
  "labels": {
    "domain": "commerce",
    "managed_by": "git"
  },
  "dataAnalyticsAgent": {
    "stagingContext": {
      "datasourceReferences": {
        "bq": {
          "tableReferences": [
            {
              "projectId": "{{data_project}}",
              "datasetId": "{{mart_dataset}}",
              "tableId": "fct_orders_daily",
              "schema": {
                "description": "Daily order-level revenue fact table partitioned by order_date.",
                "fields": [
                  {
                    "name": "order_date",
                    "type": "DATE",
                    "mode": "REQUIRED",
                    "description": "UTC checkout date partition key."
                  },
                  {
                    "name": "net_revenue_usd",
                    "type": "NUMERIC",
                    "mode": "NULLABLE",
                    "description": "Gross order value minus discounts and refunds in USD."
                  }
                ]
              }
            }
          ]
        }
      },
      "options": {
        "model": "LATEST_GA_MODEL",
        "analysis": {
          "python": {
            "enabled": true
          }
        },
        "datasource": {
          "bigQueryMaxBilledBytes": "{{max_billed_bytes}}"
        }
      },
      "exampleQueries": [
        {
          "naturalLanguageQuestion": "Total net revenue since {start_date}",
          "sqlQuery": "SELECT SUM(net_revenue_usd) AS net_revenue_usd FROM `{{data_project}}.{{mart_dataset}}.fct_orders_daily` WHERE order_date >= @start_date",
          "parameters": [
            {
              "name": "start_date",
              "dataType": "DATE",
              "description": "Inclusive UTC start date (YYYY-MM-DD)."
            }
          ]
        }
      ],
      "glossaryTerms": [
        {
          "displayName": "Net Revenue",
          "description": "Realized USD order value excluding discounts and refunds."
        }
      ]
    }
  }
}
```

### `agents/sales_analyst/envs/prod.json`

```json
{
  "project": "commerce-agents-prod",
  "location": "global",
  "data_agent_id": "commerce-revenue-analyst",
  "bigquery_agent_analytics_enabled": true,
  "bigquery_agent_analytics_table": {
    "projectId": "commerce-agents-prod",
    "datasetId": "agent_observability",
    "tableId": "commerce_revenue_traces"
  },
  "vars": {
    "env_label": "prod",
    "data_project": "commerce-warehouse-prod",
    "mart_dataset": "commerce_mart",
    "max_billed_bytes": "2147483648"
  }
}
```

## 2. Two-Stage Context Lifecycle (`staging` -> `published` -> `rollback`)

Every `DataAnalyticsAgent` carries three context slots:

1.  `stagingContext` (`staging_context`, read/write): Draft slot for authoring
    and pre-publish verification. Updating `stagingContext` never alters
    production `publishedContext` traffic.
2.  `publishedContext` (`published_context`, read/write): Production slot served
    by the Chat API once published.
3.  `lastPublishedContext` (`last_published_context`, output-only): Populated
    automatically by the service whenever `publishedContext` is overwritten.
    Copying `lastPublishedContext` back into `publishedContext` performs an
    atomic one-step rollback.

## 3. Path A: Bundled Zero-Dependency CLI (`scripts/bqca_deploy.py`)

`scripts/bqca_deploy.py` requires only Python 3 standard library (`gcloud` for
OAuth tokens on live calls and `bq` only when `--bq-dry-run` is requested).

### Offline Validation + Optional `bq` Dry-Run

```bash
python3 scripts/bqca_deploy.py validate --spec agents/sales_analyst/agent.json --env agents/sales_analyst/envs/prod.json --instruction agents/sales_analyst/system_instruction.yaml --bq-dry-run
```

### Stage -> Smoke Test -> Promote -> Rollback

```bash
# 1. Preview exact REST request & rendered payload (no network mutations)
python3 scripts/bqca_deploy.py deploy --spec agents/sales_analyst/agent.json --env agents/sales_analyst/envs/prod.json --instruction agents/sales_analyst/system_instruction.yaml --target staging --dry-run

# 2. Upsert into stagingContext (:createSync on 404, :updateSync on 200)
python3 scripts/bqca_deploy.py deploy --spec agents/sales_analyst/agent.json --env agents/sales_analyst/envs/prod.json --instruction agents/sales_analyst/system_instruction.yaml --target staging

# 3a. After staging evaluation passes, promote rendered spec to publishedContext
python3 scripts/bqca_deploy.py promote --env agents/sales_analyst/envs/prod.json --spec agents/sales_analyst/agent.json --instruction agents/sales_analyst/system_instruction.yaml

# 3b. Or promote live stagingContext -> publishedContext directly without --spec
python3 scripts/bqca_deploy.py promote --env agents/sales_analyst/envs/prod.json

# 4. Instant rollback to lastPublishedContext if regressions appear
python3 scripts/bqca_deploy.py rollback --env agents/sales_analyst/envs/prod.json

# 5. Export an existing console-authored agent into clean Git-ready JSON
python3 scripts/bqca_deploy.py export --project commerce-agents-prod --location global --agent-id commerce-revenue-analyst --output agents/sales_analyst/agent.json
```

Operational notes:

-   `promote` always patches `updateMask=data_analytics_agent.published_context`
    only. In contrast, `deploy` includes top-level metadata fields when present
    in the spec — note that including `labels` in `updateMask` replaces the
    entire `labels` map on the `DataAgent`.
-   `rollback --dry-run` and `promote --dry-run` (when invoked without `--spec`)
    still perform a read-only `GET` with OAuth credentials to inspect the live
    `lastPublishedContext` or `stagingContext` before previewing the `PATCH`.

### CI/CD Pipeline Pattern (Cloud Build or GitHub Actions)

-   **Pull request check**: Run `bqca_deploy.py validate --bq-dry-run` and
    `bqca_deploy.py deploy --target staging --dry-run` against every environment
    file (`envs/*.json`).
-   **Merge to `main`**: Deploy `--target staging`, execute automated chat
    evaluation queries against a golden Q&A evaluation gate, and require manual
    approval (or passing gate checks) before running `promote` (or
    `deploy --target published`).

## 4. Path B: Direct `v1` REST (`curl`) and Python SDK

### Regional and Multi-Regional Endpoint Routing

Route API calls to the regional or multi-regional hostname matching the
`DataAgent` `location` (the resource path `locations/{location}` must match the
endpoint location):

Location scope               | Example `location` | Base `v1` REST endpoint
:--------------------------- | :----------------- | :----------------------
Global                       | `global`           | `https://geminidataanalytics.googleapis.com/v1`
Multi-regional               | `us`, `eu`         | `https://geminidataanalytics.{location}.rep.googleapis.com/v1`
Single region (contains `-`) | `us-east4`         | `https://geminidataanalytics-{location}.googleapis.com/v1`

`scripts/bqca_deploy.py` derives this endpoint automatically from `location`
unless `--api-endpoint` is explicitly set.

### Synchronous `v1` REST Endpoints

Prefer the synchronous `:createSync`, `:updateSync`, and `:deleteSync` methods
for deterministic CI scripts (passing a UUIDv4 `requestId` for 60-minute
idempotent retries; replace `geminidataanalytics.googleapis.com` with the
matching regional or `.rep.googleapis.com` host when `LOCATION != global`):

-   **Create**: `POST
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/dataAgents:createSync?dataAgentId=AGENT_ID&requestId=UUID4`
-   **Targeted staging update** (always supply an explicit `updateMask` so you
    do not accidentally overwrite `publishedContext`, and omit immutable
    `kms_key`): `PATCH
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/dataAgents/AGENT_ID:updateSync?updateMask=display_name,description,labels,data_analytics_agent.staging_context,bigquery_agent_analytics_enabled,bigquery_agent_analytics_table&requestId=UUID4`
-   **Promote to published**: `PATCH
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/dataAgents/AGENT_ID:updateSync?updateMask=data_analytics_agent.published_context&requestId=UUID4`
-   **Soft-delete**: `DELETE
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/dataAgents/AGENT_ID:deleteSync?requestId=UUID4`

### Python SDK (`google-cloud-geminidataanalytics`) Upsert Snippet

```python
import uuid
from google.api_core import client_options
from google.api_core import exceptions
from google.cloud import geminidataanalytics
from google.protobuf import field_mask_pb2


def _endpoint_for_location(location: str) -> str:
  if location == "global":
    return "geminidataanalytics.googleapis.com"
  if "-" in location:
    return f"geminidataanalytics-{location}.googleapis.com"
  return f"geminidataanalytics.{location}.rep.googleapis.com"


def upsert_staging_agent(
    project: str,
    location: str,
    agent_id: str,
    staging_context: geminidataanalytics.Context,
    display_name: str,
) -> geminidataanalytics.DataAgent:
  endpoint = _endpoint_for_location(location)
  client = geminidataanalytics.DataAgentServiceClient(
      client_options=client_options.ClientOptions(api_endpoint=endpoint)
  )
  parent = f"projects/{project}/locations/{location}"
  name = f"{parent}/dataAgents/{agent_id}"
  agent = geminidataanalytics.DataAgent(
      name=name,
      display_name=display_name,
      data_analytics_agent=geminidataanalytics.DataAnalyticsAgent(
          staging_context=staging_context
      ),
  )
  try:
    client.get_data_agent(name=name)
  except exceptions.NotFound:
    return client.create_data_agent_sync(
        request=geminidataanalytics.CreateDataAgentRequest(
            parent=parent,
            data_agent_id=agent_id,
            data_agent=agent,
            request_id=str(uuid.uuid4()),
        )
    )
  return client.update_data_agent_sync(
      request=geminidataanalytics.UpdateDataAgentRequest(
          data_agent=agent,
          update_mask=field_mask_pb2.FieldMask(
              paths=["display_name", "data_analytics_agent.staging_context"]
          ),
          request_id=str(uuid.uuid4()),
      )
  )
```

## 5. Path C: Terraform (`google_gemini_data_analytics_data_agent`)

When provisioning via the Google Terraform provider (`hashicorp/google` /
`hashicorp/google-beta`), use `google_gemini_data_analytics_data_agent` and
`google_gemini_data_analytics_data_agent_iam_member`:

```terraform
resource "google_gemini_data_analytics_data_agent" "commerce_analyst" {
  project       = var.agent_project_id
  location      = "global"
  data_agent_id = "commerce-revenue-analyst-v1"
  display_name  = "Commerce Revenue Analyst"
  description   = "Scoped revenue agent over commerce_mart."

  labels = {
    domain     = "commerce"
    managed_by = "terraform"
  }

  data_analytics_agent {
    published_context {
      system_instruction = file("${path.module}/system_instruction.yaml")

      datasource_references {
        bq {
          table_references {
            project_id = var.data_project_id
            dataset_id = "commerce_mart"
            table_id   = "fct_orders_daily"

            schema {
              description = "Daily order-level revenue fact table."
              fields {
                name        = "order_date"
                type        = "DATE"
                mode        = "REQUIRED"
                description = "UTC checkout date partition key."
              }
              fields {
                name        = "net_revenue_usd"
                type        = "NUMERIC"
                mode        = "NULLABLE"
                description = "Net order revenue in USD."
              }
            }
          }
        }
      }

      options {
        model = "LATEST_GA_MODEL"
        analysis {
          python {
            enabled = true
          }
        }
        datasource {
          big_query_max_billed_bytes = 2147483648
        }
      }

      example_queries {
        natural_language_question = "Total net revenue since {start_date}"
        sql_query                 = "SELECT SUM(net_revenue_usd) AS net_revenue_usd FROM `${var.data_project_id}.commerce_mart.fct_orders_daily` WHERE order_date >= @start_date"

        parameters {
          name        = "start_date"
          data_type   = "DATE"
          description = "Inclusive UTC start date (YYYY-MM-DD)."
        }
      }

      glossary_terms {
        display_name = "Net Revenue"
        description  = "Realized USD order value excluding discounts and refunds."
        labels       = ["revenue", "sales"]
      }
    }
  }
}

resource "google_gemini_data_analytics_data_agent_iam_member" "analysts_chat" {
  project       = google_gemini_data_analytics_data_agent.commerce_analyst.project
  location      = google_gemini_data_analytics_data_agent.commerce_analyst.location
  data_agent_id = google_gemini_data_analytics_data_agent.commerce_analyst.data_agent_id
  role          = "roles/geminidataanalytics.dataAgentUser"
  member        = "group:commerce-analysts@example.com"
}
```

### Two Critical Terraform Caveats

1.  **`bigquery_agent_analytics_*` fields are not yet in the Terraform resource
    schema**: `google_gemini_data_analytics_data_agent` does not currently
    expose `bigquery_agent_analytics_enabled` or
    `bigquery_agent_analytics_table`. If you require per-agent BQAA trace
    logging, either manage the agent via `scripts/bqca_deploy.py` / Python SDK
    or apply a post-provision `:updateSync` patch with
    `updateMask=bigquery_agent_analytics_enabled,bigquery_agent_analytics_table`.
2.  **CMEK (`kms_key`) location rules and 30-day soft-delete `data_agent_id`
    lock (`ALREADY_EXISTS` on replace)**:
    -   **CMEK location alignment**: CMEK (`kms_key`) is **not supported** in
        `global`. For a single-region `DataAgent` (for example, `us-east4`), the
        Cloud KMS `CryptoKey` must reside in the same region (`us-east4`). For
        the `us` multi-region, the KMS key must reside in `us`. For the `eu`
        multi-region, the KMS key must reside in **`europe`** (Cloud KMS has no
        `eu` location).
    -   **Immutability and 30-day soft-delete lock**: `kms_key` is immutable on
        update (it cannot be added or changed via `:updateSync`), so adding or
        rotating `kms_key` forces Terraform resource replacement. Deleting a
        `DataAgent` soft-deletes it for **30 days** (`purge_time`), locking its
        `data_agent_id` in the same project and location. Destroying and
        recreating with the same `data_agent_id` fails with `409 ALREADY_EXISTS`
        until `purge_time` passes — always rotate to a new `data_agent_id` (for
        example, `-v1` -> `-v2`) when changing `kms_key` or any other
        replacement-forcing attribute.
