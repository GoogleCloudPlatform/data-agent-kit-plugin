---
name: bigquery-data-agent-author
metadata:
  version: v1
  publisher: google
description: >-
  Authors, validates, deploys, and promotes BigQuery Conversational Analytics
  (BQCA) DataAgents as code via the Gemini Data Analytics v1 API, Python SDK,
  or Terraform. Covers scoped agent design (table/column metadata, verified
  queries, glossaries, relationships, routines), concise YAML instructions,
  bytes-scanned caps and quotas, curated table exposure and BQ AI/ML anomaly
  detection, BigQuery Agent Analytics monitoring, and staging-to-published
  promotion. Use when creating, editing, reviewing, or deploying BQCA agents
  from an IDE or CI/CD pipeline. Don't use for chatting with an existing CA
  agent, curating standalone Knowledge Catalog context sets (use
  curate-context), or querying BigQuery job/slot telemetry (use
  bigquery-observability).
license: Apache-2.0
---

# Authoring BigQuery Conversational Analytics DataAgents as Code

Build, validate, and promote BigQuery Conversational Analytics (`DataAgent`)
resources from source control rather than manual console clicks. Follow the
five-step workflow below in order and load only the reference file needed for
the current step.

## Reference Routing

Task or phase                                                                                                                                                                                                                                   | Open when needed
:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------
Scoped table selection, structured context (`schema`, `exampleQueries`, `glossaryTerms`, `schemaRelationships`, `userFunctions`), concise YAML `systemInstruction`, `bigQueryMaxBilledBytes`, quotas, table impact, and light anomaly detection | [Design, Schema & Cost Control Guide](references/design_and_cost.md)
Per-agent BigQuery Agent Analytics (`bigqueryAgentAnalyticsEnabled`, `bigqueryAgentAnalyticsTable`), P4SA permissions, RLS/CLS logging suppression, project-level observability, and GDA + BigQuery IAM roles                                   | [Monitoring & IAM Guide](references/monitoring_and_iam.md)
Git repo layout, `stagingContext` to `publishedContext` promotion, `lastPublishedContext` rollback, `scripts/bqca_deploy.py` CLI, `v1` REST `:createSync`/`:updateSync`, Python SDK, and Terraform caveats                                      | [Deployment & Promotion Guide](references/deploy_and_promote.md)
Deterministic offline spec validation, optional `bq query --dry_run` verified-query byte checks, and `v1` REST deploy/promote/rollback/export                                                                                                   | `scripts/bqca_deploy.py`

## Five-Step Authoring Workflow

### 1. Scope and Design Structured Context First

Open [Design, Schema & Cost Control Guide](references/design_and_cost.md).

-   **Keep one domain per agent** (typically 1-10 curated tables or views) to
    reduce prompt tokens and join ambiguity.
-   **Declare explicit `datasourceReferences.bq.tableReferences`** (and optional
    `propertyGraphReferences`). Never set `searchScope` on a persistent
    `DataAgent` — `searchScope` is supported only for stateless/inline chat
    requests.
-   **Put facts in structured fields first**: table/column descriptions,
    synonyms, and tags in `BigQueryTableReference.schema`; verified SQL
    templates (including parameterized `@param` queries) in `exampleQueries`;
    domain terms in `glossaryTerms`; join paths in `schemaRelationships`; and
    UDFs/TVFs in `userFunctions.bqRoutines`.
-   **Keep `systemInstruction` concise YAML** (practical target: 2-4 KB; warn
    above 8 KB; hard API limit: 250,000 bytes). Include only persona, grain/join
    tie-breakers, metric formulas, formatting rules, and refusal/clarification
    boundaries that cannot be expressed in structured fields.
-   If curating standalone Knowledge Catalog context sets (`v1beta`
    `agent_context_reference`), use a dedicated context-curation skill (if
    available in your skill catalog, e.g. `curate-context`) instead.

### 2. Enforce Cost Caps, Table Exposure, and Anomaly Support

Open [Design, Schema & Cost Control Guide](references/design_and_cost.md).

-   **Per-query byte cap**: Always set
    `options.datasource.bigQueryMaxBilledBytes`. Over-budget queries fail a
    dry-run check before execution without incurring BigQuery charges.
-   **Project and user quotas**: Isolate high-traffic or wide-table agents in a
    dedicated GCP billing project and set BigQuery **Query usage per day** and
    **Query usage per day per user** quotas. Note that cost controls apply to
    on-demand billing (not slot reservations), and per-agent quotas or per-agent
    BigQuery job labels are not supported.
-   **Table impact and exposure**: BQCA executes read-only `SELECT` queries
    under the **end user's IAM credentials** (enforcing BigQuery RLS, CLS,
    policy tags, and masking; no DML/DDL mutations). Expose partitioned and
    clustered mart tables or curated views rather than wide raw landing tables
    (see `bigquery-optimization`).
