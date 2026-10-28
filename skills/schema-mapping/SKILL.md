---
name: schema-mapping
license: Apache-2.0
metadata:
  version: v2
  publisher: google
description: >-
  Guides the process of analyzing, mapping, and documenting transformations between source and target schemas for any database, data warehouse, or data platform. Focuses exclusively on creating a high-fidelity mapping plan (Mapping Manifesto).
  Used when initiating an ETL, ELT, or data integration task with schema mapping specification for multiple tables (i.e. more than 3 tables) before writing code.
  Do NOT use this skill for basic SQL generation without mapping requirements, or when the user already has a complete mapping specification.
---

# Skill: Semantic Schema Mapping Planning

Follow this structured process and procedures for analyzing source-to-target
data relationships and creating a high-fidelity **Mapping Plan** (also known as
a **Mapping Manifesto**). This process is platform-agnostic and should be used
before generating any target-specific pipeline code. When this skill is loaded,
you MUST use this plan and replace the existing generic plan.

## When to Use

Use this skill when:

-   You need to map schemas between a source dataset/database and a target
    destination database/warehouse.
-   You are initiating an ETL, ELT, or data integration task.
-   You need to identify schema gaps, data type conflicts, or aggregation
    requirements.

--------------------------------------------------------------------------------

## Required Input Variables

Before creating the plan, you must obtain or request:

1.  **`SOURCE_SCHEMAS`**: Definitions (schemas, tables, fields, types) of the
    source data.
2.  **`TARGET_SCHEMAS`**: Definitions of the desired target/destination schemas.
3.  **`BUSINESS_CONTEXT`**: Domain details, business rules, or use case
    description.
4.  **`TARGET_PLATFORM`**: The database or execution engine (e.g., BigQuery,
    Snowflake, Postgres, Spark, Beam).

## Optional Input Variables

1.  **`KNOWLEDGE_GRAPH`**: If there's a knowledge graph / property graph
    available, always inspect the graph for node table definitions, edge table
    definitions, and foreign key bindings (`SOURCE` / `DESTINATION` key
    references), etc.

--------------------------------------------------------------------------------

## The Schema Mapping Planning Procedure

> [!IMPORTANT] **Execution Strategy: Table-by-Table Iteration**
>
> You MUST execute this procedure **iteratively, one target table at a time**.
> For each individual table in the `TARGET_SCHEMAS`, complete Steps 1 through 6
> sequentially before moving to the next table. Do not attempt to map or
> summarize multiple tables in a single batch, as this leads to hallucinations,
> overlooked constraints, and context window bloat.

### Step 0: Discover the Semantic Model (Mandatory, Once Per Task)

A governed semantic model (`OSI+G`) may exist for the source or target data.
Before inspecting raw schemas, sampling data, or asking the user for business
rules, run **@skill:semantic-ontology-context** to find it (local workspace,
then Dataplex Knowledge Catalog). If a model or Context Set is found, use its
entities, relationships, metrics, and `ai_context` as authored throughout
Steps 1–6 and cite it in the Mapping Manifesto. Do not skip this step because
the table names are already known.

### Step 1: Semantic & Terminology Translation

Analyze the entity names and attributes in the `SOURCE_SCHEMAS` against the
`TARGET_SCHEMAS`.

1.  **Synonym Resolution**: Using the `BUSINESS_CONTEXT`, map matching concepts
    with different names (e.g., `client_id` vs `customer_num`).
2.  **Identify Domain Standards**: Match field values or formats to known
    standards (e.g., ISO country codes, currency codes, UN/LOCODE, UUIDs) based
    on the business context.
3.  **Verify Domain Semantics**: Do not rely purely on lexical matching (name
    similarity). Verify the functional business purpose of the entities in both
    schemas. Ensure that a target table representing a specific business
    resource maps to a source table modeling that same resource rather than an
    unrelated administrative log or generic list table sharing a similar name.

### Step 2: Establish the Anchor Table

