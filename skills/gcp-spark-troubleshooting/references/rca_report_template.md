# Root Cause Analysis (RCA) Report Template

Run the checks in the first section before you write the report, then use
[Template Structure](#template-structure) for the final RCA artifact.

--------------------------------------------------------------------------------

## Checks Before You Write

Run any missing read-only command first. Skip a check when its topic doesn't
come up in the evidence or in your fix. Before you send the report, re-read
every fix in it against this list. The mechanisms behind each check are in
`references/ingestion_triage_matrix.md` (the matrix), in the section named in
the check.

1.  **Every fault**: Report each fault you found, and keep later blockers apart
    from the root cause. Compare each catalog and connector setting in the code
    with the matrix: for example, an Iceberg REST catalog without `uri` or auth
    settings fails once the job reaches it.
2.  **CMEK keys**: For each bucket the workload uses, run `gcloud storage
    buckets describe gs://<BUCKET> --format="value(default_kms_key)"`, and read
    `gcloud kms keys get-iam-policy <KEY>` for that key or for a key that a
    Cloud KMS error names. Grant `roles/cloudkms.cryptoKeyEncrypterDecrypter` on
    the key itself, only to the service agent that the matrix's CMEK section
    names for the resource (for a bucket, the Cloud Storage service agent of the
    bucket's project), never to the workload's service account.
3.  **Subnet capacity**: For IP space exhaustion, list the reservations in the
    host project and in the workload's project with `gcloud compute addresses
    list --project=<PROJECT> --regions=<REGION>
    --filter="subnetwork~/subnetworks/<SUBNET>$"`. Then count the free addresses
    and size the fix as Subnet IP Capacity says: a range for the driver plus the
    executor ceiling, or fewer executors only when the free addresses hold the
    driver plus the runtime's minimum (2 executors on runtimes `2.3` and
    earlier, 1 on `3.0` and later).
4.  **Private Google Access**: Before you cite it, apply the Google APIs entry
    of Egress Paths by Destination: `False` doesn't block a batch on a subnet in
    the workload's own project, fails startup on a Shared VPC subnet in another
    project, and never matters for endpoints outside Google, which need Cloud
    NAT on that subnet.
5.  **Versions and connector JARs**: Take the Spark and Scala versions from the
    driver's runtime log line, from `runtime_spark_version` in
    `scripts/spark_env_inspector.py --action=classpath`, or from the table in
    Spark & Scala Binary Compatibility (Serverless runtime and cluster image
    numbers differ). Flag every attached JAR whose Spark version or Scala suffix
    (such as `spark-3.5` or `runtime-4.0_2.13`) doesn't match. Never propose a
    build for another Spark version, even when it is the only one you found:
    recommend removing the JAR or a release with a matching build, and name the
    artifact to look for.
6.  **Casts and rejected rows**: Cover every cast column in the failing
    statement, and scan the input for values that break any of them. Pair each
    `try_cast` or permissive read with an output that keeps the original values
    of the rejected rows, and count them (CSV Framing & ANSI Type Casting). Test
    each column on its own: a value is invalid when it isn't null but its
    `try_cast` is. Show that code. A bare `try_cast` is not a fix, and neither
    is ANSI mode off.
7.  **Data values and type drift**: Never invent values (such as placeholder
    keys), and never extract, parse, or truncate a value into a type that can't
    hold it (such as digits pulled out of a text label), even when you note the
    loss. When a column's values change type, propose a new nullable field whose
    type holds them: the owner adds it, and your code writes the values there
    and the `try_cast` result to the old field, for example
    `F.col("<col>").alias("<new_field>"), F.expr("try_cast(<col> AS
    <TARGET_TYPE>)").alias("<old_field>")`. If the old field is `REQUIRED`,
    quarantine the rows it can't hold. Or leave the mapping to the data owner.
    Offer no in-place type change that BigQuery doesn't support (Destination
    Schema Alignment).
8.  **Write targets and schemas**: Compare the whole DataFrame schema with the
    table: every `REQUIRED` column must be non-nullable in the DataFrame, and
    every type and nested field must match. A null filter keeps the DataFrame's
    `nullable=True` schema, so rebuild it with the table's schema before the
    write, for example
    `spark.createDataFrame(valid_df.select(*table_schema.names).rdd,
    table_schema)` (classic PySpark, not Spark Connect). Before you name a
    dataset or bucket in a fix, check that the workload principal can write
    there: `bq show` lists only a dataset's own access entries, so confirm with
    the troubleshoot-policy command in `references/spark_env_inspection.md`.
9.  **BigQuery views**: Name the `materializationDataset` and check that the
    workload principal can create tables there, or read the base tables
    (Connector Configuration Requirements).
10. **Executor files**: Keep driver-only paths (such as `SparkFiles.get` called
    on the driver) out of executor connection settings (Executor Filesystem
    Isolation).
11. **Skew**: For every stage after a shuffle (a join, an aggregation, or a
    `repartition` on a key), compare the median and maximum task duration in
    `scripts/spark_applications.py --action=stages`, not only the largest stage.
    A task far above the median is a straggler. Call it a hot key only when it
    also reads far more shuffle data than the median task, even in a stage with
    few tasks: compare its shuffle read in
    `--action=tasks --stage_id=<N> --sort=duration`, or the shuffle read records
    quantile of `--action=stage --stage_id=<N>` (the bytes quantile counts only
    local blocks). With even reads, it points at the node or at slow external
    calls. Name the stage, and the key when the data shows it.
12. **Perimeters and TLS**: IAM roles can't fix a VPC Service Controls denial
    (VPC Service Controls). Give the perimeter administrators the perimeter,
    service, identity, direction, and `vpcServiceControlsUniqueIdentifier`. A
    caller outside the perimeter needs an ingress rule on it, and an egress rule
    goes on the caller's own perimeter only when the caller is inside one. For a
    JDBC TLS error, check each TLS property against the driver and the
    connection path (JDBC TLS): PgJDBC has no `trustServerCertificate`, and
    behind a Cloud SQL or AlloyDB connector the driver's own TLS stays off.
13. **Commands**: Copy resource names, flags, and properties from the evidence.
    In `gcloud dataproc batches submit` and `gcloud dataproc jobs submit`, job
    arguments go after a bare `--` (there is no `--args` flag). A resubmitted
    batch needs a new batch ID, because the failed batch keeps the old one.
14. **IAM and Lakehouse catalogs**: Grant the narrowest predefined role on the
    resource that failed (Least-Privilege IAM in `SKILL.md`), such as
    `roles/storage.objectUser` instead of `roles/storage.objectAdmin`, or
    `roles/biglake.editor` instead of `roles/biglake.admin`. For a BigLake
    Iceberg REST catalog, read its credential mode with
    `gcloud biglake iceberg catalogs describe <CATALOG>` before a bucket grant:
    under end-user credentials the workload principal needs the bucket grant,
    and under vended credentials the catalog's service account does (Lakehouse
    section). Prefer a dedicated service account over widening the Compute
    Engine default account.

