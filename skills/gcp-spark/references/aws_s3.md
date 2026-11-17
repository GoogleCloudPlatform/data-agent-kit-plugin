# Reading and Writing Amazon S3 (`s3a://`) Data in PySpark

> [!IMPORTANT]
> You MUST follow these rules when reading from or writing to Amazon S3 or
> S3-compatible object storage in PySpark on Dataproc Serverless and Dataproc on
> GCE clusters.

## 1. Pre-Installed `hadoop-aws` Connector (No Extra JARs)

Managed Spark on Google Cloud (Dataproc Serverless and Dataproc on GCE clusters)
pre-installs `hadoop-aws.jar` and the matching AWS SDK bundle in
`/usr/lib/hadoop/lib/`.

> [!CAUTION]
> - **DO NOT** pass `org.apache.hadoop:hadoop-aws`,
>   `com.amazonaws:aws-java-sdk-bundle`, or `software.amazon.awssdk:bundle` via
>   `--jars`, `spark.jars`, or `spark.jars.packages`. Mixing external JARs with
>   the pre-installed Hadoop runtime causes `NoSuchMethodError` and
>   `ClassCastException` failures.
> - **ALWAYS** use the `s3a://` URI scheme (never legacy `s3://` or `s3n://`).
> - **NEVER** run `gcloud storage ls` on `s3a://` URIs.

## 2. Configuring S3A Properties (Spark Connect & Batch Compatible)

> [!CAUTION]
> **NEVER** call `spark._jsc.hadoopConfiguration()` or
> `spark.sparkContext._jsc.hadoopConfiguration()` in **any** PySpark workload
> (including standalone `.py` Serverless batch and cluster scripts as well as
> Spark Connect and Remote Kernel notebooks). `_jsc` accesses private Py4J JVM
> internals that fail on Spark Connect (`ManagedSparkSession`) with
> `AttributeError` / `PySparkAttributeError: [JVM_ATTRIBUTE_NOT_SUPPORTED]`, and
> is unnecessary in batch and cluster jobs when `spark.hadoop.fs.s3a.*`
> properties are set on `SparkSession.builder` before `.getOrCreate()`. Do NOT
> add `_jsc.hadoopConfiguration()` alongside `SparkSession.builder.config(...)`
> as a fallback.

Configure `fs.s3a.*` properties according to the execution mode:

-   **Standalone `.py` batch and cluster jobs (`SparkSession.builder`)**:
    Pass all `fs.s3a.*` properties (including credentials, `endpoint`,
    `path.style.access`, and `connection.ssl.enabled`) via
    `.config("spark.hadoop.fs.s3a.<property>", "<value>")` on
    `SparkSession.builder` **before** calling `.getOrCreate()`. On a classic JVM
    `SparkSession`, calling `spark.conf.set("fs.s3a.*", ...)` after
    `.getOrCreate()` updates Spark SQL configuration rather than the initialized
    `SparkContext` Hadoop `Configuration`.
-   **Local Python / Spark Connect notebooks (`.ipynb`,
    `ManagedSparkSession`)**:
    Set `spark.conf.set("fs.s3a.<property>", "<value>")` on the active Spark
    Connect session, or pass
    `.config("spark.hadoop.fs.s3a.<property>", "<value>")` on
    `ManagedSparkSession.builder` before calling `.getOrCreate()`.
-   **Pre-initialized Remote Kernel notebooks (`.ipynb`, classic JVM)**:
    Because `spark` is already initialized and `SparkSession.builder` cannot be
    re-invoked, use `spark.conf.set("fs.s3a.<property>", "<value>")` for
    DataFrame and Spark SQL reads/writes (which read per-session Hadoop settings
    via `SessionState.newHadoopConf()`) without calling `_jsc`.
-   **Endpoint & Region Alignment (`fs.s3a.endpoint`)**: Always set
    `fs.s3a.endpoint` explicitly to the bucket's regional endpoint
    (`s3.<AWS_REGION>.amazonaws.com`) to avoid cross-region redirects and v4
    signature errors, and run the Dataproc cluster or Serverless batch in the
    closest matching GCP region to minimize cross-cloud latency.

### Credentials Providers

-   For access key + secret key authentication, **ALWAYS** use:
    `org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider`
-   For temporary session credentials (access key + secret key + session token),
    use `org.apache.hadoop.fs.s3a.TemporaryAWSCredentialsProvider`.
-   For public/anonymous S3 buckets only, use
    `org.apache.hadoop.fs.s3a.AnonymousAWSCredentialsProvider`.

## 3. Retrieving AWS Credentials from Google Cloud Secret Manager

Never hardcode AWS access keys or secret keys in code or CLI flags. Retrieve
them at runtime from Google Cloud Secret Manager using the pre-installed
`google.auth` + `urllib.request` REST API (zero extra PyPI packages required).
If the Secret Manager secret IDs are not provided by the user or fail with
`404 Not Found` / `403 PermissionDenied`, you MUST **STOP and ask the user** for
the secret IDs—do NOT guess secret names, scan unrelated secrets, or create new
secrets without user confirmation:

