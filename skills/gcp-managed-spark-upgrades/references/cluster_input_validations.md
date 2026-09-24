# Input Validation Guide
This guide outlines the mandatory validation checks that you must perform before starting any upgrade actions.

## 1. Zero-Default Policy & Inputs Checklist

The agent MUST NEVER guess, infer, or extract configuration values from the local environment's active profile (`gcloud config get-value ...`) or default VPC network. All parameters must either be explicitly supplied by the user or dynamically resolved through verified source job/cluster metadata.

### Project ID
* **Requirement**: Mandatory (Execution)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Must be explicitly supplied. Verify project existence and permissions to manage Dataproc clusters and submit jobs via `gcloud` (Section 2.1).

### Region
* **Requirement**: Mandatory (Execution)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Must be explicitly supplied. Verify region validity and Dataproc service availability/permissions in the region (Section 2.2).

### Dataproc Job ID
* **Requirement**: Conditional (Analysis)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: The job ID. Not mandatory if job is submitted outside Dataproc API. If provided, used to automatically fetch source image version, cluster config, and subnet (Section 4.1).

### Source code location(s)
* **Requirement**: Mandatory (Analysis)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Must be explicitly supplied. Validated as accessible local file path or GCS URI (`gs://...`) with verified read access (Section 4.3).

### Source image version
* **Requirement**: Conditional (Analysis)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Mandatory if Job ID is NOT provided. Must follow complete version format `<major>.<minor>.<subminor>-<distro>` (e.g., `1.5.8-debian10`, `2.0.35-debian10`). If Job ID is provided, automatically resolved from cluster config or audit logs (Section 4.2).

### Target image version
* **Requirement**: Mandatory (Analysis)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Must be explicitly supplied. Subminor is optional (e.g., `2.2`, `2.2-debian12`, `3.0`, `3.0-debian12`). Validated and resolved to latest stable subminor via `cluster_resolve_version.py` (Section 6).

### Custom image URI
* **Requirement**: Mandatory (Execution)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Must be explicitly supplied. If the user specifies "NO", standard Dataproc images will be used. If an image URI is provided, it must be a valid container image URI used for cluster creation during the verification step.

### Subnet (name or URI)
* **Requirement**: Conditional (Execution)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: If provided by user, validated in target project/region (Section 3). If omitted, dynamically extracted from cluster config or audit logs based on Dataproc Job ID. If neither is available, prompt user.

### Temporary staging Location
* **Requirement**: Mandatory (Execution)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: GCS path (`gs://<BUCKET>/<STAGING_PATH>/`) required for staging intermediate code, dependencies, and test logs. Verified for read/write access (Section 5.1).

### Target GCS bucket
* **Requirement**: Mandatory (Execution)
* **Fallback to Default Allowed?**: NO
* **Validation Rule**: Destination GCS path (`gs://<TARGET_BUCKET>/...`) for final upgraded code and `<job_name>_<source_version>_<target_version>_migration_report.md`. Verified for write access (Section 5.2).

> [!CAUTION]
> **Stop-the-Line Rule**: If any required **Analysis** parameter is missing, invalid, or inaccessible, **DO NOT PROCEED with analysis**. Request the missing information from the user. For missing **Execution** parameters, you may proceed with static code analysis, but you MUST NOT proceed with execution (verification/handoff) until they are supplied and validated.

---

## 2. Project ID & Region Validation & Access Checks

Verify that the specified `Project ID` and `Region` exist and that the current identity has active permissions to create/manage Dataproc clusters and submit jobs.

### 2.1. Project ID Validation
* **Existence & Access Check**:
  ```bash
  gcloud projects describe <PROJECT_ID>
  ```
  Ensure this command succeeds without permission errors.

* **Dataproc Permissions Check**:
  Verify permissions to list/create Dataproc clusters and jobs:
  ```bash
  gcloud dataproc clusters list --project=<PROJECT_ID> --region=<REGION> --limit=1
  gcloud dataproc jobs list --project=<PROJECT_ID> --region=<REGION> --limit=1
  ```
  If any command returns `PERMISSION_DENIED` or `403 Forbidden`, STOP and notify the user that Dataproc permissions (such as `roles/dataproc.editor` or `roles/dataproc.admin`) are missing.

### 2.2. Region Validation
* **Region Availability Check**:
  ```bash
  gcloud compute regions describe <REGION> --project=<PROJECT_ID>
  ```
  Ensure the region is valid and active for compute resources in the target project.

---

## 3. Subnet and Network Validation

A valid subnet is required for Dataproc GCE and Serverless workloads to isolate networking and ensure secure connectivity to Google APIs (GCS, BigQuery, Artifact Registry).

