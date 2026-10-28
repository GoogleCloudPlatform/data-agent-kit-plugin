---
name: discovering-gcp-data-assets
description: |
  Finds and inspects data assets within Google Cloud.
  Relevant when any of the following conditions are true:
    1. The user request involves finding, exploring, or inspecting data assets
       in Google Cloud, such as:
         - BigQuery datasets, tables, or views
         - Dataplex Knowledge Catalog semantic models, entities, metrics, or Context Sets
         - BigLake catalog or tables
         - Spanner instances, databases or tables
         - etc.
    2. You need to retrieve the schema, metadata, or governance policies for a
       GCP data asset.
    3. You have a keyword or topic (e.g., "sales data") but lack the specific
       table or resource ID.
    4. You are attempting to find data using `bq ls`, as this skill offers a
       superior approach.
  Don't use when:
    - Assets are outside Google Cloud
license: Apache-2.0
metadata:
  version: v5
  publisher: google
---

# Instructions

## Step 1: Prioritize Assets from the Conversation

If the asset was created or mentioned earlier in the same conversation, then
proceed with that asset instead of searching. Skip steps 2, 3, and 4.

## Step 2: Handle Public Datasets or Proceed to Search

Dataplex Lookup Context provides the richest metadata for data assets. You MUST
prioritize using it for all Google Cloud assets, even if you already know their
IDs.

-   **Public Datasets (Direct Inspection)**: If the requested asset belongs to
    the `bigquery-public-data` project, Dataplex Lookup Context will fail. You
    MUST skip Steps 3 and 4 and inspect the table directly using the `bq` CLI or
    BigQuery MCP tools instead.
-   **All Other Assets (Proceed to Step 3)**: For all other BigQuery, Cloud
    Storage, Spanner, BigLake Iceberg or general GCP data assets (whether their
    IDs are known or missing), you MUST proceed to **Step 3** to search the
    Dataplex catalog and obtain their full Entry Name.

## Step 3: Execute Discovery Search

You MUST use the Dataplex search command to discover assets and retrieve their
full `projects/...` entry names. This step is required even if you already know
the asset's short ID (e.g., `my_dataset.my_table`), because Step 4 strictly
requires the full entry name.

> [!IMPORTANT]
>
> The `--project` parameter MUST ALWAYS be provided. This project_id is used to
> attribute the search only and does NOT restrict the search scope. The project
> must have the dataplex API enabled and user must have the
> `dataplex.entries.get` permissions.

### A. Semantic Search (Natural Language Intent)

Use this when the user describes the **meaning** or **intent** of the data
(e.g., "Find Q4 product sales data").

Use the `search_entries` MCP tool

OR

```bash
gcloud dataplex entries search "<NATURAL_LANGUAGE_QUERY>" \
  --project="<PROJECT_ID>" \
  --semantic-search \
  --limit=50
```

### B. Keyword Search (Technical Strings)

Use this for exact keyword matches or technical strings (e.g., `name:order_v2`).

#### Search Query Rules (MANDATORY)

-   **Mode-Specific Syntax**:
    -   **Semantic Search**: Logical operators (`AND`, `OR`) MUST be
        **UPPERCASE**. Use plural `labels.` for label filters (e.g.,
        `labels.env=prod`).
    -   **Keyword Search**: Operators are case-insensitive. Use singular
        `label.` for label filters (e.g., `label.env=prod`).
-   **Abbreviated Logic**: Use `|` for OR and `,` for AND within parentheses to
    shorten queries (e.g., `projectid:(prod|staging)` or `column:(id,name)`).
-   **Exact vs. Token Match**:
    -   Use `:` for token/substring matches (e.g., `name:sales`).
    -   Use `=` for exact matches. REQUIRED for `system`, `type`, and
        `location`.
-   **Singular Keywords**: When performing keyword search, ALWAYS convert
    plurals to singular (e.g., "product" NOT "products"). Semantic search
    handles singular/plural variations and synonyms automatically.
-   **Scope Restriction**: You SHOULD restrict the search scope using a `parent`
    filter if the project or dataset is known (e.g.,
    `parent:projects/<PROJECT_ID>`).

#### Dataplex Search Syntax Reference

-   **`name:x`**: Substring/token match on resource ID.
-   **`displayname:x`**: Substring/token match on display name.
-   **`projectid:x`**: Substring/token match on GCP project ID.
-   **`parent:x`**: Substring match on hierarchical path (e.g.,
    `projects/my-proj`).
-   **`location=x`**: Exact match on location (e.g., `us-central1`, `us`).
-   **`column:x`**: Substring/token match on column names in the schema.
-   **`system=x`**: Exact match on source system. Common values: `bigquery`,
    `storage`, `biglake`, `cloud_sql`, `cloud_spanner`, `cloud_bigtable`,
    `pubsub`.
-   **`type=x`**: Exact match on entry type (e.g., `bigquery-table`,
    `storage-bucket`, `storage-folder`).
-   **`labels.key=value`**: (Semantic Mode ONLY) Exact match on a label.
-   **`label.key=value`**: (Keyword Mode ONLY) Exact match on a label.
-   **`createtime[>|<|=]x`**: Match assets created after/before date
    `YYYY-MM-DD`.
