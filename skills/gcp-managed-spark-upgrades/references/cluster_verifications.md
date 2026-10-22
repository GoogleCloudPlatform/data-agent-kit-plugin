# Managed Spark Cluster Verification Guide

How to run the optional verification (SKILL.md Step 2) for a cluster job: a temporary cluster on the target image runs the upgraded job with redirected output, and is then deleted. Start only after the Step 2 gate in SKILL.md passes.

## V1. Gather and confirm the configuration

- **Project and region:** `--project=<PROJECT_ID> --region=<REGION>`.
- **Image:** `--image-version=<RESOLVED_IMAGE_VERSION>`, the full version from SKILL.md Step 1.4 (e.g. `2.2.88-debian12`). Don't pass a bare track such as `2.2` or `2.2-debian12`: the cluster would get whichever sub-minor is current when it's created, which may differ from the version you analyzed and report. With a custom image, pass `--image=<CUSTOM_IMAGE_URI>` **instead**: `gcloud` accepts only one of `--image` and `--image-version`. Custom image guide: https://docs.cloud.google.com/managed-spark/docs/guides/images
- **Subnet:** `--subnet=<SUBNET>`, checked as described in `cluster_input_validations.md`.
- **Service account:** `--service-account=<SA_EMAIL>` if the source cluster used one.
- **Hardware:** match the source cluster's machine types, worker count, disks, and accelerators.
- **Cluster properties and initialization actions:** carry forward the source cluster's (e.g. `dataproc:pip.packages`, Conda settings, GPU or RAPIDS initialization actions), with the Step 1 compatibility changes applied (e.g. the target `rapids-version` metadata).
- **Job settings:** the source job's entry point, arguments, properties, and dependency flags (for PySpark: `--py-files`, `--jars`, `--files`, `--archives`), with the Step 1 changes applied.
- **Staged code:** upload the changed code and its dependencies to `<target_path>/upg-verify_<app_id>_temp/`.
- **Output:** redirect every output to `<target_path>/test-output_<app_id>_temp/` (SKILL.md rule 4). Replace each job argument or property that names a production output with a path under that directory. If an output path is hardcoded in the code instead, submit the redirected `_temp` copy of the code that rule 4 describes.

**Confirm before you create the cluster (checkpoint 2).** Show the user every value above and where each came from (SKILL.md rule 1). Ask them to confirm the configuration or say what to change, e.g. fewer workers to lower the cost. Apply any changes, and re-check changed inputs as `cluster_input_validations.md` describes. Retries (SKILL.md Step 2.3) reuse the confirmed configuration; ask again only if a fix needs a different one. With `auto_approve: true`, show the configuration and continue without waiting, here and on retries (SKILL.md rule 5).

## V2. Create the temporary cluster

```bash
gcloud dataproc clusters create upg-verify-<unique-id> \
    --project=<PROJECT_ID> \
    --region=<REGION> \
    --image-version=<RESOLVED_IMAGE_VERSION> \
    --subnet=<SUBNET> \
    --labels=purpose=upgrade-verification \
    [--service-account=<SA_EMAIL>] \
    [--master-machine-type=<TYPE>] [--worker-machine-type=<TYPE>] [--num-workers=<N>] \
    [--master-accelerator=type=<GPU_TYPE>,count=<N>] [--worker-accelerator=type=<GPU_TYPE>,count=<N>] \
    [--initialization-actions=<URIS>] [--metadata=<KEY=VALUE,...>] \
    [--properties=<PREFIX:PROPERTY=VALUE,...>]
```

## V3. Submit the job and confirm the result

Submit with the `gcloud dataproc jobs submit` subcommand for the job type, keeping the cluster, project, region, label, and output redirection shown here. For PySpark:

```bash
gcloud dataproc jobs submit pyspark <target_path>/upg-verify_<app_id>_temp/<SCRIPT>.py \
    --cluster=upg-verify-<unique-id> \
    --project=<PROJECT_ID> \
    --region=<REGION> \
    --labels=purpose=upgrade-verification \
    [--py-files=<URIS>] [--jars=<URIS>] [--files=<URIS>] [--archives=<URIS>] \
    [--properties=<KEY=VALUE,...>] \
    [-- <JOB_ARGS>]
```

- `<JOB_ARGS>`: the job arguments gathered in V1, in their original order and with output paths redirected; if there are none, leave out `--` as well. Write each argument as its own single-quoted shell token so the shell doesn't split or expand it. For example, source `args` of `["--date=2026-10-01", "--output=gs://prod/curated/rollup"]` become `-- '--date=2026-10-01' '--output=<target_path>/test-output_<app_id>_temp/rollup'`.
- The command prints the job ID and streams the driver output until the job finishes. If the stream is lost, run `gcloud dataproc jobs wait <JOB_ID> --project=<PROJECT_ID> --region=<REGION>`.
- Verification passes only if `gcloud dataproc jobs describe <JOB_ID> --project=<PROJECT_ID> --region=<REGION> --format="value(status.state)"` returns `DONE` and the expected test output exists under `<target_path>/test-output_<app_id>_temp/`.
- If the job fails, its driver output is at the `driverOutputResourceUri` shown by `gcloud dataproc jobs describe`.

## V4. Clean up

> [!CAUTION]
> A cluster is billed until it is deleted. Delete the cluster once the job finishes successfully or after 3 retries (SKILL.md Step 2.3):
> `gcloud dataproc clusters delete upg-verify-<unique-id> --project=<PROJECT_ID> --region=<REGION> --quiet` (`--quiet` skips the interactive confirmation prompt).

Leave the staged `_temp` code and test output in place and list them in the report; delete them only if the user asks.
