# Spark Environment Inspection Guide (`scripts/spark_env_inspector.py`)

Use `scripts/spark_env_inspector.py` to collect read-only Google Cloud identity,
VPC network, and runtime classpath metadata for Dataproc Serverless batches,
interactive sessions, and standard GCE cluster jobs. The script only runs
`describe`, `list`, and `get-iam-policy` style `gcloud` commands: it never
changes resources and never reads secret payloads.

Treat the script as an opaque tool: you MUST run
`python3 scripts/spark_env_inspector.py --help` to check supported flags rather
than reading its source code.

--------------------------------------------------------------------------------

## 1. CLI Invocation & Target Selection

Pass one workload target flag and one `--action` plane:

```
python3 scripts/spark_env_inspector.py \
  --batch_id=<BATCH_ID> \
  --project=<PROJECT_ID> \
  --region=<REGION> \
  --action=identity
```

-   **Target flags** (choose one):
    -   `--batch_id=<BATCH_ID>`: Dataproc Serverless batch.
    -   `--session_id=<SESSION_ID>`: Dataproc Serverless interactive session.
    -   `--job_id=<JOB_ID>`: Standard Dataproc GCE cluster job. When the cluster
        still exists, the script also inspects `placement.clusterName`.
-   **Common options**:
    -   `--project=<PROJECT_ID>`: GCP project ID (defaults to active `gcloud`
        project).
    -   `--region=<REGION>` (or `--location=<REGION>`): Workload region
        (default: `us-central1`).
    -   `--action`: Inspection plane (`identity`, `network`, or `classpath`).
    -   `--format`: Output format (`markdown` default, or `json`).

--------------------------------------------------------------------------------

## 2. Inspection Planes

### Identity, KMS & Secret Manager (`--action=identity`)

Run this plane when logs show `403 PERMISSION_DENIED`, `AccessDeniedException`,
OAuth scope errors, CMEK failures, or Secret Manager errors.

-   `user_workload_authentication_type`: Either `SERVICE_ACCOUNT` or
    `END_USER_CREDENTIALS` (the default on Serverless runtime `3.0+` when no
    service account is specified).
-   `effective_principal`: The IAM member that Spark code acts as when it calls
    Google APIs.
    -   `SERVICE_ACCOUNT`: The configured service account, or the default
        `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com` account when
        none is configured (`default_service_account_inferred=True`).
    -   `END_USER_CREDENTIALS`: The session owner (`session_user`) or, for
        batches, the `creator`. Data access roles must be granted to that user
        (or to a group that contains it), not to a service account.
    -   Cluster jobs report the cluster VM service account. Clusters with secure
        multi-tenancy or personal cluster authentication run jobs as another
        principal, which the script reports in `warnings`.
-   `service_account_scopes`: GCE VM OAuth scopes on cluster jobs (Serverless
    workloads have none). Dataproc always adds `devstorage.read_write`,
    `logging.write`, and `cloud.useraccounts.readonly`, so scopes never block
    Cloud Storage object reads or writes. A custom scope list without
    `cloud-platform` blocks the APIs it does not cover (such as BigQuery or
    Secret Manager) even when IAM roles are granted.
-   `kms_key`, `staging_bucket`, and `temp_bucket`: Customer-managed encryption
    key and workspace buckets attached to the workload. An unset Serverless
    staging bucket means a Dataproc-managed bucket on runtimes before `3.0`;
    runtime `3.0+` does not use staging buckets.
-   `project_iam_roles`: Roles (and condition titles) bound **directly** to
    `effective_principal` in the workload project's IAM policy. Inherited
    folder/organization roles, group membership, and resource-level bindings
    (buckets, datasets, KMS keys, service accounts) are not evaluated, so an
    empty list does not prove that access is missing (see Section 4).
-   `auth_related_properties`: Authentication, catalog, and SSL Spark properties
    (including values set by autotuning) with sensitive values replaced by
    `<REDACTED>`.
-   `--secret_id=<SECRET_ID>` (optional): Lists Secret Manager version states
    (`ENABLED`, `DISABLED`, `DESTROYED`), secret-level IAM bindings, and the
    `principal_roles_on_secret` held directly by `effective_principal`. Accepts
    either `<SECRET_ID>` or a `projects/.../secrets/.../versions/...` URI. It
    MUST NOT read secret payloads (`secrets versions access` is never called).

### VPC, Subnet, NAT, Peering, Firewall & DNS (`--action=network`)

Run this plane when logs show `ConnectTimeoutException`, `UnknownHostException`,
`No route to host`, or subnet IP exhaustion in `stateMessage`.

-   `effective_host_project` and `effective_network`: Resolves the VPC network
    and Shared VPC host project from `subnetworkUri` or `networkUri`.
-   `workload_service_account`: The VM service account used to evaluate
    firewall rules that target service accounts. It is inferred as the Compute
    Engine default account when unset, and unknown with end-user credentials.
-   `subnet`: Reports `ip_cidr_range`, `usable_hosts_estimate`, and
    `private_ip_google_access`.
    -   `usable_hosts_estimate` is the total capacity of the primary range, not
        the number of free addresses.
    -   Dataproc enables Private Google Access automatically on the subnet of
        Serverless workloads and internal-IP-only clusters (the default on image
        `2.2+`). If it reads `False` on an internal-IP workload, Google APIs and
        Cloud Storage are reachable only through another path such as Cloud
        NAT.
-   `cloud_nats`: Lists Cloud Router NAT gateways on the VPC in the workload
    region and sets `covers_workload_subnet` when a public NAT translates the
    workload's primary subnet range. Cloud NAT is only needed for public
    internet endpoints, not for Google APIs or private (RFC 1918) destinations.
