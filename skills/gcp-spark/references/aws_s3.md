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
> **NEVER** use `spark._jsc.hadoopConfiguration()` or
> `spark.sparkContext._jsc.hadoopConfiguration()`. In Spark Connect sessions
> (`ManagedSparkSession`), `_jsc` and `sparkContext` do not exist and raise
> `AttributeError` / `PySparkAttributeError: [JVM_ATTRIBUTE_NOT_SUPPORTED]`.

Configure `fs.s3a.*` properties using either:

-   **Before session creation**:
    `.config("spark.hadoop.fs.s3a.<property>", "<value>")` on
    `SparkSession.builder` (or
    `session_config.runtime_config.properties["spark.hadoop.fs.s3a.<property>"]`
    for `ManagedSparkSession`), OR
-   **At runtime on an active `spark` session**:
    `spark.conf.set("fs.s3a.<property>", "<value>")` (or
    `spark.conf.set("spark.hadoop.fs.s3a.<property>", "<value>")`).
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
`google.auth` + `urllib.request` REST API (zero extra PyPI packages required):

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

### B. Interactive Notebook (`.ipynb`) / Spark Connect (`ManagedSparkSession`)

In Spark Connect sessions, set `fs.s3a.*` via `spark.conf.set(...)` (or via
`session_config.runtime_config.properties` before `getOrCreate()`):

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
set `fs.s3a.path.style.access` and `fs.s3a.connection.ssl.enabled`:

```python
spark.conf.set("fs.s3a.endpoint", "<CUSTOM_S3_ENDPOINT>")
spark.conf.set("fs.s3a.path.style.access", "true")
spark.conf.set("fs.s3a.connection.ssl.enabled", "true")
```

## 5. Networking & IAM Requirements

1.  **Secret Manager IAM**: Grant `roles/secretmanager.secretAccessor` to the
    Dataproc runtime service account so it can read the AWS credentials secrets.
2.  **Outbound Internet Egress (Cloud NAT)**: Dataproc Serverless batches and
    sessions run on VPC subnets with Private Google Access (`enable_private_ip`
    is default). Because Amazon S3 endpoints live outside Google Cloud, the VPC
    subnet **must** have **Cloud NAT** (or a custom egress route) configured so
    driver and executor VMs can reach `*.amazonaws.com`. Without Cloud NAT, S3A
    connections time out with `ConnectTimeoutException`.