--------------------------------------------------------------------------------

## Template Structure

### Root Cause Analysis (RCA): [Job/Batch ID] Failure

-   **Workload Type**: `[Dataproc Serverless Batch | Dataproc Cluster Job]`
-   **Target ID**: `[BATCH_ID or JOB_ID]`
-   **Region**: `[REGION]`
-   **Execution Timestamp**: `[START_TIME]` to `[END_TIME]`
-   **Status**:
    `[STATE from describe, such as FAILED, ERROR, SUCCEEDED, or TERMINATED]`

--------------------------------------------------------------------------------

### 1. Executive Summary

Brief 2-3 sentence overview of what failed, why it failed, and what immediate
action is required.

--------------------------------------------------------------------------------

### 2. Evidence Gathered

#### A. Log Diagnostics

-   **Log Source**: `[Cloud Logging | GCS Driver Output gs://... | Event Log
    gs://...]`
-   **Key Error Log / Traceback**:

```text
[Paste relevant log snippet or Python traceback here]
```

#### B. Stage & Telemetry Metrics

-   **Violated Diagnostic Rules** (only rule IDs that
    `scripts/spark_stage_diagnostics.py` reported; write `None` if it didn't run
    or found none):
    -   `[RULE_ID]`: `[e.g. GC_PRESSURE: GC was 24% of run time in Stage 2]`
    -   `[RULE_ID]`: `[e.g. DISK_SPILL: 4.2 GiB spilled to disk in Stage 2]`

#### C. Code Context (Source of Truth)

-   **Failing Script/Archive**: `[gs://path/to/script.py]`
-   **Failing Line**: Line `[LINE_NUMBER]`

```python
# [Paste relevant snippet of code from remote GCS file]
```

--------------------------------------------------------------------------------

### 3. Root Cause Analysis

Detailed explanation of why the failure occurred, explaining the correlation
between the input data, stage metrics, memory pressure/skew, and the offending
code line.

--------------------------------------------------------------------------------

### 4. Later Blockers

Faults on code paths that this run never reached, such as a write that comes
after the failing step. Each would fail the workload once the root cause is
fixed, so list each one with its evidence and its own least-privilege fix, and
keep it out of the root cause above. Omit this section when there are none.

--------------------------------------------------------------------------------

### 5. Remediation Plan

#### Immediate Fix

Code modification or Spark property tuning to resolve the failure:

```python
# Fixed code snippet or modified submission command
```

#### Spark Tuning Recommendations

Only properties that the evidence supports, each with its reason. Leave out a
setting that is already on by default, such as AQE from Spark 3.2. Omit this
section when nothing applies.

-   `--properties spark.driver.memory=...`
-   `--properties spark.executor.memory=...`
-   `--properties spark.sql.shuffle.partitions=...`
