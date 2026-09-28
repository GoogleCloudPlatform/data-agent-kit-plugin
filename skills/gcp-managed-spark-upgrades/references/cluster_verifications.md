# Dataproc Job Verification Guide

This guide outlines the procedure to verify migrated Spark jobs on a temporary Dataproc Cluster.

Verification involves running the migrated job in a temporary environment that mimics the production environment, followed by mandatory cleanup and path restoration.

## Verification Steps

### Step 1: Gather Target Configuration & Test Isolation
Determine the configuration requirements for the test:
*   **Project ID & Region**: GCP project and region for test execution (`--project=<PROJECT_ID> --region=<REGION>`).
*   **Target image version**: The Dataproc image version being upgraded to (`--image-version=<TARGET_IMAGE_VERSION>`).
*   **Target Custom Image URL**: If the source used a custom image, the URL of the target custom image (built for the target version).
*   **GPU / RAPIDS Config**: If the source used GPUs/RAPIDS:
    *   Identify target GPU type and count.
    *   Determine if using a Dataproc ML image (recommended) or initialization actions.
    *   If using initialization actions, determine the target RAPIDS version.
*   **Subnet**: The user-supplied or dynamically derived subnet (`--subnet=<SUBNET>`) validated per Section 3 of `cluster_input_validations.md`. Do not fall back to default VPC/network.
*   **Hardware Profile**: Match the source job's cluster hardware config.
*   **Temporary Test Output Location**: Ensure an isolated test output path under the temporary staging location (e.g., `gs://<STAGING_BUCKET>/test-output-<JOB_ID>/`) is configured to prevent overwriting production data.

### Step 2: Create a Temporary Cluster
Create a temporary Dataproc cluster (e.g., named `upg-verify-<unique-id>`) using `gcloud dataproc clusters create` in `<PROJECT_ID>` and `<REGION>`, configured with the target image version, custom image URI (if specified, instead of standard image), subnet (`--subnet=<SUBNET>`), or GPUs/RAPIDS as determined in Step 1.
*   **Custom Image URI**: If a Custom image URI was provided, use it to provision the verification cluster. For detailed guidelines on how to use custom images and perform verification, refer to https://docs.cloud.google.com/managed-spark/docs/guides/images

### Step 3: Submit the Test Job with Output Redirection
Submit the migrated script (PySpark) or JAR to the temporary cluster using `gcloud dataproc jobs submit [pyspark|spark]`.
*   **Output Redirection Strategy**:
    *   **Strategy A (CLI Arguments / Properties)**: If the script accepts output paths as command-line arguments or Spark properties, pass the temporary test GCS location as an argument (e.g. `--output_path=gs://<TEMP_BUCKET>/test-output-<JOB_ID>/`).
    *   **Strategy B (Temporary Test Script)**: If output paths are hardcoded in the script, create a temporary test copy of the script (e.g., `job_test.py`) with output paths redirected to the temporary GCS test location, and submit this test copy to the cluster.
*   Pass any required job arguments.
*   Verify that the job runs successfully and inspect logs.

### Step 4: Restore Original Paths in Migrated Code (MANDATORY)
> [!IMPORTANT]
> **Path Restoration**: Before proceeding to Handover (Step 4 in SKILL.md), ensure that the final migrated script in the workspace retains the **exact original production paths** and that no test-specific paths or temporary logic remain.
> Perform a diff between the original script and the final migrated script to confirm that ONLY version-compatibility changes were introduced.

### Step 5: Clean Up Resources (CRITICAL)
> [!CAUTION]
> You **MUST** delete the temporary cluster immediately after the job execution completes (whether it succeeded or failed) to avoid ongoing charges.
> Use `gcloud dataproc clusters delete <cluster-name>`.