For each table or collection in the `TARGET_SCHEMAS`:

1.  Identify the **primary source table** (the "Anchor Table") that holds the
    core records for this target.
2.  Identify **contributing/lookup tables** in the source that will enrich the
    target records.
3.  **Prefer Structured Tables over Generic Key-Value Tables**: If the same
    attribute exists in both a structured column in a domain table and as a
    generic property in an Entity-Attribute-Value (EAV) key-value/properties
    table, always anchor on the structured table to ensure schema stability and
    performant joins.

### Step 3: Proactive Data Sampling & Inspection

If a target field mapping is ambiguous or schema types do not tell the whole
story (e.g., verifying if a timestamp is ISO-8601, if a string is a JSON array,
or checking the distribution of values):

1.  **Proactive Inspection**: If environment access allows, run
    platform-specific queries (e.g., `SELECT ... LIMIT 10`, `SELECT
    COUNT(DISTINCT ... )`) to sample values.
2.  **User Inquiry**: If direct access is not possible, output sample queries
    and ask the user to provide the output to confirm assumptions before
    finalizing the plan.

### Step 4: Perform Field-Level Gap Analysis & Cleanliness Design

Evaluate every column in each target table to determine its source mapping.
Categorize mappings and plan cleanliness transformations:

*   **Direct Mapping**: A 1-to-1 match.
*   **Derived Mapping**: Requires type casting, string manipulation, date
    formatting, mathematical derivation, or case statement logic.
*   **Joined Mapping**: Requires looking up values from contributing tables
    using defined join keys.
*   **Aggregated Mapping**: Requires collapsing 1-to-many relationships (e.g.,
    calculating `SUM`, `COUNT`, `ARRAY_AGG` or string concatenation).
*   **Gaps (Unmapped fields)**: Target fields that do not exist in the source.
    *   **Constraint Checking**: Verify whether the target column has a `NOT
        NULL` or `REQUIRED` constraint in the target schema.
    *   **Handling Nullable Gaps**: If the target column is nullable, explicitly
        flag it as `NULL` or define a default value.
    *   **Handling Non-Nullable Gaps**: If the target column is `NOT NULL`, you
        MUST NOT map it to `NULL`. *(Rationale: Mapping NOT NULL target columns
        to NULL will cause execution-time database constraint violations and
        pipeline failures).* You must identify a source field to derive it from,
        default it to a valid non-null placeholder (e.g., `'UNKNOWN'`, `0`, or
        default dates), or define logic to generate a valid unique reference.

#### Universal Data Cleanliness Rules to Incorporate in Mappings:

1.  **Null Standardization**: Map source strings like `"NULL"`, `"None"`,
    `"N/A"`, or empty spaces to true database `NULL` values.
2.  **Trim & Casing**: Plan to trim leading/trailing whitespaces. Convert
    standardized codes (e.g., ISO codes, status strings) to uppercase.
3.  **Temporal Consistency**: Plan to parse all source timestamps into standard
    ISO-8601 format (`YYYY-MM-DDTHH:MM:SSZ`) or standard destination `TIMESTAMP`
    format. Plan checks to ensure logical temporal progression (e.g.,
    `start_time <= end_time`).
4.  **Defensive Checks**: Plan checks for strict destination types (e.g.,
    checking if string is a valid number before casting to `DECIMAL`).

### Step 5: Map Relationships & Joins

Specify the logical join path to connect the Anchor Table with all contributing
source tables:

1.  Define the join condition/keys (e.g., `source_order.customer_id =
    source_customer.id`).
2.  Identify join scale properties:
    -   **Large-to-Large**: Joining two high-volume transaction tables.
    -   **Large-to-Small**: Joining a transaction table to a static lookup table
        (ideal for Map-side/Broadcast joins to optimize speed/cost).
3.  Document potential join challenges:
    -   Many-to-many risks or potential duplicate generation.
    -   Type mismatches on join keys (e.g., joining an `INT` column to a
        `STRING` column).
