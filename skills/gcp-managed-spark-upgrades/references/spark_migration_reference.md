# Common Spark Migration Reference

Checks that apply to every job type when upgrading between Managed Spark image
or runtime versions: the version mapping, component versions, the Java runtime,
connectors, GPU and RAPIDS compatibility, and the Spark migration notes between
the source and target Spark versions. Checks that are specific to one job type
(its language runtime, dependencies, and build checks) are in that job type's
analysis references, listed in the SKILL.md scope gate.

## Official sources

-   Apache Spark migration guides: `fetch_migration_notes.py` downloads the
    sections that apply ("Spark Migration Notes"). Open a published guide only
    if the script reports that it couldn't download it.
-   JDK Migration Guide, one per Java release, covering the changes of every
    release since JDK 8:
    `https://docs.oracle.com/en/java/javase/<java_version>/migrate/` (e.g.
    `.../javase/21/migrate/`)
-   The `java` command reference of each Java release, whose "Obsolete Java
    Options" and "Removed Java Options" sections list the JVM options that the
    release ignores or removed, and link to the same sections of earlier
    releases:
    `https://docs.oracle.com/en/java/javase/<java_version>/docs/specs/man/java.html`
- GCP Managed Spark release notes: https://docs.cloud.google.com/managed-spark/docs/release-notes

## Version to Spark Mapping

Map the source and target to Spark versions first, using the list for their
deployment: the same version number can run a different Spark or Java version on
clusters and on Serverless (3.0, for example, runs Spark 4.1 on clusters and
Spark 4.0 on Serverless, and 2.2 runs Java 11 on clusters and Java 17 on
Serverless). The lists give the Spark minor version; the patch version can
change between sub-minor releases, so read it from "Component Versions".

### Managed Spark cluster images

-   `1.3`: Spark 2.3, Java 8, Python 2.7 / 3.6, Scala 2.11
-   `1.4`: Spark 2.4, Java 8, Python 3.6, Scala 2.11
-   `1.5`: Spark 2.4, Java 8, Python 3.7, Scala 2.12
-   `2.0`: Spark 3.1, Java 8, Python 3.8, Scala 2.12 (pandas 1.2, NumPy 1.19,
    PyArrow 3.0)
-   `2.1`: Spark 3.3, Java 11, Python 3.10, Scala 2.12 (pandas 1.4, NumPy 1.22,
    PyArrow 9.0)
-   `2.2`: Spark 3.5, Java 11, Python 3.11, Scala 2.12 (pandas 2.1, NumPy 1.26,
    PyArrow 14.0)
-   `2.3`: Spark 3.5, Java 11, Python 3.11, Scala 2.12 (pandas 2.1, NumPy 1.26,
    PyArrow 16.1)
-   `3.0`: Spark 4.1, Java 21, Python 3.12 (3.11 in 3.0.0-RC2), Scala 2.13
    (pandas 3.0, NumPy 2.4, PyArrow 19.0)

### Managed Spark Serverless runtimes

-   `1.0`: Spark 3.2, Java 11, Python 3.9, Scala 2.12
-   `1.1`: Spark 3.3, Java 11, Python 3.10, Scala 2.12
-   `1.2`: Spark 3.5, Java 17, Python 3.12, Scala 2.12 (pandas 2.2, NumPy 1.26,
    PyArrow 15.0)
-   `2.0`: Spark 3.3, Java 17, Python 3.10, Scala 2.13
-   `2.1`: Spark 3.4, Java 17, Python 3.11, Scala 2.13
-   `2.2`: Spark 3.5, Java 17, Python 3.12, Scala 2.13 (pandas 2.2, NumPy 1.26,
    PyArrow 15.0)
-   `2.3`: Spark 3.5, Java 17, Python 3.11, Scala 2.13 (pandas 2.2, NumPy 1.26,
    PyArrow 15.0)
-   `3.0`: Spark 4.0, Java 21, Python 3.12, Scala 2.13 (pandas 2.3, NumPy 2.1,
    PyArrow 19.0)

If a version isn't in its list, check the version list (https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters for clusters, https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-versions for Serverless): it may be newer than these lists, or it may not exist (e.g. a mistyped version), in which case ask the user to confirm it. Older versions can lose their own version page; their row on the version list still gives their components (as of the version's final release).

## Component Versions

Use the track component baselines above for quick analysis or when offline/read-only constraints apply. When exact sub-minor component versions are needed, look up the exact component versions (Spark, Java, Scala, Python, preinstalled libraries such as pandas, NumPy, and PyArrow, the Cloud Storage connector, and the BigQuery connector) on the version's documentation page:

- **Cluster**: `https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-<major.minor>` — read the column for the full image version (for the target, the version from SKILL.md Step 1.4).
- **Serverless**: `https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-<major.minor>` — read the newest release column (Serverless always runs the newest release).

For the source, use the column of the source version; if you know only its track, say which column you assumed.

## Java Runtime

