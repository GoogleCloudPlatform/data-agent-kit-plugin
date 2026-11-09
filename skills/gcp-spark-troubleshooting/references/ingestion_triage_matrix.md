# Google Cloud Spark Platform Mechanics & Diagnostic Reference

Mechanisms behind Spark workloads that exchange data with Google Cloud services,
databases, and external endpoints. Use it with
`references/spark_env_inspection.md` (inspector output and read-only commands)
and `references/diagnostic_rules_catalog.md` (stage rules). Examples illustrate
mechanisms; confirm each conclusion against the workload's own evidence.

--------------------------------------------------------------------------------

## 1. Identity, Credential Delegation & Encryption Planes

Different principals act at creation, execution, and storage-encryption time.
Identify the one that failed before recommending a role.

### Caller Impersonation (`iam.serviceAccounts.actAs`)

-   Creating a batch, session, or cluster that runs as a service account
    requires `iam.serviceAccounts.actAs` (for example via
    `roles/iam.serviceAccountUser`) on it for the creating user, scheduler, or
    pipeline account. Submitting a job to an existing cluster does not.
-   A rejected create request never creates the workload: `describe` returns
    `NOT_FOUND`, no Spark application exists, and the error appears only in the
    caller's output (scheduler task log or CLI output). Organization policies
    such as `iam.disableCrossProjectServiceAccountUsage` fail the same way.

### Workload Identity & GCE VM OAuth Scopes

-   **Serverless**: The configured service account; otherwise end-user
    credentials (batch creator or session owner) on runtime `3.0+`, and the
    Compute Engine default service account on earlier runtimes. Grant an
    end-user workload's data access to that user or one of its groups.
-   **Cluster jobs**: The cluster's VM service account, unless the cluster uses
    secure multi-tenancy or personal cluster authentication.
-   **OAuth scopes (clusters)**: Access is the intersection of IAM roles and VM
    scopes, which are fixed at cluster creation. Dataproc always adds
    `devstorage.read_write` and `logging.write`; without `--scopes`, clusters
    also get BigQuery and Bigtable scopes. APIs outside the scopes (such as
    Secret Manager) fail with `ACCESS_TOKEN_SCOPE_INSUFFICIENT` despite IAM
    grants; use the `cloud-platform` scope and control access with IAM.

### Customer-Managed Encryption Keys (CMEK)

-   At-rest CMEK is applied by Google service agents, not by the workload
    principal. Each agent that touches a protected resource needs
    `roles/cloudkms.cryptoKeyEncrypterDecrypter` on the key:
    -   Dataproc Service Agent (Serverless workloads, including batch args):
        `service-<PROJECT_NUMBER>@dataproc-accounts.iam.gserviceaccount.com`.
    -   Compute Engine Service Agent (persistent disks):
        `service-<PROJECT_NUMBER>@compute-system.iam.gserviceaccount.com`.
    -   Cloud Storage service agent of the bucket's project (any bucket with a
        default CMEK key, such as staging, warehouse, or output buckets):
        `service-<PROJECT_NUMBER>@gs-project-accounts.iam.gserviceaccount.com`.
    -   BigQuery encryption service account (CMEK tables):
        `bq-<PROJECT_NUMBER>@bigquery-encryption.iam.gserviceaccount.com`.
-   A missing agent grant fails I/O on the protected resource with a Cloud KMS
    permission error, while the workload principal still needs only Storage or
    BigQuery roles. Keys must be in the same location as the resource.

### Lakehouse (BigLake) Iceberg REST Catalog vs. Storage

-   Catalog calls (namespaces, table metadata commits) are authorized by BigLake
    IAM, while data and metadata files are read and written in Cloud Storage. A
    catalog call can succeed while file I/O returns `403`.
