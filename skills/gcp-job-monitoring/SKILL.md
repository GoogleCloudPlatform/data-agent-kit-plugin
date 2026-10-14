---
name: gcp-job-monitoring
description: "Lists, monitors, ranks, aggregates, and inspects Google Cloud BigQuery jobs, slot reservations, hot tables, and Dataproc Spark workloads (Dataproc Serverless batches, interactive sessions, and Dataproc clusters/jobs) across cost, slot usage, duration, status, and execution stages. Use when the user asks to show their BigQuery or Spark jobs, find which jobs or tables cost the most money or billed the most bytes/slots, get a breakdown of spend or errors by user or reservation, inspect slot reservations and capacity commitments, list active Dataproc clusters or interactive sessions, identify slow or stuck queries, or get detailed execution breakdowns for a specific job ID."
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# BigQuery & Spark Job Monitoring Skill

This skill provides a fast, zero-dependency workflow for answering admin and
developer job-monitoring questions across **BigQuery** and **Dataproc Spark**
(both **Dataproc Serverless Batches** and **Dataproc Cluster Jobs**):

1. **"Show me my BigQuery jobs"** (recent jobs, filterable by user or state)
2. **"What jobs cost the most money?"** (ranked by bytes billed, estimated
   on-demand USD cost, and slot time)
3. **"What took long to run?"** (ranked by wall-clock elapsed time and slot
   contention)
4. **"What Spark jobs have I run?"** (unified view across Dataproc Serverless
   batches and Dataproc cluster jobs)
5. **"Give me details about a specific job"** (full SQL text, execution stages,
   bytes/slots/DCUs, referenced tables, errors, and console/log links)

--------------------------------------------------------------------------------

## Critical Rules & Real-World Gotchas (MUST FOLLOW)

