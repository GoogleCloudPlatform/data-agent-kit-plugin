# Managed Spark Serverless Verification Guide

How to run the optional verification (SKILL.md Step 2) for a Serverless workload: a temporary batch on the target runtime runs the upgraded job with redirected output. Start only after the Step 2 gate in SKILL.md passes.

## V1. Gather and confirm the configuration

- **Project and region:** `--project=<PROJECT_ID> --region=<REGION>`.
- **Runtime:** `--version=<MAJOR.MINOR>` (e.g. `--version=3.0`), never a sub-minor.
- **Batch ID:** `--batch=upg-verify-<unique-id>` (4–63 characters: lowercase letters, digits, and hyphens). Use a new ID for every retry.
- **Subnet:** `--subnet=<SUBNET>`, checked as described in `serverless_input_validations.md`. Always pass it: omitting it silently uses the region's `default` subnet.
- **Network tags and encryption key:** `--tags=<TAGS>` and `--kms-key=<KMS_KEY>` if the source batch set them (`networkTags`, `kmsKey`).
- **Service account:** `--service-account=<SA_EMAIL>` if the source batch used one or the user gave one. Otherwise leave it out (see "Service account" in `serverless_input_validations.md`): on 1.x/2.x the batch then runs as the Compute Engine default service account, and on 3.x with the submitting user's credentials.
- **Custom container image:** `--container-image=<TARGET_IMAGE_URI>` only if the source batch used a custom container; the image must be rebuilt for the target runtime.
- **Carry forward from the source batch:** the entry point, job arguments, properties, and dependency flags (for PySpark: `--py-files`, `--jars`, `--files`, `--archives`), with the Step 1 changes applied.
- **Resources:** Serverless has no machine types: the source batch's [resource allocation properties](https://docs.cloud.google.com/managed-spark/docs/concepts/spark-properties-serverless#resource_allocation_properties), passed with `--properties`, set the hardware. Keep them as the source set them: driver and executor cores, memory, and memory overhead; disk size and tier; compute tier and `dataproc.tier`; `spark.executor.instances`; and the `spark.dynamicAllocation.*` limits. Anything the source didn't set uses the Serverless default (e.g. 4 cores per executor, autoscaling up to 1000 executors).
- **Staged code:** upload the changed code and its dependencies to `<target_path>/upg-verify_<app_id>_temp/`.
- **Output:** every output, redirected as SKILL.md rule 4 describes: list each job argument or property you changed, or the `_temp` copy of the code.

**Confirm before you submit the batch (checkpoint 2).** Show the user every value above, resource properties included, and where each came from (SKILL.md rule 1): the user, the source batch, or the Serverless default. Ask them to confirm the configuration or say what to change, e.g. a lower `spark.dynamicAllocation.maxExecutors` to cap the cost. Apply any changes, and re-check changed inputs as `serverless_input_validations.md` describes. Retries (SKILL.md Step 2.3) reuse the confirmed configuration; ask again only if a fix needs a different one. If the user asked to automatically approve the workflow (SKILL.md rule 5), show the configuration and continue without waiting, here and on retries.

## V2. Submit the test batch

Submit with the `gcloud dataproc batches submit` subcommand for the job type, keeping the flags shown here. For PySpark:

```bash
gcloud dataproc batches submit pyspark <target_path>/upg-verify_<app_id>_temp/<SCRIPT>.py \
    --batch=upg-verify-<unique-id> \
    --project=<PROJECT_ID> \
    --region=<REGION> \
    --version=<MAJOR.MINOR> \
    --subnet=<SUBNET> \
    --ttl=<DURATION> \
    --labels=purpose=upgrade-verification \
    [--service-account=<SA_EMAIL>] \
    [--tags=<TAGS>] [--kms-key=<KMS_KEY>] \
    [--container-image=<TARGET_IMAGE_URI>] \
    [--py-files=<URIS>] [--jars=<URIS>] [--files=<URIS>] [--archives=<URIS>] \
    [--properties=<KEY=VALUE,...>] \
    [--staging-bucket=<TARGET_BUCKET_NAME>] \
    [-- <JOB_ARGS>]
```

- `--ttl` (e.g. `2h`) unconditionally terminates a runaway batch. Set it to about 2–3 times the source batch's run time.
- `--staging-bucket` takes a bucket name, not a `gs://` path. Use it on 1.x/2.x runtimes so that dependencies and driver output stay in your bucket; 3.x manages staging internally.
- `<JOB_ARGS>`: the job arguments gathered in V1, in their original order and with output paths redirected; if there are none, leave out `--` as well. Write each argument as its own single-quoted shell token so the shell doesn't split or expand it (write a single quote inside an argument as `'\''`). For example, source `args` of `["--date=2026-10-01", "--output=gs://prod/curated/rollup"]` become `-- '--date=2026-10-01' '--output=<target_path>/test-output_<app_id>_temp/rollup'`.

## V3. Monitor and confirm the result

- The submit command streams the driver output until the batch finishes. If you used `--async` or lost the stream, run `gcloud dataproc batches wait upg-verify-<unique-id> --project=<PROJECT_ID> --region=<REGION>`.
- Confirm the final state:
    ```bash
    gcloud dataproc batches describe upg-verify-<unique-id> \
        --project=<PROJECT_ID> \
        --region=<REGION> \
        --format="value(state,stateMessage)"
    ```
    Verification passes only if the state is `SUCCEEDED` and the expected test output exists under `<target_path>/test-output_<app_id>_temp/`.
- If the batch fails, read the driver output:
    ```bash
    gcloud logging read \
        'resource.type="cloud_dataproc_batch" AND resource.labels.batch_id="upg-verify-<unique-id>" AND logName="projects/<PROJECT_ID>/logs/dataproc.googleapis.com%2Foutput"' \
        --project=<PROJECT_ID> \
        --limit=200
    ```
    Runtime 3.x log messages are in `jsonPayload`; 1.x/2.x messages are in `textPayload`.

## V4. Clean up

> [!CAUTION]
> A running batch is billed until it finishes. If you stop monitoring before the batch reaches a terminal state, cancel it:
> `gcloud dataproc batches cancel upg-verify-<unique-id> --project=<PROJECT_ID> --region=<REGION>`

- A finished batch uses no compute. Keep it, so that its details and logs stay available for the report, unless the user asks you to delete it (`gcloud dataproc batches delete upg-verify-<unique-id> --project=<PROJECT_ID> --region=<REGION> --quiet`).
- Leave the staged `_temp` code and test output in place and list them in the report; delete them only if the user asks.
