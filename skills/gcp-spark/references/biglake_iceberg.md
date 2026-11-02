# BigLake Iceberg Catalog in PySpark

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow in `SKILL.md` when writing Spark code.

## Spark Session Configuration

-   [!WARNING] BigLake Iceberg catalog must be configured in the spark session
    before tables can be read.
-   Multiple Iceberg catalogs can be configured in the same spark session.
-   [!IMPORTANT] You **MUST** identify the storage layer for the BigLake Iceberg
    table before configuring the spark session. Use
    `@skill:discovering-gcp-data-assets` to **search** and **lookup** the table
    details. Check the value for the `metadataPath` field from the lookup
    results to confirm it uses GCS storage (starts with `gs:`).
-   [!WARNING] **DO NOT** assume catalog_name, project_id, io implementation for
    a table, **ALWAYS lookup** table details before proceeding.

### Option A: Zero-Config (Preferred) — Session Template / Runtime Profile

When generating PySpark **notebook** code, assume the Dataproc kernel already
has the Iceberg catalog configured via its Session Template. **MUST NOT add
in-code catalog configuration.** On a **Remote Spark** kernel, `spark` is
pre-initialized—use `spark.read.format("iceberg")...` directly. On a **Local
Python** kernel, initialize `ManagedSparkSession`:

```python
# Catalog and BigLake settings are pre-configured by the Dataproc Session Template.
# No .config() calls are needed.
from google.cloud.managed_spark_connect import ManagedSparkSession
from google.cloud.dataproc_v1 import Session

# 1. Initialize the Dataproc Session configuration object
session = Session()
session.session_template = "projects/<PROJECT_ID>/locations/<REGION>/sessionTemplates/<TEMPLATE_ID>"
spark = (
    ManagedSparkSession.builder
    .projectId("<PROJECT_ID>")
    .location("<REGION>")
    .dataprocSessionConfig(session)
    .getOrCreate()
)

# Read directly from the catalog already registered by the kernel's session template
df = spark.read.format("iceberg").load("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
```

> [!IMPORTANT] When generating notebook code, **always use the pattern shown
> above**. Adding explicit `.config()` calls for catalogs that are already in
> the Session Template is redundant and can cause duplicate extension
> registration.

#### Locating the Session Template and Catalog Name

Use this high-level routing algorithm to determine `<TEMPLATE_ID>` and
`<CATALOG_NAME>`:

-   **If `<TEMPLATE_ID>` is already known** (passed in prompt or present in
    existing code): go to **Case 1: Known Session Template**.
-   **If `<TEMPLATE_ID>` is unknown** (only table name, Dataplex entry, or
    warehouse is known): go to **Case 2: Unknown Session Template**.
-   **If no template matches or input is incomplete**: go to **Case 3: No
    Matching Template**.

##### Case 1: Known Session Template

Use the specified `<TEMPLATE_ID>`. If `<CATALOG_NAME>` is not already known from
the code, inspect the template's properties:

```bash
gcloud beta dataproc session-templates describe <TEMPLATE_NAME> \
    --project=<PROJECT_ID> --location=<REGION> \
    --format="json(runtimeConfig.properties)"
```

-   If `spark.sql.defaultCatalog` is set, `<CATALOG_NAME>` can be omitted
    (`<NAMESPACE_NAME>.<TABLE_NAME>`).
-   If only one `spark.sql.catalog.<CATALOG_NAME>` is configured in the
    template, use that `<CATALOG_NAME>`
    (`<CATALOG_NAME>.<NAMESPACE_NAME>.<TABLE_NAME>`).
-   If multiple catalogs are configured, use the `<CATALOG_NAME>` whose
    `spark.sql.catalog.<CATALOG_NAME>.warehouse` matches the table's warehouse.

##### Case 2: Unknown Session Template

List templates in the project filtered by the table's warehouse URI (e.g.
`gs://<BUCKET>` from Dataplex `metadataPath`) to get both `<TEMPLATE_ID>` and
`<CATALOG_NAME>`:

```bash
gcloud beta dataproc session-templates list \
    --project=<PROJECT_ID> --location=<REGION> \
    --filter="runtimeConfig.properties:<WAREHOUSE_BUCKET_OR_URI>" \
    --limit=5 \
    --format="json(name.basename(), runtimeConfig.properties)"
```

-   If multiple templates match, prefer the template where `defaultCatalog`
    matches the catalog name.

##### Case 3: No Matching Template

If no session template matches the warehouse, or if required inputs are missing:

-   **STOP and ask the user** which Session Template to use.
-   Do **NOT** guess `<CATALOG_NAME>` or add in-code `.config()` calls in
    notebooks.

### Option B: Explicit In-Code Configuration

Use this only when no Session Template / Runtime Profile is available (e.g.
cluster and batch jobs, or environments without a pre-configured profile). You
**MUST NOT** use this in notebook code - ask user to configure and provide the
session template instead. Multiple Iceberg catalogs can be configured in the
same spark session.

> [!IMPORTANT]
> - **Runtime JARs**:
>   - **Dataproc Serverless**: Iceberg and `iceberg-gcp` (`GCSFileIO`) JARs are pre-installed on `/usr/lib/spark/jars/` by default. Do **NOT** pass `spark.jars.packages=org.apache.iceberg:...` when submitting serverless batches.
>   - **Dataproc on GCE Clusters**: Enable `--optional-components=ICEBERG` at cluster creation (which adds `/usr/lib/iceberg/lib/*` to `SPARK_DIST_CLASSPATH`), or pass `/usr/lib/iceberg/lib/*` via `--jars` if submitting to a cluster without the optional component.
> - **Warehouse URI & Catalog Name**: For a GCS-backed BigLake catalog, the catalog name `<BUCKET_NAME>` must match the GCS bucket name, and `spark.sql.catalog.<BUCKET_NAME>.warehouse` **MUST** be the root GCS bucket URI (`gs://<BUCKET_NAME>`) without any subfolder path. Passing a subfolder (e.g. `gs://<BUCKET_NAME>/warehouse`) causes `BadRequestException: Bucket name is invalid`.
> - **Catalog Provisioning & IAM**: Before creating namespaces or writing tables, ensure the BigLake Iceberg catalog exists (`gcloud biglake iceberg catalogs create <BUCKET_NAME> --catalog-type=gcs-bucket --project=<CATALOG_PROJECT_ID>`) and the execution service account has `roles/biglake.admin` and `roles/storage.objectUser` on the catalog bucket.

Example with GCS storage:

```python
spark = (
    SparkSession.builder
    .appName("<APP_NAME>")
    .config(
        "spark.sql.extensions",
        "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    )
    .config(
        "spark.sql.catalog.<BUCKET_NAME>",
        "org.apache.iceberg.spark.SparkCatalog",
    )
    .config("spark.sql.catalog.<BUCKET_NAME>.type", "rest")
    .config(
        "spark.sql.catalog.<BUCKET_NAME>.uri",
        "https://biglake.googleapis.com/iceberg/v1/restcatalog",
    )
    .config(
        "spark.sql.catalog.<BUCKET_NAME>.warehouse",
        "gs://<BUCKET_NAME>",
    )
    .config(
        "spark.sql.catalog.<BUCKET_NAME>.header.x-goog-user-project",
        "<CATALOG_PROJECT_ID>",
    )
    .config(
        "spark.sql.catalog.<BUCKET_NAME>.rest.auth.type",
        "org.apache.iceberg.gcp.auth.GoogleAuthManager",
    )
    .config(
        "spark.sql.catalog.<BUCKET_NAME>.io-impl",
        "org.apache.iceberg.gcp.gcs.GCSFileIO",
    )
    .getOrCreate()
)
```

## Reading from BigLake Iceberg Catalog

-   [!WARNING] BigLake Iceberg catalog must be configured before tables can be
    read (via Session Template or explicit configuration).
-   If not using a fully qualified 3-part table identifier (or if
    `spark.sql.defaultCatalog` is not set), set the current Spark catalog using
    `spark.catalog.setCurrentCatalog("<CATALOG_NAME>")`. **DO NOT** use
    backticks in this call.