-   `vpc_peerings`: Lists peered networks with their `state` (`ACTIVE` or
    `INACTIVE`) and custom route import/export flags. Private databases in
    another VPC need an `ACTIVE` peering (or VPN, Interconnect, or Private
    Service Connect). VPC peering is not transitive.
-   `firewall_rules` (optional `--target_port=<PORT>`): VPC firewall rules on
    the network that apply (`applies_to_workload=True`) or may apply (`None`,
    when a service-account target cannot be resolved) to the workload VMs, plus
    `DENY` and port-matching rules scoped to other targets so near misses stay
    visible. Rules are sorted in evaluation order: lowest priority number first
    and, at equal priority, `DENY` before `ALLOW`.
-   `firewall_policy_enforcement_order` and `firewall_policies`: The effective
    hierarchical (organization and folder), global and regional network, and
    regional system firewall policy rules for the network and region. Long IP
    range lists are truncated, and rules that target secure tags report
    `applies_to_workload=None`.
-   `private_dns_zones`: Lists private Cloud DNS zones in the host project and
    sets `bound_to_workload_network`. If `False`, the workload VPC cannot
    resolve records in that zone. Zones in other projects (cross-project
    bindings or DNS peering zones) are not listed.

#### Firewall Evaluation Order

For each new connection, Cloud NGFW applies the first matching rule in this
order:

1.  Hierarchical firewall policies (organization, then folders).
2.  Regional system firewall policies.
3.  VPC firewall rules and network firewall policies: VPC rules first under the
    default `AFTER_CLASSIC_FIREWALL` enforcement order, network policies first
    under `BEFORE_CLASSIC_FIREWALL`.
4.  Implied rules: allow all egress, deny all ingress.

`allow` and `deny` stop evaluation, while `goto_next` continues to the next
level. A rule with `applies_to_workload=False` cannot allow or block the
workload's traffic, even if it matches the port.

Serverless runtime `3.0+` workloads (except on Shared VPC) get an auto-created
regional system firewall policy (`dataproc-firewall-policy-*` or
`dataproc-fw-*`). It allows ingress from workload VMs in the same subnet and
all egress, and targets a per-subnet secure tag. Because system policies are
evaluated before VPC rules and network policies, only hierarchical policy rules
can block egress for these workloads.

### Runtime, Scala ABI & Classpath (`--action=classpath`)

Run this plane when logs show `NoSuchMethodError`, `ClassNotFoundException`,
`NoClassDefFoundError`, `ModuleNotFoundError`, or missing worker files and
catalog settings.

-   `runtime_spark_version` and `runtime_scala_binary_version`: Maps the
    Serverless runtime or GCE cluster image version to its Spark minor version
    and Scala binary version (`2.12` vs. `2.13`). Unmapped versions report
    `unknown`.
-   `classified_jars`: Checks `mainJarFileUri`, `jarFileUris`, `spark.jars`, and
    `spark.jars.packages`:
    -   `scala_binary_version`: The `_2.12` or `_2.13` artifact suffix.
    -   `spark_minor_version`: The Spark version in connector names such as
        `spark-3.5-bigquery` or `iceberg-spark-runtime-3.5_2.13`.
    -   `scala_matches_runtime` and `spark_matches_runtime`: `False` indicates a
        binary incompatibility with the runtime. `None` means that the artifact
        name carries no version (for example a shaded uber JAR); confirm with
        `scripts/spark_code_inspector.py` or the build file.
-   **Distributed files and properties**: Lists `main_python_file_uri`,
    `notebook_file_uri`, `file_uris`, `python_file_uris`, `archive_uris`,
    cluster `optional_components`, `container_image`, redacted `args`, and
    redacted `classpath_and_catalog_properties`.

--------------------------------------------------------------------------------

## 3. Exit Status & Partial Visibility

-   Verify exit code `0` before relying on output. Exit code `1` means the
    target batch, session, or job itself could not be fetched, or no project
    could be resolved.
-   If secondary calls (such as `get-iam-policy`, VPC queries, or describing a
    deleted cluster) return `403` or `404`, the script still exits `0` and
    records the skipped check in `warnings`. Always report `warnings` explicitly
    instead of assuming an unqueried IAM role, NAT, or firewall rule is absent.
-   Long VPC firewall rule and policy rule lists are capped; a warning reports
    the truncation.

--------------------------------------------------------------------------------

## 4. Read-Only Checks Outside the Script

The script reports workload configuration and direct project-level bindings.
Confirm resource-level access with these read-only commands:

-   **Bucket IAM, default KMS key, and uniform bucket-level access**:
    `gcloud storage buckets get-iam-policy gs://<BUCKET>` and
    `gcloud storage buckets describe gs://<BUCKET>`.
-   **CMEK key IAM**: `gcloud kms keys get-iam-policy <KEY>
    --keyring=<KEYRING> --location=<LOCATION> --project=<KMS_PROJECT>`.
-   **Service account impersonation** (`iam.serviceAccounts.actAs`):
    `gcloud iam service-accounts get-iam-policy <SERVICE_ACCOUNT_EMAIL>`.
-   **Inherited, group, and deny-policy effects on one permission**:
    `gcloud policy-intelligence troubleshoot-policy iam <FULL_RESOURCE_NAME>
    --principal-email=<EMAIL> --permission=<PERMISSION>`.
-   **Effective firewalls of a cluster VM**: `gcloud compute instances
    network-interfaces get-effective-firewalls <VM_NAME> --zone=<ZONE>`.
-   **VPC Service Controls**: Errors with `Request is prohibited by
    organization's policy` include a `vpcServiceControlsUniqueIdentifier`;
    look it up in the Cloud Audit Logs of the protected project.
