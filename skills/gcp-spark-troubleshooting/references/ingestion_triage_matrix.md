# Google Cloud Spark Platform Mechanics & Diagnostic Reference

Architectural reference for diagnosing Google Cloud Spark pipelines across
identity and encryption planes, VPC routing and perimeters, runtime Scala/JVM
classloading, connector contracts, and stage execution telemetry.

--------------------------------------------------------------------------------

## 1. Identity, Credential Delegation & Encryption Planes

Google Cloud evaluates three distinct principal planes during a Spark workload's
lifecycle. Identifying which plane rejected an operation prevents misdiagnosing
caller or encryption errors as worker role gaps (`scripts/spark_env_inspector.py
--action=identity`).

### Submission & Impersonation Plane (`iam.serviceAccounts.actAs`)

-   Before Dataproc creates a Serverless batch, interactive session, or cluster
    job, the submitting principal (for example, a Cloud Composer / Airflow
    worker, scheduler, or developer identity) must hold
    `iam.serviceAccounts.actAs` (`roles/iam.serviceAccountUser`) on the target
    workload service account.
-   When impersonation or a cross-project service account organization policy
    (`iam.disableCrossProjectServiceAccountUsage`) fails, control-plane creation
    is rejected before any driver starts: `describe` returns `NOT_FOUND`, `0`
    Spark applications exist, and the root cause appears in the caller or
    orchestrator logs rather than Spark driver logs.

### Workload Execution Plane & GCE VM OAuth Scopes

-   Runtime data access runs as `executionConfig.serviceAccount` on Serverless
    or `gceClusterConfig.serviceAccount` on GCE clusters. When omitted,
    **Serverless Runtime `3.0+`** defaults to `END_USER_CREDENTIALS` (the
    submitting user identity), whereas **Serverless `1.x`/`2.x`** and **GCE
    clusters** default to `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`
    (unless `END_USER_CREDENTIALS` is explicitly configured).
-   On standard GCE Dataproc clusters, effective Google API permissions equal
    the **intersection** of IAM policy bindings and the VM's OAuth
    `service_account_scopes`. A narrow scope such as `devstorage.read_only`
    blocks Cloud Storage writes, BigQuery loads, or Secret Manager calls with
    `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT` even when the service account holds
    the required IAM role; clusters must be provisioned with
    `--scopes=cloud-platform`.

### Google-Managed Service Agent Plane (CMEK)

-   When Customer-Managed Encryption Keys (`kmsKey`) protect cluster disks,
    staging or temporary Cloud Storage buckets, or BigQuery tables, Cloud KMS
    evaluates `cloudkms.cryptoKeyVersions.useToEncrypt` and `useToDecrypt`
    (`roles/cloudkms.cryptoKeyEncrypterDecrypter`) against **both** the workload
    service account and the Google-managed service agents acting on its behalf:
    -   Dataproc control plane & Serverless RM node agents:
        `service-<PROJECT_NUMBER>@dataproc-accounts.iam.gserviceaccount.com` and
        `service-<PROJECT_NUMBER>@gcp-sa-dataprocrmnode.iam.gserviceaccount.com`
    -   Compute Engine persistent disk encryption agent:
        `service-<PROJECT_NUMBER>@compute-system.iam.gserviceaccount.com`
    -   Cloud Storage service agent:
        `service-<PROJECT_NUMBER>@gs-project-accounts.iam.gserviceaccount.com`
    -   BigQuery encryption agent:
        `bq-<PROJECT_NUMBER>@bigquery-encryption.iam.gserviceaccount.com`

### Catalog Metadata Plane vs. Storage Data Plane

-   Lakehouse catalogs such as BigLake Metastore / Iceberg REST authorize table
    metadata RPCs independently from the underlying `gs://` Parquet and metadata
    objects.
-   If catalog resolution succeeds (`200 OK`) but reading or writing table files
    returns `403`, verify whether credential vending is enabled via
    `header.X-Iceberg-Access-Delegation=vended-credentials` alongside BigLake
    roles (`roles/biglake.viewer` or `roles/biglake.admin`), or whether the
    workload service account requires direct bucket-level `roles/storage` access
    (`roles/storage.objectViewer` / `roles/storage.objectUser`) on the warehouse
    bucket.

### Secret Lifecycle & Managed Database Authentication

