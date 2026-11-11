---
name: discover-assets
description: >-
  Finds and inspects data assets within Google Cloud. Use for any question that
  needs to discover data sources or find/inspect schemas, metadata, or domain
  rules for tables. Relevant when: (1) finding, exploring, or inspecting GCP
  data assets; (2) retrieving schemas, metadata, or governance policies for a
  GCP data asset (including a named table); (3) you have a keyword or topic
  (e.g., "sales data") without a table or resource ID; (4) the user asks for
  enterprise data, metrics, tables, datasets, analytics, business terms,
  financial reports, or industry statistics (e.g., banking, e-commerce, transit,
  SEC filings, solar, healthcare) without full table schemas. Don't use for
  general knowledge questions unrelated to data, or when both explicit table
  schemas and full SQL are already provided.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

<!-- disableFinding(LINE_OVER_80) -->

# Knowledge Catalog Skill

## Overview

Discover enterprise data assets (tables, datasets, views, data products, files),
surface domain context (authoritative data sources, business definitions, metric
formulas, data-quality rules, and verified enterprise metadata), and inspect
schemas, column descriptions, and systems of record using Knowledge Catalog MCP
tools (`search_entries` and `lookup_context`).

If the catalog returns no match after fallbacks, report that honestly; never
invent a business definition, metric formula, table, or SQL from prior
knowledge. Empty is a valid answer.

*   **PARALLEL SEARCH REQUIREMENT**: For open-ended discovery when the user has
    not already named the exact `<project>.<dataset>.<table>` (see **Step
    0.5**), you MUST invoke `search_entries` **4 times in parallel** (2
    `parent_entrygroup_type=context-set` variations + 2 broad semantic domain
    variations). When an asset or short table name is already provided, follow
    the **Step 0.1–0.4** fast paths instead.
*   **CRITICAL — MANDATORY FULL WORKFLOW**: You MUST execute and complete the
    Knowledge Catalog discovery workflow without interruption, prioritizing and
    looking up Context Set entries discovered in Step 2 first in Step 3A for
    authoritative domain context before choosing any table. For pure
    asset/metadata discovery questions or when invoked by another skill (e.g.,
    Spark, Dataform, dbt, or Notebook workflows) to locate assets or inspect
    schemas, **stop after Step 3** and return the discovered entry names,
    schemas, and domain context without executing SQL in Step 4; when answering
    a data-analysis question that requires querying data directly, complete
    Steps 1–4 to resolve the source contract before executing the query.

## Tool Execution

Invoke the Knowledge Catalog MCP tools directly:

```json
search_entries {"project_id": "<project_id>", "query": "customer orders revenue transactions"}
lookup_context {"project_id": "<project_id>", "location": "us", "resources": ["projects/<project_id>/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/<project_id>/datasets/sales_ds/tables/orders"]}
```

*(Fallback for CLI-only environments where Knowledge Catalog MCP tools are not
loaded: use `gcloud dataplex entries search "<QUERY>" --project="<project_id>"
--semantic-search --limit=50` and `gcloud dataplex context lookup
--project="<project_id>" --location="<location>"
--resources="<FULL_ENTRY_NAME>"`.)*

## Instructions

### Step 0: Fast Path When the User Names a Specific Table or Asset

Before running the 4-query discovery search in Steps 1–2, check whether the
asset was already identified and pick the shortest path that fits:

*   **0.1. Already in Conversation Context**: If an earlier turn or tool output
    in the current conversation already returned the target entry's full `name`,
    schema, or domain context, reuse it directly — do not re-run
    `search_entries` or `lookup_context` for the same asset and proceed directly
    to your task (writing SQL/code or answering the question).
*   **0.2. Public Datasets (`bigquery-public-data`)**: If the request targets
    `bigquery-public-data` or if the requested asset belongs to
    `bigquery-public-data`, skip `search_entries` and `lookup_context` entirely
    and inspect the table directly using BigQuery MCP tools (`get_table_info`,
    `list_table_ids`) or the `bq` CLI (`bq show`).
