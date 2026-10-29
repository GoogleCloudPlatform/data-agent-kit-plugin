# Common Spark Migration Reference

Checks that apply to every job type when upgrading between Managed Spark image or runtime versions: the version mapping, component versions, connectors, GPU and RAPIDS compatibility, and the Spark migration notes between the source and target Spark versions. Checks that are specific to one job type (its language runtime, dependencies, and build checks) are in that job type's analysis reference, listed in the SKILL.md scope gate.

## Official sources

- Apache Spark migration guides:
  - Core: https://spark.apache.org/docs/latest/core-migration-guide.html
  - SQL: https://spark.apache.org/docs/latest/sql-migration-guide.html
  - Structured Streaming: https://spark.apache.org/docs/latest/streaming/ss-migration-guide.html
  - MLlib: https://spark.apache.org/docs/latest/ml-migration-guide.html
  - PySpark: https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html
- GCP Managed Spark release notes: https://docs.cloud.google.com/managed-spark/docs/release-notes

## Version to Spark Mapping

Map the source and target to Spark versions first, using the list for their deployment: the same version number can run a different Spark version on clusters and on Serverless (3.0, for example, runs Spark 4.1 on clusters and Spark 4.0 on Serverless). The lists give the Spark minor version; the patch version can change between sub-minor releases, so read it from "Component Versions".

### Managed Spark cluster images

- `1.3`: Spark 2.3, Python 2.7 / 3.6, Scala 2.11
- `1.4`: Spark 2.4, Python 3.6, Scala 2.11
- `1.5`: Spark 2.4, Python 3.7, Scala 2.12
- `2.0`: Spark 3.1, Python 3.8, Scala 2.12 (pandas 1.2, NumPy 1.19, PyArrow 3.0)
- `2.1`: Spark 3.3, Python 3.10, Scala 2.12 (pandas 1.4, NumPy 1.22, PyArrow 9.0)
- `2.2`: Spark 3.5, Python 3.11, Scala 2.12 (pandas 2.1, NumPy 1.26, PyArrow 14.0)
- `2.3`: Spark 3.5, Python 3.11, Scala 2.12 (pandas 2.1, NumPy 1.26, PyArrow 16.1)
- `3.0`: Spark 4.1, **Python 3.12** (3.11 in 3.0.0-RC2), Scala 2.13 (pandas 3.0, NumPy 2.4, PyArrow 19.0)

### Managed Spark Serverless runtimes

- `1.0`: Spark 3.2, Python 3.9, Scala 2.12
- `1.1`: Spark 3.3, Python 3.10, Scala 2.12
- `1.2`: Spark 3.5, **Python 3.12** (note: `distutils` is removed in Python 3.12), Scala 2.12 (pandas 2.2, NumPy 1.26, PyArrow 15.0)
- `2.0`: Spark 3.3, Python 3.10, Scala 2.13
- `2.1`: Spark 3.4, Python 3.11, Scala 2.13
- `2.2`: Spark 3.5, **Python 3.12** (note: `distutils` is removed in Python 3.12), Scala 2.13 (pandas 2.2, NumPy 1.26, PyArrow 15.0)
- `2.3`: Spark 3.5, Python 3.11, Scala 2.13 (pandas 2.2, NumPy 1.26, PyArrow 15.0)
- `3.0`: Spark 4.0, **Python 3.12**, Scala 2.13 (pandas 2.3, NumPy 2.1, PyArrow 19.0)

If a version isn't in its list, check the version list (https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters for clusters, https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-versions for Serverless): it may be newer than these lists, or it may not exist (e.g. a mistyped version), in which case ask the user to confirm it. Older versions can lose their own version page; their row on the version list still gives their components (as of the version's final release).

## Component Versions

Use the track component baselines above for quick analysis or when offline/read-only constraints apply. When exact sub-minor component versions are needed, look up the exact component versions (Spark, Java, Scala, Python, preinstalled libraries such as pandas, NumPy, and PyArrow, the Cloud Storage connector, and the BigQuery connector) on the version's documentation page:

- **Cluster**: `https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-<major.minor>` — read the column for the full image version (for the target, the version from SKILL.md Step 1.4).
- **Serverless**: `https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-<major.minor>` — read the newest release column (Serverless always runs the newest release).

