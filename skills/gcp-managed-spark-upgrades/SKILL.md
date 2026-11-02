---
name: gcp-managed-spark-upgrades
description: |
  Upgrades Spark workloads on Google Cloud Managed Service for Apache Spark (formerly known as Dataproc) clusters and Serverless to a newer image or runtime version. Supports static compatibility analysis, code upgrade, build checks against the target version, and optional verification runs.
  Use when:
  - Upgrading Managed Spark versions (major, minor, or sub-minor) or assessing upgrade readiness.
  Example prompt:
  "Upgrade Managed Spark job [job_id] in project [project_id], region [region] to target version [target_version]. Code location: [local path or GCS path]. Target GCS path: [gcs_target_path]"
  Don't use when:
  - Writing new Spark code.
  - Migrating non-Spark workloads (e.g., Hive/Flink to Spark).
  - Troubleshooting a failed Spark job that is not part of an upgrade.
  Limitation: This skill does not support data/result validation currently.

license: Apache-2.0
metadata:
  version: v2
  publisher: google
---

## Scope gate

- **PySpark**: Cluster job field `pysparkJob`, Serverless batch field `pysparkBatch`. Status: **Supported**. Analysis reference: [pyspark_analysis.md](references/pyspark_analysis.md).
- **Scala/Java**: Cluster job field `sparkJob`, Serverless batch field `sparkBatch`. Status: Not yet supported.
- **Spark SQL**: Cluster job field `sparkSqlJob`, Serverless batch field `sparkSqlBatch`. Status: Not yet supported.
- **SparkR**: Cluster job field `sparkRJob`, Serverless batch field `sparkRBatch`. Status: Not yet supported.
- **PySpark notebook**: Cluster job field —, Serverless batch field `pysparkNotebookBatch`. Status: Not yet supported.

If the workload's job type isn't **Supported**, stop: tell the user which job types are currently supported, and don't change code, create clusters, or submit jobs. Non-Spark jobs (e.g. `hiveJob`, `pigJob`) are out of scope.

Everything else in this skill applies to every supported job type. Checks that depend on the job type live in its analysis reference and in the parts of the other references labeled with the job type (e.g. "For PySpark").

## Terminology

- **Managed Spark**: Google Cloud Managed Service for Apache Spark, formerly Dataproc. Commands (`gcloud dataproc …`) and many docs URLs still say `dataproc`.
- **Cluster**: A job on a Managed Spark cluster (Compute Engine). Its version is an **image version**, `<major>.<minor>.<sub-minor>-<distro>` (e.g. `2.2.50-debian12`).
- **Serverless**: A Managed Spark Serverless batch. Its version is a **runtime version**, `<major>.<minor>` only (e.g. `2.2`): every batch runs the newest sub-minor of its runtime, which can't be pinned.
- **Job type**: The kind of Spark workload (e.g. PySpark), read from the job or batch's type-specific field. See the scope gate.
- **Track**: The `<major>.<minor>` part of a version. The same track can run a different Spark version on clusters and on Serverless.
- **`<skill_dir>`**: The directory that contains this SKILL.md. Script paths below are relative to it.
- **`<app_id>`**: The sanitized job name used in temporary paths: the job's main code file name without its extension (the main `.py` file for PySpark), lowercased, with every character other than `a-z`, `0-9`, `_`, and `-` replaced by `_` (e.g. `daily_orders` for `daily_orders.py`).
- **`<target_path>`**: The Target GCS path, `gs://<TARGET_BUCKET>/<prefix>`. It receives the final code and report; temporary verification artifacts are staged under it.
- **Build checks**: Local checks that the code and its dependencies build against the target versions (language runtime, Spark, Scala). The job type's analysis reference defines them.
- **Verification run**: The optional Step 2 job or batch on GCP. It shows that the job runs; it does not validate output data.

## Rules