*   **0.3. Known Table or Asset Identifier**: If the user or calling skill
    already provides a specific table or asset identifier (e.g.,
    `project.dataset.table`, `catalog.namespace.table`, or `schema.table`),
    **skip the 4-query parallel search in Step 1**. Run **1 targeted
    `search_entries` call** with `"query": "name:<table>"` (adding
    `projectid:<project>` only if the first segment is a known GCP project ID,
    or `system=<SYSTEM>` if the system is known) to obtain the exact
    `dataplex_entry.name`, call `lookup_context` on it (Step 3), and then
    proceed directly to Step 4 or return the schema/metadata directly if no SQL
    query is needed. *(Skip Step 1 and Step 2.)*
*   **0.4. Known Short Table Name Only (`table_name` without dataset)**: *(Skip
    Step 1 and Step 2, call `search_entries` as shown below, and proceed
    directly to Step 3.)*
    *   **Engineering / pipeline / schema-only tasks** (e.g., Spark, dbt,
        Dataform, notebook scaffolding, or simple schema inspection where no
        business metric formula is needed): Call `search_entries` once to locate
        the table, then proceed directly to Step 3B (`lookup_context` on the
        matched table): `search_entries {"project_id": "<project_id>", "query":
        "name:<table_name> projectid:<project_id>"}` *(omit
        `projectid:<project_id>` if the target table may live in another
        project)*.
    *   **Business metric, KPI, financial/operational calculation, or domain
        rule questions**: Call `search_entries` twice in parallel — 1 targeted
        table search + 1 Context Set search using 2–3 space-separated domain
        nouns from the prompt (no `AND`/`OR` operators) — then proceed to Step
        3A:
        1.  `search_entries {"project_id": "<project_id>", "query":
            "name:<table_name>"}`
        2.  `search_entries {"project_id": "<project_id>", "query": "<2-3 domain
            keywords> parent_entrygroup_type=context-set"}` *(e.g.,
            `"orders revenue parent_entrygroup_type=context-set"`)*
*   **0.5. Open-Ended / Natural-Language Discovery (No Table Name Provided)**:
    When the user asks a business, analytics, or discovery question without
    naming a specific table, proceed to **Step 1 and Step 2** and execute the
    full 4-parallel `search_entries` workflow (2
    `parent_entrygroup_type=context-set` queries + 2 broad semantic queries).

### Step 1: Semantic Decomposition & Generating Variations

Analyze the user's natural language request, break it down into semantic
components, and construct valid Knowledge Catalog search queries. Do not just
search for raw user text.

*   **1.1. Semantic Decomposition**: Read the user request carefully. Break it
    down into semantic components: identify core entities, required metrics, and
    critical scope constraints (projects, locations, etc.). **Do not add
    `system`, `type`, or `column` filters by default** so data and domain
    context can be searched across different data sources.
*   **1.2. Think Like a Data Engineer**: Users ask high-level business
    questions; translate business concepts into how data is actually stored in
    database terminology (e.g., translate "orders and receipts" to
    "purchase_orders", "bookings", "receipts", "drops", or "consignments").
*   **1.3. Construct Search Queries**: Build **2 DISTINCT natural language query
    variations**:

    *   *Variation 1 (Direct & Synonyms)*: Core search terms combined with
        common domain synonyms.
    *   *Variation 2 (Data Source Translation)*: Translate concepts into
        database schema/column terms as free-text search terms (do not add
        `column:` filters by default unless the user explicitly asks for a
        specific column name).

    From these 2 variations, construct all **4** parallel `search_entries`
    queries for Step 2:

    *   **Queries 1, 2 [MANDATORY 2 Context Set Queries - CRITICAL]**: Append
        ONLY `parent_entrygroup_type=context-set` (requires `=`, never `:`) to
        each variation, with **no other filters** (no `projectid`, `system`,
        `type`, `column`, `parent`, etc.). These return **Context Set child
        entries** directly in a single turn.
    *   **Queries 3, 4 [MANDATORY 2 Broad Domain Variations - DO NOT SKIP]**:
        Search broadly across the catalog with the same 2 variations, appending
        only explicit user scope predicates from Step 1.4 (such as
        `projectid:`). Never execute only 1 or 2 queries total; all 4 parallel
        searches are required.