-   **Secret Manager**: Secret versions move through `ENABLED`, `DISABLED`, and
    `DESTROYED` (irreversible — point workloads to an `ENABLED` version and
    grant `roles/secretmanager.secretAccessor`). Inspect version metadata via
    `spark_env_inspector.py --secret_id=...` or `secrets versions list`; never
    call `secrets versions access` during triage.
-   **Cloud SQL & Spanner**: Cloud SQL IAM login requires
    `cloudsql.iam_authentication=on`, PostgreSQL user formatted without
    `.gserviceaccount.com`, `roles/cloudsql.client` +
    `roles/cloudsql.instanceUser`, and Cloud SQL JDBC Socket Factory with
    `enableIamAuth=true` (omit `sslmode` with Socket Factory; never set
    `sslmode=disable`) or an OAuth2 token over TLS (`sslmode=require`), kept
    distinct from password auth. Spanner reads require
    `roles/spanner.databaseReader` or `roles/spanner.fineGrainedAccessUser`
    with a `SELECT` `databaseRole`.

--------------------------------------------------------------------------------

## 2. VPC Routing, Name Resolution, Capacity & Perimeters

Dataproc Serverless always executes on internal IPs (`internal_ip_only=true`),
as do `--no-address` GCE clusters. Diagnose connectivity timeouts and name
errors by destination class (`scripts/spark_env_inspector.py --action=network`).

### Egress Routing by Destination Class

-   **Google APIs (`*.googleapis.com`)**: Requires `private_ip_google_access`
    enabled on the workload subnetwork (in `effective_host_project` for Shared
    VPC). Without it, connections to Cloud Storage, BigQuery, or BigLake time
    out before TLS negotiation.
-   **Public Internet Endpoints (AWS S3, Azure Blob, external HTTPS/JDBC)**:
    Private Google Access only routes Google IP ranges. External endpoints
    require a regional Cloud Router and Cloud NAT gateway (`cloud_nats`) whose
    subnetwork configuration covers the workload subnet.
-   **Private RFC1918 Endpoints (Cloud SQL private IP, AlloyDB, on-prem)**:
    Requires VPC Network Peering (Private Services Access), Private Service
    Connect (PSC), or Cloud VPN/Interconnect routes on the workload VPC.

### VPC Firewall Precedence & Network Tags

-   GCE evaluates firewall rules in ascending numeric `priority` (`0` to
    `65535`); a lower-number `EGRESS` `DENY` rule overrides higher-number
    `ALLOW` rules.
-   Tag-scoped rules apply only when the workload carries matching `networkTags`
    or cluster `tags` (`--target_port=<PORT>` checks TCP port coverage). Scope
    remediations to specific destination CIDRs, ports, and tags rather than
    `0.0.0.0/0`.

### Private Cloud DNS Zone Visibility

-   Private Cloud DNS managed zones resolve records **only** for VPC networks
    explicitly bound in `privateVisibilityConfig.networks`
    (`bound_to_workload_network=true`); otherwise lookups fail with
    `UnknownHostException` even when VPC peering exists, unless DNS peering or a
    network binding is added.

### Subnetwork IP Capacity vs. Executor Scaling

-   Google Cloud reserves 4 IP addresses per subnet CIDR ($2^{32 - p} - 4$
    usable hosts, reported as `usable_hosts_estimate`; for example, `/29` has
    `4` usable IPs and `/28` has `12`). When driver plus executor nodes exceed
    available IPs, provisioning fails before Spark starts (`0` stages); move to
    a wider subnet (`>= /24`) or cap `spark.dynamicAllocation.maxExecutors`.

### VPC Service Controls (`VPC-SC`) Perimeters

-   `403 PERMISSION_DENIED` responses carrying
    `vpcServiceControlsUniqueIdentifier` (`SECURITY_POLICY_VIOLATED`) originate
    from an organization security perimeter, which is evaluated orthogonally to
    IAM. Adding IAM roles cannot satisfy a perimeter block; correlate the
    identifier in Cloud Audit Logs and configure a VPC-SC ingress or egress
    policy rule.

--------------------------------------------------------------------------------

## 3. Runtime Versions, JVM Classloading & Executor Isolation

### Dataproc Runtime Matrix & Scala Binary Compatibility