For the source, use the column of the source version; if you know only its track, say which column you assumed.

## Connectors

1. Check the bundled Cloud Storage connector (https://github.com/GoogleCloudDataproc/hadoop-connectors) and Spark BigQuery connector (https://github.com/GoogleCloudDataproc/spark-bigquery-connector) versions from "Component Versions" for known bugs or breaking changes. If a known issue affects the workload, recommend an override or workaround.
2. If the job pins `gcs-connector` or `spark-bigquery-connector` (through `--jars`, `spark.jars.packages`, or its build dependencies), recommend removing the pin (so the image's compatible connector is used) or updating it to match the target's Spark and Scala versions. Read the Scala version from "Component Versions": it depends on the deployment as well as the Spark version (cluster image 2.2 uses Scala 2.12; Serverless runtime 2.2 and Spark 4.0 use Scala 2.13).

## GPU and RAPIDS Compatibility

If the source cluster or job uses GPUs or the RAPIDS Accelerator for Apache Spark (`com.nvidia.spark.SQLPlugin`):

1. **Identify the source setup:**
   - Accelerators on the master and worker nodes (e.g. `nvidia-tesla-t4`, `nvidia-l4`, `nvidia-tesla-a100`).
   - Initialization actions (e.g. `gs://goog-dataproc-initialization-actions-<REGION>/gpu/install_gpu_driver.sh` or `rapids/rapids.sh`).
   - Spark properties: `spark.plugins=com.nvidia.spark.SQLPlugin`, `spark.rapids.sql.enabled`, `spark.executor.resource.gpu.amount`, `spark.task.resource.gpu.amount`.
   - Jars: `rapids-4-spark_<scala_version>-<version>.jar` and `cudf-<version>-cuda<version>.jar`.
2. **Check against the target:**
   - **Spark and Scala:** the `rapids-4-spark_<scala_version>` jar must support the target Spark version and match its Scala version from "Component Versions" (e.g. for Dataproc 2.3 on Spark 3.5 / Scala 2.12, upgrade older `22.xx` jars to `24.12+` / `26.x`).
   - **Preconfigured ML image vs. init actions:** Recommend either switching to Dataproc's preconfigured ML image for the target track (e.g. `2.3-ml-ubuntu22` for Dataproc 2.3, which bundles compatible CUDA, cuDF, and RAPIDS out of the box) or updating the RAPIDS Accelerator plugin JAR (`rapids-4-spark_2.12-<version>.jar`) and driver initialization script to versions compatible with the target image.
   - **CUDA, driver, and OS:** newer images bundle newer OS kernels and default CUDA versions (e.g. CUDA 11.x → 12.x on 2.2+). The RAPIDS version must support the target CUDA runtime, the GPU driver, and the image distro (Debian, Ubuntu, or Rocky).
   - **cuDF:** starting with RAPIDS 23.08, the `cudf` jar is bundled inside the `rapids-4-spark` jar and must not be specified separately.
   - **Configs:** look for deprecated or removed `spark.rapids.*` properties between the source and target RAPIDS versions (https://nvidia.github.io/cudf-spark/docs/configs.html).
   - **Driver installation:** legacy `rapids.sh` or `install_gpu_driver.sh` scripts may fail on newer distros (e.g. Debian 12, Ubuntu 22.04). Check the recommended method for the target image in the [Managed Spark GPU guide](https://cloud.google.com/dataproc/docs/concepts/compute/gpus) and the [NVIDIA Spark RAPIDS on GCP guide](https://docs.nvidia.com/cudf-spark/latest/getting-started/google-cloud-dataproc.html).
3. **Remediate and plan verification:**
   - Update hardcoded `rapids-4-spark` jar URIs or versions (in `spark.jars`, `spark.jars.packages`, job arguments, or cluster configs) to a version compatible with the target (or use the preconfigured ML image where applicable, such as `2.3-ml-ubuntu22`).
   - Remove standalone `cudf-*.jar` references when moving to RAPIDS 23.08 or later.
   - Replace deprecated `spark.rapids.*` properties.
   - If initialization actions install RAPIDS, set the `rapids-version` metadata attribute on the target cluster to the compatible version.
   - **Verification planning (always mention when advising on GPU upgrades):**
     - Verify GPU accelerator availability in the target region/zone via `gcloud compute accelerator-types list --filter="name=<GPU_TYPE>"` and check regional GPU quota before creating the temporary verification cluster with matching worker accelerator configuration.
     - Isolate verification outputs to a temporary staging/target location (via CLI arguments or a temporary `_temp` copy of the script) so production output paths are never overwritten during testing, while preserving the original production output path in the final handed-over script.
     - Mandate deleting the temporary verification cluster (`gcloud dataproc clusters delete <CLUSTER_NAME> --region=<REGION> --quiet`) immediately after verification completes so expensive GPU nodes are not left running.

## Spark Migration Notes

Upgrades are **cumulative**: when upgrading across multiple versions (for example, Managed Spark 1.5 / Spark 2.4 directly to Managed Spark 3.0 / Spark 4.0+), apply **every** breaking change across all intermediate versions.

### High-Frequency Cumulative Breaking Changes (Always Check First)

1. **Spark 2.4 → Spark 3.0+ (Cluster 1.4/1.5 → 2.0+):**
   - **`SQLContext` / `HiveContext` deprecated/removed:** Replace `SQLContext(sc)` and `HiveContext(sc)` with `SparkSession.builder.appName(...).enableHiveSupport().getOrCreate()` (include `.enableHiveSupport()` whenever `HiveContext` or Hive tables are used).
   - **`registerTempTable` removed/deprecated:** Replace `df.registerTempTable("name")` with `df.createOrReplaceTempView("name")`.
   - **`DataFrame.unionAll` deprecated/removed:** Replace `df1.unionAll(df2)` with `df1.union(df2)`.
   - **`F.date_add` / `F.date_sub` second argument type enforcement:** The second argument (days offset) must be an integer type (`int` / `IntegerType` / `ShortType`); string or float columns fail. Explicitly cast non-integer columns, e.g. `F.date_add(F.col("txn_date"), F.col("offset_days").cast("int"))`.
   - **Proleptic Gregorian calendar:** Date/timestamp parsing and formatting in `datetimePattern` became stricter in Spark 3.0+.

2. **Spark 3.1 → Spark 3.2+ / 3.3+ (Cluster 2.0 → 2.1+):**
   - **Koalas replaced by native Pandas API on Spark:** Replace `import databricks.koalas as ks` with `import pyspark.pandas as ps` (and update `ks.` calls to `ps.`).

3. **Spark 3.3 → Spark 3.5+ (Cluster 2.1 / Serverless 1.1 → Cluster 2.2+ / Serverless 1.2, 2.2+):**
   - **YARN executor failure validity config replaced:** Replace the deprecated/removed property `spark.yarn.executor.failuresValidityInterval` with the cluster-manager-agnostic `spark.executor.failuresValidityInterval`.

4. **Spark 3.x → Spark 4.0+ (Cluster 2.x / Serverless 2.x → 3.0):**
   - **ANSI SQL mode enabled by default (`spark.sql.ansi.enabled=true`):** In Spark 4.0+, invalid casts (such as `CAST(amount_str AS INT)` on malformed strings) or arithmetic errors throw runtime exceptions instead of returning `NULL`. Always address this in SQL/DataFrame casts when upgrading to 3.0: either replace `CAST(<col> AS <type>)` with `TRY_CAST(<col> AS <type>)` in the SQL/DataFrame query (preferred per SKILL.md rule 2), or set `spark.sql.ansi.enabled=false` (and document the legacy flag).
   - **Default `CREATE TABLE` provider changed from Hive to Parquet (`spark.sql.sources.default`):** In Spark 4.0+, `spark.sql.legacy.createHiveTableByDefault` is `false`, so an unqualified `CREATE TABLE [IF NOT EXISTS] db.tbl AS SELECT ...` creates a DataSource (Parquet) table instead of a Hive table. To keep creating a Hive table on Spark 4.0+, explicitly add `USING hive` (e.g. `CREATE TABLE IF NOT EXISTS db.tbl USING hive AS SELECT ...`) or a `STORED AS` clause.

### Additional Official Migration Guides

If the workload uses additional APIs not covered in the checklist above (e.g. Structured Streaming watermarks, MLlib estimators, or specialized SQL functions), consult the relevant section of the official migration guides listed in "Official sources" for the source-to-target version range. Avoid redundant web searches for the standard items already covered above.