-   **`fully_qualified_name=x`**: Exact match on the FQN (e.g.,
    `bigquery:project.dataset.table`).

> [!TIP]
>
> Dataplex search results rely on metadata being ingested into the Universal
> Catalog (often via **Discovery Scans**). If an asset is missing from search,
> it may not be indexed. - **Fallback 1**: Try searching by the
> `fully_qualified_name` qualifier. - **Fallback 2**: Use native tools (e.g.,
> `bq show`, `gcloud storage`) or specific skills for that asset type if you
> already know the ID.

```bash
gcloud dataplex entries search "<KEYWORD_SEARCH_QUERY>" \
  --project="<PROJECT_ID>" \
  --limit=50
```

> [!IMPORTANT]
>
> Handling Search Results and Avoiding Loops:
>
> 1.  **No Results:** If the search returns no entries:
>     *   **Variation Rule:** You may try AT MOST 3 variations of the search
>         query (e.g., switching AND/OR clauses, adding/removing `parent:`,
>         removing `projectid:` or `location:`, trying `fully_qualified_name=`).
>     *   **Stop Rule:** If after 3 attempts no results are found, STOP and
>         inform the user. Ask for clarification, specifically the Dataplex
>         **full entry name** if known, or identifiers such as **project ID**,
>         **dataset ID**, or **instance ID** to help narrow the search. Example:
>         "I couldn't find any tables matching that description after several
>         attempts. If you know the Dataplex full entry name (`projects/...`),
>         please provide it. Otherwise, please provide any identifiers you know,
>         such as project, dataset, or instance name, to help locate the asset."
> 2.  **Multiple Results:**
>     *   If more than 10 results are returned, state that many matches were
>         found. Show the names of the first 5 entries and ask for
>         clarification.
>     *   If 2-10 results are returned and you cannot definitively choose, list
>         them and ask the user.
> 3.  **Single Result:** Proceed to Step 3 with the full entry name.
> 4.  **Avoid Infinite Loops:** MUST NOT re-run identical or near-identical
>     queries. If Dataplex fails to return the expected asset, prioritize asking
>     the user for the exact resource ID or using Fallback 2 (Native Tools).

*Criteria*: Once candidate assets are returned, proceed to Step 4 using the
**full entry names** from the search results.

## Step 4: Lookup Context

You MUST use the **Lookup Context** command to fetch schema and deep metadata
for the relevant results obtained from Step 3.

> [!IMPORTANT]
>
> The `--resources` parameter MUST be the **full name** (starting with
> `projects/`) returned by the search result. Passing short table IDs, GCS URIs,
> or fully qualified `bigquery:` prefixes is PROHIBITED and will fail.

### Command Execution

Use the `lookup_context` MCP tool

OR

```bash
gcloud dataplex context lookup --resources="<FULL_ENTRY_NAME>"
```

*Completion Criteria*: The command returns the detailed schema and business
context.

## Step 5: Semantic Models (When Applicable)

If the task needs a governed semantic model / ontology (`OSI+G`) for the data
in scope — e.g. schema mapping, dbt/ELT pipeline generation, or semantic
modeling — use **@skill:semantic-ontology-context**. It resolves the model
from the local workspace first, then Dataplex Knowledge Catalog, and returns it
as authored.

--------------------------------------------------------------------------------

## Troubleshooting

### Context Lookup Fails or "Resource not found"

-   **Cause**: Short table names were used improperly.
-   **Fix**: Ensure you use the correct entry name format from the search
    results (starting with `projects/`).

### Search Returns No Results

-   **Cause**: Plural terms in keyword search or lack of scoping.
-   **Fix**: Switch to singular keywords. For semantic search, try more
    descriptive natural language.

### Context Lookup Fails with "NOT_FOUND" (despite correct format)

-   **Cause**: The table belongs to a project (e.g., `bigquery-public-data`)
    that has not fully synchronized its metadata with the Dataplex Universal
    Catalog. While the entry appears in search, `context lookup` is unavailable.
-   **Fix**: Fall back to direct inspection using native tools (e.g., `bq` CLI).
-   **Stop Rule:** If the native tool (e.g., `bq show`) also returns "Not
    Found", STOP. Do not restart the Dataplex discovery loop. Specifically ask
    the user to verify the **project ID** and **table ID**.

### Breaking the Research Loop

If you find yourself repeatedly searching for the same asset:

1.  **STOP.**
2.  State what you have tried (e.g., "I tried searching Dataplex with X and Y,
    and checked `bq show`").
3.  Ask the user for the exact project, dataset, and table ID.

### Search Fails with "--project: Must be specified."

-   **Cause**: `--project <PROJECT_ID>` arguments were not provided
-   **Fix**: Provide a project which will be used to authorize and attribute the
    search request.

### Search Fails with "PERMISSION_DENIED"

-   **Cause**: The project_id provided in the `--project <PROJECT_ID>` arguments
    does not have the Dataplex API enabled or the user is missing necessary IAM
    permissions.
-   **Fix**: Ask the user if they have a project which has the Dataplex API
    enabled with the dataplex.entries.get permission