```python
import base64
import json
import urllib.request
import google.auth
import google.auth.transport.requests


def get_secret(
    project_id: str, secret_id: str, version_id: str = "latest"
) -> str:
    """Retrieve a secret payload from Google Cloud Secret Manager."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)

    url = (
        f"https://secretmanager.googleapis.com/v1/projects/{project_id}"
        f"/secrets/{secret_id}/versions/{version_id}:access"
    )
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {credentials.token}"},
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
    return base64.b64decode(data["payload"]["data"]).decode("utf-8").strip()
```

## 4. Complete PySpark Examples

### A. Dataproc Batch / Cluster Job (`.py`) Reading from S3

```python
import logging
import os
from pyspark.sql import SparkSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "<PROJECT_ID>")
aws_access_key = get_secret(project_id, "<AWS_ACCESS_KEY_SECRET_ID>")
aws_secret_key = get_secret(project_id, "<AWS_SECRET_KEY_SECRET_ID>")

spark = (
    SparkSession.builder.appName("s3-read-job")
    .config(
        "spark.hadoop.fs.s3a.aws.credentials.provider",
        "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
    )
    .config("spark.hadoop.fs.s3a.access.key", aws_access_key)
    .config("spark.hadoop.fs.s3a.secret.key", aws_secret_key)
    .config("spark.hadoop.fs.s3a.endpoint", "s3.<AWS_REGION>.amazonaws.com")
    .getOrCreate()
)

# Parquet / ORC / Avro / JSON / CSV reads work transparently with s3a://
df = spark.read.parquet("s3a://<BUCKET_NAME>/<PATH_TO_DATA>")
df.printSchema()
logging.info("Row count: %d", df.count())
```

For CSV files on S3, include `header` and `inferSchema`:

```python
df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv("s3a://<BUCKET_NAME>/<PATH_TO_FILE>.csv")
)
```

### B. Interactive Notebook (`.ipynb`, Spark Connect & Remote Kernel)

In Local Python / Spark Connect notebooks, set `fs.s3a.*` via
`spark.conf.set(...)` on the active session (or pass
`.config("spark.hadoop.fs.s3a.<property>", "<value>")` on
`ManagedSparkSession.builder` before `.getOrCreate()`). On pre-initialized
Remote Kernel notebooks (classic JVM), use `spark.conf.set(...)` on the active
`spark` session for DataFrame and Spark SQL reads/writes:

```python
spark.conf.set(
    "fs.s3a.aws.credentials.provider",
    "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
)
spark.conf.set("fs.s3a.access.key", aws_access_key)
spark.conf.set("fs.s3a.secret.key", aws_secret_key)
spark.conf.set("fs.s3a.endpoint", "s3.<AWS_REGION>.amazonaws.com")

df = spark.read.parquet("s3a://<BUCKET_NAME>/<PATH_TO_DATA>")
df.show(10)
```

### C. S3-Compatible Object Storage / Custom Endpoint

When connecting to S3-compatible object storage or a custom S3 endpoint, also
configure `fs.s3a.endpoint`, `fs.s3a.path.style.access`, and
`fs.s3a.connection.ssl.enabled` (`"true"` by default for HTTPS; set to `"false"`
only for plain HTTP endpoints) without calling `_jsc.hadoopConfiguration()`:

-   **Standalone `.py` batch / cluster job (`SparkSession.builder`)**:

    ```python
    spark = (
        SparkSession.builder.appName("s3-custom-endpoint-job")
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        )
        .config("spark.hadoop.fs.s3a.access.key", aws_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", aws_secret_key)
        .config("spark.hadoop.fs.s3a.endpoint", "<CUSTOM_S3_ENDPOINT>")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config(
            "spark.hadoop.fs.s3a.connection.ssl.enabled", "true"
        )  # Set to "false" for plain HTTP endpoints (e.g., local MinIO)
        .getOrCreate()
    )
    ```

-   **Interactive notebook (`.ipynb` — Local Python / Spark Connect or Remote
    Kernel)**:

    ```python
    spark.conf.set("fs.s3a.endpoint", "<CUSTOM_S3_ENDPOINT>")
    spark.conf.set("fs.s3a.path.style.access", "true")
    spark.conf.set(
        "fs.s3a.connection.ssl.enabled", "true"
    )  # Set to "false" for plain HTTP endpoints (e.g., local MinIO)
    ```

## 5. Networking & IAM Requirements

1.  **Secret Manager IAM & GCE Scopes**: Grant
    `roles/secretmanager.secretAccessor` to the Dataproc runtime service account
    so it can read the AWS credentials secrets (and pass
    `--scopes=cloud-platform` when creating a Dataproc on GCE cluster).
2.  **Outbound Internet Egress (Cloud NAT)**: Dataproc Serverless batches and
    sessions run on VPC subnets with Private Google Access (`enable_private_ip`
    is default). Because Amazon S3 endpoints live outside Google Cloud, the VPC
    subnet **must** have **Cloud NAT** (or a custom egress route) configured so
    driver and executor VMs can reach `*.amazonaws.com`. Without Cloud NAT, S3A
    connections time out with `ConnectTimeoutException`.