### 3.1. Subnet Resolution Strategy
1. **User-Provided Subnet**: If the user explicitly provides a Subnet name or URI, use and validate it directly.
2. **Derived from Dataproc Job ID**: If the user does NOT provide a subnet, but provides a `Dataproc Job ID`:
   * **Step A: Extract Cluster Name and Cluster UUID from Job ID**:
     Execute the following command and extract the Cluster Name and Cluster UUID from the output:
     ```bash
     gcloud dataproc jobs describe <JOB_ID> \
         --region=<REGION> \
         --project=<PROJECT_ID> \
         --format="value(placement.clusterName, placement.clusterUuid)"
     ```
   * **Step B: Look up Subnet URI from Active Cluster (via Cluster Name)**:
     ```bash
     gcloud dataproc clusters describe <CLUSTER_NAME> \
         --region=<REGION> \
         --project=<PROJECT_ID> \
         --format="value(config.gceClusterConfig.subnetworkUri)"
     ```
   * **Step C: Ephemeral / Deleted Cluster Fallback (via Cluster UUID in Audit Logs)**:
     If the cluster was ephemeral and has been deleted (`NOT_FOUND`), query Cloud Audit Logs using the unique immutable `cluster_uuid`:
     ```bash
     gcloud logging read \
         'resource.type="cloud_dataproc_cluster" AND resource.labels.cluster_uuid="<CLUSTER_UUID>" AND protoPayload.methodName="google.cloud.dataproc.v1.ClusterController.CreateCluster"' \
         --project=<PROJECT_ID> \
         --limit=1 \
         --format="value(protoPayload.request.cluster.config.gceClusterConfig.subnetworkUri)"
     ```
3. **Prompt User**: If the subnet is neither provided by the user nor discoverable from the cluster config or audit logs, **STOP and ask the user to specify a Subnet in the target project.**

### 3.2. Subnet Validation Command
```bash
gcloud compute networks subnets describe <SUBNET_NAME> \
    --region=<REGION> \
    --project=<PROJECT_ID> \
    --format="json(name,network,privateIpGoogleAccess,ipCidrRange)"
```

### 3.3. Validation Criteria
1. **Existence**: Verify the subnet exists in `<PROJECT_ID>` and `<REGION>`.
2. **Private Google Access**: Check if `privateIpGoogleAccess` is `true`. If `false`, warn the user that Private Google Access should be enabled for clusters without public IPs.
3. **VPC Network**: Extract and verify the parent VPC network name.

---

## 4. Source Environment & Code Identification

Identify the source configuration based on whether a Dataproc Job ID or standalone code files are provided.

### 4.1. Dataproc Job ID Validation (Optional / Conditional)
If a Job ID is provided:
* **Command**:
  ```bash
  gcloud dataproc jobs describe <JOB_ID> \
      --region=<REGION> \
      --project=<PROJECT_ID> \
      --format="json(status,config,placement)"
  ```
* **Validation & Identification**:
  * Verify the job exists and check `status.state`.
  * Extract:
    * Associated cluster name (`placement.clusterName`) and cluster UUID (`placement.clusterUuid`).
    * Main script URI (GCS path) and additional python files/archives.
    * Job arguments, Spark properties, and jar dependencies.
  * Fetch source cluster details (Active Cluster):
    ```bash
    gcloud dataproc clusters describe <CLUSTER_NAME> \
        --region=<REGION> \
        --project=<PROJECT_ID> \
        --format="json(config)"
    ```
    * Extract **Source image version** from `config.softwareConfig.imageVersion` (e.g. `1.5.8-debian10`, `2.0.35-debian10`).
    * Extract **Subnet** from `config.gceClusterConfig.subnetworkUri` (if user did not specify one).
    * Detect **Custom Image**, **GPUs / Accelerators**, and **RAPIDS** initialization actions.
  * **Ephemeral Cluster Fallback (via Cluster UUID in Audit Logs)**: If the cluster is deleted (`NOT_FOUND`), retrieve image version and cluster configuration from Cloud Audit Logs:
    ```bash
    gcloud logging read \
        'resource.type="cloud_dataproc_cluster" AND resource.labels.cluster_uuid="<CLUSTER_UUID>" AND protoPayload.methodName="google.cloud.dataproc.v1.ClusterController.CreateCluster"' \
        --project=<PROJECT_ID> \
        --limit=1 \
        --format="value(protoPayload.request.cluster.config.softwareConfig.imageVersion)"
    ```

### 4.2. Source Image Version Validation
* **If Job ID provided**: Automatically retrieved from cluster config (`config.softwareConfig.imageVersion`) or audit logs as described in Section 4.1.
* **If Job ID NOT provided**: The user **must explicitly specify** the complete Source image version including subminor and distro (e.g., `1.5.8-debian10`, `2.0.35-debian10`). Confirm the format matches `<major>.<minor>.<subminor>-<distro>`.

### 4.3. Source Code Location(s) Validation
The source code must be explicitly provided as a local path or a GCS URI.
* **Local Source File**: Check that the file exists and is readable in the current workspace filesystem.
* **GCS Source File**: Verify read access using:
  ```bash
  gcloud storage ls gs://<BUCKET>/<PATH_TO_SCRIPT_OR_DIR>
  ```