Every job runs on the target's Java, PySpark and Spark SQL jobs included:
Spark's driver and executors are JVMs. Take the source's and the target's Java
versions from the list for their deployment in "Version to Spark Mapping"
(confirm them on the component pages, where those still exist);
`fetch_migration_notes.py` also prints the Java versions that each Spark version
supports. A job or cluster can override the image's Java through `JAVA_HOME`
(e.g. `spark.executorEnv.JAVA_HOME` and `spark.yarn.appMasterEnv.JAVA_HOME`, or
an initialization action that installs another JDK): then the source ran on that
Java, and the report says whether the target still needs the override. If the
Java version changes:

-   **JVM options.** Check the options in `spark.driver.extraJavaOptions`,
    `spark.executor.extraJavaOptions`, their `defaultJavaOptions` counterparts,
    and on clusters `spark.yarn.am.extraJavaOptions`, whether the job, the
    cluster properties (`spark:` prefix), or an initialization action sets them.
    An option that the target's Java removed stops the JVM from starting
    (`Unrecognized VM option`, `Could not create the Java Virtual Machine`), and
    one that it made obsolete is ignored with a warning. Look each `-X` and
    `-XX:` option up in the `java` command reference ("Official sources") of
    every release after the source's Java, up to the target's, and run it as
    `java <option> -version` on a JDK of the target's version if one is
    installed: an error or a warning is a finding. Remove or replace every
    option that the target rejects or ignores, and report the change.
-   **Code and libraries.** The JDK Migration Guide ("Official sources") lists
    the significant changes and removed APIs of each release: the releases after
    the source's Java version apply. For Scala/Java jobs (and Spark SQL jobs
    that attach custom UDF/SerDe jars), `jvm_build_reference.md` checks the
    job's code and jars against them.

## Connectors

