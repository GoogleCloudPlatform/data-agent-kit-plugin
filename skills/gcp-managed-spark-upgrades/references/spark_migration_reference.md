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

- 1.3: Spark 2.3
- 1.4: Spark 2.4
- 1.5: Spark 2.4
- 2.0: Spark 3.1
- 2.1: Spark 3.3
- 2.2: Spark 3.5
- 2.3: Spark 3.5
- 3.0: Spark 4.1

### Managed Spark Serverless runtimes

- 1.0: Spark 3.2
- 1.1: Spark 3.3
- 1.2: Spark 3.5
- 2.0: Spark 3.3
- 2.1: Spark 3.4
- 2.2: Spark 3.5
- 2.3: Spark 3.5
- 3.0: Spark 4.0

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
   - **Configs:** look for deprecated or removed `spark.rapids.*` properties between the source and target RAPIDS versions (https://nvidia.github.io/cudf-spark/docs/configs.html).
   - **Driver installation:** legacy `rapids.sh` or `install_gpu_driver.sh` scripts may fail on newer distros (e.g. Debian 12, Ubuntu 22.04). Check the recommended method for the target image in the [Managed Spark GPU guide](https://cloud.google.com/dataproc/docs/concepts/compute/gpus) and the [NVIDIA Spark RAPIDS on GCP guide](https://docs.nvidia.com/cudf-spark/latest/getting-started/google-cloud-dataproc.html).
3. **Remediate:**
   - Update hardcoded `rapids-4-spark` jar URIs or versions (in `spark.jars`, `spark.jars.packages`, job arguments, or cluster configs) to a version compatible with the target (or use the preconfigured ML image where applicable).
   - Remove standalone `cudf-*.jar` references when moving to RAPIDS 23.08 or later.
   - Replace deprecated `spark.rapids.*` properties.
   - If initialization actions install RAPIDS, set the `rapids-version` metadata attribute on the target cluster to the compatible version.
   - For new Spark versions, check whether a shim provider override (`spark.rapids.shims-provider-override`) is needed.

## Spark Migration Notes

This skill doesn't keep a list of Spark breaking changes, which would go stale. Look them up for the exact source and target Spark versions ("Component Versions"):

1. **Look up the changes.** Open each migration guide listed in "Official sources". Each guide keeps the sections of all earlier releases. Read every "Upgrading from … X to Y" section where Y is newer than the source Spark version and not newer than the target: upgrades are cumulative. Web fetch tools can truncate these long pages; if a page is cut off, download it and read it in full. Name any guide you couldn't read in the report.
2. **Check every note.** Check each note in those sections against the code, its dependency manifests, Spark properties, and job arguments; don't skip notes by guessing their importance. Each note that applies is a finding, fixed as SKILL.md rule 2 describes; a note about a feature the job doesn't use needs no change.