-   **Dataproc Serverless Runtimes**: `1.1` (Spark `3.3`) and `1.2` (Spark
    `3.5`) run **Scala `2.12`**; `2.0` (Spark `3.3`), `2.1` (Spark `3.4`), and
    `2.2` / `2.3` (Spark `3.5`, default) run **Scala `2.13`**; `3.0` runs Apache
    Spark `4.0` on **Scala `2.13`** with `spark.sql.ansi.enabled=true` and
    `END_USER_CREDENTIALS` by default, and emits driver logs primarily to Cloud
    Logging (`cloud_dataproc_batch`).
-   **Dataproc GCE Cluster Images**: `2.0` (Spark `3.1`), `2.1` (Spark `3.3`),
    and `2.2` / `2.3` (Spark `3.5`) run **Scala `2.12`**; `3.0` runs Apache
    Spark **`4.1`** on **Scala `2.13`** with `spark.sql.ansi.enabled=true`.
-   Scala `2.12` and `2.13` are binary incompatible (`NoSuchMethodError`,
    `IncompatibleClassChangeError`, `NoClassDefFoundError` on `scala.*`). Every
    Scala-suffixed JAR (`_2.12` vs. `_2.13`) in `classified_jars`
    (`spark_env_inspector.py --action=classpath`) must match
    `runtime_scala_binary_version` (note that Serverless `2.2` requires `_2.13`
    whereas GCE Cluster `2.2` requires `_2.12`). Pure Java drivers (such as
    PostgreSQL or MySQL JDBC JARs) carry no Scala suffix.

### Pre-Installed Libraries, External JARs & Shading

-   Dataproc Serverless pre-installs runtime-matched `spark-bigquery` and
    `iceberg-spark-runtime` connectors; passing conflicting or wrong-Scala
    copies in `--jars` or `spark.jars.packages` shadows built-in classes and
    should be removed. On GCE clusters, enable `--optional-components=ICEBERG`
    or attach the matching runtime artifact.
-   Connectors not bundled in the base runtime (such as `spark-spanner` or
    vendor JDBC drivers) raise `ClassNotFoundException` unless attached via
    `--jars` / `jarFileUris`.
-   Enabling `userClassPathFirst=true` lets unshaded Guava, Protobuf, or Jackson
    classes inside user uber-JARs override Spark runtime dependencies; relocate
    conflicting packages via shading instead of inverting classloader order.

### Driver vs. Executor Filesystem Isolation

-   Executors run on isolated worker nodes and cannot read local files present
    only on the client or driver, causing executor tasks to fail with
    `FileNotFoundException` or `SSLHandshakeException` (`PKIX path building
    failed`) when loading custom CA certificates, JKS truststores, or keytabs.
-   Distribute auxiliary files via `--files=gs://...` (`spark.files` /
    `file_uris`) and resolve them from the working directory via
    `SparkFiles.get("<name>")` or `./<name>`, preserving certificate validation
    (`sslmode=verify-ca` or `verify-full`).

--------------------------------------------------------------------------------

## 4. Connector Contracts, Data Framing & Schema Evolution

### Session-Startup vs. Runtime-Mutable Spark Properties

-   `spark.sql.extensions` and catalog plugins (`spark.sql.catalog.<name>`) bind
    when the `SparkSession` initializes. Calling `spark.conf.set(...)` inside
    application or notebook code after session startup cannot register SQL
    parser extensions (`IcebergSparkSessionExtensions`) or catalog classes; set
    them at batch/job submission or interactive session / session-template
    creation (`gcloud beta dataproc sessions` uses `--location`).

### Coupled Connector Property Sets

-   **BigQuery (`spark-bigquery`)**: Reading logical `VIEW`s requires
    `viewsEnabled=true` together with `materializationProject` and
    `materializationDataset`. `INDIRECT` writes stage files to GCS and require
    `temporaryGcsBucket` (`DIRECT` uses the Storage Write API).
-   **BigLake Iceberg REST**: Under `spark.sql.catalog.<cat>` (where `<cat>`
    matches `<bucket>` for GCS-backed BigLake catalogs), configure
    `SparkCatalog`, `type=rest`, the BigLake REST `uri`, root bucket
    `warehouse=gs://<bucket>`, `header.x-goog-user-project=<project>`,
    `rest.auth.type=org.apache.iceberg.gcp.auth.GoogleAuthManager` (required on
    Iceberg `1.6.x` in Dataproc `2.2`/`2.3`; short alias `google` requires
    Iceberg `1.10+`), `io-impl=org.apache.iceberg.gcp.gcs.GCSFileIO`, and
    `header.X-Iceberg-Access-Delegation=vended-credentials` alongside
    `IcebergSparkSessionExtensions`.
