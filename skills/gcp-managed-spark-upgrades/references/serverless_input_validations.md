# Serverless Input Checks & Source Discovery

How to check inputs and discover the source configuration for **Managed Spark Serverless** batches. Which inputs are required, and when, is defined in the Inputs section of SKILL.md; this file covers only how to check or discover them. For clusters, use `cluster_input_validations.md`.

> [!IMPORTANT]
> **Runtime versions are `<major>.<minor>` only.** Serverless can't pin a sub-minor: every batch runs the newest sub-minor of its runtime. Never ask for, require, or submit a sub-minor version or OS distro. If the user supplies one (e.g. `2.2.45`), use `2.2` and explain why. If the user supplies a cluster image version (e.g. `2.2-debian12`), confirm the deployment type before proceeding. Serverless also fills in whatever you omit (no `--version` runs the current default runtime; no `--subnet` uses the region's `default` subnet), which is why every value must come from the user or the source batch.

## Access checks (input gate, SKILL.md Step 1.2)

```bash
gcloud projects describe <PROJECT_ID> --format="value(projectId)"
gcloud dataproc batches list --project=<PROJECT_ID> --region=<REGION> --limit=1
gcloud storage ls gs://<TARGET_BUCKET>/
```

List the bucket root, not the target prefix: a prefix that doesn't exist yet returns an error even though uploads to it will work. If a command fails with `PERMISSION_DENIED`, `403 Forbidden`, or `NOT_FOUND`, stop and tell the user what failed. The required roles are in the IAM Requirements section of SKILL.md.

## Discover the source (Batch ID)

```bash
gcloud dataproc batches describe <BATCH_ID> --region=<REGION> --project=<PROJECT_ID> --format=json
```

Extract:
- **Job type:** read it from the type-specific field (`pysparkBatch`, `sparkBatch`, `sparkSqlBatch`, `sparkRBatch`, …) and apply the scope gate in SKILL.md: continue only if the job type is supported.
- **Code:** the main code, code dependencies, and arguments from the type-specific field. For PySpark (`pysparkBatch`): `mainPythonFileUri` and `pythonFileUris` (`.py`, `.zip`, `.egg`), plus `jarFileUris`, `fileUris`, `archiveUris` (archives may contain packed Python environments), and `args`; archives that contain compiled extensions must be rebuilt for the target Python (`pyspark_analysis.md`, section 4.2).
- **Runtime:** `runtimeConfig.version` (the source runtime), `runtimeConfig.containerImage` (a custom container, if any), and `runtimeConfig.properties` (carry them forward and re-check them against the target, including GPU properties).
- **Environment:** `environmentConfig.executionConfig.subnetworkUri` or `networkUri`, `serviceAccount`, `networkTags`, and `kmsKey`.
- **Status:** `state` and `stateMessage`, for context. A failed source batch doesn't block the analysis.

**Deleted batch:** if `describe` returns `NOT_FOUND`, recover the original request from the Admin Activity audit log, and read the same fields under `protoPayload.request.batch`:
```bash
gcloud logging read 'protoPayload.methodName="google.cloud.dataproc.v1.BatchController.CreateBatch" AND protoPayload.request.batchId="<BATCH_ID>"' --project=<PROJECT_ID> --limit=1 --format=json
```
If nothing is found, ask the user for the source runtime version and code location.

## Source runtime version

Use `runtimeConfig.version`. If it is empty, the batch ran on whichever runtime was the default when it was submitted: ask the user to confirm the source runtime instead of guessing. Without a Batch ID, the user must give `<major>.<minor>`.

## Target runtime version

- The target must be a supported runtime: check the supported runtimes at https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-versions. If it isn't supported, stop and ask the user to choose a supported runtime.
- `resolve_version.py --type=serverless` confirms that the runtime's page lists releases and prints `<major>.<minor>` (SKILL.md Step 1.4).
- Read the Spark, Java, Scala, Python, and connector versions, and the preinstalled Python libraries, from the newest release column on `https://cloud.google.com/dataproc-serverless/docs/concepts/versions/spark-runtime-<major.minor>`. Serverless tracks map to different Spark versions than cluster images (runtime `1.2` runs Spark 3.5; runtime `2.1` runs Spark 3.4), so use the Serverless list in "Version to Spark Mapping" in `spark_migration_reference.md`.
- Check https://cloud.google.com/dataproc-serverless/docs/release-notes for breaking changes, deprecations, and rollbacks that affect the target runtime.

