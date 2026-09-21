# Definitive Guide to reading and writing tables using spark code

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow when writing spark code.

## Task Execution Workflow

1. Configure the spark session to read or write data from the required source
   or destination
2. Read or write the data from the required source or destination

## BigQuery

### Spark Session Configuration

On Managed Spark on Google Cloud, BigQuery connector jars are pre-installed.
When initializing local session, set the BigQuery package coordinates and
dependencies:

```python
from pyspark.sql import SparkSession

# For Spark 4.0 environments
spark = (
    SparkSession.builder.appName("<APP_NAME>")
    .config(
        "spark.jars.packages",
        "com.google.cloud.spark:spark-4.0-bigquery:0.45.0,javax.inject:javax.inject:1",
    )
    .getOrCreate()
)
```

### Reading from BigQuery
#### Basic example to read a Big Query table

```python
df = spark.read.format("bigquery") \
    .option("table", "<PROJECT_ID>.<DATASET_NAME>.<TABLE_NAME>") \
    .load()
```

#### Executing a BigQuery SQL query
The Spark BigQuery connector allows you to run Standard SQL SELECT queries
directly on BigQuery and load the results into a spark dataframe.
> [!IMPORTANT] You must enable views option to run direct queries

```python
# Define Standard SQL query
sql = """
  SELECT name, SUM(number) as total
  FROM `bigquery-public-data.usa_names.usa_1910_2013`
  GROUP BY name
  LIMIT 10
"""

df = spark.read.format("bigquery").option("viewsEnabled", "true").load(sql)
```

#### BigQuery Join Patterns
When enriching data with BigQuery reference tables:

```python
# Read BigQuery table directly (connector is built-in)
reference_df = spark.read.format("bigquery") \
    .option("table", "<PROJECT_ID>.<DATASET_NAME>.<TABLE_NAME>") \
    .load()

# Join with your main DataFrame
enriched_df = main_df.join(
    reference_df.select("entity_id", "entity_name", "category"),
    on="entity_id",
    how="left"
)
```

#### Optimization Tips

1. Select only needed columns from BigQuery

```python
ref_df = spark.read.format("bigquery") \
    .option("table", "<PROJECT_ID>.<DATASET_NAME>.<LARGE_TABLE_NAME>") \
    .option("filter", "active = true") \
    .load() \
    .select("id", "name")
```

2. Using broadcast joins for small reference tables

```python
from pyspark.sql.functions import broadcast

enriched_df = main_df.join(
    broadcast(small_ref_df),  # < 10MB
    on="key"
)
```

3. Cache reference data if used multiple times, example: `ref_df.cache()`

### Writing to BigQuery

#### Non partitioned data
Write DataFrame to BigQuery using direct writes,

 - Set writeMethod to direct
 - Set mode to one of `overwrite`, `append`, `errorifexists` based on task

```python
df.write \
    .format("bigquery") \
    .option("table", "<PROJECT_ID>.<DATASET_NAME>.<TABLE_NAME>") \
    .option("writeMethod", "direct") \
    .mode("overwrite") \
    .save()
```
#### Partitioned data
Write DataFrame to a partitioned BigQuery table using indirect writes. In
this method, data is written to GCS first and then loaded into BigQuery.
A GCS bucket is required as the temporary data location.

 - Set temporaryGcsBucket to a gcs bucket name
 - Set a check point path location

```python
df.write \
  .format("bigquery") \
  .option("temporaryGcsBucket","<STAGING_GCS_BUCKET>") \
  .option("checkpointLocation", "<STAGING_PATH>") \
  .save("<PROJECT_ID>.<DATASET_NAME>.<TABLE_NAME>")
```

## BigLake Iceberg Catalog

### Spark Session Configuration

- [!WARNING] BigLake Iceberg catalog must be configured in the spark session
  before tables can be read.
- Multiple Iceberg catalogs can be configured in the same spark session
-   [!IMPORTANT] You **MUST** identify the storage layer for the BigLake Iceberg
    table before configuring the spark session. Use
    `@skill:discovering-gcp-data-assets` to **search** and **lookup** the table
    details. Check the value for the `metadataPath` field from the lookup
    results to confirm it uses GCS storage (starts with `gs:`).
- [!WARNING] **DO NOT** assume catalog_name, project_id, io implementation for a
  table, **ALWAYS lookup** table details before proceeding.

#### Option A: Zero-Config (Preferred) — Session Template / Runtime Profile

When generating PySpark **notebook** code, assume the Dataproc kernel already
has the Iceberg catalog configured via its Session Template. **MUST NOT add
in-code catalog configuration.** Always use the simple `getOrCreate()` pattern:

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

##### Locating the Session Template and Catalog Name

Use this high-level routing algorithm to determine `<TEMPLATE_ID>` and
`<CATALOG_NAME>`:

-   **If `<TEMPLATE_ID>` is already known** (passed in prompt or present in
    existing code): go to **Case 1: Known Session Template**.