*   **1.4. Extract Predicates & Tool Arguments**: Map explicit scope keywords in
    the request (such as project ID or location) to valid predicates (see the
    **Predicate Reference** below).

    *   **`project_id` tool parameter (REQUIRED)**: Always pass
        `"project_id": "<project_id>"` in every `search_entries` and
        `lookup_context` tool call for consumer GCP project billing and
        attribution.
    *   **`projectid:` query predicate**: To filter search results to a specific
        GCP project ID, append `projectid:<project>` inside `"query"` ONLY on
        the 2 broad queries (Queries 3 & 4). Never add `projectid:` to the
        Context Set queries (Queries 1 & 2).
    *   **`location` handling**: If the user explicitly provides a `location`,
        append `location=<location>` inside `"query"` on the broad
        `search_entries` calls, and pass `"location": "<location>"` in the tool
        arguments for `lookup_context`.
*   **1.5. Format Constraints & Syntax Guardrails**:

    *   **Do Not Add `system`, `type`, or `column` Filters by Default**: Do not
        add query filters that restrict by `system`, `type`, or `column` by
        default in Step 2 so that data and domain context can be searched across
        different data sources (e.g., BigQuery, BigLake, Spanner, Cloud SQL,
        AlloyDB, Vertex AI, filesets, and custom context entries). Express
        column names, asset types, or source systems as plain free-text keywords
        unless the user explicitly asks for a specific column name, system, or
        asset type. **NEVER** include `system`, `type`, or `column` filters in
        Context Set queries (`parent_entrygroup_type=context-set`) or in Step 3B
        when searching for a rules-sheet-named table.
    *   **Keep Natural Language Query Clean & Unparenthesized**: Keep the
        natural language query clean and unparenthesized. Do NOT wrap natural
        language search terms or query variations in parentheses (e.g., never
        write `(customer orders revenue transactions)`).
    *   **Parentheses Reserved for Disjunctions**: Reserve parentheses strictly
        for predicate value disjunctions using `|` (e.g., `projectid:(p1|p2)`).
    *   **Wildcards Are NOT Supported**: Do NOT write
        `name:projects/<project>/locations/<location>/entryGroups/<group1>/entries/*`
        or `projectid:sales_*`. The colon (`:`) operator is already a native
        substring match.
    *   Concatenate scope predicates directly with the clean natural language
        query without unnecessary outer parentheses (e.g., `{"project_id":
        "<project_id>", "query": "customer orders revenue transactions
        projectid:finance-prod"}`).
    *   Do NOT use double quotes in free-text query parts.
    *   Use space separation (implicit AND) between natural language terms and
        predicates. If explicit logical operators (`AND`, `OR`) are used, they
        must be uppercase.
    *   Use hyphen (`-`) for negation (e.g., `-name:test`, `-name:staging`).

### Step 2: Parallel Discovery Search (Context Set & Broad Search)

Execute all 4 `search_entries` calls **simultaneously in parallel in a single
turn (never just 1 or 2)**:

```json
search_entries {"project_id": "<project_id>", "query": "<query_variation_1> parent_entrygroup_type=context-set"}
search_entries {"project_id": "<project_id>", "query": "<query_variation_2> parent_entrygroup_type=context-set"}
search_entries {"project_id": "<project_id>", "query": "<query_variation_1>"}
search_entries {"project_id": "<project_id>", "query": "<query_variation_2>"}
```

### Step 3: Two-Pass Context Lookup (`lookup_context`)