## Runtime 3.x platform changes

When upgrading from a 1.x/2.x runtime to 3.x, report these platform changes. They aren't code changes, but each can break a working job:
- **Execution identity:** 3.x runs workloads with the submitting user's end-user credentials (EUC) by default; 1.x/2.x run as the Compute Engine default service account. Without `--service-account`, the upgraded job accesses data as the user, who may lack those permissions. To keep the previous identity, pass the source service account explicitly. Automated submitters (Cloud Composer, Cloud Scheduler, CI/CD) must always pass `--service-account` on 3.x, because there is no end user.
- **Staging buckets:** not required on 3.x (managed internally).
- **Log format:** 3.x writes structured JSON logs (`jsonPayload`) instead of plain text (`textPayload`). Update log-based metrics, alerts, and log parsers.
- **Firewall:** 3.x automatically creates a regional system firewall policy for internal subnet traffic.

## Step 2 input checks

### Subnet

Use the user's subnet, otherwise the source batch's `environmentConfig.executionConfig.subnetworkUri`. If that field is empty, the source ran on a network or on the region's `default` subnet; don't assume either, ask.

```bash
gcloud compute networks subnets describe <SUBNET_NAME> --region=<REGION> --project=<SUBNET_PROJECT_ID> --format="json(name,network,privateIpGoogleAccess,ipCidrRange)"
```

For a Shared VPC subnet (`projects/<HOST_PROJECT_ID>/regions/<REGION>/subnetworks/<SUBNET_NAME>`), pass `--project=<HOST_PROJECT_ID>` and `<SUBNET_NAME>` to `subnets describe` and `firewall-rules list` (otherwise use `<PROJECT_ID>`).

1. **Existence:** the subnet exists in `<SUBNET_PROJECT_ID>` and `<REGION>`.
2. **Private Google Access:** Serverless VMs have internal IP addresses only and rely on Private Google Access to reach GCS, BigQuery, and Artifact Registry. If `privateIpGoogleAccess` is `false`, warn the user.
3. **Internal connectivity:** the subnet must allow ingress between its own VMs on all ports. Runtime 3.x creates this rule automatically. For 1.x/2.x targets, confirm that a matching ingress rule exists:
   ```bash
   gcloud compute firewall-rules list --project=<SUBNET_PROJECT_ID> --filter="network:<NETWORK_NAME> AND direction=INGRESS"
   ```
4. **Internet egress:** if the job downloads packages or models at runtime, the subnet needs Cloud NAT.

### Service account

Reuse the source batch's `environmentConfig.executionConfig.serviceAccount`. If it has none, ask whether to use one: it is mandatory on 3.x when an automated system submits the batch (see "Runtime 3.x platform changes").

### Custom container image (only if the source batch used one)

Don't ask about a container image unless the source batch had `runtimeConfig.containerImage`. An image built for the source runtime isn't automatically valid for the target, so ask for an image rebuilt for the target runtime, and review its configuration or Dockerfile when available:
- It is hosted in Artifact Registry or Container Registry.
- It contains no Spark and no JRE: the runtime mounts them.
- For PySpark: it contains no installed `pyspark` package (an old `pyspark` in the image shadows the target version), and if it sets `PYSPARK_PYTHON` to its own environment, that Python (not the runtime's) runs the job, so it must meet the target Spark's Python requirement and its packages must be built for it.
- It includes the `procps` and `tini` packages.

## GPU workloads

If `runtimeConfig.properties` sets `spark.dataproc.executor.resource.accelerator.type`:
- Serverless runtimes bundle the Spark RAPIDS library. If the batch supplies its own RAPIDS jar, check it against the target Spark and Scala versions ("GPU and RAPIDS Compatibility" in `spark_migration_reference.md`).
- XGBoost is bundled only on 1.x runtimes. When moving to 2.x or 3.x, supply XGBoost through dependencies or a custom container.
- The `spark.dataproc.driverEnv.LANG=C.UTF-8` and `spark.executorEnv.LANG=C.UTF-8` properties are required only on runtimes earlier than 2.2.
- Before Step 2, verify the GPU quota (e.g. `NVIDIA_L4_GPUS`) in the target region.
