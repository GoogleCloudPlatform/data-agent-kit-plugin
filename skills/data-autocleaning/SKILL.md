---
name: data-autocleaning
description: Automated data quality and transformation capabilities for Dataform/dbt/BigQuery
  pipelines. Processes data sourced from BigQuery or Cloud Storage (GCS), applying
  best practices for data ingestion, movement, schema mapping, and comprehensive data
  cleaning.
license: Apache-2.0
metadata:
  version: v2
  publisher: google
---

# Data Autocleaning Skill

Automated data profiling, quality assessment, and transformation for data
sourced from **BigQuery** or **Google Cloud Storage (GCS)**.

## When to Use

> [!IMPORTANT]
>
> You **MUST** use this skill for **ANY** task where the source is BigQuery or
> GCS — including seemingly simple operations like "move data" or "copy table".

-   Apply to **all operations** on new and existing sources: copying, moving,
    appending, ingesting, or extracting data.
-   Apply to the **source node** specifically, not to subsequent pipeline steps.
-   **Never skip** Dataplex profiling (Steps 1 and 3). Always use Dataplex —
    **not** ad-hoc BigQuery profiling.

## Task Execution Workflow

### Step 1: Preliminary Checks (Before Implementation Planning)

Perform these checks **before** generating the `implementation_plan.md`.

1.  **Check Eligibility** — You MUST confirm the source is a BigQuery table or
    GCS source.
2.  **Gather Data Profile via Dataplex**:

    -   **GCS sources**: For GCS sources, you MUST create an external table
        first before running the dataplex scan.
    -   **Wait for results**: You **MUST NOT** proceed until the Dataplex
        profile is available, unless user scan approval was denied.
    -   Use the profile as input for cleansing and schema mapping decisions. The
        transformations **MUST NOT** be finalized before profile information is
        available (unless scan was denied).
    -   **Commands**:

        1.  **Obtain user approval**: Present the `scripts/dataplex_scanner.py`
            scan command to the user and obtain explicit approval before
            executing it. Use the following template to present the command:
            -   **Command**: `python3 scripts/dataplex_scanner.py ...` (Fetch
                full arguments from step 6 below)
            -   **Summary**: The script automates Dataplex data profiling. It
                checks table sizes, applies dynamic sampling for large tables
                (>1M rows) to reduce costs, skips empty tables, executes
                concurrent scans for multiple tables, and polls for results
                automatically.
            -   **Value Add**: Enables deep data analysis (null rates, distinct
                values, distributions) allowing data-driven cleansing decisions.
                It helps identify hidden anomalies (garbage values, format
                variance) to guide accurate transformations and verifies that
                the cleaning logic resolves them without introducing
                regressions.
            -   **Scope**: The approval obtained here covers all executions of
                this scanner script for this task (including verification
                steps).
        2.  Run the `scripts/dataplex_scanner.py` script located in the same
            directory as this `SKILL.md` file. This script handles concurrent
            scan creation, dynamic sampling for large tables, and polling for
            results. Use --help to learn more.
        3.  The script will save the full results as JSON files in the specified
            output directory.
        4.  **[!IMPORTANT]** The location MUST be a specific Google Cloud region
            like `us-central1`; multi-regions like `us` are not supported in
            Dataplex scan.
        5.  If there are multiple tables to scan, provide them all in the
            `--tables` argument to run them concurrently.
        6.  Use the following command template:

            ```bash
            python3 scripts/dataplex_scanner.py \
              --tables <project.dataset.table> <project.catalog.namespace.table> \
              --location <location> \
              --output-dir <output_dir>
            ```

            Note: The script accepts table IDs in the format
            `project.dataset.table` for BigQuery tables and
            `project.catalog.namespace.table` for BigLake Iceberg tables.

3.  **Fetch Schema & Samples** — Use `bq` commands to fetch schema and sample
    data for **both** source and destination tables.

### Step 1.5: Implementation Plan Requirements

1.  Your `implementation_plan.md` **MUST** include a **Profiling Evidence**
    section. **Note**: If scan execution was denied by the user, document the
    denial reason here instead of Job IDs.

```markdown
## Profiling Evidence
- [ ] Dataplex Data Profile Job ID: <JOB_ID>
- [ ] Profile Result Summary: <Brief summary of key findings, e.g., % nulls, distinct values>
```

1.  Your `implementation_plan.md` **MUST** include a step to generate cleansing
    SQL transformations based on the profile output and instructions in Step 2:
    Generate Transformations.
2.  Your `implementation_plan.md` **MUST** also reference Step 3 (Quality
    Review) under its **Verification Plan** section.

> [!CAUTION]
>
> **Do not proceed to implementation** until both sections are completed. You
> MUST ensure that the verification phase only validates that your
> transformations successfully addressed the anomalies found in Step 1.

### Step 2: Generate Transformations

#### Schema Alignment

-   Match the destination table schema (types and names) if provided.
-   **Do not** perform column splits, merges, or other schema operations when no
    destination table is specified.

#### Data Cleaning Rules

-   **Garbage Values**: Drop or convert to `NULL` only for malformed data (e.g.,
    unparseable dates, zero-length strings for non-nullable integers).
-   **Unit Normalization**: Standardize measurable units (e.g., `'C'` → `'F'`)
    to the most common unit. If units are too varied (e.g., `mg`, `liter`),
    leave as-is.
-   **Type Conversion**: Use `COALESCE` with `SAFE.PARSE_*` functions for
    multiple date/time/datetime/timestamp formats. Fetch diverse samples when
    source data shows high variance.

#### JSON Data Handling

-   **Parsing**: Use `SAFE.PARSE_JSON` to cast JSON strings to `JSON` type.
    **Never** use deprecated `JSON_EXTRACT_*`.
