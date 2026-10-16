# JDBC Databases & Cloud SQL in PySpark

> [!IMPORTANT]
> You MUST ALWAYS follow the Task Execution Workflow in `SKILL.md` when writing Spark code.

## 1. Attaching a Custom JDBC Driver JAR (`gs://...`)

JDBC drivers are not pre-installed on Dataproc and must be attached at session
creation (`gs://` JAR URIs cannot be passed to `spark.jars.packages`, which only
accepts Maven coordinates):

-   **Interactive Notebooks (`.ipynb`) & Spark Connect**: Attach the driver JAR
    via a Session Template or `session_config.runtime_config.properties["spark.jars"]`
    at session creation (setting `spark.jars` after a Spark Connect session has
    started does not register the JDBC driver with the JVM):

    ```python
    from google.cloud.dataproc_v1 import Session
    from google.cloud.managed_spark_connect import ManagedSparkSession

    session_config = Session()
    session_config.runtime_config.properties["spark.jars"] = (
        "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar"
    )
    spark = (
        ManagedSparkSession.builder.projectId("<PROJECT_ID>")
        .location("<REGION>")
        .dataprocSessionConfig(session_config)
        .getOrCreate()
    )
    ```

-   **Dataproc Batch & Cluster Jobs (`.py`)**: Pass
    `--jars=gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar` (and
    `--subnet=<SUBNET>` for private IP databases) on the `gcloud` CLI, and set
    `spark.jars` on `SparkSession.builder`:

    ```python
    jar_uri = os.environ.get(
        "JAR_URI", "gs://<BUCKET_NAME>/jars/<JDBC_DRIVER>.jar"
    )
    spark = (
        SparkSession.builder.appName("<APP_NAME>")
        .config("spark.jars", jar_uri)
        .getOrCreate()
    )
    ```

### Common JDBC Driver Classes & URL Formats

| Database Engine | Driver Class (`driver`) | JDBC URL Format (`url`) |
| :--- | :--- | :--- |
| **PostgreSQL / AlloyDB** | `org.postgresql.Driver` | `jdbc:postgresql://<HOST>:5432/<DATABASE>` |
| **MySQL** | `com.mysql.cj.jdbc.Driver` | `jdbc:mysql://<HOST>:3306/<DATABASE>` |
| **SQL Server** | `com.microsoft.sqlserver.jdbc.SQLServerDriver` | `jdbc:sqlserver://<HOST>:1433;databaseName=<DATABASE>;encrypt=true;trustServerCertificate=true` |

## 2. Retrieving Database Passwords from Secret Manager

> [!WARNING] NEVER embed plaintext secrets or passwords directly in code or
> scripts, and do not rely on unset local environment variables in remote
> Dataproc jobs. Always retrieve database passwords from Google Cloud Secret
> Manager.

On Dataproc Serverless, `google-cloud-secret-manager` is not pre-installed
by default. Either pass
`--properties="spark.dataproc.pip.packages=google-cloud-secret-manager==<VERSION>"`
at submission time and use `SecretManagerServiceClient`, or fetch the secret via
the pre-installed `google.auth` and `urllib.request` libraries:

```python
import base64
import json
import urllib.request
import google.auth
from google.auth.transport.requests import Request


def get_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    url = (
        f"https://secretmanager.googleapis.com/v1/projects/{project_id}"
        f"/secrets/{secret_id}/versions/{version}:access"
    )
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {creds.token}"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))["payload"]["data"]
        return base64.b64decode(data).decode("utf-8").strip()
```

If `google-cloud-secret-manager` is installed in the environment:

```python
from google.cloud import secretmanager


def get_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

project_id = os.environ.get("PROJECT_ID", "<PROJECT_ID>")
secret_id = os.environ.get("SECRET_ID", "<SECRET_ID>")
jdbc_url = os.environ.get(
    "JDBC_URL", "jdbc:<ENGINE>://<HOST_OR_PRIVATE_IP>:<PORT>/<DATABASE>"
)
jdbc_driver = os.environ.get("JDBC_DRIVER", "<JDBC_DRIVER_CLASS>")
db_user = os.environ.get("DB_USER", "<USER>")
table_name = os.environ.get("TABLE_NAME", "<TABLE_NAME>")
partition_col = os.environ.get("PARTITION_COL", "<PARTITION_COL>")
db_password = get_secret(project_id, secret_id)

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
