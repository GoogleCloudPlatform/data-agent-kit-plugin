# Root Cause Analysis (RCA) Report Template

Use the following markdown structure when generating the final RCA artifact for
the user.

--------------------------------------------------------------------------------

## Template Structure

### Root Cause Analysis (RCA): [Job/Batch ID] Failure

-   **Workload Type**: `[Dataproc Serverless Batch | Dataproc Cluster Job]`
-   **Target ID**: `[BATCH_ID or JOB_ID]`
-   **Region**: `[REGION]`
-   **Execution Timestamp**: `[START_TIME]` to `[END_TIME]`
-   **Status**: `FAILED`

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

-   **Violated Diagnostic Rules**:
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

### 4. Remediation Plan

#### Immediate Fix

Code modification or Spark property tuning to resolve the failure:

```python
# Fixed code snippet or modified submission command
```

#### Spark Tuning Recommendations

-   `--properties spark.driver.memory=...`
-   `--properties spark.executor.memory=...`
-   `--properties spark.sql.shuffle.partitions=...`
-   `--properties spark.sql.adaptive.enabled=true`
