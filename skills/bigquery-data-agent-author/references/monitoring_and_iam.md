# Monitoring (`bigqueryAgentAnalyticsTable`) and IAM Access Control

This reference covers step 3 of authoring a BigQuery Conversational Analytics
(`DataAgent`) resource: enabling per-agent BigQuery Agent Analytics (BQAA) trace
logging and configuring least-privilege Gemini Data Analytics + BigQuery IAM.

## 1. Per-Agent BigQuery Agent Analytics Trace Logging (`v1`)

In `v1`, `DataAgent` exposes two top-level fields for streaming structured turn
traces into a BigQuery table:

-   `bigqueryAgentAnalyticsEnabled` (`bigquery_agent_analytics_enabled`, `bool`)
-   `bigqueryAgentAnalyticsTable` (`bigquery_agent_analytics_table`,
    `BigQueryTableReference`)

```json
{
  "displayName": "Commerce Revenue Analyst",
  "bigqueryAgentAnalyticsEnabled": true,
  "bigqueryAgentAnalyticsTable": {
    "projectId": "analytics-prod",
    "datasetId": "agent_observability",
    "tableId": "commerce_agent_traces"
  },
  "dataAnalyticsAgent": {
    "stagingContext": { "...": "..." }
  }
}
```

### Seven Mandatory API Rules and Production Gotchas

1.  **Both fields are required to write rows**: Trace rows are written **only**
    when `bigqueryAgentAnalyticsEnabled` is `true` **and**
    `bigqueryAgentAnalyticsTable` is populated. Setting
    `bigqueryAgentAnalyticsEnabled: true` without a table (or setting a table
    while `bigqueryAgentAnalyticsEnabled` is `false`/omitted) creates no table
    and writes zero rows.
2.  **Same-project enforcement (`INVALID_ARGUMENT`)**:
    `bigqueryAgentAnalyticsTable.projectId` **must** match the GCP project that
    owns the `DataAgent`. Cross-project destination tables are rejected on
    `CreateDataAgent` and `UpdateDataAgent` with `INVALID_ARGUMENT`.
3.  **BigQuery data sources only (`INVALID_ARGUMENT`)**: Setting
    `bigqueryAgentAnalyticsEnabled: true` or setting
    `bigqueryAgentAnalyticsTable` on a Looker, Looker Studio, or database agent
    is rejected with `INVALID_ARGUMENT`.
4.  **Pre-created dataset + explicit P4SA IAM grant (silent drop if missing)**:
    The destination BigQuery dataset must already exist, and you **must** grant
    BigQuery Data Editor (`roles/bigquery.dataEditor`) on that dataset to the
    project's Gemini Data Analytics service agent:
    `service-PROJECT_NUMBER@gcp-sa-geminidataanalytics.iam.gserviceaccount.com`.
    This grant is **not** created automatically. Without it, the agent answers
    user questions normally and writes **zero trace rows**.
5.  **Silent turn-level suppression on RLS / CLS / masking**: Trace logging is
    suppressed for the **entire turn without error** whenever **any** table in
    the agent's `datasourceReferences` carries BigQuery row-level security
    (RLS), column-level security (CLS), policy tags, or data masking — or when
    the caller lacks IAM permission to inspect table security policies. If an
    agent needs trace logging over governed data, expose a curated de-identified
    mart/view that does not carry RLS/CLS policy tags rather than expecting
    partial trace rows.
6.  **No inheritance from project-level observability**: Per-agent trace logging
    is completely independent of
    `observabilitySettings:setAgentOpsObservability`. Enabling project-level
    `bqaa_enabled` does **not** automatically enable trace logging on individual
    `DataAgent` resources.
7.  **Staging + published update semantics**: Updating
    `bigqueryAgentAnalyticsEnabled` or `bigqueryAgentAnalyticsTable` applies to
    conversations served from `stagingContext` and, once published, from
    `publishedContext`. Changing `bigqueryAgentAnalyticsTable` affects
    subsequent turns only; historical rows remain in the previous table.

### Granting the Service Agent Dataset Write Access

Ensure the GDA service identity exists and grant `roles/bigquery.dataEditor` on
the destination dataset (replace `PROJECT_ID`, `PROJECT_NUMBER`, and
`agent_observability`):

```bash
gcloud beta services identity create --service=geminidataanalytics.googleapis.com --project=PROJECT_ID

bq mk --dataset --location=US PROJECT_ID:agent_observability

gcloud projects describe PROJECT_ID --format="value(projectNumber)"

bq query --use_legacy_sql=false \
  'GRANT `roles/bigquery.dataEditor` ON SCHEMA `PROJECT_ID`.agent_observability TO "serviceAccount:service-PROJECT_NUMBER@gcp-sa-geminidataanalytics.iam.gserviceaccount.com"'
```

