# PySpark Compatibility Analysis Guide

This guide details compatibility checks and migration patterns specifically for PySpark workloads when upgrading to newer Spark/Dataproc versions.

As an agent, you must perform this analysis by reviewing the codebase against the rules in this document and the referenced official documentation.

## Relevant Documentation

Review the official documentation and migration guides:

*   **Dataproc Image Releases**: [Dataproc Image Releases](https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-2.2) (Replace track with target version, e.g., 2.0, 2.1, 2.2, 2.3).
*   **Dataproc Serverless Runtimes**: [Dataproc Serverless Runtimes](https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-2.2) (Replace track with target version).
*   **Dataproc/Managed Spark Release Notes**: [Managed Spark Release Notes](https://cloud.google.com/dataproc/docs/release-notes) (Covers Dataproc platform changes, image updates, and breaking changes).
*   **Spark SQL Migration Guide**: [Spark SQL Migration Guide](https://spark.apache.org/docs/latest/sql-migration-guide.html) (Covers SQL parser changes, datetime rebasing, behavior changes in functions).
*   **PySpark Migration Guide**: [PySpark Migration Guide](https://spark.apache.org/docs/latest/api/python/migration_guide/pyspark_upgrade.html) (Covers PySpark specific changes like Arrow optimization, Row sorting, ML mixins).
*   **Spark Core Migration Guide**: [Spark Core Migration Guide](https://spark.apache.org/docs/latest/core-migration-guide.html) (Covers core Spark behavior changes).
*   **Python Documentation**: Refer to [Python Release Docs](https://docs.python.org/3/whatsnew/) if upgrading Python versions to identify deprecated syntax or libraries.
*   **Hadoop Migration**: Refer to [Hadoop Release Notes](https://hadoop.apache.org/releases.html) if there are major Hadoop version jumps (e.g., 2.x to 3.x), which may affect classpaths or configuration properties (e.g., GCS connector).

## Analysis Procedure

To conduct the analysis:
1.  **Identify Versions**: Determine the source and target versions of Spark, Python, and Hadoop (from Job ID or user input).
2.  **Read Migration Guides & Release Notes**: Review the relevant sections of the migration guides and Dataproc release notes listed above for the version jump.
3.  **Scan Source Code**: Review the PySpark code files for:
    *   Deprecated/removed APIs (e.g., `SQLContext`, `unionAll`, `pyspark.mllib`).
    *   Behavior changes (e.g., datetime parsing with `to_date`/`to_timestamp`, `Row` construction with named args).
    *   Configuration changes.
    *   **Data Sinks & Output Destinations**: Identify how and where data is written (e.g., `df.write.save()`, `df.write.parquet()`, `insertInto()`, `saveAsTable()`) and how output paths are passed (CLI arguments vs hardcoded paths) to plan test output redirection during verification.
> [!IMPORTANT]
> **Preserve Functional Logic**: Analysis and remediation are strictly limited to version compatibility and deprecation fixes. Do NOT alter business logic, filter conditions, column transformations, or permanent dataset paths in the source code.
4.  **Verify Dependencies & Conda Configs**:
    *   Check `requirements.txt` or `setup.py` against Python version compatibility.
    *   **Conda Channel Analysis**: Check if Conda is used (e.g., `environment.yml` file present, or conda properties in job/cluster configurations).
        *   Analyze based on Conda channel changes (e.g., default channel disabled in May 2024, preconfigured channels removed in June 2026 subminors and all images after Aug 2026).
        *   If Conda channels are configured in job artifacts (like environment files), update them to use valid channels (e.g., `conda-forge` explicitly if defaults are disabled/missing).
        *   If Conda is used but not configured in job artifacts, warn the user and request them to configure Conda channels at the cluster level (e.g., via cluster properties or initialization actions).
5.  **Search Jira for Known Issues (Proactive/Troubleshooting)**:
    *   If the code uses specific complex APIs or if you encounter errors during compilation/verification that are not explained by the migration guides:
        *   Search Apache Jira (project `SPARK` or `HADOOP`) for known issues related to the target version and the error message or feature name.
        *   Use the results to identify if a regression or known bug exists in the target version and if there are workarounds (e.g., setting specific Spark properties).


## 1. Python Version Compatibility

Spark versions have minimum Python version requirements. Ensure the target environment's Python version is supported.

*   **Spark Version**: 2.4
    *   **Min Python Version**: 2.7, 3.4
    *   **Max Python Version**: 3.7
*   **Spark Version**: 3.0
    *   **Min Python Version**: 3.6
    *   **Max Python Version**: 3.8
*   **Spark Version**: 3.1
    *   **Min Python Version**: 3.6
    *   **Max Python Version**: 3.9
*   **Spark Version**: 3.2
    *   **Min Python Version**: 3.6
    *   **Max Python Version**: 3.10
*   **Spark Version**: 3.3
    *   **Min Python Version**: 3.7
    *   **Max Python Version**: 3.10
*   **Spark Version**: 3.4
    *   **Min Python Version**: 3.8
    *   **Max Python Version**: 3.11
*   **Spark Version**: 3.5
    *   **Min Python Version**: 3.8
    *   **Max Python Version**: 3.11
*   **Spark Version**: 4.0
    *   **Min Python Version**: 3.9
    *   **Max Python Version**: 3.12 (estimated)

**Action**:
1.  **Dynamic Verification**: If the target Spark version is not listed in the table above (or is marked as estimated), you MUST dynamically verify the supported Python version by checking the official Dataproc documentation for the target image track (e.g., `https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-2.2`).
2.  Check `requirements.txt` or `setup.py` and ensure they don't force an incompatible Python version.

## 2. Dependency Analysis (Python Packages)

When upgrading Spark, you must also upgrade `pyspark` package in your development/test dependencies to match the target Spark version.

*   Verify `requirements.txt`, `Pipfile`, or `setup.py`.
*   Ensure that other library dependencies (e.g., `numpy`, `pandas`, `pyarrow`) are compatible with the new Python and PySpark versions.

> [!TIP]
> Spark 3.x+ strongly recommends using PyArrow for pandas conversion (`toPandas()`, `createDataFrame()`). Ensure `pyarrow` is installed and enabled: `spark.sql.execution.arrow.pyspark.enabled = true`.

## 3. Dataproc Platform Changes (Conda)

### 3.1. Conda Channel Changes (June 2026 / May 2024)
*   **Issue**: 
    *   **June 22, 2026**: Newer Dataproc subminor versions (e.g., `1.3.96`, `1.4.81`, `1.5.92`, `2.0.161`, `2.3.32` and all versions after August 25, 2026) **do not have preconfigured Conda channels**. Packages cannot be installed using Conda unless channels are manually configured.
    *   **May 16, 2024**: Anaconda's `default` channel is disabled by default on Dataproc on Compute Engine.
*   **Remediation**:
    *   If using `environment.yml` or other Conda environment files, ensure they explicitly define valid channels (e.g., `conda-forge`) and do not rely on `defaults` if it is disabled.
    *   If Conda configuration is part of the job properties or metadata, update them to configure channels.
    *   If Conda is required but cannot be configured via job artifacts, **warn the user** that they must configure Conda channels explicitly at the cluster level (e.g., `conda install --channel <CHANNEL> <PACKAGE>`).

## 4. Component Version Resolution

To ensure you are using the correct versions of Spark, Scala, Java, Python, Hadoop, and connectors (GCS, BigQuery) for the target Dataproc image, resolve them using the provided helper script or the official documentation.

### Resolution Steps:
1.  **Resolve Subminor Version**: Run the version resolution script to find the latest suitable subminor version for the image track:
    ```bash
    uv run ../scripts/cluster_resolve_version.py --version <major.minor> --type gce [--distro <distro>]
    ```
2.  **Determine Target Components**: Look up the target image version on the corresponding documentation page:
    *   **Dataproc on GCE Images**: `https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-2.2` (replace 2.2 with target track)
    *   **Dataproc Serverless Runtimes**: `https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-2.2` (replace 2.2 with target track)
3.  **Identify Component Versions**: In the release documentation table, locate the column corresponding to your subminor version and verify the exact versions for:
    *   **Apache Spark**
    *   **Apache Hadoop**
    *   **Python**
    *   **Scala / Java**
    *   **Cloud Storage (GCS) Connector**
    *   **BigQuery Connector**

## 5. Common PySpark Migration Reference

Please refer to the separate reference guide for a list of common Spark migration incompatibilities, broken down by Core Spark and PySpark-specific issues:
[Common Spark Migration Reference](spark_migration_reference.md)

## 6. GPU and RAPIDS Compatibility

If the workload requires GPU acceleration via NVIDIA GPUs and the RAPIDS Accelerator for Apache Spark, ensure version compatibility:

### 6.1. Dataproc ML Images (Recommended)
Dataproc provides ML-flavored images (e.g., `2.2-ml-ubuntu22`, `2.3-ml-ubuntu22`) which come pre-installed with compatible versions of CUDA, NVIDIA drivers, and the RAPIDS Accelerator plugin.
*   **Action**: Prefer using the corresponding `-ml` image for the target Dataproc version (e.g., if upgrading to `2.3-debian12`, use `2.3-ml-ubuntu22` if GPUs are needed).

### 6.2. RAPIDS Plugin and Spark Compatibility
If installing RAPIDS via initialization actions (e.g., on standard images), you must specify compatible versions of the RAPIDS Spark plugin. The RAPIDS plugin version usually follows the `YY.MM.x` format.

*   **Dataproc Image**: 2.0
    *   **Spark Version**: 3.1.x
    *   **Compatible RAPIDS Version (Example)**: 22.x, 23.x
*   **Dataproc Image**: 2.1
    *   **Spark Version**: 3.3.x
    *   **Compatible RAPIDS Version (Example)**: 23.x, 24.x
*   **Dataproc Image**: 2.2
    *   **Spark Version**: 3.5.x
    *   **Compatible RAPIDS Version (Example)**: 24.x, 25.x
*   **Dataproc Image**: 2.3
    *   **Spark Version**: 3.5.x
    *   **Compatible RAPIDS Version (Example)**: 24.12, 26.x
*   **Dataproc Image**: 3.0
    *   **Spark Version**: 4.0.x / 4.1.x
    *   **Compatible RAPIDS Version (Example)**: 26.x

*   **Action**:
    1.  Check the target Spark version.
    2.  Refer to the [NVIDIA Spark-RAPIDS Compatibility Matrix](https://docs.nvidia.com/cudf-spark/latest/) (or search the web) to find the exact compatible RAPIDS version.
    3.  Configure the `rapids-version` metadata attribute during cluster creation to match the compatible version if using initialization actions.
    4.  Verify shim provider overrides if using experimental/new Spark versions (e.g., `spark.rapids.shims-provider-override`).