1. **Use `scripts/gcp_job_monitor.py` FIRST for BigQuery and Spark job
   queries:**
   - Do **NOT** start by running `SELECT ... FROM INFORMATION_SCHEMA.JOBS_BY_PROJECT`
     or `JOBS_BY_USER` when shell execution is available.
   - **Why:** In many enterprise GCP projects, users with `roles/bigquery.jobUser`
     get `403 Access Denied` on both `INFORMATION_SCHEMA.JOBS_BY_PROJECT`
     (`bigquery.jobs.listAll`) and `INFORMATION_SCHEMA.JOBS_BY_USER`, whereas
     the BigQuery `jobs.list` (`projection=full`) and `jobs.get` REST API used
     by `scripts/gcp_job_monitor.py` **succeeds across all regions in a single
     call** and **costs $0** (no query job is billed).
   - `scripts/gcp_job_monitor.py` automatically tries `allUsers=true` (project
     admin view) and falls back to `allUsers=false` (current user's jobs) if the
     caller lacks `bigquery.jobs.listAll`.
2. **Dual-Transport Auth (Cloudtop/Remote VMs + GE Sobi VMaaS `remote_cli mcp`):**
   - **Cloudtop & Remote VMs (Context-Aware Access)**: Bare `bq ls -j` or
     `gcloud auth print-access-token` often fails with `Access was blocked by
     Context Aware Access`. `scripts/gcp_job_monitor.py` automatically
     authenticates via Application Default Credentials (`gcloud auth
     application-default print-access-token --quiet`) first and falls back to
     user credentials (`--quiet`), never hanging on interactive `(y/N)?`
     prompts.
   - **Gemini Enterprise (GE) Sobi VMaaS / ACE Sandboxes (`/usr/local/bin/remote_cli`)**:
     In the Sobi VMaaS sandbox, local `gcloud` has no token and all
     authenticated egress goes through `remote_cli mcp` (`bigquery`,
     `google-managed-apache-spark`, and `google-cloud-cli`).
     `scripts/gcp_job_monitor.py` automatically detects when `gcloud` has no
     token and `remote_cli` is on `PATH` (or you can pass
     `--transport=remote_cli`) and routes every action through
     `RemoteCliMcpClient` (`remote_cli mcp bigquery` and `remote_cli mcp
     google-managed-apache-spark`).
   - If authentication is missing or expired on a local VM, run `gcloud auth
     application-default login` or configure Google Application Default Credentials.
3. **Always Check Both Dataproc Serverless Batches AND Cluster Jobs for Spark:**
   - Users asking *"What Spark jobs have I run?"* rarely distinguish between
     **Dataproc Serverless Batches** (`projects.locations.batches`) and
     **Dataproc Cluster Jobs** (`projects.regions.jobs`).
   - `scripts/gcp_job_monitor.py` queries **both** APIs in one call and merges
     them into a unified table with workload type (`SERVERLESS_BATCH` vs.
     `CLUSTER_JOB`), engine (`PYSPARK`, `SPARK`, `SPARK_SQL`), duration, and DCU
     usage.
4. **Deep-Dive Troubleshooting Handoff:**
   - When `spark_describe` or `spark_list` reveals a `FAILED` Spark batch or
     cluster job and the user wants root-cause analysis (driver logs, GCS event
     logs, JVM bytecode, or stage skew/spill diagnostics), hand off to
     `@skill:gcp-spark-troubleshooting`.

--------------------------------------------------------------------------------

## Workflow 1: BigQuery Job Monitoring (`scripts/gcp_job_monitor.py`)

Run `scripts/gcp_job_monitor.py` using `python3`. It requires **only the Python
standard library** (do not `pip install` anything). If `--project` (or
`--project_id`) is omitted, it auto-detects the active project from `gcloud
config get-value project`.

### 1. List Recent BigQuery Jobs ("Show me my BQ jobs")

```bash
# List recent jobs in the active project (auto-falls back to caller's jobs if not admin)
python3 scripts/gcp_job_monitor.py \
  --action=bq_list \
  --project="<PROJECT_ID>" \
  --limit=20

# Filter strictly to the authenticated user's own jobs
python3 scripts/gcp_job_monitor.py \
  --action=bq_list \
  --project="<PROJECT_ID>" \
  --mine \
  --limit=20

# Filter to failed jobs only (or --state=DONE, --state=RUNNING)
python3 scripts/gcp_job_monitor.py \
  --action=bq_list \
  --project="<PROJECT_ID>" \
  --state=FAILED \
  --limit=20
```

### 2. Find Most Expensive BigQuery Jobs ("What jobs cost the most money?")

Ranks jobs by **bytes billed** (and **total slot ms** as tie-breaker), reporting
both on-demand estimated cost (`$6.25 / TiB`) and total slot consumption for
capacity/edition workloads:

```bash
python3 scripts/gcp_job_monitor.py \
  --action=bq_top_cost \
  --project="<PROJECT_ID>" \
  --limit=10 \
  --days=30
```

### 3. Find Slowest / Longest-Running BigQuery Jobs ("What took long to run?")

Ranks jobs by **wall-clock duration** (`endTime - startTime`) alongside slot
time so you can distinguish long wait/skew from heavy parallel compute:

```bash
python3 scripts/gcp_job_monitor.py \
  --action=bq_slowest \
  --project="<PROJECT_ID>" \
  --limit=10 \
  --days=30
```

### 4. Inspect a Specific BigQuery Job ("Give me details about job `<job_id>`")

Accepts `job_id`, `project:location.job_id`, or `location.job_id` and returns
full metadata, cost/slot metrics, referenced tables, error message (if failed),
full SQL text, and a per-stage `queryPlan` table (records read/written, slot
ms, max wait/compute, shuffle spill):

```bash
python3 scripts/gcp_job_monitor.py \
  --action=bq_describe \
  --project="<PROJECT_ID>" \
  --job_id="<JOB_ID>"
```

### 5. Project-Wide Cost Attribution, Edition/Reservation Usage & Error Triage ("Break down spend by user / reservation" or "Why are queries failing?")

Aggregates recent jobs into 3 admin tables: (1) **Cost & Slot Attribution by
User**, (2) **Usage by Edition & Slot Reservation** (`ON_DEMAND` vs.
`ENTERPRISE`), and (3) **Top Error Reasons** grouped by failure count:

```bash
python3 scripts/gcp_job_monitor.py \
  --action=bq_summary \
  --project="<PROJECT_ID>" \
  --days=30 \
  --limit=10
```

### 6. Most Queried / Highest-Cost Tables ("Which tables are costing the most money?")

Unnests `referencedTables` across recent queries and ranks tables by total bytes
billed, estimated on-demand cost, total slot time, query count, and distinct
users:

```bash
python3 scripts/gcp_job_monitor.py \
  --action=bq_hot_tables \
  --project="<PROJECT_ID>" \
  --days=30 \
  --limit=10
```

### 7. Inspect BigQuery Slot Reservations & Capacity Commitments ("What slot reservations do we have?")

Queries the BigQuery Reservation API (`bigqueryreservation.googleapis.com`) to
list configured slot reservations (edition, baseline slots, current/max
autoscale slots), capacity commitments, and active project assignments:

```bash
python3 scripts/gcp_job_monitor.py \
  --action=bq_reservations \
  --project="<PROJECT_ID>" \
  --location=US
```

--------------------------------------------------------------------------------

## Workflow 2: Spark Workload Monitoring (`scripts/gcp_job_monitor.py`)

Spark workloads are regional (`--region`, defaulting to `us-central1`). You can
pass a single region (`--region=us-central1`) or comma-separated regions in a
single call (`--region=us-central1,us-east1,us-west1,europe-west1`) to scan
multiple regions with one authentication token.

### 1. List Recent Spark Workloads ("What Spark jobs have I run?")

Queries both **Dataproc Serverless Batches** and **Dataproc Cluster Jobs**:

```bash
# All recent Spark workloads in the region (or comma-separated regions)
python3 scripts/gcp_job_monitor.py \
  --action=spark_list \
  --project="<PROJECT_ID>" \
  --region=us-central1 \
  --limit=20

# Only Spark workloads submitted by the current authenticated user across common regions
python3 scripts/gcp_job_monitor.py \
  --action=spark_list \
  --project="<PROJECT_ID>" \
  --region=us-central1,us-east1,us-west1,europe-west1 \
  --mine \
  --limit=20
```

### 2. Find Slowest / Most Resource-Intensive Spark Workloads

Ranks Spark batches and cluster jobs by wall-clock duration and reports
approximate Serverless DCU-hours (`milliDcuSeconds`) and shuffle storage
(`shuffleStorageGbSeconds`):

```bash
python3 scripts/gcp_job_monitor.py \
  --action=spark_slowest \
  --region=us-central1 \
  --limit=10
```

### 3. Inspect a Specific Spark Batch or Cluster Job

Automatically checks Dataproc Serverless Batches first and falls back to
Dataproc Cluster Jobs (or you can force `--workload_type=batch|cluster_job`):

```bash
python3 scripts/gcp_job_monitor.py \
  --action=spark_describe \
  --region=us-central1 \
  --job_id="<BATCH_OR_JOB_ID>"
```

If the workload failed and the user wants a root-cause analysis of driver logs,
GCS event logs, or stage skew, load `@skill:gcp-spark-troubleshooting`.

### 4. Inspect Active Dataproc Clusters & Interactive Spark Sessions ("Are any clusters or Spark sessions running?")

Lists active/idle Dataproc clusters (master/worker machine types, worker count,
state) and Dataproc Serverless interactive sessions across one or more regions:

```bash
python3 scripts/gcp_job_monitor.py \
  --action=spark_clusters \
  --project="<PROJECT_ID>" \
  --region=us-central1,us-east1,us-west1,europe-west1
```

--------------------------------------------------------------------------------

## Workflow 3: Active / Stuck Queue Monitoring & Cancelling Runaway Jobs

1. **Find Currently Running or Pending Jobs:**
   ```bash
   # BigQuery active/pending queue (computes live elapsed time since startTime)
   python3 scripts/gcp_job_monitor.py --action=bq_list --project="<PROJECT_ID>" --state=RUNNING
   python3 scripts/gcp_job_monitor.py --action=bq_list --project="<PROJECT_ID>" --state=PENDING

   # Spark active/pending batches and cluster jobs
   python3 scripts/gcp_job_monitor.py --action=spark_list --project="<PROJECT_ID>" --region=us-central1 --state=RUNNING
   ```
2. **Cancel a Runaway Job (Requires Explicit User Confirmation First):**
   - **BigQuery Job**: `bq cancel --location=<LOCATION> <JOB_ID>` (or via SQL: `CALL BQ.JOBS.CANCEL('<LOCATION>.<JOB_ID>');`)
   - **Dataproc Serverless Batch**: `gcloud dataproc batches cancel <BATCH_ID> --project=<PROJECT_ID> --region=<REGION> --quiet`
   - **Dataproc Cluster Job**: `gcloud dataproc jobs kill <JOB_ID> --project=<PROJECT_ID> --region=<REGION> --quiet`

--------------------------------------------------------------------------------

## Workflow 4: Dynamic / Ad-Hoc Admin Queries (Any Unscripted Question)

The preset `--action` commands above cover the most common admin views, but
admins will frequently ask **arbitrary, unscripted questions** (e.g., *"Which
queries spilled to disk?"*, *"What is our query cache hit rate by user?"*,
*"Show me all `DELETE` or `MERGE` DML jobs that modified table X"*, *"What time
of day has the highest slot spike?"*, *"Which jobs have label `env=prod`?"*, or
*"Are any datasets using physical storage billing?"*).

Whenever a question requires custom filtering, custom grouping, or inspecting a
resource not covered by a preset table, **do not stop at the preset CLI flags**—
use one of these three dynamic patterns:

### 1. Pipe `--format=json` into a Python Filter / Aggregation One-Liner
Every action in `scripts/gcp_job_monitor.py` supports `--format=json`, emitting
rich normalized objects (`bytesBilled`, `bytesProcessed`, `slotMs`, `cacheHit`,
`spilledBytes`, `maxWaitMs`, `biEngineMode`, `priority`, `labels`,
`statementType`, `destinationTable`, `numDmlAffectedRows`, `referencedTables`,
`stages`, `reservationId`, `edition`, `errorReason`, `errorMessage`, etc.):

```bash
python3 scripts/gcp_job_monitor.py --action=bq_list --project="<PROJECT_ID>" --limit=200 --format=json | \
  python3 -c '
import json, sys
data = json.load(sys.stdin)
jobs = data.get("jobs", [])
# Example: dynamically filter or group by any arbitrary condition
spilled = [j for j in jobs if j.get("spilledBytes", 0) > 0 or j.get("maxWaitMs", 0) > 5000]
print(json.dumps(spilled, indent=2))
'
```

### 2. Import `gcp_job_monitor.RestClient` to Call Any GCP REST Endpoint
Because `gcp_job_monitor.RestClient` handles Context-Aware Access (CAA) token
fallback (`application-default` -> `user` credentials) automatically, you can
import it in a short `python3 -c` snippet to query **any** BigQuery or Dataproc
REST API endpoint (such as `datasets.list`, `tables.get`, `routines.list`,
`workflowTemplates.list`, or `autoscalingPolicies.list`) without writing auth
boilerplate:

```bash
PYTHONPATH="$(dirname scripts/gcp_job_monitor.py)" python3 -c '
import gcp_job_monitor as m, json
client = m.RestClient()
# Call any BigQuery or Dataproc REST endpoint with CAA-safe auth:
resp = client.get_json(f"{m.BQ_ENDPOINT}/bigquery/v2/projects/<PROJECT_ID>/datasets")
print(json.dumps(resp, indent=2))
'
```

### 3. Custom SQL on `INFORMATION_SCHEMA` (`references/information_schema_queries.md`)
When the user has `INFORMATION_SCHEMA` access (or when only the BigQuery MCP
tool `bigquery__execute_sql` is available) and needs 180-day historical
analysis, per-second slot timelines (`JOBS_TIMELINE_BY_PROJECT`), or storage
economics (`TABLE_STORAGE`), read `references/information_schema_queries.md` and
compose custom SQL against those views.
