# Common Spark Migration Reference

Checks that apply to every job type when upgrading between Managed Spark image or runtime versions: the version mapping, component versions, connectors, GPU and RAPIDS compatibility, and Spark breaking changes by Spark version. Checks that are specific to one job type (its language runtime, dependencies, and build checks) are in that job type's analysis reference, listed in the SKILL.md scope gate.

## Official sources

Start with the curated checks below. When the workload uses Spark SQL/Core APIs, properties, or platform behaviors not covered in the sections below—or when a build check or verification run fails with an unfamiliar error—fetch and check the intermediate version sections in these official guides:

- Spark SQL, Datasets and DataFrame migration guide: https://spark.apache.org/docs/latest/sql-migration-guide.html
- Spark Core migration guide: https://spark.apache.org/docs/latest/core-migration-guide.html
- GCP Managed Spark release notes: https://docs.cloud.google.com/managed-spark/docs/release-notes

## Version to Spark Mapping

Map the source and target to Spark versions first, using the list for their deployment: the same version number can run a different Spark version on clusters and on Serverless (3.0, for example, runs Spark 4.1 on clusters and Spark 4.0 on Serverless). The lists give the Spark minor version, which decides the sections of "Common Breaking Changes by Spark Version" that apply; the patch version can change between sub-minor releases, so read it from "Component Versions".

### Track 1.0
- Managed Spark cluster image: —
- Managed Spark Serverless runtime: Spark 3.2

### Track 1.1
- Managed Spark cluster image: —
- Managed Spark Serverless runtime: Spark 3.3

### Track 1.2
- Managed Spark cluster image: —
- Managed Spark Serverless runtime: Spark 3.5

### Track 1.3
- Managed Spark cluster image: Spark 2.3
- Managed Spark Serverless runtime: —

### Track 1.4
- Managed Spark cluster image: Spark 2.4
- Managed Spark Serverless runtime: —

### Track 1.5
- Managed Spark cluster image: Spark 2.4
- Managed Spark Serverless runtime: —

### Track 2.0
- Managed Spark cluster image: Spark 3.1
- Managed Spark Serverless runtime: Spark 3.3

### Track 2.1
- Managed Spark cluster image: Spark 3.3
- Managed Spark Serverless runtime: Spark 3.4

### Track 2.2
- Managed Spark cluster image: Spark 3.5
- Managed Spark Serverless runtime: Spark 3.5

### Track 2.3
- Managed Spark cluster image: Spark 3.5
- Managed Spark Serverless runtime: Spark 3.5

### Track 3.0
- Managed Spark cluster image: Spark 4.1
- Managed Spark Serverless runtime: Spark 4.0

If a version isn't in its list, check the version list (https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters for clusters, https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-versions for Serverless): it may be newer than these lists, or it may not exist (e.g. a mistyped version), in which case ask the user to confirm it. Older versions can lose their own version page; their row on the version list still gives their components (as of the version's final release).

## Component Versions