4.  **Model / Graph Validation**: If a semantic model or graph was identified
    in input, cross-reference the proposed join conditions with the model's
    `relationships[]` or the graph's edge table definitions to validate foreign
    key relationships.

### Step 6: Draft the "Mapping Manifesto" (Output Format & Example)

Analyze the schemas and reference the `ONE_SHOT_EXAMPLE` below to structure your
output.

#### ONE_SHOT_EXAMPLE (How to Structure the Mapping Manifesto)

##### Example Source Schemas

```markdown
dataset: my_music_library
style: {id: int, style: string}
band: {name: string, biography: string, style: int}
cd: {name: string, year: int, artist: string, numbers: array<string>}
track: {id: string, number: int, name: string}
```

##### Example Target Schemas

```markdown
dataset: music_standard
artist: {name: string, albums: array<string>}
album: {name: string, year: int, genre: string, tracks: array<string>}
```

##### The Mapping Manifesto (Expected Output Format)

For each target table, document your column-to-column reasoning:

```markdown
# Mapping Plan: `album`
* **Anchor Source Table**: `cd`
* **Join Paths & Optimization**:
    * `cd` JOIN `band` ON `cd.artist = band.name`
    * `band` JOIN `style` ON `band.style = style.id`
    * `cd` JOIN `track` ON `track.id IN UNNEST(cd.numbers)`

### Field Mappings

| Target Field | Source Field / Logic | Mapping Type | Rationale / Transformation Details |
| :--- | :--- | :--- | :--- |
| `album.name` | `cd.name` | Direct | A CD is a physical medium representing an album; direct semantic match |
| `album.year` | `cd.year` | Direct | Direct semantic match for release year |
| `album.genre` | `style.style` | Joined | Resolved via `cd.artist` -> `band.name` -> `band.style` (ID) -> `style.id` -> `style.style` (String) |
| `album.tracks` | `ARRAY_AGG(track.name)` | Aggregated | Aggregation Point: Collapses 1-to-many track IDs in `cd.numbers` into an array of track names |
```

--------------------------------------------------------------------------------

## Critical Operational Rules

*   **Plan Before Execution**: You MUST NOT generate any ETL code,
    target-specific pipeline configurations, or migration scripts until the
    Mapping Manifesto has been presented to and approved by the user.
    *(Rationale: Establishing clear mapping logic first prevents coding errors,
    avoids circular dependencies, and ensures user alignment on semantic
    mappings before wasting resources on implementation).*
*   **Strict Schema Grounding**: Every source table and field name referenced in
    the mapping plan MUST exactly match the names and data types present in the
    provided `SOURCE_SCHEMAS`. You MUST NOT reference non-existent columns,
    guess field names, or make assumptions about source schemas without
    explicitly confirming them in the schema definitions. *(Rationale: Proposing
    guesses leads to compilation errors and invalid mapping specifications).*
*   **Target Schema Constraint Integrity**: You must never propose a mapping
    that writes `NULL` to a column defined as `NOT NULL` or `REQUIRED` in the
    `TARGET_SCHEMAS`.
*   **Exhaustive Field Search**: Before declaring a target field as an "Unmapped
    / Gap", search all available source schemas to verify the data is not in a
    less-obvious table. *(Rationale: Lazy mappings that default target fields to
    NULL lead to downstream data loss and incomplete pipelines).*
*   **Defensive Type Mapping**: Explicitly plan the transformation rules for
    strict destination types (e.g. `TIMESTAMP`, `BOOLEAN`, `DECIMAL`) to avoid
    load failures. *(Rationale: Different databases and platforms handle type
    validation strictly; pre-planning casts prevents execution-time runtime
    errors).*
*   **Data Integrity Check**: Identify join conditions that could cause
    Cartesian product expansion or data duplication, and note prevention
    strategies in the plan. *(Rationale: Unvalidated joins can distort
    aggregated metrics or exhaust processing memory on large datasets).*