1. **Zero defaults.** Take every input from the user or from the source job/batch (its `describe` output or audit logs). Never take values from local `gcloud` configuration (e.g. `gcloud config get-value project`), environment variables, or project defaults such as the `default` network: Managed Spark silently fills in omitted values (default runtime, default subnet), so a guessed value produces a run that looks valid but tests the wrong environment. A value the user supplied or the source job/batch actually used is not a default, even if it is named `default`. Record where each value came from in the report.
2. **Compatibility changes only.** Change only what the target version requires: removed or deprecated APIs, dependency versions, Spark properties, and edits that keep the source behavior on the target (for example adding `USING hive` to a `CREATE TABLE`, or casting an argument whose type is now enforced). Don't change business logic, filters, joins, schemas, or production input/output paths. Prefer code changes over legacy flags (`spark.sql.legacy.*`, `spark.sql.ansi.enabled=false`), because later Spark releases can remove those flags; use a flag only when the code can't keep the old behavior or can't be edited, and list every flag in the report.
3. **Edit a local working copy.** Never overwrite the source objects in GCS, and don't push to a Git remote unless the user asks. Step 1.3 describes how to get the working copy. If a write to the Target GCS path would replace one of the job's source objects or go into a production input or output location, ask for another Target GCS path first.
4. **Isolate verification output.** A verification run must never write to production destinations. Send every output to `<target_path>/test-output_<app_id>_temp/`: pass that path through job arguments or Spark properties when the job accepts them; otherwise submit a temporary copy of the job's code whose output paths are redirected, named `<name>_<app_id>_temp` (for PySpark, `<script>_<app_id>_temp.py`). For an output that isn't a storage path (e.g. a BigQuery or Hive table), ask the user for a test destination. Never put temporary paths into the working copy, so the final code keeps its production paths.
5. **Approvals.** There are two checkpoints: applying code changes (before Step 1.6) and running a verification job/batch, which costs money (Step 2.1). A checkpoint is approved when either:
   - the user explicitly asked for that action, e.g. "upgrade the code" (checkpoint 1) or "run the verification" / "execute the full upgrade, verification, and handover workflow" (both checkpoints), **and** every input that action needs is supplied and valid; or
   - the user asked to **automatically approve** (or auto-approve) the workflow without waiting for confirmation, either in their initial request or when asked.

   Otherwise, ask the user whether they want to automatically approve all remaining steps or confirm at each checkpoint, and wait for the answer. Unless automatic approval is active, Checkpoint 2 also needs the user to confirm or change the verification configuration you present in Step 2.1, even if they asked for the verification. When automatic approval is active, apply the code changes, then, once all Step 2 inputs are supplied and valid, present the verification configuration and run Step 2, retries included, without waiting for a reply. Automatic approval never relaxes the input gates or rule 4, and an analysis-only request never turns into code changes or a verification run.
6. **Temporary names.** Name every temporary file or directory you create, locally or in GCS, `<name>_<app_id>_temp` (files inside such a directory need no extra suffix), so that concurrent upgrades don't collide. Temporary GCP resources use `upg-verify-<unique-id>` instead, because cluster names and batch IDs allow only lowercase letters, digits, and hyphens.
7. **One token per flag.** Write each long option that takes a value as a single `--flag=value` token (e.g. `--version=2.2`): some command wrappers, including test harnesses, treat a standalone `--version` token as a request for the tool's own version.

## Inputs