Don't rely on static tables: look up the exact component versions (Spark, Java, Scala, Python, preinstalled libraries such as pandas, NumPy, and PyArrow, the Cloud Storage connector, and the BigQuery connector) on the version's documentation page:

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
   - **Spark and Scala:** the `rapids-4-spark_<scala_version>` jar must support the target Spark version and match its Scala version from "Component Versions".
   - **CUDA, driver, and OS:** newer images bundle newer OS kernels and default CUDA versions (e.g. CUDA 11.x → 12.x on 2.2+). The RAPIDS version must support the target CUDA runtime, the GPU driver, and the image distro (Debian, Ubuntu, or Rocky).
   - **cuDF:** starting with RAPIDS 23.08, the `cudf` jar is bundled inside the `rapids-4-spark` jar and must not be specified separately.
   - **Configs:** look for deprecated or removed `spark.rapids.*` properties between the source and target RAPIDS versions (https://docs.nvidia.com/spark-rapids/user-guide/latest/configs.html).
   - **Driver installation:** legacy `rapids.sh` or `install_gpu_driver.sh` scripts may fail on newer distros (e.g. Debian 12, Ubuntu 22.04). Check the recommended method for the target image in the [Managed Spark GPU guide](https://cloud.google.com/dataproc/docs/concepts/compute/gpus) and the [NVIDIA Spark RAPIDS on GCP guide](https://docs.nvidia.com/spark-rapids/user-guide/latest/getting-started/gcp.html).
   - **Regional availability and quota:** verify that the GPU accelerator type (`nvidia-tesla-t4`, `nvidia-l4`, etc.) is available in the target region/zone (`gcloud compute accelerator-types list --filter="name=<GPU_TYPE>"`) and that sufficient regional GPU quota exists before creating a verification cluster.
3. **Remediate:**
   - Update hardcoded `rapids-4-spark` jar URIs or versions (in `spark.jars`, `spark.jars.packages`, job arguments, or cluster configs) to a version compatible with the target (or use the preconfigured ML image where applicable).
   - Remove standalone `cudf-*.jar` references when moving to RAPIDS 23.08 or later.
   - Replace deprecated `spark.rapids.*` properties.
   - If initialization actions install RAPIDS, set the `rapids-version` metadata attribute on the target cluster to the compatible version.
   - For new Spark versions, check whether a shim provider override (`spark.rapids.shims-provider-override`) is needed.
   - On the temporary verification cluster (Step 2), match the source worker accelerator configuration, isolate test output to `<target_path>/test-output_<app_id>_temp/`, and delete the GPU cluster (`gcloud dataproc clusters delete`) immediately after verification completes.

## Common Breaking Changes by Spark Version

> [!NOTE]
> **Upgrades are cumulative.** Apply **every** section below whose range lies between the source and target Spark versions. For example, cluster image 1.5 → 3.0 (Spark 2.4 → 4.1) needs every section between Spark 2.4 and 4.1, while Serverless runtime 2.0 → 2.2 (Spark 3.3 → 3.5) needs only "Spark 3.3 → 3.5". The sections are keyed by Spark version because the same track number can run a different Spark version on clusters and on Serverless. For any part of the upgrade that no section covers (such as a newer Spark release), review the intermediate versions in the official migration guides above. Language-specific breaking changes (e.g. PySpark) are in the job type's analysis reference.

### Spark 2.4 → 3.0/3.1

- **Calendar system:** changed to Proleptic Gregorian in Spark 3.0. Date and timestamp parsing, formatting, and Parquet/Avro timestamp rebasing might behave differently.
- **SQLContext/HiveContext:** `HiveContext` (deprecated in 2.0) and `SQLContext` (`new SQLContext(sc)` deprecated in 2.0; `SQLContext` deprecated in PySpark 3.0) should be replaced with `SparkSession.builder` (with `.enableHiveSupport()` where `HiveContext` was used).
- **spark.mllib:** RDD-based `spark.mllib` is in maintenance mode in favor of DataFrame-based `spark.ml`.
- **date_add/date_sub:** the second argument must be an integer (`IntegerType`, `ShortType`, or `ByteType`); floats and non-literal strings are rejected with `AnalysisException`.

### Spark 3.1 → 3.3

- **Log4j 2 migration:** Spark 3.3 migrates from Log4j 1.x (`log4j.properties`) to Log4j 2.x (`log4j2.properties`). Custom Log4j 1.x configuration files or `-Dlog4j.configuration=...` JVM options must be rewritten for Log4j 2 (`-Dlog4j2.configurationFile=...`).

### Spark 3.3 → 3.5

- **YARN configs:** YARN-specific executor failure configs are deprecated in Spark 3.5 in favor of general Spark executor configs (`spark.yarn.executor.failuresValidityInterval` → `spark.executor.failuresValidityInterval`, `spark.yarn.max.executor.failures` → `spark.executor.maxNumFailures`).

### Spark 3.5 → 4.0

- **ANSI SQL by default:** `spark.sql.ansi.enabled` now defaults to `true`, so stricter SQL semantics apply: division by zero, invalid casts, and overflow throw runtime exceptions instead of returning `NULL`. Where the affected expressions are identifiable, keep the old results with `try_cast`, `try_divide`, or other `try_*` functions. If the job has SQL you can't audit, set `spark.sql.ansi.enabled=false` and list it in the report as a legacy flag.
- **Table provider:** Spark 4.0 sets `spark.sql.legacy.createHiveTableByDefault` to `false`, so `CREATE TABLE` (including `CREATE TABLE ... AS SELECT`) without a `USING` or `STORED AS` clause creates a data source table in the `spark.sql.sources.default` format (Parquet) instead of a Hive table. **Remediation:** add `USING hive` (or a `STORED AS <format>` clause) to each such statement so it keeps creating Hive tables. Set `spark.sql.legacy.createHiveTableByDefault=true` only if the DDL can't be edited (for example, SQL generated outside the job), because legacy flags can be removed in later Spark releases.
- **Removed legacy datetime rebase configs:** `spark.sql.legacy.parquet.datetimeRebaseModeInRead`/`Write`, `spark.sql.legacy.parquet.int96RebaseModeInRead`/`Write`, and `spark.sql.legacy.avro.datetimeRebaseModeInRead`/`Write` are removed in Spark 4.0. Replace them with the non-legacy `spark.sql.parquet.*` and `spark.sql.avro.*` equivalents.

### Spark 4.0 → 4.1

- **Removed `*.blacklist.*` configs:** Spark 4.1 ignores legacy `*.blacklist.*` configuration names (deprecated since Spark 3.1). Replace them with the corresponding `spark.excludeOnFailure.*` configs.
