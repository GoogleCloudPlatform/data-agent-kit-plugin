# Scoped Agent Design, Concise Instructions, Cost Controls, and Table Impact

This reference covers steps 1 and 2 of authoring a BigQuery Conversational
Analytics (`DataAgent`) resource on the Gemini Data Analytics `v1` API.

## 1. Scoped Agent Design

Keep each `DataAgent` focused on **one business domain** (typically 1-10 curated
BigQuery tables or views). Over-scoping an agent across dozens of raw warehouse
tables inflates prompt latency, increases join hallucinations, and raises
per-turn scan risk.

### Explicit `tableReferences` Only (`searchScope` Is Forbidden on `DataAgent`)

In `Context.datasourceReferences.bq`, populate `tableReferences` (and/or
`propertyGraphReferences` for BigQuery Graph).

-   **Hard API rule**: `BigQueryTableReferences.searchScope` (`search_scope`) is
    supported **only** for stateless/inline conversations
    (`ChatRequest.inline_context` or
    `ClientManagedResourceContext.inline_context`). Setting `searchScope` on a
    persistent `DataAgent` is unsupported and rejected by validation.
-   **Knowledge Catalog context sets**: `agent_context_reference`
    (`context_set_id`) is currently available only in `v1beta`
    (`google.cloud.geminidataanalytics.v1beta.BigQueryTableReferences`), not in
    stable `v1`. If your task is curating standalone Knowledge Catalog context
    sets, use a dedicated context-curation skill (if available in your skill
    catalog, e.g. `curate-context`).

### Priority Order: Structured Context Before Prose

Ingest domain facts into typed `Context` fields first so the service indexes,
retrieves, and cites them deterministically:

1.  **Table and column metadata (`BigQueryTableReference.schema`)**
    -   Table-level: `description`, `synonyms`, `tags`.
    -   Column-level (`fields[]`): `name`, `type`, `mode`, `description`,
        `synonyms`, `tags`, `subfields` (for `STRUCT`/`RECORD`).
    -   Only override or supplement columns whose BigQuery catalog descriptions
        are missing, ambiguous, or domain-specific; you do not need to repeat
        every self-explanatory column.
2.  **Verified queries (`Context.exampleQueries`)**
    -   Each `ExampleQuery` pairs `naturalLanguageQuestion` (max **2,000 UTF-8
        bytes**) with `sqlQuery` (max **50,000 UTF-8 bytes**).
    -   **Parameterized verified queries**: Use `{param_name}` placeholders in
        `naturalLanguageQuestion`, `@param_name` query parameters in GoogleSQL
        `sqlQuery`, and declare every parameter in `parameters[]` with `name`,
        `dataType` (standard GoogleSQL type such as `STRING`, `INT64`,
        `FLOAT64`, `NUMERIC`, `BOOL`, `DATE`, `TIMESTAMP`), and `description`.
    -   **Runtime behavior**: When an incoming user question semantically
        matches an `ExampleQuery`, the agent extracts parameter values via LLM,
        executes or adapts the verified SQL pattern, and surfaces provenance in
        `CitationSource.example_query` / `MatchedQuery` (`matched_query`).
3.  **Domain glossary (`Context.glossaryTerms`)**
    -   Define business acronyms, status codes, and canonical KPI names using
        `displayName` (required, max **256 UTF-8 bytes**), `description`
        (required, max **5,000 UTF-8 bytes**), and optional `labels` (synonyms
        or category tags). Matched terms are cited via
        `CitationSource.glossary_term`.
4.  **Join paths (`Context.schemaRelationships`)**
    -   Declare explicit join keys between tables using `leftSchemaPaths` and
        `rightSchemaPaths` (equal-length `paths` arrays).
    -   `tableFqn` uses the service-qualified format:
        `bigquery.googleapis.com/projects/PROJECT_ID/datasets/DATASET_ID/tables/TABLE_ID`.
    -   Optional metadata: `sources` (`BIGQUERY_TABLE_CONSTRAINTS`,
        `BIGQUERY_JOB_HISTORY`, `LLM_SUGGESTED`) and `confidenceScore` (`0.0` to
        `1.0`; `1.0` for verified author-defined joins).
5.  **Custom SQL routines (`Context.userFunctions.bqRoutines`)**
    -   Expose authorized UDFs or table-valued functions (TVFs) via
        `routineReference` (`projectId`, `datasetId`, `routineId`) and a clear
        `description` explaining when the agent should call the routine.

### Worked `v1` Structured Context Snippet (JSON)

