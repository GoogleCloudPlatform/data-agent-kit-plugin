# Reading and Writing Azure Blob Storage & ADLS Gen2 Data in PySpark

> [!IMPORTANT]
> You MUST follow these rules when reading from or writing to Azure Data Lake
> Storage Gen2 (`abfss://`) or Azure Blob Storage (`wasbs://`, `wasb://`) in
> PySpark on Dataproc Serverless and Dataproc on GCE clusters.

## 1. Pre-Installed `hadoop-azure` Connector (No Extra JARs)

Managed Spark on Google Cloud (Dataproc Serverless and Dataproc on GCE clusters)
pre-installs `hadoop-azure.jar` and its required Azure Storage SDK dependencies
in `/usr/lib/hadoop/lib/`.

> [!CAUTION]
> - **DO NOT** pass `org.apache.hadoop:hadoop-azure` or
>   `com.microsoft.azure:azure-storage*` via `--jars`, `spark.jars`, or
>   `spark.jars.packages`. Mixing external JARs with the pre-installed Hadoop
>   runtime causes `NoSuchMethodError` and `ClassCastException` failures.
> - **NEVER** run `gcloud storage ls` on `abfss://`, `wasbs://`, or `wasb://`
>   URIs.

## 2. Choosing the URI Scheme (`abfss://` vs `wasbs://`)

-   **Azure Data Lake Storage Gen2 (ADLS Gen2 — hierarchical namespace)**:
    Use the `abfss://` scheme with the `.dfs.core.windows.net` endpoint:
    ```
    abfss://<CONTAINER>@<STORAGE_ACCOUNT>.dfs.core.windows.net/<PATH>
    ```
-   **Azure Blob Storage (Standard flat-namespace Blob containers)**:
    Use the `wasbs://` (TLS, preferred) or `wasb://` (non-TLS) scheme with the
    `.blob.core.windows.net` endpoint:
    ```
    wasbs://<CONTAINER>@<STORAGE_ACCOUNT>.blob.core.windows.net/<PATH>
    ```

## 3. Configuring Azure Storage Properties (Spark Connect & Batch Compatible)

> [!CAUTION]
> **NEVER** call `spark._jsc.hadoopConfiguration()` or
> `spark.sparkContext._jsc.hadoopConfiguration()` in **any** PySpark workload
> (including standalone `.py` Serverless batch and cluster scripts as well as
> Spark Connect and Remote Kernel notebooks). `_jsc` accesses private Py4J JVM
> internals that fail on Spark Connect (`ManagedSparkSession`) with
> `AttributeError` / `PySparkAttributeError: [JVM_ATTRIBUTE_NOT_SUPPORTED]`, and
> is unnecessary in batch and cluster jobs when `spark.hadoop.fs.azure.*`
> properties are set on `SparkSession.builder` before `.getOrCreate()`. Do NOT
> add `_jsc.hadoopConfiguration()` alongside `SparkSession.builder.config(...)`
> as a fallback.

Configure `fs.azure.*` properties according to the execution mode:

-   **Standalone `.py` batch and cluster jobs (`SparkSession.builder`)**:
    Pass all `fs.azure.*` properties via
    `.config("spark.hadoop.fs.azure.<property>", "<value>")` on
    `SparkSession.builder` **before** calling `.getOrCreate()`. On a classic JVM
    `SparkSession`, calling `spark.conf.set("fs.azure.*", ...)` after
    `.getOrCreate()` updates Spark SQL configuration rather than the initialized
    `SparkContext` Hadoop `Configuration`.
-   **Local Python / Spark Connect notebooks (`.ipynb`,
    `ManagedSparkSession`)**:
    Set `spark.conf.set("fs.azure.<property>", "<value>")` on the active Spark
    Connect session, or pass
    `.config("spark.hadoop.fs.azure.<property>", "<value>")` on
    `ManagedSparkSession.builder` before calling `.getOrCreate()`.
-   **Pre-initialized Remote Kernel notebooks (`.ipynb`, classic JVM)**:
    Because `spark` is already initialized and `SparkSession.builder` cannot be
    re-invoked, use `spark.conf.set("fs.azure.<property>", "<value>")` for
    DataFrame and Spark SQL reads/writes (which read per-session Hadoop settings
    via `SessionState.newHadoopConf()`) without calling `_jsc`.

## 4. Retrieving Azure Credentials from Google Cloud Secret Manager

Never hardcode Azure Storage Account keys, SAS tokens, or OAuth client secrets
in code or CLI flags. Retrieve them at runtime from Google Cloud Secret Manager
using the pre-installed `google.auth` + `urllib.request` REST API (zero extra
PyPI packages required). If the Secret Manager secret ID is not provided by the
user or fails with `404 Not Found` / `403 PermissionDenied`, you MUST **STOP and
ask the user** for the secret ID—do NOT guess secret names, scan unrelated
secrets, or create new secrets without user confirmation:

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

## 5. Complete PySpark Examples

### A. ADLS Gen2 (`abfss://`) with Shared Key Authentication

```python
import logging
import os
from pyspark.sql import SparkSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "<PROJECT_ID>")
storage_account = "<STORAGE_ACCOUNT>"
container = "<CONTAINER>"
azure_account_key = get_secret(project_id, "<AZURE_STORAGE_KEY_SECRET_ID>")

spark = (
    SparkSession.builder.appName("azure-adls-read-job")
    .config(
        f"spark.hadoop.fs.azure.account.auth.type.{storage_account}.dfs.core.windows.net",
        "SharedKey",
    )
    .config(
        f"spark.hadoop.fs.azure.account.key.{storage_account}.dfs.core.windows.net",
        azure_account_key,
    )
    .getOrCreate()
)

df = spark.read.parquet(
    f"abfss://{container}@{storage_account}.dfs.core.windows.net/<PATH_TO_DATA>"
)
df.printSchema()
logging.info("Row count: %d", df.count())
```

