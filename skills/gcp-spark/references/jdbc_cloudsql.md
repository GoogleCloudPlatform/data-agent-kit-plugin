# JDBC Databases, Cloud SQL & AlloyDB in PySpark

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow in `SKILL.md` when writing Spark code.

## 1. Attaching Custom JDBC Driver & Socket Factory JARs (`gs://...`)

JDBC drivers and Cloud SQL / AlloyDB Socket Factory JARs are not pre-installed on
Dataproc and must be attached at session creation (`gs://` JAR URIs cannot be
passed to `spark.jars.packages`, which only accepts Maven coordinates):

-   **When to attach 1 JAR vs. 2 JARs**:
    -   **Direct IP + Password**: Requires only the base **JDBC Driver JAR** (`gs://<BUCKET>/jars/<JDBC_DRIVER>.jar`).
    -   **Cloud SQL or AlloyDB Socket Factory (Instance Connection Name / IAM Auth)**: Requires **both** the base **JDBC Driver JAR** and the shaded **Socket Factory Uber JAR** passed as comma-separated `gs://` URIs (`gs://<BUCKET>/jars/<JDBC_DRIVER>.jar,gs://<BUCKET>/jars/<SOCKET_FACTORY>.jar`).
-   **Interactive Notebooks (`.ipynb`) & Spark Connect**: Attach the JAR(s) via a
    Session Template or `session_config.runtime_config.properties["spark.jars"]`
    at session creation (setting `spark.jars` after a Spark Connect session has
    started does not register the JDBC driver with the JVM):

    ```python
    from google.cloud.dataproc_v1 import Session
    from google.cloud.managed_spark_connect import ManagedSparkSession

    session_config = Session()
    # Direct IP + Password (1 JAR):
    # session_config.runtime_config.properties["spark.jars"] = "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar"
    # Cloud SQL / AlloyDB Socket Factory (2 JARs, comma-separated):
    session_config.runtime_config.properties["spark.jars"] = (
        "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar,gs://<BUCKET_NAME>/jars/<SOCKET_FACTORY>.jar"
    )
    spark = (
        ManagedSparkSession.builder.projectId("<PROJECT_ID>")
        .location("<REGION>")
        .dataprocSessionConfig(session_config)
        .getOrCreate()
    )
    ```

-   **Dataproc Batch & Cluster Jobs (`.py`)**: Pass
    `--jars=gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar` (or comma-separated
    `--jars=gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar,gs://<BUCKET_NAME>/jars/<SOCKET_FACTORY>.jar`)
    and `--subnet=<SUBNET>` (for VPC Private IP databases) on the `gcloud` CLI,
    and set `spark.jars` on `SparkSession.builder`:

    ```python
    import os
    from pyspark.sql import SparkSession

    # Direct IP + Password (1 JAR): "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar"
    # Cloud SQL / AlloyDB Socket Factory (2 JARs): "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar,gs://<BUCKET_NAME>/jars/<SOCKET_FACTORY>.jar"
    jar_uris = os.environ.get(
        "JAR_URIS", "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar"
    )
    spark = (
        SparkSession.builder.appName("<APP_NAME>")
        .config("spark.jars", jar_uris)
        .getOrCreate()
    )
    ```

### Common JDBC Driver Classes, Socket Factories & URL Formats

#### Cloud SQL for PostgreSQL
-   **Driver Class (`driver`)**: `org.postgresql.Driver`
-   **Direct IP JDBC URL (`url`)**: `jdbc:postgresql://<HOST>:5432/<DB>`
-   **Socket Factory Class**: `com.google.cloud.sql.postgres.SocketFactory`
-   **Socket Factory JDBC URL (`url`)**: `jdbc:postgresql:///<DB>?cloudSqlInstance=<PROJECT>:<REGION>:<INSTANCE>&socketFactory=com.google.cloud.sql.postgres.SocketFactory&enableIamAuth=true&sslmode=disable&ipTypes=PRIVATE`