-   The catalog's credential mode decides who needs bucket access:
    -   **End-user credentials** (the default `--credential-mode=end-user`): The
        Spark principal needs BigLake roles plus bucket roles
        (`roles/storage.objectViewer` to read, `roles/storage.objectUser` to
        write).
    -   **Credential vending**: Requires a catalog created with
        `--credential-mode=vended-credentials`, `roles/storage.objectUser` on
        each bucket for the catalog's auto-provisioned service account, and the
        `header.X-Iceberg-Access-Delegation=vended-credentials` catalog property
        (with `io-impl=org.apache.iceberg.gcp.gcs.GCSFileIO`). The Spark
        principal then needs only BigLake roles. Adding the header to an
        end-user-credentials catalog changes nothing.
-   Read the mode with `gcloud alpha biglake iceberg catalogs describe
    <CATALOG>` and the bucket bindings with `gcloud storage buckets
    get-iam-policy gs://<BUCKET>`.

### Secrets & Database Authentication

-   **Secret Manager**: Versions are `ENABLED`, `DISABLED` (reversible), or
    `DESTROYED` (permanent); reading a non-enabled version fails with
    `FAILED_PRECONDITION`. The reading principal needs
    `roles/secretmanager.secretAccessor`. Check states and bindings with
    `spark_env_inspector.py --secret_id=<SECRET_ID>`; never read payloads.
-   **Cloud SQL IAM database authentication** needs the instance flag
    (`cloudsql.iam_authentication=on` for PostgreSQL,
    `cloudsql_iam_authentication=on` for MySQL), a database user named after the
    principal (PostgreSQL: the user email, or the service account email without
    `.gserviceaccount.com`; MySQL: the part before `@`),
    `roles/cloudsql.instanceUser` plus `roles/cloudsql.client`, and a client
    that sends IAM credentials: the Cloud SQL Java connector with
    `enableIamAuth=true`, the Auth Proxy with `--auto-iam-authn`, or an OAuth2
    access token as the password over TLS.
-   **Cloud Spanner**: Reads need `roles/spanner.databaseReader` (or, with
    fine-grained access control, a database role that grants `SELECT`); writes
    need `roles/spanner.databaseUser`.

--------------------------------------------------------------------------------

## 2. VPC Routing, Name Resolution, Capacity & Perimeters

Serverless workloads and internal-IP-only clusters (the default on image `2.2+`)
have no external IPs. Inspect the path with `scripts/spark_env_inspector.py
--action=network`. Timeouts usually point to routing or firewalls,
`UnknownHostException` to DNS, and `Connection refused` to a reachable host
without a listener on that port.

### Egress Paths by Destination

-   **Google APIs**: Private Google Access on the subnet (Dataproc enables it
    automatically for Serverless and internal-IP-only cluster subnets) plus a
    route to the default internet gateway, or routes and DNS for
    `private.googleapis.com` / `restricted.googleapis.com`. A deleted default
    route breaks API access even with Private Google Access enabled.
-   **Public internet endpoints** (other clouds' object stores, public APIs,
    package mirrors): A Cloud NAT gateway on a Cloud Router in the workload
    region whose configuration covers the subnet's primary range. Private Google
    Access does not help.
-   **Private endpoints** (Cloud SQL private IP, AlloyDB, other VPCs,
    on-premises): A route through VPC Network Peering (not transitive), Private
    Service Connect, or Cloud VPN/Interconnect, plus firewall rules that allow
    the traffic on both sides.

### Firewall Evaluation

-   Cloud NGFW applies the first matching rule in this order: hierarchical
    policies (organization, then folders), regional system policies, then VPC
    firewall rules and network firewall policies in the network's enforcement
    order (`AFTER_CLASSIC_FIREWALL` by default: VPC rules first), and finally
    the implied rules (allow egress, deny ingress). `allow` and `deny` stop
    evaluation; `goto_next` continues.
-   Within VPC firewall rules the lowest priority number wins, and `DENY` wins
    over `ALLOW` at equal priority. Rules target all instances, network tags, or
    service accounts; a rule that does not target the workload VMs has no effect
    on them.
-   Serverless runtime `3.0+` workloads (except on Shared VPC) get an
    auto-created regional system policy that allows ingress between workload VMs
    in the subnet and all egress, so only hierarchical policy rules can deny
    their egress. Earlier runtimes and clusters need a VPC rule that allows
    ingress on all ports between workload VMs in the subnet.
