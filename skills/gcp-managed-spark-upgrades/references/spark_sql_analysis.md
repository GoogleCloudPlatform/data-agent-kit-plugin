# Spark SQL Compatibility Analysis Guide

Spark SQL-specific checks: SQL scripts and inline queries, variable substitution
and `SET` properties, SQL grammar and evaluation behavior, table DDL/DML and
catalogs, custom UDF/SerDe jars, and local Catalyst parser and function build
checks. Use it with `spark_migration_reference.md`, which covers what every job
type shares (version mapping, component versions, the Java runtime, connectors,
GPU/RAPIDS, and the Spark migration notes; for Spark SQL jobs, the SQL and Core
notes apply, and the PySpark notes don't). Also apply this guide's SQL and
Catalyst parser checks whenever a PySpark or Scala/Java job executes inline SQL
strings (`spark.sql(...)`, `sqlContext.sql(...)`, `selectExpr(...)`,
`expr(...)`) or loads `.sql` files. When a Spark SQL job attaches custom UDF,
UDAF, or SerDe jars, also use `jvm_build_reference.md` (and `scala_analysis.md`
or `java_analysis.md` if rebuilding their source).

This guide doesn't keep a fixed list of Spark SQL breaking changes by version,
which would go stale: `fetch_migration_notes.py` downloads the exact Spark SQL
and Core migration sections between the source and target Spark versions ("Spark
Migration Notes" in `spark_migration_reference.md`), and the target Spark's
Catalyst parser and configuration validator (section 4) check the queries
against the target grammar and property definitions.

## Procedure

1.  Take the source's and the target's Spark, Java, Scala, and Hive versions
    from "Version to Spark Mapping" and the component pages
    (`spark_migration_reference.md`).
2.  Fetch the Spark migration notes with `fetch_migration_notes.py` ("Spark
    Migration Notes" in `spark_migration_reference.md`) and read `sql.md` and
    `core.md` in full.
3.  Scan every `.sql` file (or inline `queryList.queries`, or inline SQL strings
    in host code), its variable bindings (`scriptVariables` on clusters,
    `queryVariables` on Serverless), its `SET` statements, `spark.conf.set`
    calls, and `--properties`, and any attached jars (`jarFileUris`, `ADD JAR`)
    as sections 1–3 below describe and against every note in `sql.md` and
    `core.md`.
4.  Run the build checks (section 4) on the original SQL in Step 1.5, and re-run
    them on the upgraded SQL in Step 1.6.
5.  Record each finding with its `file:line`, why it breaks on the target, and
    the fix. The report format is in SKILL.md Step 3. The fixes are applied in
    Step 1.6, not during the analysis.

--------------------------------------------------------------------------------

## 1. SQL Scripts, Inline Queries, Variables, and Configuration

-   **SQL script vs. inline queries:**
    -   Cluster jobs (`sparkSqlJob`) specify either `queryFileUri` (`--file`) or
        inline `queryList.queries` (`-e` / `--execute`). When a cluster job uses
        inline `queryList.queries`, save the queries (joined with `;\n`) to
        `src_<app_id>_temp/<app_id>.sql` so they can be checked, upgraded, and
        delivered like a script file, and note in the report whether production
        should switch to `--file` or update its inline `-e` string.
    -   Serverless batches (`sparkSqlBatch`) always take a script file URI
        (`queryFileUri`, passed as the positional `SQL_SCRIPT` argument to
        `gcloud dataproc batches submit spark-sql`).
    -   When PySpark, Scala, or Java code executes inline SQL (`spark.sql(...)`,
        `sqlContext.sql(...)`, `selectExpr(...)`, `expr(...)`) or reads `.sql`
        resource files, host language compilers do not validate the embedded SQL
        text. Extract every SQL statement and `SET` / `spark.conf.set` property
        into `build_<app_id>_temp/` (substituting any host string interpolations
        with representative literal values in the temporary copy) so they are
        checked against `sql.md` and validated by the Catalyst parser check in
        section 4, then apply the compatibility fixes back to the SQL strings in
        the host source file.
-   **Variable substitution:**
    -   Cluster jobs pass script variables via `scriptVariables`
        (`--params=KEY=VALUE,...`); Serverless batches pass them via
        `queryVariables` (`--vars=KEY=VALUE,...`). Inside the `.sql` script,
        variables are referenced as `${var}`, `${hivevar:var}`, or
        `${hiveconf:var}`.
    -   Carry all source variables forward to Step 2 and Step 3, and check
        whether output paths or table names are parameterized through variables
        (which lets Step 2 redirect outputs via `--params` or `--vars` without
        editing a temporary copy of the `.sql` file).
-   **`SET` statements and `spark.sql.*` properties:**
    -   Check every `SET key = value` statement, `spark.conf.set(...)` call, and
        `--properties` entry (`sparkSqlJob.properties` or
        `runtimeConfig.properties`) against `sql.md` and `core.md`.
    -   Replace removed or renamed Spark SQL configuration keys with the
        supported target configuration keys documented in `sql.md`.
-   **Prefer SQL code fixes over legacy flags (SKILL.md rule 2):**
    -   Check every query's syntax, identifiers and aliases, operators, built-in
        function signatures, type coercions, and runtime evaluation rules
        against every section in `sql.md`.
    -   When `sql.md` documents a parser, keyword, function, type-coercion, or
        evaluation behavior change between the source and target Spark versions,
        update the affected SQL statements and expressions directly so they
        preserve the source behavior under the target Spark version's default
        settings, rather than setting `spark.sql.legacy.*` or compatibility
        flags that restore older Spark behavior.
    -   Use a legacy or compatibility flag only when the query cannot preserve
        the source behavior through SQL edits alone, and list every such flag in
        the report.

## 2. Table DDL/DML, Hive Metastore, and Catalogs

-   **Table provider and DDL/DML defaults:**
    -   Check `CREATE [EXTERNAL] TABLE`, `CREATE TABLE ... AS SELECT`, `INSERT`,
        and `MERGE` statements against `sql.md` for any change in default table
        provider, storage format, or schema/partition semantics between the
        source and target Spark versions, and declare changed defaults
        explicitly in the DDL when needed to preserve the source behavior.
-   **Metastore and catalogs:**
    -   On clusters, check whether the source cluster configured an external
        Hive Metastore (`hive.metastore.uris`) or Dataproc Metastore service,
        and confirm compatibility with the target image's Hive version from
        "Component Versions" (`spark_migration_reference.md`).
    -   On Serverless, check
        `environmentConfig.peripheralsConfig.metastoreService`
        (`--metastore-service`) and carry it forward to Step 2.
    -   If the workload uses catalog extensions (`spark.sql.extensions`,
        `spark.sql.catalog.<name>`), check that any catalog jars or packages
        match the target's Spark and Scala versions (`jvm_build_reference.md`,
        section 4).
-   **Output isolation for Step 2 verification (SKILL.md rule 4):**
    -   Inspect every `INSERT OVERWRITE [LOCAL] DIRECTORY`,
        `CREATE [EXTERNAL] TABLE ... LOCATION`, `INSERT INTO`,
        `INSERT OVERWRITE TABLE`, and `MERGE INTO` statement for output paths
        and target tables.
    -   During Step 2 verification, redirect all storage output paths to
        `<target_path>/test-output_<app_id>_temp/`—either by overriding output
        path variables in `--params` (clusters) or `--vars` (Serverless), via
        job arguments for host jobs, or by creating a temporary copy
        (`<script>_<app_id>_temp.sql` or a temporary host script/jar) with
        redirected `DIRECTORY` / `LOCATION` paths and temporary (`_temp`) table
        names so production tables and production GCS paths are never modified.
        Keep the original production paths and table names in the working copy
        delivered in Step 3.

## 3. UDF, UDAF, and SerDe Jars

If the job attaches jars through `jarFileUris` (`--jars`), `spark.jars`,
`spark.jars.packages`, cluster initialization actions, or `ADD JAR` statements
in the `.sql` script (for example, to register custom functions with
`CREATE [TEMPORARY] FUNCTION ... AS '<class>'` or custom Hive SerDes with
`ROW FORMAT SERDE`):

-   **Connectors:** follow "Connectors" in `spark_migration_reference.md` and
    remove any pinned `gcs-connector` or `spark-bigquery-connector` jars or
    packages.
-   **Custom JVM jars:** inspect every custom UDF, UDAF, or SerDe jar as
    described in `jvm_build_reference.md` (section 1). Jars that link against
    Scala (`scala/`) or Spark (`org/apache/spark/`) classes must match the
    target's Scala binary version (`_2.12` vs. `_2.13`) and Spark version, and
    their bytecode major version must be supported by the target's Java runtime.
    If a jar is incompatible, ask for its source repository (if not already
    supplied) and upgrade and rebuild it following `jvm_build_reference.md`,
    `scala_analysis.md`, and `java_analysis.md`.

## 4. Build Checks Against the Target Version

Build checks validate that every SQL statement and property in a `.sql` script
(or extracted from inline `spark.sql(...)` / `expr(...)` / `selectExpr(...)`
calls in a PySpark, Scala, or Java job) parses and resolves against the target
Spark version. Run them twice in Step 1: on the original SQL during the analysis
(each failure is a finding), and on the upgraded SQL in Step 1.6 (all checks
must pass). Take `<TARGET_PYTHON>` (e.g. `3.12`) and `<TARGET_SPARK>` (e.g.
`4.1.2` or `4.0.0`) from the target's component page.

-   Copy the `.sql` files (or write extracted inline SQL statements separated by
    `;\n`) to `build_<app_id>_temp/` and run the checks there. Delete
    `build_<app_id>_temp/` after recording the results.
-   If the SQL contains variable placeholders (`${var}`, `${hivevar:var}`,
    `${hiveconf:var}`) or host-language format tokens, substitute them in the
    `build_<app_id>_temp/` copy using the job's `scriptVariables` /
    `queryVariables` (or representative sample values when variables are not
    supplied) before running the parser check, so unexpanded placeholders do not
    cause false syntax errors.
-   If a check can't run (tool missing, no network access), don't install
    toolchains to force it: record it as "not run" with the reason.

### 4.1. L1: Catalyst Parser & Property Check (always, when `uv` is available)

Parse every SQL statement and validate `SET` properties using the target Spark's
native Catalyst parser (`sqlParser().parsePlan` and `parseExpression` for
standalone SQL expressions) in a local PySpark session without executing queries
against external tables:

```bash
uv run --no-project --python=<TARGET_PYTHON> --with=pyspark==<TARGET_SPARK> -- python -c "
import re, sys
from pyspark.sql import SparkSession

spark = SparkSession.builder.master('local[1]').appName('sql_validator').getOrCreate()
parser = spark._jsparkSession.sessionState().sqlParser()

with open('build_<app_id>_temp/<SQL_FILE>', 'r', encoding='utf-8') as f:
    sql_text = f.read()

# Strip SQL block and line comments before splitting on semicolons
no_block = re.sub(r'/\*.*?\*/', '', sql_text, flags=re.DOTALL)
no_comments = '\n'.join(
    re.sub(r'--.*$', '', line) for line in no_block.splitlines()
)

errors = 0
for raw_stmt in no_comments.split(';'):
    stmt = raw_stmt.strip()
    if not stmt:
        continue
    try:
        parser.parsePlan(stmt)
        m = re.match(r'^SET\s+([A-Za-z0-9_.]+)\s*=\s*(.+)$', stmt, flags=re.IGNORECASE | re.DOTALL)
        if m:
            spark.conf.set(m.group(1).strip(), m.group(2).strip())
    except Exception as e:
        print(f'ERROR in statement: {stmt[:120]}\n{e}\n', file=sys.stderr)
        errors += 1

spark.stop()
sys.exit(1 if errors else 0)
"
```

-   The script strips `--` and `/* ... */` comments before splitting on `;` so
    that statements preceded by comment headers are never skipped.
-   Applying `SET` statements to `spark.conf` during the loop both flags removed
    or invalid `spark.sql.*` properties that `spark.conf.set` rejects and
    ensures subsequent statements in the file are parsed under the script's own
    parser settings. Note that `spark.conf.set` does not reject every removed
    arbitrary key name, so always check `SET` and `spark.conf.set` keys against
    `sql.md` as well. If the job also passes `spark.sql.*` properties via
    `--properties`, set those on `spark.conf` before the loop.
-   Note that `parsePlan` validates syntax and grammar only: runtime evaluation
    changes on data (documented in `sql.md`) require the migration-notes scan in
    section 1.
-   If `uv` fails during package resolution (for example, if `<TARGET_SPARK>` is
    not available on PyPI), retry with the target's `<major>.<minor>.0` release
    on PyPI or record the check as "not run (package resolution failure)".
    Without `uv`, record L1 as "not run" and rely on the manual migration-notes
    scan.

### 4.2. L2: Function Registry & UDF Jar Check

-   **Built-in function check:** When `uv` is available, check that every SQL
    function invoked in the queries is registered in the target Spark's
    `spark.catalog.listFunctions()` (excluding custom UDFs registered by the
    script or host job), or check function names and argument types against
    `sql.md`.
-   **UDF/SerDe jar check (when the job attaches jars):** Run the jar inspection
    and build checks in `jvm_build_reference.md` (sections 1 and 5) on every
    custom jar in `jarFileUris`, `spark.jars`, `spark.jars.packages`, or
    `ADD JAR`.