-   **Parallel JDBC Reads**: Without partitioning options, Spark runs a single
    unbounded query (`numTasks=1`). Parallelizing requires `partitionColumn`
    (indexed numeric, date, or timestamp), `lowerBound`, `upperBound`, and
    `numPartitions` **together**, plus `fetchsize` (for example, `5000` to
    `10000`) while keeping `numPartitions` safely below database
    `max_connections`.

### Text Framing, Malformed Input & Spark 4.0 ANSI Mode

-   CSV payloads containing embedded newlines or quotes shift columns unless
    `multiLine=true`, `quote`, and `escape` options are configured together.
-   With `spark.sql.ansi.enabled=true` (default on Spark `4.0`), invalid casts
    fail fast (`[CAST_INVALID_INPUT]` / `SparkNumberFormatException`). Use
    column-scoped `TRY_CAST` (`expr("try_cast(...)")`) or quarantine corrupt
    records (`badRecordsPath` or `PERMISSIVE` with `columnNameOfCorruptRecord`)
    rather than disabling `spark.sql.ansi.enabled` globally.

### Sink Schema & Nullability Alignment

-   Compare code-level DataFrame projections (`scripts/spark_code_inspector.py`)
    with live destination schemas via `@skill:discovering-gcp-data-assets`.
    Pre-existing tables define schema contracts (`REQUIRED` modes, nested
    `STRUCT` types, partitioning, and ACLs) even at `0` rows: never drop,
    `CREATE OR REPLACE TABLE`, or `mode("overwrite")` target tables; filter or
    quarantine nulls, cast/project explicit `STRUCT` subfields, or use additive
    `ALTER TABLE ... ADD COLUMN` only when intended.

--------------------------------------------------------------------------------

## 5. Stage Telemetry Mechanics & End-to-End Conservation

Author workload-calibrated rules for `scripts/spark_stage_diagnostics.py` per
`references/diagnostic_rules_catalog.md` (and summarize GCE cluster event logs
via `scripts/spark_gcs_log_reader.py --action=summarize_events`):

-   **Single-Task Root Scans**: A root scan (`num_tasks == 1` with
    `stage_shuffle_read_metrics.bytes_read == 0` and non-trivial input bytes or
    records) reflects unpartitioned JDBC or non-splittable `.gz` archives;
    partition JDBC reads or use splittable Parquet, Avro, ORC, or Zstandard
    files (tuning `spark.sql.files.maxPartitionBytes` when splits are huge).
-   **Partition Skew & Python `@udf` Serialization**: Compare
    `task_quantile_metrics.duration_millis.maximum` and byte quantiles against
    `percentile_50` (noting sparse stages where `percentile_50 == 0` makes
    `ratio(max, p50)` return `0.0`). Check SQL exchange sizes
    (`spark_applications.py --action=sql`) to size `autoBroadcastJoinThreshold`,
    enable AQE skew join or salting, and replace row-wise `@udf`
    (`BatchEvalPython`) code with Spark SQL expressions or `@pandas_udf`.
-   **Memory & Disk Spill Pressure**: Non-zero `memory_bytes_spilled` or
    `disk_bytes_spilled` indicates shuffle/sort memory pressure; push filters
    early, raise `spark.sql.shuffle.partitions`, or raise
    `spark.executor.memory` within Serverless minimums (`>= 4` cores, `>= 1024m`
    per core).
-   **Small-File & Tiny-Task Storms**: High `num_tasks` with tiny average
    `stage_input_metrics.bytes_read` or sub-100ms p50 runtime means scheduling
    dominates; compact files, remove tiny `maxPartitionBytes` overrides, enable
    AQE coalescing, and use `.coalesce(N)` before writes rather than
    `.repartition(N)`.
-   **Post-Read Zero-Output Conservation & Full-Script Verification**: Across
    `stages`, completed stages with `records_read > 0`, `0` failed tasks, and
    `0` total `stage_output_metrics.records_written` / `bytes_written` show that
    a filter, timestamp/timezone literal, join key, or path pattern dropped all
    data (`.count()`/`.show()` jobs also write `0` output records). Always
    inspect the complete remote script and config so masked downstream sink or
    catalog bugs are surfaced in the same RCA.
