# Definitive Guide to Reading and Writing Data in PySpark

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow when writing spark code.

## Task Execution Workflow

1. Configure the spark session to read or write data from the required source
   or destination.
2. Read or write the data from the required source or destination.

## Connector Reference Routing

Load only the reference file(s) needed for your target data source or
destination:

-   **BigQuery, Google Cloud Storage (GCS), & Pub/Sub**: Covered below in this
    file (`references/read_write_data.md`).
-   **BigLake Iceberg Catalog**: Refer to `references/biglake_iceberg.md`.
-   **Cloud Spanner**: Refer to `references/spanner.md`.
-   **JDBC & Cloud SQL (PostgreSQL / MySQL) & Secret Manager Credentials**:
    Refer to `references/jdbc_cloudsql.md`.
-   **Amazon S3 (`s3a://` / S3-compatible object storage)**: Refer to
    `references/aws_s3.md`.
-   **Azure Blob Storage & ADLS Gen2 (`abfss://`, `wasbs://`, `wasb://`)**:
    Refer to `references/azure_storage.md`.

--------------------------------------------------------------------------------

## BigQuery

### Spark Session Configuration

On Managed Spark on Google Cloud (Dataproc Serverless and Dataproc Clusters),
BigQuery connector JARs (`spark-bigquery-with-dependencies`) are pre-installed
in the runtime environment. Do **NOT** pass `com.google.cloud.spark:spark-*-bigquery`
via `spark.jars.packages` when running on Dataproc.

-   **Interactive Notebooks (`.ipynb`) & Spark Connect**: Initialize with
    `ManagedSparkSession` (see `SKILL.md`).
-   **Dataproc Batch & Cluster Jobs (`.py`)**: Initialize with standard
    `SparkSession.builder` (see `SKILL.md`).

### Reading from BigQuery

#### Basic example to read a BigQuery table

```python
df = spark.read.format("bigquery") \
    .option("table", "<PROJECT_ID>.<DATASET_NAME>.<TABLE_NAME>") \
    .load()
```

#### Executing a BigQuery SQL query

The Spark BigQuery connector allows you to run Standard SQL SELECT queries
directly on BigQuery and load the results into a spark dataframe.

> [!IMPORTANT] You must set `viewsEnabled` to `"true"` and specify a writable
> `materializationDataset` in your project to run direct SQL queries or read
> BigQuery views.

```python
# Define Standard SQL query
sql = """
  SELECT name, SUM(number) as total
  FROM `bigquery-public-data.usa_names.usa_1910_2013`
  GROUP BY name
  LIMIT 10
"""

df = (
    spark.read.format("bigquery")
    .option("viewsEnabled", "true")
    .option("materializationDataset", "<DATASET_NAME>")
    .load(sql)
)
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

1. Select only needed columns from BigQuery:

```python
ref_df = spark.read.format("bigquery") \
    .option("table", "<PROJECT_ID>.<DATASET_NAME>.<LARGE_TABLE_NAME>") \
    .option("filter", "active = true") \
    .load() \
    .select("id", "name")
```

2. Using broadcast joins for small reference tables:

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

Write DataFrame to BigQuery using direct writes:

- Set `writeMethod` to `direct`
- Set `mode` to one of `overwrite`, `append`, `errorifexists` based on task

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
A GCS bucket is required as the temporary data location:

- Set `temporaryGcsBucket` to a GCS bucket name
- Set a `checkpointLocation` path

```python
df.write \
  .format("bigquery") \
  .option("temporaryGcsBucket", "<STAGING_GCS_BUCKET>") \
  .option("checkpointLocation", "<STAGING_PATH>") \
  .save("<PROJECT_ID>.<DATASET_NAME>.<TABLE_NAME>")
```

## Google Cloud Storage (GCS)

No session configuration is needed to read from GCS; all JARs and
configuration are provided by default in Dataproc.

### Reading from GCS

#### CSV format

Read with `header` and `inferSchema`; without these, the header row becomes data
and all columns are strings:

```python
df = spark.read.option("header", "true") \
    .option("inferSchema", "true") \
    .csv("gs://<BUCKET>/<PATH_TO_CSV>")
```

#### Parquet format

`df = spark.read.parquet("gs://<BUCKET>/<PATH_TO_PARQUET>")`

#### JSON format

`df = spark.read.json("gs://<BUCKET>/<PATH_TO_JSON>")`

### Writing to GCS

#### CSV format

`df.write.csv("gs://bucket/output_path")`

#### Model artifacts

```python
# Warehouse already includes gs://, don't add it again
warehouse = spark.conf.get("spark.sql.catalog.<CATALOG_NAME>.warehouse")
model_path = f"{warehouse}/models/my_model"
model.write().overwrite().save(model_path)
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