Note: `bq add-iam-policy-binding` applies only to BigQuery tables and views, not
datasets. For datasets, use BigQuery DCL `GRANT ... ON SCHEMA` (above),
`bq show --format=prettyjson` with `bq update --source`, or Terraform
`google_bigquery_dataset_iam_member`.

## 2. Project-Level AgentOps Observability Settings

To enable or inspect project-level Cloud Trace / Cloud Logging / Cloud
Monitoring / BQAA API readiness on `projects/{project}/locations/{location}`:

-   **Inspect**: `GET
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION:retrieveAgentOpsObservability?dataSourceType=bigquery`
-   **Configure** (returns a long-running `Operation`; note an explicit
    `updateMask` containing `bqaa_enabled` is required when toggling
    `bqaaEnabled`, especially to disable it):

```json
{
  "telemetryEnabled": true,
  "dataSourceType": "bigquery",
  "bqaaEnabled": true
}
```

`POST
https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/observabilitySettings:setAgentOpsObservability?updateMask=telemetry_enabled,bqaa_enabled`

## 3. Post-Deploy Trace Analysis

Once trace rows are landing in `bigqueryAgentAnalyticsTable`, query the table
directly with BigQuery SQL to:

-   Measure end-to-end turn latency, tool-call counts, and SQL retry/error
    rates.
-   Audit generated SQL scan volume and recurring unverified queries that should
    be promoted into `Context.exampleQueries`.
-   Correlate trace activity with project-level BigQuery job and slot telemetry
    via `INFORMATION_SCHEMA.JOBS` (or the `bigquery-observability` skill, if
    available in your skill catalog).

## 4. Gemini Data Analytics IAM and the Dual-Permission Model

### Dual-Permission Requirement

Gemini Data Analytics IAM roles govern **only** the `DataAgent` resource and
Chat API. Because BigQuery queries execute under the caller's own IAM
credentials, every principal interacting with a BigQuery `DataAgent` requires
**both**:

1.  **Gemini Data Analytics role** (for example,
    `roles/geminidataanalytics.dataAgentUser` on the specific `DataAgent`).
2.  **BigQuery data and job roles**:
    -   `roles/bigquery.dataViewer` on the exposed BigQuery datasets or tables
        (plus `roles/datacatalog.categoryFineGrainedReader` where policy-tagged
        columns are intentionally exposed).
    -   `roles/bigquery.jobUser` on the GCP project where queries are billed.

Note: Granting access to a `DataAgent` never exposes other users' chat
conversations — listing conversations returns only those created by the caller.

### Predefined Gemini Data Analytics Roles

Role ID                                            | Typical grant scope    | Primary use case
:------------------------------------------------- | :--------------------- | :---------------
`roles/geminidataanalytics.admin`                  | Project                | Platform admins managing all agents, IAM policies, and operations in a project
`roles/geminidataanalytics.dataAgentCreator`       | Project                | CI/CD deploy service accounts or authors creating new agents (creator automatically receives `dataAgentOwner` on created agents)
`roles/geminidataanalytics.dataAgentOwner`         | **Agent** (or Project) | Agent owners who update, publish, share (`setIamPolicy`), or delete a specific agent
`roles/geminidataanalytics.dataAgentEditor`        | **Agent** (or Project) | Co-authors updating `stagingContext` / `publishedContext` without IAM sharing or delete rights
`roles/geminidataanalytics.dataAgentUser`          | **Agent** (or Project) | End users and client apps chatting with a specific published agent
`roles/geminidataanalytics.dataAgentViewer`        | **Agent** (or Project) | Auditors inspecting `DataAgent` configurations without chat access
`roles/geminidataanalytics.viewer`                 | Project                | Read-only config view + chat across all agents in a project
`roles/geminidataanalytics.dataAgentStatelessUser` | Project                | Callers invoking stateless inline-context chat without persistent `DataAgent` resources

Prefer granting `dataAgentOwner`, `dataAgentEditor`, `dataAgentUser`, and
`dataAgentViewer` on the **individual `DataAgent` resource** rather than at the
project level.

### Programmatic Agent Sharing (`:getIamPolicy` -> `:setIamPolicy`)

`setIamPolicy` **replaces** the entire allow policy on the `DataAgent`. Always
follow a **read-modify-write** flow (preserving `etag` and existing bindings):

1.  **Read current policy**: `POST
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/dataAgents/AGENT_ID:getIamPolicy`
    with body `{}`.
2.  **Merge binding and write back**: `POST
    https://geminidataanalytics.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/dataAgents/AGENT_ID:setIamPolicy`

```json
{
  "policy": {
    "etag": "BwY...",
    "bindings": [
      {
        "role": "roles/geminidataanalytics.dataAgentOwner",
        "members": ["serviceAccount:bqca-deployer@PROJECT_ID.iam.gserviceaccount.com"]
      },
      {
        "role": "roles/geminidataanalytics.dataAgentUser",
        "members": ["group:commerce-analysts@example.com"]
      }
    ]
  }
}
```
