---
name: gcp-spark
description: >-
  Runs PySpark/Spark/BigFrames on Managed Spark (Dataproc clusters, Serverless,
  notebooks, and jobs). Use when authoring or running Spark notebooks, batches,
  or clusters. Don't use for observability (@skill:gcp-spark-observability) or
  troubleshooting (@skill:gcp-spark-troubleshooting).
license: Apache-2.0
metadata:
  version: v32
  publisher: google
---
# Managed Spark on Google Cloud
## Env: NEVER modify local env (no venvs/installs/probing); user selects kernel.
## Task Execution Workflow
1. Kernel: Clarify "Local Python"/"Remote Spark" & session template if Local.
2. **Schemas**: ALWAYS use `@skill:discovering-gcp-data-assets` or
   `references/schema_direct_inspection.md` (no guessing; max 3 retries).
   *MISSING SOURCE*: If unnamed, <=1 search; if not 1 match, list candidates,
   ask user which to use, and STOP. *MINOR TYPO*: Fix and proceed.
   *STRICT HALT*: If table differs by >typo, report missing & neutral list;
   ask user which to use & STOP. No code/fallbacks without user permission.
3. **Verify source**: `gcloud storage ls gs://<path-to-dataset>`. On storage
   error (403/404/PermissionDenied/NotFound), report immediately; ask user or
   save notebook with error. Do NOT scan all buckets for fallback datasets.
4. **Generate spark code**: ALWAYS Notebooks (.ipynb); .py on request (no local).
   - Connect: MUST `ManagedSparkSession.builder.projectId(...).location(...)`
     `.getOrCreate()`. Batch: `SparkSession.builder.appName(...).getOrCreate()`
     via `gcloud dataproc batches submit pyspark` or `jobs submit pyspark`
     (see `references/gcloud_dataproc.md`). MUST `broadcast()` (~10 MB).
   - Batch: `logging.basicConfig(level=INFO)`; nb: `print()`. Secrets via
     Secret Manager (`references/jdbc_cloudsql.md`).
   - Refs: `references/read_write_data.md`, `references/spanner.md`,
     `references/biglake_iceberg.md`, `references/spark_optimizations.md`,
     `references/ml_tasks.md`, `@skill:ml-best-practices`.
5. **Verify schema**: `df.printSchema()` vs Step 2 discovery references.
6. **Compile & Run**: `jupyter nbconvert --to script <nb>.ipynb` &&
   `python3 -m py_compile <script>.py`. Ask user to select kernel dropdown.
## Mistakes: `from pyspark.ml.functions import vector_to_array` (NOT sql).
- CSV: `header`/`inferSchema`. NEVER `toPandas()`, `collect()`, or `read_file`.
- Deps: `--py-files`, `--container-image`, `--archives=gs://...#env`,
  `--properties=spark.jars.packages=...`.
## IAM: `roles/dataproc.worker`, `roles/biglake.admin`, `roles/bigquery.jobUser`,
`roles/bigquery.dataEditor`, `roles/bigquery.readSessionUser`,
`roles/storage.objectUser`, `roles/spanner.databaseUser`,
`roles/secretmanager.secretAccessor`.
## Spark resource management & observability: see `references/gcloud_dataproc.md` and `@skill:gcp-spark-observability`.
## Optimization: check `references/spark_refactoring_guide.md` with user.
## Troubleshooting & RCA: use `@skill:gcp-spark-troubleshooting`.
