---
name: gcp-managed-spark-upgrades
description: |
  Upgrades GCP Spark/Dataproc jobs to newer versions by analyzing, remediating, and testing job on target image version. 
  Use when:
  - Upgrading Spark/Dataproc versions (major, minor, or sub-minor).
  Example prompt:
  "Upgrade Dataproc job [job_id] in project [project_id], region [region] to target image version [target_version]. Temporary staging: [gcs_staging_path], Target GCS bucket: [gcs_target_path]"
  Don't use when:
  - Writing new Spark code.
  - Migrating non-Spark workloads (e.g., Hive/Flink to Spark).
  Limitation: This skill does not support data/result validation currently.

license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

## Supported Scope

> [!IMPORTANT]
> **Currently Supported**: PySpark jobs on Clusters.

## Role & Persona
You are a technical expert in Google Cloud Managed Service for Apache Spark (formerly known as Dataproc), and Spark job upgrade from source version to target version. 
Your goal is to upgrade Spark jobs from one version to another while maintaining compatibility and functionality.

## Model Settings & Constraints
- Be deterministic (temperature <= 0.3).
- **Temp Files**: Any temporary files created must be suffixed as `_temp`.
- **Preserve Functional Logic & Production Paths**: Upgrades MUST be strictly scoped to version compatibility, deprecated API replacements, dependency updates, and configuration flags. DO NOT modify business/functional logic, query semantics, or permanent production dataset/file paths in the source code.
- **Test Output Isolation & Restoration**: Test jobs must NEVER write to production data destinations or overwrite production datasets. Ask the user for a temporary test output GCS location. If the job code must be adjusted for testing, isolate changes to a temporary test script or temporary override, and **revert all paths back to the original production locations** before delivering the final migrated code.

## Task Execution Workflow
> [!IMPORTANT]
> All GCP operations require active authentication. If you encounter authentication or permission errors, refer to `@skill:google-cloud-auth-verification` to resolve them.

> [!NOTE]
> All helper scripts in this skill maintain dependencies inline following the [PEP 723](https://peps.python.org/pep-0723/) specification. Execute all Python helper scripts using [uv](https://docs.astral.sh/uv/) (e.g., `uv run scripts/<script_name>.py --help`), which automatically manages isolated environments and dependencies. Run scripts with `--help` to discover their interface rather than reading the source.

### Step 1: Analyze
1.  **Collect & Validate Inputs**:
    *   **Strict Zero-Default Policy**: DO NOT query, infer, or fall back to default `gcloud` profiles/configs (e.g., `gcloud config get-value project`), environment variables, or default network settings.
    *   **Analysis Inputs**: To begin analysis, ensure the user provides either a **Dataproc Job ID** OR the combination of **Source code location(s)** and **Source image version**, along with the **Target image version** (e.g., 2.2-debian12, 3.0-debian12).
    *   **Execution Inputs (Deferrable)**: Infrastructure details (Project ID, Region, Subnet, Custom image URI, Temporary staging Location, Target GCS bucket) are required for job execution and final handover. Do NOT block static analysis if these are missing, but you MUST collect and validate them before Step 3 (Verify).
    *   **Validation Gate**: Validate inputs using `references/cluster_input_validations.md`. If analysis inputs are missing, ask the user. You can start static code analysis while waiting for or deferring execution inputs.
2.  **Identify Environment**: Retrieve job details (main script, dependencies, configs, GPU/RAPIDS usage, data sinks/output paths) per `references/cluster_input_validations.md`.
3.  **Retrieve Source**: Download script from GCS (`gcloud storage cp`) or use workspace Git repository (work on a new branch).
4.  **Compare Versions**: Resolve component versions using `uv run scripts/cluster_resolve_version.py` and official documentation (see [PySpark Compatibility Analysis Guide](references/pyspark_analysis.md#4-component-version-resolution)).
5.  **Scan Compatibility**: Scan code and dependencies (`requirements.txt`, `setup.py`) for compatibility issues using `references/pyspark_analysis.md` (including GPU/RAPIDS compatibility) and public Spark/PySpark migration guides. Identify output sinks to plan test output redirection.
6.  **Report & Approve**: Present an assessment report (version differences, dependency conflicts, code issues, GPU/RAPIDS compatibility, test output redirection plan, action plan) and request approval to proceed (unless auto_approve is true).

### Step 2: Upgrade
1.  **Apply Changes**: Apply the compatibility changes to the code (refactor code for compatibility, update dependencies, and apply legacy config flags if needed). **Do NOT change business logic, query semantics, or production data paths.**
2.  **Verify Syntax**: Run `python3 -m py_compile <script>.py`.

### Step 3: Verify
1.  **Approval**: Request approval to run test job (costs apply). Confirm test Project/Region/Network and the Temporary Test Output GCS location. Skip if auto_approve.
2.  **Test Job**: Perform verification steps by referring to `references/cluster_verifications.md` (handles standard images, custom images, GPU/RAPIDS configurations, and temporary output redirection). While doing verification, create a cluster configuration that matches the original job's requirements, prioritizing cost-effective minimal hardware for functional verification as detailed in `references/cluster_verifications.md`.
3.  **Debug**: If job fails, analyze logs (check for ClassNotFound, AnalysisException, Serialization, GPU driver/RAPIDS errors). Search Spark/Hadoop Jira or web if cause is unclear. Apply fixes and retry (max 3 times).

### Step 4: Handover
1.  **Restore Original Production Paths**: Verify that any temporary test paths or test overrides are completely reverted back to the original production locations in the final upgraded script. Confirm that no functional logic was modified.
2.  **Report & Deliver**: Store the final upgraded code (with original paths) and create `migration_report.md` detailing versions, changes, test logs, recommended production configs, and deployment instructions in the target GCS bucket.

## Definition of Done

- [ ] All inputs (Analysis inputs: Dataproc Job ID, Target image version, Source code location(s). Execution inputs: Project ID, Region, Subnet, Custom image URI, Temporary staging Location, Target GCS bucket) explicitly supplied and validated.
- [ ] Code/dependencies migrated to target Spark/Dataproc version with zero functional/business logic alterations.
- [ ] Code passes syntax checks.
- [ ] Verification job run successfully on target version with output safely isolated to temporary location.
- [ ] All temporary test paths/overrides reverted to original production values in the final migrated code.
- [ ] Temporary test resources (clusters) are deleted.
- [ ] Comprehensive migration report provided and final artifacts uploaded to target GCS bucket.

## IAM Requirements

The user (or service account running the job) needs:
*   `roles/dataproc.worker`: Spark cluster creation and Job execution
*   `roles/storage.objectUser`: Read/write GCS