-   **Light anomaly detection**: Enable `options.analysis.python.enabled: true`
    for sandboxed statistical checks on query results, or expose time-series
    views alongside BigQuery AI/ML functions (`AI.DETECT_ANOMALIES`,
    `ML.DETECT_ANOMALIES`, `AI.FORECAST`, `ML.FORECAST`) in `exampleQueries` or
    `userFunctions.bqRoutines` (see `bigquery-ai-ml`).

### 3. Configure Monitoring and IAM

Open [Monitoring & IAM Guide](references/monitoring_and_iam.md).

-   **Per-agent trace logging (`v1`)**: Set BOTH
    `bigqueryAgentAnalyticsEnabled: true` and `bigqueryAgentAnalyticsTable` in
    the **same GCP project** as the `DataAgent`.
-   **Mandatory P4SA dataset grant**: Pre-create the destination dataset and
    grant `roles/bigquery.dataEditor` to
    `service-PROJECT_NUMBER@gcp-sa-geminidataanalytics.iam.gserviceaccount.com`.
    Without this grant, the agent answers normally and silently writes zero
    trace rows.
-   **RLS/CLS suppression caveat**: Trace logging is silently suppressed for the
    entire turn if any table in the agent's data source has row-level security,
    column-level security, policy tags, or data masking (or if the caller lacks
    permission to inspect table security policies).
-   **Dual-permission IAM model**: Grant least-privilege Gemini Data Analytics
    roles (`roles/geminidataanalytics.dataAgentUser` on the agent resource for
    consumers) **plus** BigQuery data/job roles (`roles/bigquery.dataViewer` on
    queried datasets/tables and `roles/bigquery.jobUser` on the billing
    project).
-   Once traces are flowing, query `bigqueryAgentAnalyticsTable` directly using
    BigQuery SQL to inspect turn latency, tool-call counts, SQL errors, and
    scanned bytes (and `bigquery-observability`, if available, for BigQuery
    job/slot telemetry).

### 4. Run Local Validation and BigQuery Dry-Run Pre-Flight

Before touching any GCP environment, validate the rendered specification with
the zero-dependency bundled CLI:

```bash
python3 scripts/bqca_deploy.py validate --spec agents/sales_analyst/agent.json --env agents/sales_analyst/envs/staging.json --instruction agents/sales_analyst/system_instruction.yaml --bq-dry-run
```

Fix any unresolved `{{var}}` placeholders, AIP-122 `data_agent_id` errors,
byte-cap violations, undeclared `@param` tokens in `exampleQueries`,
cross-project monitoring tables, or `bq query --dry_run` syntax/byte failures
before proposing deployment.

### 5. Deploy to Staging, Promote to Published, and Roll Back Safely

Open [Deployment & Promotion Guide](references/deploy_and_promote.md).

-   **Two-stage promotion**: Deploy edits to `stagingContext` first
    (`deploy --target staging`), run smoke/evaluation tests, and only then
    promote to `publishedContext` (`promote` subcommand or
    `deploy --target published`). Use `lastPublishedContext` (`rollback`
    subcommand) for instant single-version rollback.
-   **Choose the right delivery tool**:
    -   `scripts/bqca_deploy.py` or `v1` REST (`:createSync` / `:updateSync`) /
        Python SDK (`google-cloud-geminidataanalytics`) for full `v1` field
        coverage including `bigqueryAgentAnalyticsEnabled`.
    -   Terraform (`google_gemini_data_analytics_data_agent`) when teams manage
        infra via HCL — noting two critical limits: `bigquery_agent_analytics_*`
        fields are not yet exposed in the Terraform resource schema, and
        deleting a `DataAgent` soft-deletes it for **30 days** (`purge_time`),
        causing force-replacement changes (such as `kms_key`) with the same
        `data_agent_id` to fail with `ALREADY_EXISTS`.

## Non-Negotiable Guardrails

-   **Always ask for explicit user confirmation** before executing live mutating
    operations (`deploy` or `promote` without `--dry-run`, `rollback`,
    `:createSync`, `:updateSync`, `:deleteSync`, `:setIamPolicy`, or
    `terraform apply`). Show the target project, location, `data_agent_id`,
    target context (`staging` vs `published`), and `--dry-run` summary first.
-   **Never invent schemas, join keys, metric formulas, or verified SQL.**
    Inspect BigQuery `INFORMATION_SCHEMA` or user-provided DDL before authoring
    `tableReferences`, `schemaRelationships`, or `exampleQueries`.
-   **Never configure `searchScope` on a `DataAgent`.** Always enumerate
    explicit `tableReferences` or `propertyGraphReferences`.
-   **Never omit `bigQueryMaxBilledBytes`** unless the user explicitly
    acknowledges unbounded per-query scan risk (`--allow-unbounded-bytes`).
