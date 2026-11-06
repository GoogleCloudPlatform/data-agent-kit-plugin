<!-- disableFinding(LINE_OVER_80) -->

# Source engines (`references/source_engines.md`)

A context set can cover tables from any Knowledge Catalog source engine, and one
context set can mix engines. Every rule in this skill that says "the source's
engine", "the engine's system entry", or "the engine's compile check" resolves
through this list. BigQuery is the worked example in the templates; substitute
the entry for each table's engine.

Each table's Knowledge Catalog entry sits in its engine's **system entry group**
(id starts with `@`), and its entry id is the table's resource name without a
leading `//`. Use the full entry name for the `Table Context` page's `resource:`
and as the `reference` link `target`:
`projects/<PROJECT>/locations/<location>/entryGroups/<@group>/entries/<resource
name>` (`<PROJECT>` is the table's project; `<location>` is lowercase and must
be read, not guessed: a lookup in the wrong location answers 403 like a missing
entry).

-   **BigQuery**
    -   **System entry group & entry id (resource name):** `@bigquery`;
        `bigquery.googleapis.com/projects/<p>/datasets/<d>/tables/<t>`
    -   **Entry location:** Dataset location (e.g. `us`)
    -   **Read the schema:** `lookup_entry`; fallback `bq show --schema`
    -   **Cost-free compile check:**
        `bq query --dry_run --use_legacy_sql=false "<SQL>"`
    -   **`sqlDialect`:** `GOOGLE_SQL`
-   **Spanner**
    -   **System entry group & entry id (resource name):** `@spanner`;
        `spanner.googleapis.com/projects/<p>/instances/<i>/databases/<db>/tables/<t>`
    -   **Entry location:** Default leader region of the instance config
    -   **Read the schema:** `lookup_entry`; fallback
        `gcloud spanner databases ddl describe`
    -   **Cost-free compile check:** `gcloud spanner databases execute-sql <db>
        --instance=<i> --query-mode=PLAN --sql="<SQL>"` (plan only, no rows)
    -   **`sqlDialect`:** `GOOGLE_SQL` for a GoogleSQL-dialect database;
        PostgreSQL-dialect: omit (see note)
-   **BigLake** (Iceberg REST catalog)
    -   **System entry group & entry id (resource name):** `@biglake`;
        `biglake.googleapis.com/projects/<p>/catalogs/<c>/namespaces/<n>/tables/<t>`
    -   **Entry location:** Catalog region (or multi-region)
    -   **Read the schema:** `lookup_entry`
    -   **Cost-free compile check:** BigQuery dry run when the table is
        queryable from BigQuery; otherwise none (report "not run")
    -   **`sqlDialect`:** `GOOGLE_SQL` via BigQuery; `SPARK_SQL` for Spark SQL
-   **Hive Metastore** (Dataproc Metastore)
    -   **System entry group & entry id (resource name):** Per-service group
        `@dataproc_metastore_<hash>`; entry ids are opaque, never constructed
    -   **Entry location:** The service's region
    -   **Read the schema:** `search_entries` to find the entry name, then
        `lookup_entry`
    -   **Cost-free compile check:** Through BigQuery dry run if exposed there;
        otherwise none (report "not run")
    -   **`sqlDialect`:** `SPARK_SQL` for Spark SQL; `GOOGLE_SQL` via BigQuery
-   **Cloud SQL** (MySQL / PostgreSQL)
    -   **System entry group & entry id (resource name):** `@cloudsql`; MySQL
        `cloudsql.googleapis.com/projects/<p>/locations/<l>/instances/<i>/databases/<db>/tables/<t>`;
        PostgreSQL adds `/schemas/<s>` before `/tables/<t>`
    -   **Entry location:** `<l>` in the resource name
    -   **Read the schema:** `lookup_entry` (entry type names the engine, e.g.
        `cloudsql-postgresql-table`); fallback `INFORMATION_SCHEMA.COLUMNS`
    -   **Cost-free compile check:** `EXPLAIN <SQL>` (never `EXPLAIN ANALYZE`)
    -   **`sqlDialect`:** Omit (see note)
-   **AlloyDB** (PostgreSQL)
    -   **System entry group & entry id (resource name):** `@alloydb`;
        `alloydb.googleapis.com/projects/<p>/locations/<l>/clusters/<c>/databases/<db>/schemas/<s>/tables/<t>`
    -   **Entry location:** `<l>` in the resource name
    -   **Read the schema:** `lookup_entry`; fallback
        `INFORMATION_SCHEMA.COLUMNS`
    -   **Cost-free compile check:** `EXPLAIN <SQL>` (never `EXPLAIN ANALYZE`)
    -   **`sqlDialect`:** Omit (see note)

Notes that apply to every engine:

-   **`sqlDialect` values.** The `dataplex-types.global.queries` aspect accepts
    only `GOOGLE_SQL`, `SPARK_SQL`, `DATABRICKS_SQL`, `SNOWFLAKE_SQL`, and the
    field is optional. For PostgreSQL / MySQL SQL there is no matching value:
    omit `sqlDialect` on that query and say which engine and dialect it runs on
    in its `description`. Never write a value outside the enum.
-   **Schema reads.** Prefer the Knowledge Catalog MCP (`lookup_entry`,
    `search_entries`) for every engine: it returns columns, descriptions, and
    existing aspects in one call. Use the engine CLI or `INFORMATION_SCHEMA`
    only when the entry lacks what you need.
-   **Compile check.** Run the engine's check on each query in the engine's own
    dialect (no rows read, no cost). If no check exists for the engine, or it
    can't run (no client, credentials, or network access to the database),
    report "<engine> compile check: not run" with the one-line reason; never
    present a manual schema comparison as a compile check.
-   **Bounded profiling** (only after the compile check passes): aggregates
    (`COUNT`, `MIN`, `MAX`, `COUNT(DISTINCT ...)`, top values with
    `GROUP BY ... ORDER BY COUNT(*) DESC LIMIT <n>`; BigQuery also
    `APPROX_TOP_COUNT`) or a bounded `LIMIT` query. On Spanner, Cloud SQL, and
    AlloyDB these run on the operational database: keep them small and say so in
    the plan.
-   **Bundle layout.** Table pages go under
    `bundle/assets/<engine>/<container path>/<table>.md` with one container
    index page per deepest container
    (`bundle/assets/<engine>/<container path>.md`,
    `extra.resource.parent: assets`). Container paths: BigQuery
    `<project>/<dataset>`; Spanner `<project>/<instance>/<database>`; BigLake
    `<project>/<catalog>/<namespace>`; Cloud SQL
    `<project>/<instance>/<database>[/<schema>]`; AlloyDB
    `<project>/<cluster>/<database>/<schema>`; Hive Metastore
    `<project>/<service>/<database>`. `<engine>` is the group name without `@`
    (`bigquery`, `spanner`, `biglake`, `cloudsql`, `alloydb`,
    `dataproc_metastore`). Keep existing pulled layouts as they are.
-   **Location rule** (`SUBSKILL.md` §3): on a regional context set, each
    `reference` target must be in the context set's location, whatever its
    engine; a mixed-engine context set often needs `global` or omitted links.