---

## 5. Storage Locations, Staging & Logic Preservation

### 5.1. Temporary Staging Location Validation (Mandatory)
* The agent requires a temporary staging location (e.g., `gs://<STAGING_BUCKET>/<STAGING_DIR>/`) to stage modified code, packaging artifacts, dependencies, and test logs during the upgrade process.
* **Validation Command**:
  ```bash
  gcloud storage ls gs://<STAGING_BUCKET>/
  ```
  Ensure read and write access to the staging bucket.

### 5.2. Target GCS Bucket Validation (Final Delivery)
* The target GCS bucket where the final migrated code (with original production paths) and `<job_name>_<source_version>_<target_version>_migration_report.md` will be placed upon completion.
* **Validation Command**:
  ```bash
  gcloud storage ls gs://<TARGET_BUCKET>/
  ```
  Verify write access to the target bucket.

### 5.3. Temporary Test Output Location Validation (Test Isolation)
* When executing verification test jobs, test runs must NEVER overwrite or write to production data destinations.
* Verify the test output path (e.g., `gs://<STAGING_BUCKET>/test_output/`) is isolated.
* **Rule**: Isolate changes to a temporary test script or parameter override during Step 3 (Verify). In Step 4 (Handover), the script must be restored to its original production paths.

### 5.4. Functional Logic & Production Path Preservation Policy
* **Strict Non-Interference**: Do NOT modify business logic, query filters, join conditions, schema definitions, or production input/output datasets.
* Upgrades must strictly target version compatibility, deprecated API replacements, dependency adjustments, and cluster/runtime configuration flags.

---

## 6. Target Image Version Validation

Validate the target image version provided by the user. Providing a subminor version is **optional**:
* If the user specifies `<major>.<minor>` (e.g., `2.2`, `2.2-debian12`, `3.0`, `3.0-debian12`), the agent resolves the latest suitable stable subminor version automatically.
* If the user specifies a full version with subminor (e.g., `2.2.30-debian12`), the agent validates that specific subminor against release notes and blocklists.

* **Automatic Resolution (Recommended)**:
  * Use the [cluster_resolve_version.py](../scripts/cluster_resolve_version.py) script to find the latest suitable subminor version for a given track. The script automatically filters out blocklisted versions and rolled-back versions from public release notes.
  * **Command**:
    ```bash
    uv run scripts/cluster_resolve_version.py --version <major.minor> --type <gce|serverless> [--distro <distro>] [--raw]
    ```
  * **Example**: `uv run scripts/cluster_resolve_version.py --version 2.2 --type gce`
* **Manual Version Lookup (Fallback)**:
  * If you cannot run the script, manually look up available versions in the documentation:
    * **GCE Images**: `https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-2.2` (replace `2.2` with target track)
    * **Serverless Runtimes**: `https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-2.2` (replace `2.2` with target track)
* **Release Notes Check (Manual)**:
  * Look at the release notes: https://cloud.google.com/dataproc/docs/release-notes
  * **Actions**:
    1. If the target image version has known critical bugs, rollbacks, or breaking changes, recommend the latest stable sub-minor version in the same image track.
    2. If there are specific cases like conda channel removal, suggest a suitable alternative based on analysis (e.g., see [June 22, 2026 release notes](https://cloud.google.com/dataproc/docs/release-notes#June_22_2026)).
* **Connector GitHub Issues Check**:
  * Identify GCS and BQ connector versions for the target image by reading the corresponding Dataproc Image Release document on the fly (see [PySpark Compatibility Analysis Guide](pyspark_analysis.md#4-component-version-resolution-on-the-fly)).
  * Check for reported issues, bugs, or release notes in:
    * GCS Connector: https://github.com/GoogleCloudDataproc/hadoop-connectors
    * BQ Connector: https://github.com/GoogleCloudDataproc/spark-bigquery-connector
  * **Actions**:
    1. If the connector versions have reported critical issues, warn the user and document the findings.
    2. Recommend upgrading to a newer subminor image version that uses more stable connector versions.

---

## 7. RAPIDS and GPU Validation

If the source environment uses GPUs and RAPIDS, validate the target configuration compatibility:
* **Target Image compatibility**: Ensure the target image version supports GPUs. Dataproc ML images (e.g., `2.2-ml`, `2.3-ml`) have RAPIDS pre-installed and are recommended.
* **RAPIDS Version compatibility**: If using initialization actions to install RAPIDS, verify that the target RAPIDS version is compatible with the target Spark version (see [PySpark Compatibility Analysis Guide](pyspark_analysis.md#6-gpu-and-rapids-compatibility) for mapping).
* **Hardware compatibility**: Ensure the target project/region has quota for the required GPU types (e.g., `NVIDIA Tesla T4`, `NVIDIA L4`).
  * **Command**: `gcloud compute accelerator-types list --project <PROJECT_ID> --filter="zone:( <ZONE> )"`
  * **Action**: Verify that the requested GPU type is available in the target zone.