```json
{
  "datasourceReferences": {
    "bq": {
      "tableReferences": [
        {
          "projectId": "analytics-prod",
          "datasetId": "commerce_mart",
          "tableId": "fct_orders_daily",
          "schema": {
            "description": "Daily order-level revenue fact table partitioned by order_date.",
            "synonyms": ["orders", "sales"],
            "tags": ["commerce", "revenue"],
            "fields": [
              {
                "name": "order_date",
                "type": "DATE",
                "mode": "REQUIRED",
                "description": "UTC date when checkout completed. Partition key; filter in every query."
              },
              {
                "name": "net_revenue_usd",
                "type": "NUMERIC",
                "mode": "NULLABLE",
                "description": "Gross item value minus discounts and refunds in USD.",
                "synonyms": ["net sales", "revenue"]
              },
              {
                "name": "status",
                "type": "STRING",
                "mode": "REQUIRED",
                "description": "Lifecycle state: COMPLETE, SHIPPED, PROCESSING, CANCELLED, RETURNED."
              }
            ]
          }
        },
        {
          "projectId": "analytics-prod",
          "datasetId": "commerce_mart",
          "tableId": "dim_customers",
          "schema": {
            "description": "One row per registered customer account.",
            "synonyms": ["buyers", "users"],
            "fields": [
              {
                "name": "customer_id",
                "type": "STRING",
                "mode": "REQUIRED",
                "description": "Primary key joining to fct_orders_daily.customer_id."
              },
              {
                "name": "segment",
                "type": "STRING",
                "mode": "NULLABLE",
                "description": "Commercial tier: ENTERPRISE, SMB, or CONSUMER."
              }
            ]
          }
        }
      ]
    }
  },
  "exampleQueries": [
    {
      "naturalLanguageQuestion": "What was net revenue for segment {segment} since {start_date}?",
      "sqlQuery": "SELECT SUM(o.net_revenue_usd) AS net_revenue_usd FROM `analytics-prod.commerce_mart.fct_orders_daily` AS o JOIN `analytics-prod.commerce_mart.dim_customers` AS c ON o.customer_id = c.customer_id WHERE o.order_date >= @start_date AND c.segment = @segment AND o.status NOT IN ('CANCELLED', 'RETURNED')",
      "parameters": [
        {
          "name": "segment",
          "dataType": "STRING",
          "description": "Customer commercial tier in uppercase (ENTERPRISE, SMB, CONSUMER)."
        },
        {
          "name": "start_date",
          "dataType": "DATE",
          "description": "Inclusive start date in YYYY-MM-DD format."
        }
      ]
    }
  ],
  "glossaryTerms": [
    {
      "displayName": "Net Revenue",
      "description": "SUM(net_revenue_usd) over orders where status NOT IN ('CANCELLED', 'RETURNED').",
      "labels": ["net sales", "realized revenue"]
    }
  ],
  "schemaRelationships": [
    {
      "leftSchemaPaths": {
        "tableFqn": "bigquery.googleapis.com/projects/analytics-prod/datasets/commerce_mart/tables/fct_orders_daily",
        "paths": ["customer_id"]
      },
      "rightSchemaPaths": {
        "tableFqn": "bigquery.googleapis.com/projects/analytics-prod/datasets/commerce_mart/tables/dim_customers",
        "paths": ["customer_id"]
      },
      "sources": ["BIGQUERY_TABLE_CONSTRAINTS"],
      "confidenceScore": 1.0
    }
  ]
}
```

## 2. Concise YAML `systemInstruction` (Token Budget)

Although `Context.systemInstruction` allows up to **250,000 UTF-8 bytes**,
bloated system prompts degrade SQL accuracy and increase per-turn latency.

-   **Practical target**: **2-4 KB** (`<= 4,096` bytes).
-   **Warning threshold**: `scripts/bqca_deploy.py` warns when
    `systemInstruction` exceeds **8,192 bytes**.
-   **Anti-patterns to eliminate**:
    -   Pasting raw `CREATE TABLE` DDL or repeating column descriptions already
        present in BigQuery or `tableReferences[].schema`.
    -   Embedding 20 full SQL queries in YAML prose instead of
        `Context.exampleQueries`.
    -   Dumping every company acronym into YAML instead of
        `Context.glossaryTerms`.

### Recommended Minimal YAML Structure

Keep `systemInstruction` limited to five high-leverage blocks:

```yaml
role: >-
  You are the Commerce Revenue Analyst agent for Acme Retail. Answer questions
  strictly using the configured commerce_mart tables.
query_rules:
  - Always include a partition filter on `fct_orders_daily.order_date` (default
    to the trailing 90 days relative to CURRENT_DATE('UTC') when the user omits
    a date window, and state the assumed window).
  - Join `fct_orders_daily` to `dim_customers` on `customer_id` using INNER JOIN
    for segment breakdowns; never fan out across unaggregated line items.
business_calculations:
  - Exclude `status IN ('CANCELLED', 'RETURNED')` from revenue and order-volume
    KPIs unless the user explicitly asks about cancellations or returns.
  - Fiscal year starts February 1 (`FY2026` = `2026-02-01` through `2027-01-31`).
output_format:
  - Format USD values to 2 decimal places (`$1,234.56`) and percentages to 1
    decimal place.
  - State the date range and filters applied in the first sentence.
boundaries:
  - Ask a brief clarifying question when "revenue" could mean gross vs. net and
    the distinction materially changes the answer.
  - Decline requests for customer PII (email, phone, street address) and explain
    that PII columns are excluded from this mart.
```

## 3. Controlling Bytes Scanned and BigQuery Costs

Layer per-query byte caps with project/user daily quotas to prevent runaway
BigQuery spend.