Documentation is read first and decides; table metadata is read second and must
agree with it.

*   **Prioritize Context Set Entries for Lookup (CRITICAL)**: Look up Step 2
    Context Set entries (`dataplex_entry.entry_type` ending in
    `/entryTypes/document`, under a custom `entryGroups/<group>`, not a system
    entry group `@<system>`) naming the question's business entities FIRST in
    Step 3A before any table is chosen—they are the independent authority for
    sources, definitions, and rules.
*   **If No Context Set Entries Match an Entity**: Do NOT run a second search
    turn; in Step 3A, use the broad search-result descriptions of data assets
    returned in Step 2 as the domain documentation for any uncovered entity.

**Lookup cap**: look up at most 3 entries in total per question with
`lookup_context`, counted across both passes and all calls; every entry looked
up is added to the context. Spend them only on entries the answer will use, in
this order: Context Set entries that name one of the question's business
entities; then each entity's documented source; then a bridge table the join
needs. Never look up a table already ruled out from its search-result
description. Beyond the cap, use what the search results already show. The
follow-up in Step 3C is the only exception to this cap.

#### 3A. Rules pass — read the domain documentation

Look up the Context Set entries and other documentation entries (glossary or
guidance entries) that cover the question's domains, within the lookup cap
above. From them write a short **rules sheet**, quoting the text:

*   per business entity (from Step 1.1): the **documented source** — the table
    the documentation designates for that entity in the system that holds the
    question's data — and any tables the documentation says not to use;
*   documented join keys between systems;
*   documented dedup / resolution / normalization rules;
*   documented meanings of status values, effective dates and time windows.

If a table's description directs you to another table, use the table it points
to. Mark any item the documentation does not settle as `open`.

#### 3B. Candidate pass — read the tables

For EACH entity, look up only the table you will query, within the lookup cap
above. If the table the rules sheet names was not in the search results, run ONE
more `search_entries` call for it first (NEVER include `system`, `type`, or
`column` filters in this search). For `open` entities, decide from the
descriptions and lineage; if still tied, see Step 4 item 1. Read each looked-up
table's own notes for data-quality rules (duplicates, latest-record-wins, soft
deletes) and add them to the rules sheet.

*   **Data Products are valid lookup candidates**: Entries with
    `dataplex_entry.entry_type`
    `projects/dataplex-types/locations/global/entryTypes/data-product` are Data
    Products: curated, owner-certified bundles of the domain tables and datasets
    for a business area. Treat them as lookup candidates even though their
    `fully_qualified_name` is empty and they are not table entries. Pass their
    `dataplex_entry.name` (e.g.,
    `projects/<project>/locations/<location>/entryGroups/@dataplex/entries/projects/<project>/locations/<location>/dataProducts/<id>`)
    to `lookup_context` unchanged.
*   **Entry Name**: Pass `dataplex_entry.name` (the catalog entry identifier) in
    the `resources` parameter of `lookup_context`.
*   **Filter with structured fields** (`dataplex_entry.entry_type`,
    `dataplex_entry.entry_source.resource`,
    `dataplex_entry.entry_source.system`), never regex on entry names.
*   **Dynamic Location Resolution (CRITICAL)**: Use the exact `<location>`
    segment of each entry name (`projects/<project>/locations/<location>/...`,
    or `dataplex_entry.entry_source.location`); Context Set entries and tables
    may differ, so never hardcode `"us"` or `"global"`. All resource entry paths
    passed in a single `lookup_context` call MUST belong to the same
    `<location>`. Within each pass, make ONE `lookup_context` call per location
    and emit all calls of the pass in parallel in a single turn:

```json
lookup_context {"project_id": "<project_id>", "location": "<location>", "resources": ["projects/<project>/locations/<location>/entryGroups/<group>/entries/<entry_1>", "projects/<project>/locations/<location>/entryGroups/<group>/entries/<entry_2>"]}
```