#### Cloud SQL for MySQL
-   **Driver Class (`driver`)**: `com.mysql.cj.jdbc.Driver`
-   **Direct IP JDBC URL (`url`)**: `jdbc:mysql://<HOST>:3306/<DB>`
-   **Socket Factory Class**: `com.google.cloud.sql.mysql.SocketFactory`
-   **Socket Factory JDBC URL (`url`)**: `jdbc:mysql:///<DB>?cloudSqlInstance=<PROJECT>:<REGION>:<INSTANCE>&socketFactory=com.google.cloud.sql.mysql.SocketFactory&enableIamAuth=true&sslMode=DISABLED&ipTypes=PRIVATE`
-   **Dataproc on GCE Cluster Note**: Because Dataproc GCE images pre-install the MySQL driver in `/usr/lib/spark/jars/` (the parent system classloader), when using `com.google.cloud.sql.mysql.SocketFactory` on a GCE cluster, you MUST also pass `--properties="spark.driver.extraClassPath=<JDBC_DRIVER>.jar:<SOCKET_FACTORY>.jar,spark.executor.extraClassPath=<JDBC_DRIVER>.jar:<SOCKET_FACTORY>.jar"` (using the exact JAR filenames from `--jars` without the `gs://.../` path prefix) on `gcloud dataproc jobs submit pyspark` so the parent classloader can locate `com.google.cloud.sql.mysql.SocketFactory`.

#### AlloyDB for PostgreSQL
-   **Driver Class (`driver`)**: `org.postgresql.Driver`
-   **Direct IP JDBC URL (`url`)**: `jdbc:postgresql://<HOST>:5432/<DB>`
-   **Socket Factory Class**: `com.google.cloud.alloydb.SocketFactory`
-   **Socket Factory JDBC URL (`url`)**: `jdbc:postgresql:///<DB>?socketFactory=com.google.cloud.alloydb.SocketFactory&alloydbInstanceName=projects/<PROJECT>/locations/<REGION>/clusters/<CLUSTER>/instances/<INSTANCE>&alloydbEnableIAMAuth=true&alloydbIpType=PRIVATE`

#### Cloud SQL for SQL Server
-   **Driver Class (`driver`)**: `com.microsoft.sqlserver.jdbc.SQLServerDriver`
-   **Direct IP JDBC URL (`url`)**: `jdbc:sqlserver://<HOST>:1433;databaseName=<DB>;encrypt=true;trustServerCertificate=true`
-   **Socket Factory Class**: `com.google.cloud.sql.sqlserver.SocketFactory`
-   **Socket Factory JDBC URL (`url`)**: `jdbc:sqlserver://localhost;databaseName=<DB>;socketFactoryClass=com.google.cloud.sql.sqlserver.SocketFactory;socketFactoryConstructorArg=<PROJECT>:<REGION>:<INSTANCE>;encrypt=false;trustServerCertificate=true;`

## 2. Retrieving Database Passwords from Secret Manager

> [!WARNING] NEVER embed plaintext secrets or passwords directly in code or
> scripts, and do not rely on unset local environment variables in remote
> Dataproc jobs. When using password authentication, always retrieve database
> passwords from Google Cloud Secret Manager.

Fetch the secret via the pre-installed `google.auth` and `urllib.request`
libraries (falling back to `SecretManagerServiceClient` if
`google-cloud-secret-manager` is installed):

```python
import base64
import json
import urllib.request
import google.auth
from google.auth.transport.requests import Request


def get_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(Request())
        url = f"https://secretmanager.googleapis.com/v1/{name}:access"
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {creds.token}"}
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))["payload"]["data"]
            return base64.b64decode(data).decode("utf-8").strip()
    except Exception:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8").strip()
```

## 3. Parallel Partitioned JDBC Reads

Calling `spark.read.format("jdbc").load()` without partitioning options reads
the entire table on a single executor thread. For parallel JDBC reads on a
numeric, date, or timestamp column (`<PARTITION_COL>`):

1.  **Dynamically query `MIN` and `MAX` bounds first** (never hardcode or guess
    `lowerBound` / `upperBound`).
2.  **Read the table in parallel** using `partitionColumn`, `lowerBound`,
    `upperBound`, `numPartitions`, and `fetchsize`:

```python
import logging
import os
from pyspark.sql import SparkSession

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

project_id = os.environ.get("PROJECT_ID", "<PROJECT_ID>")
secret_id = os.environ.get("SECRET_ID", "<SECRET_ID>")
jar_uris = os.environ.get(
    "JAR_URIS", "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar"
)
jdbc_url = os.environ.get(
    "JDBC_URL", "jdbc:<ENGINE>://<HOST_OR_PRIVATE_IP>:<PORT>/<DATABASE>"
)
jdbc_driver = os.environ.get("JDBC_DRIVER", "<JDBC_DRIVER_CLASS>")
db_user = os.environ.get("DB_USER", "<USER>")
table_name = os.environ.get("TABLE_NAME", "<TABLE_NAME>")
partition_col = os.environ.get("PARTITION_COL", "<PARTITION_COL>")
db_password = get_secret(project_id, secret_id)

spark = (
    SparkSession.builder.appName("<APP_NAME>")
    .config("spark.jars", jar_uris)
    .getOrCreate()
)

# Step 1: Dynamically fetch MIN and MAX bounds for the partition column
bounds_query = (
    f"(SELECT MIN({partition_col}) AS min_id, MAX({partition_col}) AS max_id "
    f"FROM {table_name}) AS bounds_q"
)
bounds_row = (
    spark.read.format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", bounds_query)
    .option("user", db_user)
    .option("password", db_password)
    .option("driver", jdbc_driver)
    .load()
    .first()
)
lower_bound = str(bounds_row["min_id"])
upper_bound = str(bounds_row["max_id"])
logging.info("Resolved bounds: lower=%s, upper=%s", lower_bound, upper_bound)

# Step 2: Parallel partitioned read across executors
df = (
    spark.read.format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", table_name)
    .option("user", db_user)
    .option("password", db_password)
    .option("driver", jdbc_driver)
    .option("partitionColumn", partition_col)
    .option("lowerBound", lower_bound)
    .option("upperBound", upper_bound)
    .option("numPartitions", "4")
    .option("fetchsize", "10000")
    .load()
)
```

## 4. Cloud SQL & AlloyDB Socket Factory & IAM Authentication

When connecting via a Cloud SQL instance connection name
(`<PROJECT>:<REGION>:<INSTANCE>`) or AlloyDB instance URI
(`projects/<PROJECT>/locations/<REGION>/clusters/<CLUSTER>/instances/<INSTANCE>`),
use the **Socket Factory Uber JAR** alongside the base JDBC driver JAR.

### 4.1 Required IAM Roles, Database Flags, Networking & Conscrypt

-   **Cloud SQL IAM Roles & Flags**:
    -   `roles/cloudsql.client` (required for all Cloud SQL Socket Factory connections)
    -   `roles/cloudsql.instanceUser` (required for IAM database authentication)
    -   Instance flag: `cloudsql.iam_authentication=on` (PostgreSQL) or `cloudsql_iam_authentication=on` (MySQL)
-   **AlloyDB IAM Roles & Flags**:
    -   `roles/alloydb.client` (required for all AlloyDB Socket Factory connections)
    -   `roles/alloydb.databaseUser` (required for IAM database authentication)
    -   Instance flag: `alloydb.iam_authentication=on`
-   **Private IP Networking on Dataproc**: Dataproc Serverless VMs do not have
    public IPs. Always pass `--subnet=<SUBNET>` on the `gcloud` CLI and specify
    `ipTypes=PRIVATE` (Cloud SQL) or `alloydbIpType=PRIVATE` (AlloyDB) unless
    the subnet has Cloud NAT configured for public IP egress.

> [!CAUTION]
> **AlloyDB & SQL Server Socket Factory Conscrypt Requirement**: Dataproc's
> default Conscrypt OpenSSL provider conflicts with the Netty gRPC TLS handshake
> in `com.google.cloud.alloydb.SocketFactory` and the TDS login TLS handshake
> over `com.google.cloud.sql.sqlserver.SocketFactory`. You MUST set the following
> properties to disable Conscrypt when submitting AlloyDB or SQL Server Socket
> Factory workloads:
> -   **Dataproc Serverless Batch**: Pass `--properties="dataproc.artifacts.remove=conscrypt"`
> -   **Dataproc GCE Cluster Creation**: Pass `--properties="dataproc:dataproc.conscrypt.provider.enable=false"`
> -   **`ManagedSparkSession`**: Set `session_config.runtime_config.properties["dataproc.artifacts.remove"] = "conscrypt"`

### 4.2 IAM Database Authentication vs. Username/Password Authentication