### B. Azure Blob Storage (`wasbs://`) with Account Key or SAS Token

-   **Standalone `.py` batch / cluster job (`SparkSession.builder`)**:

    -   **Using a Storage Account Key**:

        ```python
        spark = (
            SparkSession.builder.appName("azure-blob-read-job")
            .config(
                f"spark.hadoop.fs.azure.account.key.{storage_account}.blob.core.windows.net",
                azure_account_key,
            )
            .getOrCreate()
        )
        df = spark.read.parquet(
            f"wasbs://{container}@{storage_account}.blob.core.windows.net/<PATH_TO_DATA>"
        )
        ```

    -   **Using a Container SAS Token** (strip any leading `?` from the SAS
        token):

        ```python
        sas_token = get_secret(project_id, "<AZURE_SAS_TOKEN_SECRET_ID>").lstrip("?")
        spark = (
            SparkSession.builder.appName("azure-blob-sas-read-job")
            .config(
                f"spark.hadoop.fs.azure.sas.{container}.{storage_account}.blob.core.windows.net",
                sas_token,
            )
            .getOrCreate()
        )
        df = spark.read.parquet(
            f"wasbs://{container}@{storage_account}.blob.core.windows.net/<PATH_TO_DATA>"
        )
        ```

-   **Interactive notebook (`.ipynb` — Local Python / Spark Connect or Remote
    Kernel)**:

    -   **Using a Storage Account Key**:

        ```python
        spark.conf.set(
            f"fs.azure.account.key.{storage_account}.blob.core.windows.net",
            azure_account_key,
        )
        df = spark.read.parquet(
            f"wasbs://{container}@{storage_account}.blob.core.windows.net/<PATH_TO_DATA>"
        )
        ```

    -   **Using a Container SAS Token** (strip any leading `?` from the SAS
        token):

        ```python
        sas_token = get_secret(project_id, "<AZURE_SAS_TOKEN_SECRET_ID>").lstrip("?")
        spark.conf.set(
            f"fs.azure.sas.{container}.{storage_account}.blob.core.windows.net",
            sas_token,
        )
        df = spark.read.parquet(
            f"wasbs://{container}@{storage_account}.blob.core.windows.net/<PATH_TO_DATA>"
        )
        ```

### C. ADLS Gen2 (`abfss://`) with Service Principal (OAuth 2.0 Client Credentials)

-   **Standalone `.py` batch / cluster job (`SparkSession.builder`)**:

    ```python
    client_secret = get_secret(project_id, "<AZURE_CLIENT_SECRET_ID>")
    dfs_host = f"{storage_account}.dfs.core.windows.net"

    spark = (
        SparkSession.builder.appName("azure-adls-oauth-job")
        .config(f"spark.hadoop.fs.azure.account.auth.type.{dfs_host}", "OAuth")
        .config(
            f"spark.hadoop.fs.azure.account.oauth.provider.type.{dfs_host}",
            "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
        )
        .config(
            f"spark.hadoop.fs.azure.account.oauth2.client.id.{dfs_host}",
            "<CLIENT_ID>",
        )
        .config(
            f"spark.hadoop.fs.azure.account.oauth2.client.secret.{dfs_host}",
            client_secret,
        )
        .config(
            f"spark.hadoop.fs.azure.account.oauth2.client.endpoint.{dfs_host}",
            "https://login.microsoftonline.com/<TENANT_ID>/oauth2/token",
        )
        .getOrCreate()
    )
    ```

-   **Interactive notebook (`.ipynb` — Local Python / Spark Connect or Remote
    Kernel)**:

    ```python
    client_secret = get_secret(project_id, "<AZURE_CLIENT_SECRET_ID>")
    dfs_host = f"{storage_account}.dfs.core.windows.net"

    spark.conf.set(f"fs.azure.account.auth.type.{dfs_host}", "OAuth")
    spark.conf.set(
        f"fs.azure.account.oauth.provider.type.{dfs_host}",
        "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
    )
    spark.conf.set(f"fs.azure.account.oauth2.client.id.{dfs_host}", "<CLIENT_ID>")
    spark.conf.set(f"fs.azure.account.oauth2.client.secret.{dfs_host}", client_secret)
    spark.conf.set(
        f"fs.azure.account.oauth2.client.endpoint.{dfs_host}",
        "https://login.microsoftonline.com/<TENANT_ID>/oauth2/token",
    )
    ```

## 6. Networking & IAM Requirements

1.  **Secret Manager IAM & GCE Scopes**: Grant
    `roles/secretmanager.secretAccessor` to the Dataproc runtime service account
    so it can read the Azure credentials secrets (and pass
    `--scopes=cloud-platform` when creating a Dataproc on GCE cluster).
2.  **Outbound Internet Egress (Cloud NAT)**: Dataproc Serverless batches and
    sessions run on VPC subnets with Private Google Access (`enable_private_ip`
    is default). Because Azure Storage endpoints (`*.core.windows.net`) live
    outside Google Cloud, the VPC subnet **must** have **Cloud NAT** (or a
    custom egress route) configured so driver and executor VMs can reach Azure.
    Without Cloud NAT, connections time out with `ConnectTimeoutException`.