*   **Empty `{}` Response Means Wrong `location`**: If `lookup_context` returns
    an empty `{}` object with no error, the `"location"` parameter did not match
    the entry's actual region. Extract the exact `<location>` segment from the
    entry path (`projects/<project>/locations/<location>/...`, or run a `name:`
    search if the entry path was constructed manually) and retry
    `lookup_context` once with that location.
*   **Stop Immediately on `PERMISSION_DENIED` or `SERVICE_DISABLED`**: If
    `search_entries` or `lookup_context` fails with `PERMISSION_DENIED` or
    `SERVICE_DISABLED`, stop immediately without retrying search variations;
    report the missing permission (`dataplex.projects.search`,
    `dataplex.entries.get`, or `roles/dataplex.catalogViewer`) or disabled API
    (`dataplex.googleapis.com`). If an asset exists in GCP but is not yet
    indexed in the catalog, you may fall back to native inspection (`bq show`,
    `gcloud spanner databases ddl describe`, `gcloud storage ls`).

If an entity still has no confident candidate after 3B, run ONE targeted
`search_entries` call for it (e.g., by `name:` or its join key with `column:`)
and look up the result, within the lookup cap.

#### 3C. Using Data Product Context (CRITICAL)

When a Data Product
(`projects/dataplex-types/locations/global/entryTypes/data-product`) is looked
up—or when the lookup response's `relatedResources` lists a Data Product
(`type: Data Product`, `catalogEntry` ending in `/dataProducts/<id>`)—use its
context to choose the tables for SQL:

*   **3C.1. Use Data Product Assets as the Curated Domain Candidates**:
    *   If a Data Product was looked up, its response returns
        `dataProduct.assets` (curated tables and datasets for the domain) and
        `relatedResources` (full name, description, and schema of each table
        asset). Use these curated assets as your primary candidates when they
        cover the entities in the request.
    *   If the lookup response's `relatedResources` lists a Data Product
        (`type: Data Product`, `catalogEntry` ending in `/dataProducts/<id>`)
        matching the request's domain, only count a table as a curated asset of
        that Data Product when its `dataProduct.assets` lists the table (or when
        the lookup call had a single resource)—prioritize those curated assets
        as primary candidates for SQL over competing tables outside the Data
        Product.
*   **3C.2. Resolve Ambiguous Table Candidates Using Membership & Metadata**:
    When multiple tables appear to cover the same entity, compare their catalog
    descriptions, grain, and Data Product membership against the user's request:
    prefer the table included in the domain's Data Product whose description and
    grain match the user's request over tables outside the Data Product.
*   **3C.3. Dataset Assets**: If a Data Product asset is a whole dataset rather
    than individual tables, its tables are not expanded. Run ONE scoped
    `search_entries` call inside it (`<core terms> parent:<dataset>`, with no
    `system`, `type`, or `column` filters), apply 3C.2 to the returned tables,
    and issue ONE follow-up `lookup_context` call on the table whose description
    and grain best match the user's request.
*   **3C.4. Limits**: At most ONE follow-up search and ONE follow-up lookup call
    (3C.3) per request.
*   **3C.5. Fallback**: If a needed table or column is not in the Data Product's
    assets, you may use broad-search candidates.

### Step 4: Resolve a Source Contract Before Any SQL

*(Apply Step 4 only when generating or executing SQL to answer a data question;
if you only need asset IDs and schemas for a calling skill such as Spark,
Dataform, dbt, or Notebook setup—or for a pure discovery request—stop after Step
3 and return the discovered metadata.)*

Read the lookup payloads and write this contract explicitly, one line per item,
citing the metadata that supports each. SQL must follow it.

Probe and check queries bill the user's BigQuery project: keep each one to the
question's time window and include the partition filter on partitioned tables
(tables that require one reject queries without it).

