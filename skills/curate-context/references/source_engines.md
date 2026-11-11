<!-- disableFinding(LINE_OVER_80) -->

# Source engines (`references/source_engines.md`)

A context set can cover tables, views, and other data assets from any Knowledge
Catalog source engine, and one context set can mix engines. Every rule in this
skill that says "the source's engine", "the engine's system entry", or "the
engine's compile check" resolves through this list. BigQuery is the worked
example in the templates; substitute the entry for each asset's engine.

Each asset's Knowledge Catalog entry sits in its engine's **system entry group**
(id starts with `@`), and its entry id is the asset's resource name without a
leading `//`. Use the full entry name for the asset page's `resource:` and as
the `reference` link `target`:
`projects/<PROJECT>/locations/<location>/entryGroups/<@group>/entries/<resource
name>` (`<PROJECT>` is the asset's project; `<location>` is lowercase and must
be read, not guessed: a lookup in the wrong location answers 403 like a missing
entry). Always copy the exact `entry.name` from `search_entries` or
`lookup_entry`; the forms below are the usual shapes. In the six tabular engines
below, views and materialized views use the same `/tables/<name>` path as tables
and can have `Table Context` pages too; other Knowledge Catalog systems (for
example `@oracledatabase` `/views/<v>`, `@bigtable` `/logicalViews/<lv>` and
`/materializedViews/<mv>`, or `@looker` `/views/<v>`) use their own collection
segment in `entry.name`.

-   **BigQuery**

    -   **System entry group & entry id (resource name):** `@bigquery`;
        `bigquery.googleapis.com/projects/<p>/datasets/<d>/tables/<t>` (other
        dataset/regional assets use `.../models/<m>`, `.../routines/<r>`,
        `.../propertyGraphs/<g>`, or
        `bigqueryconnection.googleapis.com/projects/<p>/locations/<l>/connections/<c>`)
    -   **Entry location:** Dataset or connection location (e.g. `us`)
    -   **Read the schema:** `lookup_entry` with `view: "ALL"`; fallback
        BigQuery MCP `get_table_info` or
        `bq show --schema --format=prettyjson <p>:<d>.<t>` (required on
        `bigquery-public-data`, where `lookup_entry` fails IAM)
    -   **Cost-free compile check:** BigQuery MCP `execute_sql_readonly`
        (`dry_run: true`), or CLI (`--project_id=<billing_project>` if needed):

        ```bash
        bq query --dry_run --use_legacy_sql=false <<'SQL'
        <SQL>
        SQL
        ```

    -   **`sqlDialect`:** `GOOGLE_SQL`
-   **Spanner**

    -   **System entry group & entry id (resource name):** `@spanner`;
        `spanner.googleapis.com/projects/<p>/instances/<i>/databases/<db>/tables/<t>`
        (property graphs use `.../databases/<db>/graphs/<g>`)
    -   **Entry location:** Default leader region of the instance config
    -   **Read the schema:** `lookup_entry` with `view: "ALL"`; fallback Spanner
        MCP `get_database_ddl` or `gcloud spanner databases ddl describe <db>
        --instance=<i> --project=<p>`
    -   **Cost-free compile check** (plan only, reads no rows): Spanner MCP
        `get_query_plan`, or CLI:

        ```bash
        sql=$(cat <<'SQL'
        <SQL>
        SQL
        )
        gcloud spanner databases execute-sql <db> --instance=<i> --project=<p> --query-mode=PLAN --sql="$sql"
        ```

    -   **`sqlDialect`:** `GOOGLE_SQL` for a GoogleSQL-dialect database;
        PostgreSQL-dialect: omit (see note)
-   **BigLake** (Iceberg REST catalog, BigLake Metastore Hive, & Delta Sharing)

    -   **System entry group & entry id (resource name):** `@biglake`;
        `biglake.googleapis.com/projects/<p>[/locations/<l>]/catalogs/<c>/namespaces/<n>/tables/<t>`
        (Iceberg),
        `biglake.googleapis.com/projects/<p>[/locations/<l>]/catalogs/<c>/databases/<d>/tables/<t>`
        (BigLake Hive), or
        `biglake.googleapis.com/projects/<p>[/locations/<l>]/catalogs/<c>/shares/<s>/schemas/<sch>/tables/<t>`
        (Delta Sharing)
    -   **Entry location:** Catalog region or multi-region (from `lookup_entry`)
    -   **Read the schema:** `lookup_entry`
    -   **Cost-free compile check:** BigQuery dry run when the table is
        queryable from BigQuery; otherwise none (report "not run")
    -   **`sqlDialect`:** `GOOGLE_SQL` via BigQuery; `SPARK_SQL` for Spark SQL