-   For the full effective view, run `gcloud compute networks
    get-effective-firewalls <NETWORK>`. Scope fixes to the destination range and
    port, either with a higher-priority allow rule or by narrowing the blocking
    rule's targets.

### Private Cloud DNS Visibility

-   A private zone resolves only for the networks in its visibility list
    (`bound_to_workload_network`). VPC Network Peering does not share private
    zones, so bind the zone to the workload network or create a DNS peering
    zone. Zones can live in another project, so an empty list from the host
    project is not conclusive.

### Subnet IP Capacity

-   Every Serverless driver and executor and every cluster VM uses an address
    from the subnet's primary range. Google Cloud reserves 4 addresses per range
    ($2^{32 - p} - 4$ usable, for example `12` in a `/28`), and other workloads
    and VMs share the rest, so `usable_hosts_estimate` is an upper bound.
-   Exhaustion either blocks creation (`stateMessage` reports insufficient IP
    addresses and no Spark application starts) or, with dynamic allocation,
    leaves executor requests unfulfilled after the driver starts. Fix with a
    larger or additional range, a lower executor ceiling
    (`spark.dynamicAllocation.maxExecutors` or `spark.executor.instances`), or
    fewer concurrent workloads.

### VPC Service Controls (`VPC-SC`)

-   Errors such as `Request is prohibited by organization's policy` with a
    `vpcServiceControlsUniqueIdentifier` come from a service perimeter, which is
    enforced independently of IAM: no role grant (including `roles/owner`)
    bypasses it. Look up the identifier in the protected project's Policy Denied
    audit logs, then change the perimeter's ingress/egress rules or access
    levels (an Access Context Manager administrator task).
-   Workloads inside a perimeter cannot download packages from outside it; use a
    custom container image with dependencies preinstalled.

--------------------------------------------------------------------------------

## 3. Runtime Versions, JVM Classloading & Executor Isolation

### Spark & Scala Binary Compatibility

-   **Dataproc Serverless**: Runtimes `1.1` and `1.2` run Scala `2.12` (Spark
    `3.3` and `3.5`). Runtimes `2.0` to `2.3` run Scala `2.13` (Spark `3.3` to
    `3.5`). Runtime `3.0` runs Spark `4.0` on Scala `2.13` and Java 21, and does
    not use staging buckets, so its batches often have no
    `runtimeInfo.outputUri`; read driver output from Cloud Logging.
-   **Dataproc GCE clusters**: Images `2.0` to `2.3` run Scala `2.12` (Spark
    `3.1` to `3.5`). Image `3.0` runs Spark `4.1` on Scala `2.13`.
-   **Binary matching**: `_2.12` and `_2.13` artifacts are incompatible, and
    connectors built for another Spark minor version (names such as
    `spark-3.5-...` or `...-runtime-3.5_2.13`) can fail on Spark 4 even with the
    right Scala suffix (`NoSuchMethodError`, `NoClassDefFoundError`,
    `AbstractMethodError`). `classified_jars` (`spark_env_inspector.py
    --action=classpath`) compares both versions with the runtime. Note that
    Serverless `2.2` uses Scala `2.13` while image `2.2` uses `2.12`. Pure Java
    JDBC drivers carry neither version.
-   **Spark 4 defaults**: ANSI SQL mode is on, so casts, overflows, and division
    by zero that used to produce `NULL` now fail (see Section 4). Planning a
    runtime upgrade belongs to the `gcp-managed-spark-upgrades` skill.

### Bundled vs. External Connector JARs