With the Cloud SQL or AlloyDB Socket Factory, select the JDBC Driver Class and
Socket Factory JDBC URL format for your target engine from Section 1, and
authenticate using either **IAM Database Authentication** or
**Username/Password (via Secret Manager)**:

1.  **IAM Database Authentication (`enableIamAuth=true` / `alloydbEnableIAMAuth=true`)**:
    -   **Supported on**: Cloud SQL for PostgreSQL, Cloud SQL for MySQL, and AlloyDB for PostgreSQL (not supported on Cloud SQL for SQL Server).
    -   **Username format** (when not explicitly specified in the prompt, query the active Dataproc VM service account from the GCE metadata server via `get_iam_db_user`):
        -   **PostgreSQL & AlloyDB**: Strip the `.gserviceaccount.com` suffix (e.g., `<sa-name>@<project>.iam.gserviceaccount.com` becomes `<sa-name>@<project>.iam`, and `<project-number>-compute@developer.gserviceaccount.com` becomes `<project-number>-compute@developer`).
        -   **MySQL**: Take the prefix before `@` (e.g., `<sa-name>@<project>.iam.gserviceaccount.com` becomes `<sa-name>`, and `<project-number>-compute@developer.gserviceaccount.com` becomes `<project-number>-compute`).
    -   **Password option**: Pass `.option("password", "")` (an empty string); the Socket Factory automatically fetches and refreshes the OAuth2 IAM token.
2.  **Username/Password Authentication with Socket Factory (via Secret Manager)**:
    -   **When to use**: When the prompt specifies a built-in database user (e.g., `postgres`, `root`, `sqlserver`) and a Secret Manager secret alongside a Cloud SQL or AlloyDB Socket Factory JAR, or for Cloud SQL for SQL Server.
    -   **Configuration**: Omit `enableIamAuth=true` / `alloydbEnableIAMAuth=true` from the JDBC URL, set `.option("user", db_user)`, and pass `.option("password", get_secret(project_id, secret_id))`.

```python
import os
import urllib.request
from pyspark.sql import SparkSession


def get_iam_db_user(engine: str = "postgresql") -> str:
    req = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        sa_email = resp.read().decode("utf-8").strip()
    if engine.lower() == "mysql":
        return sa_email.split("@")[0]
    return sa_email.removesuffix(".gserviceaccount.com")


# Use the Socket Factory JDBC URL and Driver Class for your engine from Section 1
jar_uris = os.environ.get(
    "JAR_URIS",
    "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar,gs://<BUCKET_NAME>/jars/<SOCKET_FACTORY>.jar",
)
jdbc_url = os.environ.get("JDBC_URL", "<SOCKET_FACTORY_JDBC_URL_FROM_SECTION_1>")
jdbc_driver = os.environ.get("JDBC_DRIVER", "<JDBC_DRIVER_CLASS>")

# For IAM Auth (PostgreSQL, MySQL, AlloyDB): resolve IAM user and pass empty password ""
# For Password Auth (or SQL Server): set db_user and fetch db_password = get_secret(project_id, secret_id)
db_user = os.environ.get("DB_USER") or get_iam_db_user("<ENGINE>")
db_password = ""

spark = (
    SparkSession.builder.appName("<APP_NAME>")
    .config("spark.jars", jar_uris)
    .getOrCreate()
)

jdbc_opts = {
    "url": jdbc_url,
    "driver": jdbc_driver,
    "user": db_user,
    "password": db_password,
}
# Combine jdbc_opts with the two-step MIN/MAX bounds pre-query from Section 3 for parallel reads
```

### 4.3 Writing DataFrames to Cloud SQL & AlloyDB via JDBC

When writing DataFrames back to Cloud SQL or AlloyDB, set `batchsize` and use
`.option("truncate", "true")` with `.mode("overwrite")` so Spark truncates the
table in place instead of dropping and recreating it (which would lose indexes,
constraints, and IAM grants):

```python
(
    df.write.format("jdbc")
    .options(**jdbc_opts)
    .option("dbtable", "<TARGET_TABLE>")
    .option("batchsize", "5000")
    .option("isolationLevel", "READ_COMMITTED")
    .option("truncate", "true")
    .mode("overwrite")
    .save()
)
```