-   **Hive Metastore** (Dataproc Metastore)

    -   **System entry group & entry id (resource name):** `@dataprocmetastore`;
        `metastore.googleapis.com/projects/<p>/locations/<l>/services/<s>/databases/<db>/tables/<t>`
    -   **Entry location:** `<l>`, the service's region
    -   **Read the schema:** `lookup_entry`
    -   **Cost-free compile check:** Through BigQuery dry run if exposed there;
        otherwise none (report "not run")
    -   **`sqlDialect`:** `SPARK_SQL` for Spark SQL; `GOOGLE_SQL` via BigQuery
-   **Cloud SQL** (MySQL / PostgreSQL / SQL Server)

    -   **System entry group & entry id (resource name):** `@cloudsql`; MySQL
        `cloudsql.googleapis.com/projects/<p>/locations/<l>/instances/<i>/databases/<db>/tables/<t>`;
        PostgreSQL and SQL Server add `/schemas/<s>` before `/tables/<t>`
    -   **Entry location:** `<l>` in the resource name
    -   **Read the schema:** `lookup_entry` with `view: "ALL"` (entry type names
        the engine, e.g. `cloudsql-postgresql-table`); fallback
        `INFORMATION_SCHEMA.COLUMNS`
    -   **How to run SQL:** the Cloud SQL MCP server's `execute_sql_readonly` /
        `execute_sql` tool (needs the instance's Data API access enabled and a
        database user through IAM database auth or a Secret Manager password),
        or a database client the user already has connected
    -   **Cost-free compile check:** `EXPLAIN <SQL>` (never `EXPLAIN ANALYZE`);
        SQL Server: in a stateful connected client only, run as separate batches
        (`SET SHOWPLAN_XML ON` → `<SQL>` → `SET SHOWPLAN_XML OFF`, never across
        stateless MCP calls), otherwise report "not run"
    -   **`sqlDialect`:** Omit (see note)
-   **AlloyDB** (PostgreSQL)

    -   **System entry group & entry id (resource name):** `@alloydb`;
        `alloydb.googleapis.com/projects/<p>/locations/<l>/clusters/<c>/databases/<db>/schemas/<s>/tables/<t>`
    -   **Entry location:** `<l>` in the resource name
    -   **Read the schema:** `lookup_entry` with `view: "ALL"`; fallback
        `INFORMATION_SCHEMA.COLUMNS`
    -   **How to run SQL:** the AlloyDB MCP server's `execute_sql_read_only` /
        `execute_sql` tool (uses IAM database auth on
        `projects/<p>/locations/<l>/clusters/<c>/instances/<i>` — needs an IAM
        database user on the instance; `execute_sql`'s `validate_only` option
        checks a statement without running it), or a database client the user
        has connected (using database user/password credentials the user
        provides)
    -   **Cost-free compile check:** `EXPLAIN <SQL>` (never `EXPLAIN ANALYZE`,
        e.g. via `execute_sql_read_only` or a connected client), or
        `execute_sql` with `validate_only: true`
    -   **`sqlDialect`:** Omit (see note)
-   **Other Knowledge Catalog systems** (for example Bigtable `@bigtable`,
    Firestore `@firestore`, or third-party systems in custom entry groups): find
    the entry with `search_entries`, read it with `lookup_entry`
    (`view: "ALL"`), and copy its exact name. Table Context pages and documents
    work the same way. If there's no cost-free compile check for the system,
    don't author SQL for it, or report "compile check: not run".

Notes that apply to every engine:

-   **`sqlDialect` values.** The `dataplex-types.global.queries` aspect accepts
    only `GOOGLE_SQL`, `SPARK_SQL`, `DATABRICKS_SQL`, `SNOWFLAKE_SQL`, and the
    field is optional. For PostgreSQL / MySQL SQL there is no matching value:
    omit `sqlDialect` on that query and say which engine and dialect it runs on
    in its `description`. Never write a value outside the enum.
-   **Schema reads.** Prefer the Knowledge Catalog MCP (`lookup_entry` with
    `view: "ALL"` and `location` matching the entry's location, plus
    `search_entries`) for every engine: `view: "ALL"` returns columns,
    descriptions, `overview`, `queries`, and custom aspects in one call
    (omitting `view: "ALL"` returns empty `{}` for optional aspects; CLI
    fallback `gcloud dataplex entries lookup --view=ALL`). Use the engine MCP /
    CLI or `INFORMATION_SCHEMA` when the entry lacks what you need (or on
    `bigquery-public-data`, where `lookup_entry` fails IAM).