-   [!IMPORTANT] You **MUST ALWAYS** surround the catalog name with backticks in
    SQL statements and `load()` calls to ensure proper handling of special
    characters (e.g., `` `catalog-name` ``).

```python
df = (
    spark.read.format("iceberg")
    .load("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
)
```

## Writing to BigLake Iceberg Catalog

> [!IMPORTANT] Follow these instructions before writing code to write to BigLake
> Iceberg tables.

-   [!WARNING] BigLake Iceberg catalog must be configured before tables can be
    written (via Session Template or explicit configuration).
-   **ALWAYS** use Spark's `DataFrameWriterV2` API (`writeTo`) for writing to
    Iceberg tables. This provides a richer API with specific write modes.
-   If not using a fully qualified 3-part table identifier (or if
    `spark.sql.defaultCatalog` is not set), set the current Spark catalog using
    `spark.catalog.setCurrentCatalog("<CATALOG_NAME>")`. **DO NOT** use
    backticks in this call.
-   **ALWAYS** Ensure namespace is created before writing, using:

    ```python
    spark.sql(
        "CREATE NAMESPACE IF NOT EXISTS `<CATALOG_NAME>`.<NAMESPACE_NAME>"
    )
    ```
    > [!IMPORTANT] You **MUST ALWAYS** surround the catalog name with backticks
    > in SQL statements and `writeTo()` calls to ensure proper handling of
    > special characters.

```python
# The basic pattern
spark.catalog.setCurrentCatalog("<CATALOG_NAME>")
(
    df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
    .using("iceberg")
    .createOrReplace()
)
```

### Write Modes

-   **DataFrameWriterV2 `createOrReplace()`**: Creates the table if it does not
    exist, or replaces it if it does.

    ```python
    (
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
        .using("iceberg")
        .createOrReplace()
    )
    ```

-   **DataFrameWriterV2 `append()`**: Equivalent to `INSERT INTO`. Appends data
    to an existing table.

    ```python
    (
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
        .using("iceberg")
        .append()
    )
    ```

-   **SPARK SQL MERGE INTO**: Performs row-level updates, inserts, and deletes
    by rewriting data files that contain affected rows. The source table can be
    persisted as a temp view to allow using it in the MERGE INTO statement. The
    source view and the target table must be joined on the primary key(s) to
    ensure correct row-level updates, inserts, and deletes.

    ```python
    df.createOrReplaceTempView("source_updates")

    spark.sql(f"""
        MERGE INTO `<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME> t
        USING source_updates s
        ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    ```

-   [!WARNING] These are less preferred write modes, use them ONLY if explicitly
    asked to:
    *   **`create()`**: Equivalent to `CREATE TABLE AS SELECT`. Fails if the
        table already exists.

        ```python
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
            .using("iceberg") \
            .create()
        ```

    *   **`replace()`**: Equivalent to `REPLACE TABLE AS SELECT`.

        ```python
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
            .using("iceberg") \
            .replace()
        ```

    *   **`overwritePartitions()`**: Equivalent to dynamic `INSERT OVERWRITE`.
        Overwrites partitions in the table that match the data in the DataFrame.

        ```python
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
            .using("iceberg") \
            .overwritePartitions()
        ```

    *   **`overwrite(condition)`**: Overwrites data that matches a specific
        condition (e.g. static overwrite).

        ```python
        from pyspark.sql.functions import col
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
            .using("iceberg") \
            .overwrite(col("level") == "INFO")
        ```

### Advanced Iceberg Writes

#### Writing with partitions
Use partitioning transform functions if writing to partitioned tables using
timestamp fields. Ex: years, months, days, hours etc.

```python
from pyspark.sql.functions import days

df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
    .using("iceberg") \
    .partitionedBy("level", days("ts")) \
    .createOrReplace()
```

#### Schema Evolution
Iceberg supports safe schema evolution. You can merge schema changes during an
append.

```python
df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
    .option("mergeSchema", "true") \
    .append()
```

#### Writing to a Specific Branch

```python
# To insert into an `audit` branch
df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>.branch_audit") \
    .append()
```