-   **Extraction**: Flatten or extract fields **only** if a destination schema
    requires it.
-   **Accessors**: Use `JSON_VALUE`, `JSON_QUERY`, `JSON_QUERY_ARRAY`,
    `JSON_VALUE_ARRAY` without `SAFE.` prefix (they are safe by default).
-   **Schema mapping**: When a destination schema is provided, extract JSON
    fields to match target column names and types.
-   **NULL handling**: If `SAFE.PARSE_JSON` returns NULL, keep the original
    string and note the invalid JSON in the cleaning summary.

#### Array Data Handling

-   **Unnesting**: Unnest array fields **only** if a destination schema
    explicitly requires it.
-   **Type Casting**: Attempt to cast elements to the most appropriate common
    type.
-   **CRITICAL**: Filter out `NULL` elements after `SAFE_CAST` (e.g., using
    `ARRAY`) as BigQuery arrays cannot contain `NULL`s.
-   **Normalization**: Only trim whitespace on string fields. Make sure to
    **PRESERVE CASE**. **DO NOT** perform case conversions (e.g., `LOWER()`,
    `UPPER()`) unless explicitly required.
-   **Filtering**: Filter out `NULL` values using
    `ARRAY_FILTER(array_column, e -> e IS NOT NULL)`.
-   **Deduplication**: Use `ARRAY(SELECT DISTINCT x FROM UNNEST(array_column))`
    for case-sensitive deduplication.
-   **Transformations**: Use `ARRAY_TRANSFORM` or `UNNEST`/`ARRAY_AGG` for
    element-wise changes (e.g., date parsing).
-   **Restructuring**: Use `UNNEST` to expand to rows, or `ARRAY_AGG` to group
    rows into an array, as required by the destination schema.

#### STRUCT/Record Data Handling

-   **Extraction**: Extract fields to top-level columns **only** if the
    destination schema requires it.
-   **Type Casting**: Cast each field using `SAFE_CAST` based on the destination
    schema or inferred profile.
-   **Normalization**: Only trim whitespace on string fields. Make sure to
    **PRESERVE CASE**. **DO NOT** perform case conversions (e.g., `LOWER()`,
    `UPPER()`) unless explicitly required.
-   **Field Mapping**: Map directly if structures align; use dot notation (e.g.,
    `struct.field`) to extract; or use `STRUCT()` constructor to group columns.
-   **Schema Alignment**: Populate missing fields with `NULL` and drop fields
    not present in the destination schema.

### Step 3: Quality Review & Profiling

> [!IMPORTANT]
>
> You **MUST** verify transformations strictly using the protocol below before
> completing the task. **Never** skip this step. Use **Dataplex profiling only**
> (unless scan was denied by the user) — not ad-hoc SQL queries.

**Quality review protocol:**

1.  Extract the `SELECT` query containing all generated transformations
    (autocleaning, schema mapping, JSON extractions).
2.  Create a **temporary sample output table** (max 1M rows, 1-hour TTL) by
    running the transformation query.
3.  Fix any runtime errors and re-run until the query succeeds.
4.  **Profile the temporary sample output table using Dataplex**:
    -   **Verify approval**: If scan execution was approved in Step 1, proceed.
        If approval was DENIED in Step 1, DO NOT run the scanner script and DO
        NOT ask the user for approval again. Proceed with manual verification
        using `bq` sample queries to ensure transformations were successful.
    -   Run the `scripts/dataplex_scanner.py` script on the temporary table.
    -   The script will automatically wait for the profile job to finish and
        save the results as JSON.
5.  **Compare profiles** (Skip if scans were denied) — Check the new profile
    against the Step 1 profile for **every transformed column**:

    ```markdown
    | Anomaly Type | Threshold |
    | --- | --- |
    | **NULL increase** | >1% increase compared to source (unless expected) |
    | **Value range shift** | Unexpected ranges or formats |
    ```

6.  **Iterate on anomalies** — For each anomaly:

    1.  **Identify**: Query samples where source is `NOT NULL` but transformed
        value `IS NULL`.
    2.  **Fix**: Update the transformation logic.
    3.  **Repeat**: Re-run Step 3 until the anomaly is resolved.

### Step 3.5: Quality Review Evidence Requirements

Your `walkthrough.md` **MUST** include a **Quality Review Profiling Evidence**
section. **Note**: If scan execution was denied by the user, document the denial
reason here instead of Job IDs.

```markdown
## Quality Review Profiling Evidence
- [ ] Post-Transformation Dataplex Profile Job ID: <JOB_ID>
- [ ] Profile Comparison Summary: <Detailed comparison between initial and final profiles per column>
```

> [!CAUTION]
>
> **Do not** conclude the task or ask for user review until this section is
> filled and the profile comparison is documented.

### Step 4: Documentation

Your `walkthrough.md` must contain a table for each transformation in the
following format:

```markdown
| Field | Description |
| --- | --- |
| **Destination schema considered** | The target column/type being matched |
| **Issue Detected** | What data quality problem was found |
| **Transformation Applied** | The SQL logic used to fix it |
| **Benefit** | Why this transformation improves the data |
```

Include a summary of all quality review steps and profiling evidence.

## Definition of Done

-   All source data quality issues are identified and addressed via SQL
    transformations.
-   Verification MUST be completed using the **Quality review protocol** and
    documented with evidence.
-   The verification step **MUST only** test the changes and should succeed when
    the sql is executed.
-   Transformations align with the target schema if provided.
-   Cleaning summary is provided with clear justification for each
    transformation.
-   If skipped, the reason is clearly stated (e.g., ineligible source).