The target image or runtime preinstalls the Cloud Storage connector
(https://github.com/GoogleCloudDataproc/hadoop-connectors) and, if its component
page lists it, the Spark BigQuery connector
(https://github.com/GoogleCloudDataproc/spark-bigquery-connector), built for its
Spark and Scala versions; "Component Versions" lists their versions. Rely on
these platform defaults first:

1.  Check the preinstalled connector versions for known bugs or breaking
    changes. If a known issue affects the workload, recommend a workaround or a
    connector override (step 3).
2.  If the job pins a connector, remove the pin so that the preinstalled
    connector is used: the Maven artifacts
    `com.google.cloud.bigdataoss:gcs-connector` and
    `com.google.cloud.spark:spark-bigquery*` or `spark-<x.y>-bigquery`, or their
    jars, in `jarFileUris` or `--jars`, `ADD JAR`, `spark.jars`,
    `spark.jars.packages`, initialization actions, a custom image, or the build
    dependencies. Never supply a second copy of a preinstalled connector: it
    collides with the platform's (e.g. `Multiple sources found for bigquery`),
    relocated or not. For Scala/Java jobs that compile against a connector,
    `jvm_build_reference.md` describes how to do that without bundling it.
3.  Keep or set another connector version only when the workload needs a fix or
    feature that the preinstalled version lacks, and record why in the report.
    Select it through the platform rather than in the job:

    -   on clusters, with the `SPARK_BQ_CONNECTOR_VERSION` (or
        `SPARK_BQ_CONNECTOR_URL`) and `GCS_CONNECTOR_VERSION` metadata, which
        takes effect when the cluster is created: set it on the Step 2 cluster,
        and list it in the report's production configuration;
    -   on Serverless 2.3 and earlier, with the
        `dataproc.sparkBqConnector.version` and `dataproc.gcsConnector.version`
        properties; on Serverless 3.0 and later (which no longer supports those
        version properties), remove the preinstalled BigQuery connector with
        `dataproc.artifacts.remove=spark-bigquery-connector` before passing a
        custom BigQuery connector jar
        (https://docs.cloud.google.com/managed-spark/docs/concepts/spark-properties-serverless).

    If the platform doesn't preinstall the connector (or after removing the
    preinstalled connector via `dataproc.artifacts.remove`), pass the
    connector's own jar, built for the target's Spark and Scala versions. The
    Scala version depends on the deployment as well as the Spark version: read
    it from "Version to Spark Mapping".

## GPU and RAPIDS Compatibility

If the source cluster or job uses GPUs or the RAPIDS Accelerator for Apache Spark (`com.nvidia.spark.SQLPlugin`):

1. **Identify the source setup:**
   - Accelerators on the master and worker nodes (e.g. `nvidia-tesla-t4`, `nvidia-l4`, `nvidia-tesla-a100`).
   - Initialization actions (e.g. `gs://goog-dataproc-initialization-actions-<REGION>/gpu/install_gpu_driver.sh` or `rapids/rapids.sh`).
   - Spark properties: `spark.plugins=com.nvidia.spark.SQLPlugin`, `spark.rapids.sql.enabled`, `spark.executor.resource.gpu.amount`, `spark.task.resource.gpu.amount`.
   - Jars: `rapids-4-spark_<scala_version>-<version>.jar` and `cudf-<version>-cuda<version>.jar`.
2. **Check against the target:**
    -   **Spark and Scala:** the `rapids-4-spark_<scala_version>` jar must
        support the target Spark version and match its Scala version from
        "Component Versions" (e.g. for Dataproc 2.3 on Spark 3.5 / Scala 2.12,
        upgrade older `22.xx` jars to `24.12+` / `26.x`).
    -   **Preconfigured ML image vs. init actions:** Recommend either switching
        to Dataproc's preconfigured ML image for the target track (e.g.
        `2.3-ml-ubuntu22` for Dataproc 2.3, which bundles compatible CUDA, cuDF,
        and RAPIDS out of the box) or updating the RAPIDS Accelerator plugin JAR
        (`rapids-4-spark_<scala_version>-<version>.jar`) and driver
        initialization script to versions compatible with the target image.
    -   **CUDA, driver, and OS:** newer images bundle newer OS kernels and
        default CUDA versions (e.g. CUDA 11.x → 12.x on 2.2+). The RAPIDS
        version must support the target CUDA runtime, the GPU driver, and the
        image distro (Debian, Ubuntu, or Rocky).
    -   **cuDF:** starting with RAPIDS 23.08, the `cudf` jar is bundled inside
        the `rapids-4-spark` jar and must not be specified separately.
    -   **Configs:** look for deprecated or removed `spark.rapids.*` properties
        between the source and target RAPIDS versions
        (https://nvidia.github.io/cudf-spark/docs/configs.html).
    -   **Driver installation:** legacy `rapids.sh` or `install_gpu_driver.sh`
        scripts may fail on newer distros (e.g. Debian 12, Ubuntu 22.04). Check
        the recommended method for the target image in the
        [Managed Spark GPU guide](https://cloud.google.com/dataproc/docs/concepts/compute/gpus)
        and the
        [NVIDIA Spark RAPIDS on GCP guide](https://docs.nvidia.com/cudf-spark/latest/getting-started/google-cloud-dataproc.html).
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

This skill doesn't keep a list of Spark breaking changes, which would go stale.
Fetch them for the exact source and target Spark versions ("Component Versions";
e.g. `3.5.3` and `4.1.2`, or a source known only as `<major>.<minor>`):

1.  **Fetch the notes.**

    ```bash
    uv run <skill_dir>/scripts/fetch_migration_notes.py --from=<source_spark> --to=<target_spark> --out=migration_notes_<app_id>_temp
    ```

    The script downloads the Core, SQL, Structured Streaming, MLlib, and PySpark
    migration guides (plus `koalas_to_pyspark.rst` when upgrading across Spark
    3.2) from the Apache Spark repository at the target's release tag, keeps
    every "Upgrading from X to Y" section between the two versions (upgrades are
    cumulative), and writes one file per guide. (On pre-3.0 upgrades such as
    `2.3` → `2.4`, guides read from `master` whose sections start at `2.4 to
    3.0` report `no sections in range`.) It also prints an index, saved as
    `index.md`, that lists those files and gives the Java, Scala, and Python
    versions that each Spark version supports and the target's minimum PySpark
    dependency versions; use these instead of looking them up. Take any value
    that the index marks as `unavailable` from the version's Managed Spark
    component page ("Component Versions") or its Spark documentation root
    (`https://spark.apache.org/docs/<x.y.z>/` for current releases,
    `https://archive.apache.org/dist/spark/docs/<x.y.z>/` for archived releases,
    or `https://spark.apache.org/docs/latest/` when only `<major>.<minor>` is
    known): `<docs_root>/index.html` lists Java, Scala, and Python runtimes, and
    `<docs_root>/api/python/getting_started/install.html` (Spark 3.1+) lists
    minimum PySpark dependency versions. Act on the exit code:

    -   `0`: every guide was downloaded.
    -   `1`: a download failed or a guide wasn't found, and the error links the
        target's published migration guides. The index marks those guides as
        `NOT FETCHED` or `not found`; if there's no `index.md`, no guide was
        downloaded. Read the missing guides' sections in the published guides,
        or report those guides as not checked.
    -   `2`: a Spark version is invalid, the target has no Apache Spark release
        tag or branch, or `--out` isn't a directory of its own. Re-check the
        versions from "Component Versions", or use a new
        `migration_notes_<app_id>_temp` directory, and run the script again.
2.  **Check every note.** You MUST read each file that the index lists, in full,
    and check each note against the code, its dependency manifests, Spark
    properties, and job arguments; don't skip notes by guessing their
    importance. Each note that applies is a finding, fixed as SKILL.md rule 2
    describes; a note about a feature the job doesn't use needs no change.
    Delete `migration_notes_<app_id>_temp/` in SKILL.md Step 3 after writing the
    report.