- **Project ID, Region**: Cluster: Required. Serverless: Required. Needed before: Step 1. If not provided: Ask.
- **Target GCS path**: Cluster: `gs://<bucket>/<prefix>`. Serverless: Same. Needed before: Step 1. If not provided: Ask.
- **Target version**: Cluster: `<major>.<minor>[.<sub-minor>][-<distro>]`; Step 1.4 resolves a missing sub-minor or validates a given one. Serverless: `<major>.<minor>` only. Needed before: Step 1. If not provided: Ask.
- **Source code location**: Cluster: Local path, `gs://…` path, or Git URL (optionally with a branch, tag, commit, or subdirectory). Serverless: Same. Needed before: Step 1. If not provided: Take it from the Job/Batch ID; otherwise ask.
- **Source version**: Cluster: `<major>.<minor>.<sub-minor>-<distro>`. Serverless: `<major>.<minor>`. Needed before: Step 1. If not provided: Take it from the Job/Batch ID; otherwise ask.
- **Job ID / Batch ID**: Cluster: Optional. Serverless: Optional. Needed before: —. If not provided: Never required. It lets you discover the source code, source version, job arguments and properties, and the Step 2 inputs.
- **Subnet**: Cluster: Required. Serverless: Required. Needed before: Step 2. If not provided: Take it from the Job/Batch ID; otherwise ask.
- **Service account**: Cluster: VM service account. Serverless: Workload service account. Needed before: Step 2. If not provided: Reuse what the source job/batch used (none recorded means it ran as the default identity; don't ask, even for a Serverless 3.x target). On Serverless 3.x the default identity changes; see [serverless_input_validations.md](references/serverless_input_validations.md#runtime-3x-platform-changes). Without a Job/Batch ID, ask whether to provide one for the verification run (Step 2).
- **Custom image**: Cluster: Image URI, or `NO` for a standard image. Serverless: —. Needed before: Step 2. If not provided: Ask. If the source cluster used a custom image, Step 2 needs one built for the target version, or `NO` for a standard image (see "Discover the source" in [cluster_input_validations.md](references/cluster_input_validations.md)).
- **Custom container image**: Cluster: —. Serverless: Needed before Step 2 if the source batch used one or when no Batch ID is provided. If not provided: When the source batch used one, ask for an image rebuilt for the target runtime; when no Batch ID is provided, ask for the Custom container image (noting `NO` is acceptable if using the standard runtime environment).
- **Approval preference**: Cluster: Optional (automatically approve all steps vs. confirm at each checkpoint). Serverless: Same. Needed before: Step 1.6. If not provided: Follow rule 5.

## Workflow

> [!IMPORTANT]
> All GCP operations require active authentication. If you encounter authentication errors, ask the user to run `gcloud auth login` and `gcloud auth application-default login`. If an account is active but a call returns `403`, diagnose missing IAM roles instead.

`<skill_dir>/scripts/resolve_version.py` uses only the Python standard library. Run it with `uv run`; if `uv` isn't installed, use `python3` instead.

### Step 1: Analyze & Upgrade (mandatory)

1. **Classify and discover.** Determine the deployment (cluster or Serverless) and the job type.
   - With a Job/Batch ID (this needs the Project ID and Region): follow "Discover the source" in [cluster_input_validations.md](references/cluster_input_validations.md) or [serverless_input_validations.md](references/serverless_input_validations.md). Discovery also supplies the source code location, source version, output paths, and Step 2 inputs. If the job/batch no longer exists and its audit logs are gone, ask for the source code location and source version.
   - Without one: infer the job type from the file extension or path (e.g. `.py` means PySpark; `.scala`, `.java`, or `.jar` means Scala/Java); note that a Job/Batch ID is never required for static code analysis and upgrade.
   - If it's unclear whether the workload runs on a cluster or on Serverless, ask: the same version number can mean a different Spark version on each.
   - Apply the scope gate.
2. **Input gate.** Check which inputs are supplied (or discovered in Step 1.1):
   - **When local source files, source version, and target version are already available:** Do **not** block local code analysis, local build checks (Step 1.5), or requested local file remediation (Step 1.6) if GCP inputs (`Project ID`, `Region`, `Target GCS path`, `Temporary GCS staging location`) are missing or if the user asked not to run `gcloud` commands. Instead, perform the full local static compatibility analysis and local build checks first, and in your response also:
     - Explicitly ask for every missing mandatory analysis/handover and execution input without assuming defaults (rule 1): `Target Project ID`, `Target Region`, `Temporary GCS staging location`, `Target GCS bucket` (`Target GCS path`), `Subnet`, and `Custom image URI` (for clusters, noting `NO` is acceptable if using a standard image) or `Custom container image` (for Serverless when no Batch ID is given, noting `NO` is acceptable).
     - If a cluster source version was given only as `<major>.<minor>` (e.g. `1.5`) without a Job ID, explain that the full `<major>.<minor>.<sub-minor>-<distro>` version (or confirmation of a specific sub-minor and OS distro) is needed for exact component delta analysis, while completing the track-level compatibility analysis meanwhile.
     - Present Step 2 execution/verification on GCP as an optional step and note that a Job/Batch ID is not required for static code analysis and upgrade.
   - **When source code or versions must be discovered from GCP (or before running GCP commands):** The `Project ID`, `Region`, `Target GCS path`, `Target version`, `Source code location`, and `Source version` must be supplied and pass the access checks in the deployment's input-validation reference (skip `gcloud` access checks whenever the user instructs not to run `gcloud` commands). If any mandatory input needed to obtain the source code or versions is missing or inaccessible, stop and ask for the missing inputs above.
   - Step 2 inputs never block Step 1.
3. **Get a local working copy** (rule 3).
   - **Local path:** confirm it exists. If it is inside a Git repository and not in an evaluation/staging workspace, create a working branch before editing. When remediating a local file (Step 1.6), apply the compatibility changes directly to that local file (keeping its original production input/output paths intact); never leave the user-specified local file un-remediated by only editing a separate copy.
   - **GCS path:** download the main code file and every code dependency or auxiliary file the job references (for PySpark: `pythonFileUris`, `fileUris`, and `archiveUris`) into `src_<app_id>_temp/` with `gcloud storage cp -r`, and carry `fileUris` forward to Step 2.
   - **Git URL:** clone into `<repo_name>_<app_id>_temp`, check out the requested branch, tag, or commit, then create the working branch:
     ```bash
     git clone <REPO_URL> <repo_name>_<app_id>_temp
     git -C <repo_name>_<app_id>_temp checkout <REF>
     git -C <repo_name>_<app_id>_temp checkout -b spark-upgrade-<target_version>
     ```
   - Confirm that the job's source files and dependency manifests are present. If a Git repository and the job's GCS objects both exist and differ, ask which one is the source of truth.
4. **Resolve versions.**
   - **Target version:** run the script.
     ```bash
     uv run <skill_dir>/scripts/resolve_version.py --type=cluster --version=<target_version> --distro=<distro_or_family>
     uv run <skill_dir>/scripts/resolve_version.py --type=serverless --version=<major.minor>
     ```
     - Cluster: pass the target version as given, with or without a sub-minor ([cluster_input_validations.md](references/cluster_input_validations.md#target-image-version) describes what the script does with each). Pass the user's target distro; if they gave none, pass the source's OS family (e.g. `--distro=ubuntu` for a `2.0.85-ubuntu18` source) so the OS doesn't change silently; if the source distro is unknown too, ask. Record the result: Step 2 pins it.
     - Serverless: confirms that the runtime exists and prints `<major>.<minor>`. Serverless has no sub-minor to resolve or pin.
   - **Source version:** never resolve it with the script. The source is whatever the job actually ran.
   - Map the source and target to Spark versions with [spark_migration_reference.md](references/spark_migration_reference.md#version-to-spark-mapping), and look up the component versions (Java, Scala, Python, connectors, preinstalled libraries) as described in its [Component Versions](references/spark_migration_reference.md#component-versions) section.
5. **Scan and run baseline build checks.**
   - Scan the code, its dependency manifests, Spark properties, and job arguments with the job type's analysis reference (see the scope gate) and [spark_migration_reference.md](references/spark_migration_reference.md): the Spark migration notes between the source and target (looked up in the official guides), and the connector and GPU/RAPIDS checks. For a Serverless upgrade from runtime 1.x/2.x to 3.x, also report the platform changes in [serverless_input_validations.md](references/serverless_input_validations.md#runtime-3x-platform-changes).
   - Run the job type's build checks (for PySpark, [pyspark_analysis.md](references/pyspark_analysis.md#4-build-checks-against-the-target-version)) on the original code; each failure is a finding.
   - Note the job's output paths: Step 2 redirects them (rule 4).
   - Present the assessment: version and component deltas, findings with `file:line`, build-check results, and the planned changes.
   - For an analysis-only request, go to Step 3. Otherwise continue to Step 1.6 once checkpoint 1 is approved (rule 5).
6. **Upgrade and build against the target.**
   - Apply the changes (rule 2).
   - Re-run the build checks on the changed code and fix failures, up to 3 attempts. If a check still fails, skip Step 2 and report the failure in Step 3.
   - If the user hasn't requested Step 2 or automatically approved the full workflow, summarize the results, offer Step 2, and list the Step 2 inputs that are still missing. If they decline, go to Step 3.

### Step 2: Verify on GCP (optional)

Run this step only when the user requested verification, accepted the offer in Step 1.6, or asked to automatically approve the full workflow (rule 5).

1. **Verification gate.** The Subnet, Service account, and (clusters) Custom image, plus a custom container image if the source batch used one, must be supplied or discovered and pass the checks that the deployment's input-validation reference defines for them. Without a Job/Batch ID there is no source configuration to copy, so also ask for the job's entry point (main file or main class), arguments, Spark properties, dependencies, and (clusters) machine types and worker count. Never create a cluster or submit a job/batch until this gate passes. Then get checkpoint 2 (rule 5): present the full verification configuration, resources included, and let the user confirm it or change it (V1 in the verification reference).
2. **Run** the verification as described in [cluster_verifications.md](references/cluster_verifications.md) or [serverless_verifications.md](references/serverless_verifications.md).
3. **Debug.** If the run fails, read the driver output as the verification reference describes, and look for class-loading or linkage errors (e.g. `ClassNotFoundException`, `NoSuchMethodError`), `AnalysisException`, serialization errors, import or dependency errors (for PySpark, `ImportError` or `ModuleNotFoundError`), and GPU driver or RAPIDS errors. Fix the code, re-run the build checks, and retry with a new job/batch ID: at most 3 retries.
4. **Clean up** as the verification reference describes.

### Step 3: Handover (mandatory)

1. **Confirm the production paths are untouched.** Diff the original and final code: only compatibility changes, no `_temp` paths, no test-only logic.
2. **Write the report**, `<app_id>_<source_version>_<target_version>_spark_upgrade_report.md`, with secrets (e.g. passwords or tokens in job arguments or properties) redacted, covering:
   - the inputs and where each came from (user, Job/Batch ID, or audit logs);
   - source and target versions and component deltas (Spark, Python, Java/Scala, connectors or any other component versions that got changed during the upgrade), and any assumption made (e.g. a source version known only as `<major>.<minor>`);
   - findings and changes with `file:line`, including every legacy flag added;
   - build-check results, with "not run" and the reason for any check that couldn't run;
   - verification results, or "not run";
   - the recommended production configuration (pinned image version or runtime, properties, and cluster-level changes such as Conda channels or a rebuilt custom image) and deployment instructions;
   - temporary resources left behind (e.g. `_temp` paths in GCS).
3. **Deliver** to the Target GCS path with `gcloud storage cp`: the final code (the job's main file and code dependencies, changed or not, keeping their relative layout) and the report. For an analysis-only request, upload only the report. For a Git source, also leave the changes on the `spark-upgrade-<target_version>` branch (don't push unless the user asks) and name the branch in the report.

## Definition of Done

- [ ] **Inputs:** the scope gate passed, and the Step 1 inputs were supplied or discovered, checked, and recorded with their sources.
- [ ] **Upgrade** (unless analysis-only): code and dependencies changed for compatibility only, and the target build checks pass (or are reported as "not run" with the reason).
- [ ] **Verification** (if Step 2 ran): the job/batch ran on the target version (clusters: the pinned full image version) with outputs isolated under the Target GCS path, the temporary cluster was deleted, and no verification batch is still running.
- [ ] **Handover:** the diff confirms that production paths are untouched, and the report (plus the final code, unless analysis-only) is in the Target GCS path.

## IAM Requirements

- **Discovery & Storage (Step 1)**:
  - **Managed Spark Cluster**: `roles/dataproc.viewer`; `roles/storage.objectViewer` on target/code buckets; `roles/logging.viewer` for audit-log fallback.
  - **Managed Spark Serverless Batch**: Same as Cluster.
- **Verification (optional, Step 2)**:
  - **Managed Spark Cluster**: User: `roles/dataproc.editor`, `roles/iam.serviceAccountUser` on VM SA, `roles/storage.objectUser` on target/staging bucket. VM SA: `roles/dataproc.worker` + data roles.
  - **Managed Spark Serverless Batch**: Runtime 1.x/2.x: user needs `roles/dataproc.editor` + `roles/iam.serviceAccountUser`; workload SA needs `roles/dataproc.worker` + `roles/storage.objectAdmin` + data roles. Runtime 3.x: user needs `roles/dataproc.serverlessEditor` + data roles (or `roles/iam.serviceAccountUser` with a custom SA that has `roles/dataproc.serverlessNode` + data roles).
- **Delivery (Step 3)**:
  - **Managed Spark Cluster**: `roles/storage.objectUser` on the bucket of the Target GCS path.
  - **Managed Spark Serverless Batch**: Same as Cluster.