1.  **Source per entity**: the documented source, i.e. the table the 3A rules
    sheet names for the entity. A table's claim to be authoritative never
    overrides the rules sheet. Only for `open` entities, prefer the curated
    asset chosen in Step 3C; otherwise decide by lineage direction (upstream
    over derived) and freshness/deprecation notes; if still tied, run one cheap
    probe per candidate (row count, distinct keys, max date) and prefer the
    current, complete one. If entities live in different systems, use each
    system's own authoritative table; do not substitute a single table that
    merely contains similar columns.
2.  **Join path**: the documented shared key between the chosen sources (and any
    bridge table needed). Note key format differences to normalize.
3.  **Data-quality rule**: any documented dedup, latest-record-wins,
    normalization (case, whitespace, ID format, currency/unit) or reconciliation
    rule for ANY table the SQL touches (including joined lookup / dimension
    tables) — quote it. Guard: the SQL applies each rule in its own cleaning CTE
    per table, BEFORE any join, filter or aggregate (e.g. end the CTE with
    `QUALIFY ROW_NUMBER() OVER (PARTITION BY <documented key> ORDER BY
    <documented tie-break>) = 1`, never put a window function in `WHERE`;
    normalize join keys on both sides). Before the final answer, run one check:
    each cleaning CTE has `COUNT(*) = (SELECT COUNT(*) FROM (SELECT DISTINCT
    <key> FROM cleaning_cte))` at its documented grain. If not equal, the rule
    is not applied — fix the SQL; never answer from uncleaned rows. If the raw
    table has duplicate keys and no rule is quoted, re-read its column and table
    descriptions for one before choosing how to resolve them.
4.  **Business filters**: the documented meaning of status values, effective /
    valid-from-to dates, and the exact time window and boundaries the question
    implies. Check actual distinct status values before filtering.
5.  **Population**: if the question says all / every / rank all, return the
    complete set — no `LIMIT`, sample or top-N.
6.  **Answerability**: if a required entity, attribute or time period does not
    exist in the catalog or data, say the data cannot answer it and why. Do not
    approximate with a proxy.

Then pass the contract, with the full untruncated lookup payloads (schemas,
column descriptions, aspects, overview, data-quality notes, join keys), to SQL
generation. After running the SQL, confirm the result matches every contract
line before giving the final answer.

## Predicate Reference

Strictly adhere to official Knowledge Catalog operator syntax when appending
predicates to `query`. **Exact-match predicates require `=`; substring and
hierarchy predicates require `:`** (never add `system`, `type`, or `column`
filters by default in Step 2 or in Context Set queries; see Step 1.5).

*   **`parent_entrygroup_type`** — **Operator**: `=` | **Syntax**:
    `parent_entrygroup_type=context-set` | **Rule**: Matches Context Set child
    entries; append ONLY this predicate to Queries 1 & 2 in Step 2.
*   **`system`** — **Operator**: `=` | **Syntax**: `system=BIGQUERY`,
    `system=CLOUD_SQL`, `system=CLOUD_SPANNER`, `system=(BIGQUERY|BIGLAKE)` |
    **Rule**: Matches source system (`BIGQUERY`, `BIGLAKE`, `CLOUD_SQL`,
    `CLOUD_SPANNER`, `ALLOYDB`, `STORAGE`, `CLOUD_BIGTABLE`, `CLOUD_PUBSUB`,
    `VERTEX_AI`; case-insensitive); use ONLY when user names a system.
*   **`type`** — **Operator**: `=` | **Syntax**: `type=TABLE`,
    `type=(TABLE|VIEW)`, `type=DATA_PRODUCT` | **Rule**: Matches asset type
    (`TABLE`, `VIEW`, `DATASET`, `DATA_PRODUCT`, `storage-bucket`,
    `storage-folder`); use `type=DATA_PRODUCT` when asked for a Data Product.
*   **`location`** — **Operator**: `=` | **Syntax**: `location=us-central1` |
    **Rule**: Exact match on resource location inside `query`.