-   **If `<TEMPLATE_ID>` is unknown** (only table name, Dataplex entry, or
    warehouse is known): go to **Case 2: Unknown Session Template**.
-   **If no template matches or input is incomplete**: go to **Case 3: No
    Matching Template**.

###### Case 1: Known Session Template

Use the specified `<TEMPLATE_ID>`. If `<CATALOG_NAME>` is not already known from
the code, inspect the template's properties:

```bash
gcloud beta dataproc session-templates describe <TEMPLATE_NAME> \
    --project=<PROJECT_ID> --location=<REGION> \
    --format="json(runtimeConfig.properties)" \
  | jq '{defaultCatalog: .runtimeConfig.properties["spark.sql.defaultCatalog"], warehouses: (.runtimeConfig.properties | with_entries(select(.key | endswith(".warehouse"))))}'
```

-   If `spark.sql.defaultCatalog` is set, `<CATALOG_NAME>` can be omitted
    (`<NAMESPACE_NAME>.<TABLE_NAME>`).
-   If only one `spark.sql.catalog.<CATALOG_NAME>` is configured in the
    template, use that `<CATALOG_NAME>`
    (`<CATALOG_NAME>.<NAMESPACE_NAME>.<TABLE_NAME>`).
-   If multiple catalogs are configured, use the `<CATALOG_NAME>` whose
    `spark.sql.catalog.<CATALOG_NAME>.warehouse` matches the table's warehouse.

###### Case 2: Unknown Session Template

List templates in the project filtered by the table's warehouse URI (e.g.
`gs://<BUCKET>` from Dataplex `metadataPath`) to get both `<TEMPLATE_ID>` and
`<CATALOG_NAME>`:

```bash
gcloud beta dataproc session-templates list \
    --project=<PROJECT_ID> --location=<REGION> \
    --filter="runtimeConfig.properties:<WAREHOUSE_BUCKET_OR_URI>" \
    --format="json(name.basename(), runtimeConfig.properties)" \
  | jq '[.[] | {template: .name, defaultCatalog: .runtimeConfig.properties["spark.sql.defaultCatalog"], warehouses: (.runtimeConfig.properties | with_entries(select(.key | endswith(".warehouse"))))}]'
```

-   If multiple templates match, prefer the template where `defaultCatalog`
    matches the catalog name.

###### Case 3: No Matching Template

If no session template matches the warehouse, or if required inputs are missing:

-   **STOP and ask the user** which Session Template to use.
-   Do **NOT** guess `<CATALOG_NAME>` or add in-code `.config()` calls in
    notebooks.

#### Option B: Explicit In-Code Configuration

Use this only when no Session Template / Runtime Profile is available (e.g.
cluster and batch jobs, or environments without a pre-configured profile). You
**MUST NOT** use this in notebook code - ask user to configure and provide the
session template instead. Multiple Iceberg catalogs can be configured in the
same spark session.

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
        "spark.sql.catalog.<GCS_CATALOG_NAME>",
        "org.apache.iceberg.spark.SparkCatalog",
    )
    .config("spark.sql.catalog.<GCS_CATALOG_NAME>.type", "rest")
    .config(
        "spark.sql.catalog.<GCS_CATALOG_NAME>.uri",
        "https://biglake.googleapis.com/iceberg/v1/restcatalog",
    )
    .config(
        "spark.sql.catalog.<GCS_CATALOG_NAME>.warehouse",
        "gs://<GCS_CATALOG_NAME>",
    )
    .config(
        "spark.sql.catalog.<GCS_CATALOG_NAME>.header.x-goog-user-project",
        "<CATALOG_PROJECT_ID>",
    )
    .config(
        "spark.sql.catalog.<GCS_CATALOG_NAME>.rest.auth.type",
        "org.apache.iceberg.gcp.auth.GoogleAuthManager",
    )
    .config(
        "spark.sql.catalog.<GCS_CATALOG_NAME>.io-impl",
        "org.apache.iceberg.gcp.gcs.GCSFileIO",
    )
    .getOrCreate()
)
```

### Reading from BigLake Iceberg Catalog

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

### Writing to BigLake Iceberg Catalog

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
- **ALWAYS** Ensure namespace is created before writing, using:

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

#### Write Modes

- **DataFrameWriterV2 `createOrReplace()`**: Creates the table if it does not
    exist, or replaces it if it does.

    ```python
    (
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
        .using("iceberg")
        .createOrReplace()
    )
    ```

- **DataFrameWriterV2 `append()`**: Equivalent to `INSERT INTO`. Appends data to
    an existing table.

    ```python
    (
        df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>")
        .using("iceberg")
        .append()
    )
    ```

- **SPARK SQL MERGE INTO**: Performs row-level updates, inserts, and deletes by
    rewriting data files that contain affected rows. The source table can be
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

- [!WARNING] These are less preferred write modes, use them ONLY if explicitly
  asked to:
*   **`create()`**: Equivalent to `CREATE TABLE AS SELECT`. Fails if the table
    already exists.

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

#### Advanced Iceberg Writes

##### Writing with partitions
Use partitioning transform functions if writing to partitioned tables using
timestamp fields. Ex: years, months, days, hours etc.
Example: 

```python
from pyspark.sql.functions import days

