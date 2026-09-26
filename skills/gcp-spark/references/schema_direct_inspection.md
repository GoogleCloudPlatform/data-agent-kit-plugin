# Direct Inspection of table schema

## For BigQuery, Spanner and BigLake Iceberg tables and views

Biglake tables are often specified in format `catalog.schema.table`, the first
segment is the **Catalog Name**, NOT a GCP project ID.

Prefer using `@skill:discovering-gcp-data-assets` skill to find and lookup
schema and use the following examples as a fallback mechanisms:

### 1. Cloud Spanner

```sh
gcloud spanner databases ddl describe <DATABASE_ID> --instance=<INSTANCE_ID> --project=<PROJECT_ID>
```

### 2. BigQuery/Biglake

```bash
bq show --schema --format=prettyjson <PROJECT_ID>:<DATASET_ID>.<TABLE_NAME>
```

### 3. Cloud SQL (PostgreSQL / MySQL)

```bash
gcloud sql instances describe <INSTANCE_ID> --project=<PROJECT_ID>
```

## For GCS bucket or folder exploration

If the user specifies a GCS bucket or folder instead of specific files, you
**MUST** explore the folder contents first to identify relevant files using
`gcloud storage objects list "gs://<GCS_BUCKET>/<PATH>/**" --limit=100
--format="value(name)"` command. In case of errors, cap GCS discovery attempts
at **3 retries max**.

## For CSV file

Peek first row of CSV file

### For CSV file in GCS

Use `gcloud storage cat gs://bucket/file.csv | head -n 1`

### For local CSV file
Use `head -n 1 file.csv`