-   Serverless runtimes bundle the Cloud Storage and BigQuery connectors
    (versions are listed in each runtime's release notes). Change the BigQuery
    connector with `dataproc.sparkBqConnector.version` or
    `dataproc.sparkBqConnector.uri` instead of adding a second copy with
    `--jars`. GCE images provide Iceberg through the `ICEBERG` optional
    component; otherwise attach the runtime JAR that matches the image's Spark
    and Scala versions.
-   Connectors outside the runtime (such as the Spanner connector or vendor JDBC
    drivers) fail with `ClassNotFoundException` or `DATA_SOURCE_NOT_FOUND`
    unless attached through `--jars`/`jarFileUris` or `spark.jars.packages`.
-   Avoid `spark.{driver,executor}.userClassPathFirst` when uber JARs bundle
    unshaded Guava, Protobuf, or Jackson; relocate conflicting packages with
    shading instead.

### Executor Filesystem Isolation

-   Executors run on other VMs and cannot read files that exist only on the
    client or driver, so tasks fail with `FileNotFoundException` or
    `SSLHandshakeException` when opening CA certificates, truststores, or
    keytabs.
-   `--files` (`spark.files`) places each file in every executor's working
    directory under its bare name, while `SparkFiles.get()` called on the driver
    returns a driver-only temporary path. Pass a path that resolves on every JVM
    that opens the connection, or use a connector that needs no local
    certificate files (such as the Cloud SQL Java connector). Keep certificate
    verification (`sslmode=verify-ca` or `verify-full`) enabled.

--------------------------------------------------------------------------------

## 4. Connector Contracts, Data Framing & Schema Evolution

### Session-Startup vs. Runtime Properties

-   Static SQL configurations, notably `spark.sql.extensions` (for example
    `IcebergSparkSessionExtensions`), take effect only when the first
    `SparkSession` starts. `spark.conf.set()` rejects them, and builder
    `.config()` calls on an already running session (notebooks, interactive
    sessions) are ignored with a warning. Pass them as batch, job, or session
    properties (`gcloud beta dataproc sessions` takes `--location`).
-   Catalog plugins (`spark.sql.catalog.<name>` and its options) are runtime
    settings: a catalog is created on first use with the options set at that
    moment, so set them before the first reference.

### Connector Configuration Requirements

-   **BigQuery views and queries**: Reading a view or a SQL query needs
    `viewsEnabled=true`. The connector runs a query job and materializes the
    result in a temporary table, so the principal needs `bigquery.jobs.create`
    (for example `roles/bigquery.user`) and table creation rights where
    `materializationProject` / `materializationDataset` point.
-   **BigQuery writes**: The indirect write method stages files in Cloud Storage
    and needs `temporaryGcsBucket` with write access for the principal;
    `writeMethod=direct` uses the Storage Write API and needs no bucket.
-   **BigLake Iceberg REST catalog**: Under `spark.sql.catalog.<name>`, set
    `org.apache.iceberg.spark.SparkCatalog`, `type=rest`,
    `uri=https://biglake.googleapis.com/iceberg/v1/restcatalog`, `warehouse`
    (`bl://projects/<PROJECT>/catalogs/<CATALOG>` for multi-bucket catalogs or
    `gs://<BUCKET>` for single-bucket catalogs), `header.x-goog-user-project`,
    `rest.auth.type=org.apache.iceberg.gcp.auth.GoogleAuthManager`, and
    `io-impl=org.apache.iceberg.gcp.gcs.GCSFileIO`, plus the Iceberg SQL
    extensions. `GoogleAuthManager` ships with Dataproc's Iceberg (image
    `2.2.65+` / `2.3.11+`) and OSS Iceberg `1.10+`; older OSS releases use
    OAuth2 token settings instead. The simplified property
    `dataproc.lakehouse.catalog.<name>=projects/<PROJECT>/catalogs/<CATALOG>`
    (with a `dataproc:` prefix on clusters) sets all of this.
-   **Parallel JDBC reads**: Without `partitionColumn`, `lowerBound`,
    `upperBound`, and `numPartitions` (set together) or a `predicates` list,
    Spark reads the table with one query in one task. Bounds only set the stride
    (rows outside them land in the first or last partition), and every partition
    opens its own connection, so keep `numPartitions` within the database's
    connection limits. `fetchsize` tunes rows per round trip and does not add
    parallelism.

### CSV Framing & ANSI Type Casting