-   **Read-only access to operational databases.** On Spanner, Cloud SQL, and
    AlloyDB, run only read-only statements (`EXPLAIN`, plan-only queries,
    `INFORMATION_SCHEMA` reads, bounded aggregates); never DDL, DML, or user or
    permission changes. Don't create database users or change instance settings
    to get access: if no access path works, say so and ask.
-   **Compile check.** Run the engine's check on each query in the engine's own
    dialect (no rows read, no cost). If no check exists for the engine, or it
    can't run (no client, credentials, or network access to the database),
    report "<engine> compile check: not run" with the one-line reason; never
    present a manual schema comparison as a compile check.
-   **Bounded profiling** (only after the compile check passes): aggregates
    (`COUNT`, `MIN`, `MAX`, `COUNT(DISTINCT ...)`, top values with
    `GROUP BY ... ORDER BY COUNT(*) DESC LIMIT <n>`; BigQuery also
    `APPROX_TOP_COUNT`) or a bounded `LIMIT` query. On BigQuery, `LIMIT` doesn't
    reduce bytes scanned: check the dry run's bytes estimate first and prefer
    partition filters. `TABLESAMPLE SYSTEM` samples storage blocks, so on a
    small table it can read every row or none: check the row count it returns
    and fall back to aggregates. On Spanner, Cloud SQL, and AlloyDB these run on
    the operational database: keep them small and say so in the plan.
-   **Bundle layout.** Derive each asset page's path under
    `bundle/assets/<engine>/` (`<engine>` is the entry group ID without `@`)
    from its `entry.name`
    (`.../entryGroups/<group>/entries/<service_api>/<resource_path>`):
    1.  Drop `<service_api>/`, `projects/` (`projects/_/` for Cloud Storage),
        `locations/` (keeping `<location>` when present in `entry.name`), and
        single-spine container collection keywords (`datasets/`, `instances/`
        when containing databases or tables, `clusters/`, `services/`,
        `catalogs/`, `namespaces/`, `databases/`, `schemas/`).
    2.  For `/tables/<name>` entries, drop `/tables/` so the page sits at
        `bundle/assets/<engine>/<container path>/<table>.md` — BigQuery
        `<project>/<dataset>/<table>.md`; Spanner
        `<project>/<instance>/<database>/<table>.md`; BigLake
        `<project>[/<location>]/<catalog>/<namespace>/<table>.md` (Iceberg),
        `<project>[/<location>]/<catalog>/<database>/<table>.md` (Hive), or
        `<project>[/<location>]/<catalog>/shares/<share>/<schema>/<table>.md`
        (Delta Sharing); Cloud SQL
        `<project>/<location>/<instance>/<database>[/<schema>]/<table>.md`;
        AlloyDB `<project>/<location>/<cluster>/<database>/<schema>/<table>.md`;
        Hive Metastore `<project>/<location>/<service>/<database>/<table>.md`.
    3.  For any non-`/tables/` resource collection (sibling assets in a
        database/dataset or project/regional resources), **keep the leaf
        collection segment** `<collection>/<name>.md` so resource types never
        collide — e.g. BigQuery `models/<m>.md`, `routines/<r>.md`,
        `propertyGraphs/<g>.md`, or `<project>/<location>/connections/<c>.md`;
        Spanner `graphs/<g>.md`; Bigtable `<project>/<instance>/tables/<t>.md`,
        `.../logicalViews/<lv>.md`, or `.../materializedViews/<mv>.md`; Oracle
        `views/<v>.md`; Pub/Sub `<project>/topics/<t>.md`; Cloud Storage
        `buckets/<b>.md`.
    4.  Create one `Knowledge Base Index` page per container
        (`bundle/assets/<engine>/<container path>.md`) with
        `extra.resource.parent` set to its nearest existing ancestor index
        (`assets` by default on small new sets; add intermediate index pages
        when fan-out or shared database context warrants it, and keep existing
        pulled or imported layouts intact — `SUBSKILL.md` §1).
-   **Location rule** (`SUBSKILL.md` §3): on a regional context set, each
    `reference` target must be in the context set's location, whatever its
    engine; for a mixed-location set, ask the user about a `global` context set
    (which can link to any location).
