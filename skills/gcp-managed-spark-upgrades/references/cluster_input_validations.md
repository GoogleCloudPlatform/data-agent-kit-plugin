# Cluster Input Checks & Source Discovery

How to check inputs and discover the source configuration for **Managed Spark cluster** jobs. Which inputs are required, and when, is defined in the Inputs section of SKILL.md; this file covers only how to check or discover them. For Serverless batches, use `serverless_input_validations.md`.

## Access checks (input gate, SKILL.md Step 1.2)

```bash
gcloud projects describe <PROJECT_ID> --format="value(projectId)"
gcloud dataproc clusters list --project=<PROJECT_ID> --region=<REGION> --limit=1
gcloud storage ls gs://<TARGET_BUCKET>/
```

- The second command confirms the region, the Managed Spark API, and your access in one call.
- List the bucket root, not the target prefix: a prefix that doesn't exist yet returns an error even though uploads to it will work.
- If a command fails with `PERMISSION_DENIED`, `NOT_FOUND`, or an API-not-enabled error, stop and tell the user what failed. The required roles are in the IAM Requirements section of SKILL.md.

## Discover the source (Job ID)

1. Describe the job and keep the full JSON. The job payload sits in a type-specific field (`pysparkJob`, `sparkJob`, `sparkSqlJob`, …), so a narrower `--format` projection silently drops the code URIs, arguments, and properties.
   ```bash
   gcloud dataproc jobs describe <JOB_ID> --region=<REGION> --project=<PROJECT_ID> --format=json
   ```
2. Read the job type from that field and apply the scope gate in SKILL.md: continue only if the job type is supported.
3. From the job, extract:
   - `placement.clusterName` and `placement.clusterUuid`;
   - from the type-specific field: the main code, code dependencies, arguments, and properties. For PySpark (`pysparkJob`): `mainPythonFileUri`, `pythonFileUris`, and `archiveUris` (source code), `jarFileUris` (JVM dependencies), `args`, and `properties`;
   - `status.state`, for context (a failed source job doesn't block the analysis).
4. Describe the source cluster:
   ```bash
   gcloud dataproc clusters describe <CLUSTER_NAME> --region=<REGION> --project=<PROJECT_ID> --format="json(config)"
   ```
   Extract:
   - **Source image version:** `config.softwareConfig.imageVersion`.
   - **Subnet:** `config.gceClusterConfig.subnetworkUri`. If only `networkUri` is set, ask the user for a subnet before Step 2.
   - **Service account:** `config.gceClusterConfig.serviceAccount` (absent means the default Compute Engine service account).
   - **Custom image:** a `config.masterConfig.imageUri` outside the `cloud-dataproc` project (`projects/<IMAGE_PROJECT>/global/images/<IMAGE_NAME>`). Inspect its base Managed Spark version with:
     ```bash
     gcloud compute images describe <IMAGE_NAME> --project=<IMAGE_PROJECT> --format="json(name,labels,family,description)"
     ```
     Read `labels.goog-dataproc-version` (and `family` / `description`) to identify the underlying source Managed Spark version, and tell the user that a custom image built for the target version is needed (or that a standard image can be used instead).
   - **Hardware:** machine types, disk configuration, worker count, and accelerators in `config.masterConfig` and `config.workerConfig`, for the Step 2 cluster.
   - **GPU/RAPIDS:** accelerators, GPU-driver or RAPIDS initialization actions, and RAPIDS properties (analyze them with "GPU and RAPIDS Compatibility" in `spark_migration_reference.md`).
   - **Dependencies outside the code:** `config.initializationActions`, plus (for PySpark) the `dataproc:pip.packages` and `dataproc:conda.packages` properties in `config.softwareConfig.properties`. They feed the dependency build check.
5. **Deleted (ephemeral) cluster:** if the cluster `describe` returns `NOT_FOUND`, recover the configuration from the Admin Activity audit log, using the cluster UUID (cluster names can be reused; UUIDs can't):
   ```bash
   gcloud logging read 'resource.type="cloud_dataproc_cluster" AND resource.labels.cluster_uuid="<CLUSTER_UUID>" AND protoPayload.methodName="google.cloud.dataproc.v1.ClusterController.CreateCluster"' --project=<PROJECT_ID> --limit=1 --format="json(protoPayload.request.cluster.config)"
   ```
   Read the same fields under `protoPayload.request.cluster.config`. If the audit logs have expired or are inaccessible, ask the user for the source image version (Step 1 needs it); ask for the Step 2 inputs only when Step 2 is about to run.

## Source image version

- Expected format: `<major>.<minor>.<sub-minor>-<distro>` (e.g. `1.5.8-debian10`, `2.0.35-debian10`).
- If the user gives only `<major>.<minor>` (e.g. `1.5`), ask for the full version (or for the sub-minor and OS distro) and continue the analysis at track level meanwhile: sub-minor releases can change component versions, so an exact delta needs the full version. State the assumption in the report.

## Target image version

- Accepted formats: `<major>.<minor>[.<sub-minor>][-<distro>]` (e.g. `2.2`, `2.2-debian12`, `2.2.88-debian12`).
- Without a sub-minor, resolve one with `resolve_version.py --type=cluster` (SKILL.md Step 1.4). The script skips rolled-back versions. To minimize environment drift, check the source image's OS family (e.g. `debian`, `ubuntu`, `rocky`) and pass it via `--distro` if known. Step 2 pins the result with `--image-version`, because a bare track such as `2.2` would get whichever sub-minor is current when the cluster is created.
- If the script can't run, read the version columns on `https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-release-<major.minor>` and take the newest one for the chosen distro.
- Skim the release notes (https://cloud.google.com/dataproc/docs/release-notes) for the chosen version. If it has a known critical issue, pick the previous sub-minor and explain why in the report.

## Subnet checks (before Step 2)

A cluster needs a subnet in the job's region that can reach Google APIs (GCS, BigQuery, Artifact Registry). Use the user's subnet, otherwise the source cluster's; if neither exists, ask. Don't fall back to the project's `default` network on your own.

```bash
gcloud compute networks subnets describe <SUBNET_NAME> --region=<REGION> --project=<SUBNET_PROJECT_ID> --format="json(name,network,privateIpGoogleAccess,ipCidrRange)"
```

For a Shared VPC subnet (`projects/<HOST_PROJECT_ID>/regions/<REGION>/subnetworks/<SUBNET_NAME>`), pass `--project=<HOST_PROJECT_ID>` and `<SUBNET_NAME>` to `subnets describe` (otherwise use `<PROJECT_ID>`).

1. **Existence and region:** the command succeeds, and the subnet is in `<REGION>`.
2. **Private Google Access:** internal-IP-only clusters need `privateIpGoogleAccess: true` to reach GCS and the Managed Spark control plane. If it is `false`, warn the user and recommend enabling it or confirming that Cloud NAT is configured.
3. **Internal traffic (advisory):** cluster nodes need open internal TCP/UDP/ICMP traffic within the subnet. If the verification job fails with heartbeat or master–worker connection timeouts, check the firewall rules on the network.

## GPU checks (before Step 2)

If the source uses GPUs, confirm that the target region offers the GPU type (e.g. `nvidia-tesla-t4`, `nvidia-l4`): `gcloud compute accelerator-types list --filter="name=<GPU_TYPE>"` lists the zones that have it. If cluster creation fails, check the regional GPU quota. Compatibility of the image, CUDA, driver, and RAPIDS versions belongs to the analysis ("GPU and RAPIDS Compatibility" in `spark_migration_reference.md`).