-   **Multi-line CSV**: Quoted fields with embedded newlines need
    `multiLine=true` (with matching `quote` and `escape`); otherwise records
    split into extra rows with shifted columns. Each multi-line file is read by
    a single task.
-   **ANSI mode** (`spark.sql.ansi.enabled=true`, the Spark 4 default): Invalid
    casts raise `[CAST_INVALID_INPUT]`, and overflow or division by zero raise
    errors instead of returning `NULL`.
    -   Cast errors: apply `try_cast` (or other `try_*` functions) to the dirty
        columns and route rows whose result is `NULL` while the input was not
        into a quarantine table.
    -   Parse errors while reading CSV or JSON: use `mode=PERMISSIVE` with an
        explicit schema and `columnNameOfCorruptRecord` to keep malformed
        records. `badRecordsPath` is a Databricks option that Apache Spark
        ignores.
    -   Turning ANSI mode off globally restores silent `NULL` or wrapped values
        for every query in the job, so bad data loads unnoticed. It is a
        trade-off for the user to decide, not a fix.

### Destination Schema Alignment

-   Compare the DataFrame schema (from the code, via
    `scripts/spark_code_inspector.py`) with the live destination schema (via
    `@skill:knowledge-catalog`): `REQUIRED` columns reject nulls, and nested
    `STRUCT` / `RECORD` fields must match by name and type.
-   Fix by casting and aligning columns and by filtering or quarantining rows
    that violate `REQUIRED`. Relaxing or extending the destination schema is a
    change for the table owner, and dropping, replacing, or overwriting an
    existing table loses data.

--------------------------------------------------------------------------------

## 5. Stage Telemetry Mechanics & End-to-End Conservation

Author workload-specific rules for `scripts/spark_stage_diagnostics.py` using
`references/diagnostic_rules_catalog.md` (or summarize GCE cluster event logs
with `scripts/spark_gcs_log_reader.py --action=summarize_events`), and read the
complete remote script with `scripts/spark_code_inspector.py`:

-   **Single-Task Scans**: A root read stage with `num_tasks == 1` and
    substantial input points to an unpartitioned JDBC read, non-splittable
    compressed text (gzip, or raw zstd/Snappy text), or multi-line CSV/JSON.
    Parquet, ORC, and Avro (with any internal codec) and bzip2 or uncompressed
    text are splittable.
-   **Partition Skew**: Compare `task_quantile_metrics.duration_millis.maximum`
    and the input byte/record quantiles with `percentile_50`. Enable Adaptive
    Query Execution skew handling, check join and exchange sizes
    (`spark_applications.py --action=sql`) and whether hints or
    `spark.sql.autoBroadcastJoinThreshold` prevent broadcasting a small side,
    or salt hot keys.
-   **Row-Wise Python UDFs**: `@udf` functions move rows one at a time between
    the JVM and Python workers (`BatchEvalPython` in the plan, which the bundled
    tools do not print). Find them in the code with
    `scripts/spark_code_inspector.py` and replace them with built-in functions
    or vectorized `@pandas_udf` functions.
-   **Small-File Overhead**: Many short tasks that each read little data mean
    scheduling dominates. Look for many small input files or a
    `spark.sql.files.maxPartitionBytes` far below its default; compact files,
    let AQE coalesce shuffle partitions, and reduce output files with
    `.coalesce(N)` before writes (it avoids a shuffle but lowers the parallelism
    of the final stage).
-   **Memory & Disk Spill**: Non-zero `memory_bytes_spilled` or
    `disk_bytes_spilled` indicates sort, shuffle, or aggregation memory
    pressure. Push filters and projections earlier, increase
    `spark.sql.shuffle.partitions`, or raise executor memory within the
    Serverless memory-per-core limits.
-   **Zero-Output Row Drops**: When input stages read `records_read > 0` with no
    failed tasks but nothing reaches the destination, a filter predicate, join
    condition, or type or format mismatch removed every row after the read.
    Output metrics (`records_written`) stay `0` for JDBC writes, `foreach` /
    `foreachPartition` sinks, and actions such as `.count()` or `.show()`, so
    confirm with a read-only row count at the destination.