*   **`labels`** — **Operator**: `=` | **Syntax**: `labels.env=prod` | **Rule**:
    Exact match on resource labels (`label.<key>=<value>` in CLI keyword mode).
*   **`aspect`** — **Operator**: `:` and `=` | **Syntax**:
    `aspect:governance.tier=RESTRICTED` | **Rule**: Exact match on aspect field
    (`aspect:<type>.<field>=<value>`).
*   **`has`** — **Operator**: `:` | **Syntax**:
    `has:dataplex-types.global.overview` | **Rule**: Checks existence of an
    attached aspect type (`has:<aspect_type>`).
*   **`parent`** — **Operator**: `:` | **Syntax**: `parent:thelook_ecommerce` |
    **Rule**: Scopes search to a BigQuery dataset (`parent=` is invalid).
*   **`projectid`** — **Operator**: `:` | **Syntax**: `projectid:finance-prod`,
    `projectid:(p1|p2)` | **Rule**: Filters to GCP project IDs inside `query`
    (also pass `"project_id"` in tool args).
*   **`column`** — **Operator**: `:` | **Syntax**: `column:customer_id`,
    `column:(id1|id2)` | **Rule**: Substring match on column names; use ONLY
    when user asks for a column name or in Step 3B join-key fallback.
*   **`name`** — **Operator**: `:` | **Syntax**: `name:orders_daily` | **Rule**:
    Substring match on entry resource name.
*   **`description`** — **Operator**: `:` | **Syntax**: `description:orders` |
    **Rule**: Substring/free-text match in description (never use `=`).
*   **`displayname`** — **Operator**: `:`, `=` | **Syntax**:
    `displayname:orders`, `displayname="Daily Orders"` | **Rule**: Matches
    display name (`:` for substring, `="value"` for exact).
*   **Negation (`-`)** — **Operator**: `-` | **Syntax**: `-type=MODEL`,
    `-name:test` | **Rule**: Excludes matching entries from results.

## Examples

*   **Query**: *Customer orders and revenue*
    *   **Mapped Context Set Search**: `search_entries {"project_id":
        "<project_id>", "query": "customer orders revenue transactions
        parent_entrygroup_type=context-set"}`
    *   **Mapped Broad Search**: `search_entries {"project_id": "<project_id>",
        "query": "customer orders revenue transactions"}`
*   **End-to-End Context Set Discovery & Prioritized Lookup (Step 2 -> Step
    3)**:

    *   **Query**: *Search for sales data in project finance-prod*
    *   **Turn 1 (Step 2 — 4 Parallel Searches: 2 Context Set Variations without
        other filters + 2 Broad Variations)**:
        *   **Mapped Search 1 (Context Set)**: `search_entries {"project_id":
            "finance-prod", "query": "sales revenue transactions
            parent_entrygroup_type=context-set"}`
        *   **Mapped Search 2 (Context Set)**: `search_entries {"project_id":
            "finance-prod", "query": "sales_amount order_total gross_sales
            parent_entrygroup_type=context-set"}`
        *   **Mapped Search 3 (Broad)**: `search_entries {"project_id":
            "finance-prod", "query": "sales revenue transactions
            projectid:finance-prod"}`
        *   **Mapped Search 4 (Broad)**: `search_entries {"project_id":
            "finance-prod", "query": "sales_amount order_total gross_sales
            projectid:finance-prod"}`
    *   **Turn 2 (Step 3A — Prioritize Context Set Entry in `lookup_context`
        using its own `"location"`, before looking up candidate tables in Step
        3B)**:

        ```json
        lookup_context {
          "project_id": "finance-prod",
          "location": "<context_location>",
          "resources": ["projects/finance-prod/locations/<context_location>/entryGroups/sales-commerce-context-set/entries/<context_entry>"]
        }
        ```
*   **Query**: *Find customer analytics data in region europe-west1*

    *   **Mapped Search**: `search_entries {"project_id": "<project_id>",
        "query": "customer analytics metrics location=europe-west1"}`