### Per-Query Cap: `options.datasource.bigQueryMaxBilledBytes`

Set `options.datasource.bigQueryMaxBilledBytes` in both `stagingContext` and
`publishedContext`:

```json
{
  "options": {
    "model": "LATEST_GA_MODEL",
    "datasource": {
      "bigQueryMaxBilledBytes": "1073741824"
    }
  }
}
```

-   Before running each generated SQL query, BigQuery estimates bytes billed via
    dry run. Any query exceeding `bigQueryMaxBilledBytes` **fails immediately
    without incurring a BigQuery charge**.
-   Size the cap slightly above the dry-run byte estimate of your largest
    verified query in `exampleQueries` (for example, `1073741824` for 1 GiB or
    `10737418240` for 10 GiB on partitioned marts).

### Project and User Daily Quotas

For agents backed by large datasets or broad user populations:

1.  **Isolate the agent in a dedicated GCP billing project** so its BigQuery
    query jobs do not share quota pools with production ETL pipelines.
2.  In Google Cloud Console (**IAM & Admin > Quotas & System Limits** for the
    `bigquery.googleapis.com` service), set:
    -   **Query usage per day** (project-wide daily TiB ceiling).
    -   **Query usage per day per user** (per-principal daily GiB/TiB ceiling to
        prevent a single user from exhausting project quota).

### Documented Cost-Control Limitations

Always surface these three platform limits when designing cost governance:

1.  **On-demand billing only**: `bigQueryMaxBilledBytes` and BigQuery daily
    query-usage quotas govern **on-demand** bytes-billed pricing. They do
    **not** cap spend on **BigQuery Editions / slot reservations** (where
    compute is governed by reservation baseline/autoscale max slots and query
    queues).
2.  **No per-agent quotas**: BigQuery quotas apply per project or per user, not
    per `data_agent_id`. Isolating an agent in its own GCP project is the
    supported way to enforce an agent-specific daily ceiling.
3.  **No per-agent BigQuery job labels**: Conversational Analytics does not
    attach custom BigQuery job labels per agent, so you cannot slice
    `INFORMATION_SCHEMA.JOBS` billing by label alone without project isolation
    or per-agent BigQuery Agent Analytics trace tables.

## 4. Table Impact, Exposure Strategy, and Light Anomaly Detection

### How Agent Queries Affect Underlying Tables

-   **Read-only execution**: BQCA generates and executes read-only `SELECT`
    queries. It does not execute DML (`INSERT`, `UPDATE`, `DELETE`, `MERGE`) or
    DDL (`CREATE`, `ALTER`, `DROP`) against your tables.
-   **End-user credential pass-through**: Queries execute using the **calling
    end user's IAM identity**, not an elevated shared service account. BigQuery
    row-level access policies (RLS), column-level security (CLS) policy tags,
    and dynamic data masking rules apply automatically per caller, and query
    slots/bytes are billed to the execution project.

### Which Tables to Expose (and Avoid)

Prefer exposing                                                                                                    | Avoid exposing directly
:----------------------------------------------------------------------------------------------------------------- | :----------------------
Curated, denormalized star-schema fact and dimension marts (`fct_*`, `dim_*`)                                      | Raw ingestion/landing tables, CDC changelogs, or wildcard `_TABLE_SUFFIX` shards
Date/timestamp-partitioned and key-clustered tables (with `require_partition_filter = true` on multi-TB facts)     | Unpartitioned multi-TB event logs where a missing `WHERE` clause scans the full table
Curated or authorized views that project only clean business columns and pre-apply safe status/soft-delete filters | Wide tables carrying raw `JSON`/`BYTES` blobs, unmasked PII, or deprecated legacy columns with misleading names

When underlying tables suffer from missing partition keys, poor clustering, or
expensive view chains, apply the `bigquery-optimization` skill before exposing
them to an agent.

### Supporting Light Anomaly Detection and Forecasting

You have two complementary patterns depending on whether anomalies should be
computed in-memory over small query results or natively inside BigQuery at
scale:

1.  **Sandboxed Python analysis (`options.analysis.python.enabled: true`)**
    -   Enables the agent's managed Python analysis step so it can compute
        rolling z-scores, IQR outliers, week-over-week deltas, and charts over
        aggregated SQL result sets.
    -   Keep SQL aggregations coarse (for example, daily or weekly series)
        before passing rows to Python. Treat any agent-generated Python code
        exported into notebooks or pipelines as untrusted until reviewed in an
        isolated sandbox.
2.  **BigQuery AI/ML functions via `bqRoutines` or `exampleQueries`**
    -   For native time-series anomaly detection and forecasting directly in
        BigQuery, expose clean daily/hourly metric tables or views and wire
        verified templates or TVF wrappers using `AI.DETECT_ANOMALIES`,
        `ML.DETECT_ANOMALIES`, `AI.FORECAST`, or `ML.FORECAST` in
        `Context.exampleQueries` or `Context.userFunctions.bqRoutines`.
    -   For detailed syntax, model options, and TimesFM (`AI.DETECT_ANOMALIES` /
        `AI.FORECAST`) best practices, consult the `bigquery-ai-ml` skill.