df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
    .using("iceberg") \
    .partitionedBy("level", days("ts")) \
    .createOrReplace()
```

##### Schema Evolution
Iceberg supports safe schema evolution. You can merge schema changes during an
append.

```python
df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>") \
    .option("mergeSchema", "true") \
    .append()
```

##### Writing to a Specific Branch

```python
# To insert into an `audit` branch
df.writeTo("`<CATALOG_NAME>`.<NAMESPACE_NAME>.<TABLE_NAME>.branch_audit") \
    .append()
```

## Google Cloud Storage (GCS)
No session configuration is needed to read from GCS, all jars and
configuration are provided by default in Dataproc.

### Reading from GCS

#### CSV format
Read with `header` and `inferSchema` without these, the header row becomes data
and all columns are strings

```python
df = spark.read.option("header", "true") \
    .option("inferSchema", "true") \
    .csv("gs://<BUCKET>/<PATH_TO_CSV>")
```

#### Parquet format
`df = spark.read.parquet("gs://<BUCKET>/<PATH_TO_PARQUET>")`

#### Json format
`df = spark.read.json("gs://<BUCKET>/<PATH_TO_JSON>")`

### Writing to GCS

#### Csv format
`df.write.csv("gs://bucket/output_path")`

#### Model artifacts

```python
# Warehouse already includes gs://, don't add it again
warehouse = spark.conf.get(f"spark.sql.catalog.<CATALOG_NAME>.warehouse")
model_path = f"{warehouse}/models/my_model"
model.write().overwrite().save(model_path)
```

## Spanner
### Spark Session Configuration
The spanner jar must be configured in the spark session before tables can be
read. In the notebook code we can ONLY validate the spanner connector is
configured.
Example:

```python
spark = SparkSession.builder \
    .appName("<APP_NAME>") \
    .config(
        "spark.jars.packages",
        "gs://spark-lib/spanner/spark-3.5-spanner-1.3.0.jar",
    ) \
    .getOrCreate()
```

#### Reading Spanner tables

```python
df = spark.read.format('cloud-spanner') \
  .option("projectId", "<PROJECT_ID>") \
  .option("instanceId", "<INSTANCE_ID>") \
  .option("databaseId", "<DATABASE_ID>") \
  .option("table", "<TABLE_NAME>")
  .load()
```

### Writing to Spanner
The connector supports writing to Spanner tables using the DataFrame `write`
API.

#### Write Modes

*   **`Append`**: Inserts rows into the existing Spanner table. This is the
    default write mode.

    ```python
    df.write.format("cloud-spanner") \
        .option("projectId", "<PROJECT_ID>") \
        .option("instanceId", "<INSTANCE_ID>") \
        .option("databaseId", "<DATABASE_ID>") \
        .option("table", "<TABLE_NAME>") \
        .mode("append") \
        .save()
    ```

*   **`Overwrite`**: Clears the existing data before writing.

    ```python
    df.write.format("cloud-spanner") \
        .option("projectId", "<PROJECT_ID>") \
        .option("instanceId", "<INSTANCE_ID>") \
        .option("databaseId", "<DATABASE_ID>") \
        .option("table", "<TABLE_NAME>") \
        .mode("overwrite") \
        .save()
    ```

## Cloud SQL (PostgreSQL / MySQL)

### Reading from Cloud SQL via JDBC

> [!WARNING] NEVER embed plaintext secrets or passwords directly in code or
> scripts. Always retrieve credentials securely via environment variables (or
> Secret Manager).

```python
import os

password = os.environ.get("DB_PASSWORD", "")

df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://<HOST_OR_PRIVATE_IP>:5432/<DATABASE>") \
    .option("dbtable", "<TABLE_NAME>") \
    .option("user", "<USER>") \
    .option("password", password) \
    .option("driver", "org.postgresql.Driver") \
    .load()
```

## Google Cloud Pub/Sub

### Batch Ingestion via Pub/Sub Client

```python
from google.cloud import pubsub_v1
import json

subscriber = pubsub_v1.SubscriberClient()
sub = f"projects/{PROJECT_ID}/subscriptions/{SUBSCRIPTION_NAME}"
response = subscriber.pull(request={"subscription": sub, "max_messages": 100}, timeout=10.0)
records = [json.loads(m.message.data.decode("utf-8")) for m in response.received_messages]
if response.received_messages:
    subscriber.acknowledge(request={"subscription": sub, "ack_ids": [m.ack_id for m in response.received_messages]})
df = spark.createDataFrame(records)
```
