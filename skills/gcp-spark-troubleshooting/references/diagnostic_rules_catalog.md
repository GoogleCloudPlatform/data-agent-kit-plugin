# Spark Stage Diagnostic Rules: Authoring Guide

`scripts/spark_stage_diagnostics.py` ships **no rules or thresholds**. You write
the rules; the script evaluates them against the application's stage telemetry
and reports which stages matched.

This is deliberate. What counts as "too much" GC, skew, or spill depends on the
workload. A ratio that is healthy for a long-running nightly ETL job is
pathological for an interactive query. A partition size that is fine on a
32-core executor is too large on a 4-core one. Built-in numbers would produce
confident-looking findings that are wrong for most jobs.

Rules are **Python expressions** over the application's stage telemetry.

Everything below is an **illustrative starting point**. Read the stage telemetry
first, then choose thresholds that fit the job in front of you.

--------------------------------------------------------------------------------

## 1. Rule format

A rule is a JSON object. Pass a list of rules with `--rules_file <path>` or
`--custom_rule '<json>'`. `--custom_rule` accepts inline JSON or a file path.

```json
{
  "ruleId": "GC_PRESSURE",
  "description": "GC exceeds 15% of executor run time",
  "remediation": "Raise spark.executor.memory, or cache/persist less data.",
  "expression": "s['stage_metrics.executor_run_time_millis'] > 60000 and ratio(s['stage_metrics.jvm_gc_time_millis'], s['stage_metrics.executor_run_time_millis']) > 0.15",
  "detail": "f'{s[\"stage_metrics.jvm_gc_time_millis\"]} ms GC of {s[\"stage_metrics.executor_run_time_millis\"]} ms run time'"
}
```

- `ruleId` (required): a short identifier, echoed into the report.
- `expression` (required): a Python expression over the variables in section
  2. Section 3 explains how its result is read.
- `description` (optional): a one-line explanation, shown in the report heading.
- `remediation` (optional): what to do about the finding.
- `detail` (optional): a second expression, rendered as the text of each
  finding, with the violating stage bound to `s`. Use it to quote the
  **measured values**: a bare "rule matched" is not actionable. It has the same
  variables and functions as `expression` and should yield a string; an
  f-string is the easiest way, for example
  `f'{gb(s["stage_metrics.disk_bytes_spilled"])} GiB spilled'`. A detail that
  fails to compile or evaluate is reported as a warning and the finding falls
  back to "Rule expression matched.".

**Quoting.** In JSON, write field keys with single quotes in expressions
(`s['num_tasks']`). Inside an f-string delimited by `'`, use escaped double
quotes (`\"`) for the keys, as in the `detail` above.

--------------------------------------------------------------------------------

## 2. Data model

Three variables are in scope. Each record is a **flat Python `dict`** keyed by
the Dataproc v1 proto field path, in `snake_case`, with `.` between nested
messages: `s["stage_metrics.jvm_gc_time_millis"]`,
`s["task_quantile_metrics.duration_millis.percentile_50"]`. Telemetry sent in
camelCase is converted, so the keys are the same either way.

1.  **`s`**: one stage (a flattened `StageData`). Reading `s` makes the rule a
    per-stage rule (section 3).
    -   `stage_id`, `stage_attempt_id`, `name`, `description`, `details`,
        `failure_reason`, `scheduling_pool`
    -   `num_tasks`, `num_active_tasks`, `num_complete_tasks`,
        `num_failed_tasks`, `num_killed_tasks`, `num_completed_indices`
    -   `status`: the enum value name, a string such as
        `'STAGE_STATUS_FAILED'` (`ACTIVE`, `COMPLETE`, `FAILED`, `PENDING`,
        `SKIPPED`; `STAGE_STATUS_UNSPECIFIED` when absent)
    -   `submission_time`, `first_task_launched_time`, `completion_time`:
        timezone-aware `datetime`s, or `None` when unset. Every field whose
        name ends in `_time` is parsed this way.
    -   `parent_stage_ids`, `job_ids`, `rdd_ids` (lists of ints)
    -   Map fields stay dicts, because their keys are data: `locality` and
        `killed_tasks_summary` (dicts of ints), `executor_summary` (executor
        ID to a dict of `ExecutorStageSummary` fields)
    -   `stage_metrics.*`:
        -   `executor_run_time_millis`, `executor_cpu_time_nanos`,
            `jvm_gc_time_millis`, `executor_deserialize_time_millis`,
            `result_serialization_time_millis`, `result_size`
        -   `memory_bytes_spilled`, `disk_bytes_spilled`,
            `peak_execution_memory_bytes`
        -   `stage_input_metrics.{bytes_read, records_read}`
        -   `stage_output_metrics.{bytes_written, records_written}`
        -   `stage_shuffle_read_metrics.{bytes_read, records_read,
            fetch_wait_time_millis, remote_bytes_read, local_bytes_read, ...}`
        -   `stage_shuffle_write_metrics.{bytes_written, records_written,
            write_time_nanos}`
    -   `task_quantile_metrics.*`: per-task distributions. Each ends in
        `.minimum`, `.percentile_25`, `.percentile_50`, `.percentile_75`,
        `.maximum`, `.sum` or `.count`:
        -   `duration_millis`, `executor_run_time_millis`,
            `jvm_gc_time_millis`, `scheduler_delay_millis`,
            `peak_execution_memory_bytes`, `memory_bytes_spilled`,
            `disk_bytes_spilled`
        -   `input_metrics.bytes_read`, `output_metrics.bytes_written`
        -   `shuffle_read_metrics.read_bytes`,
            `shuffle_write_metrics.write_bytes`,
            `shuffle_write_metrics.write_time_nanos`
    -   `speculation_summary.*`, `executor_metrics_distributions.*`,
        `peak_executor_metrics.*`, `accumulator_updates` (a list)
2.  **`stages`**: every stage attempt of the application, as a list of stage
    dicts.
3.  **`total_executor_summary`** (a flattened `ConsolidatedExecutorSummary`):
    application totals.
    -   `active_tasks`, `completed_tasks`, `failed_tasks`, `total_tasks`,
        `total_cores`, `count`
    -   `total_duration_millis`, `total_gc_time_millis`, `total_input_bytes`,
        `total_shuffle_read`, `total_shuffle_write`
    -   `memory_used`, `max_memory`, `disk_used`, `memory_metrics.*`

Rules about the data:

-   **Absent fields read as proto3 defaults.** The REST API omits zero values,
    so reading a missing key never raises: a number reads as `0`, the string
    fields above as `''`, the list fields as `[]`, the map fields as `{}` and
    the timestamps as `None`. Stage 0 carries no `stage_id`, and reads as `0`.
    You therefore never need `None` checks on numbers.
-   **Testing for presence.** A message has no key of its own, only its leaf
    fields. `0 < s["task_quantile_metrics.duration_millis.percentile_50"]`
    skips stages that ran no tasks; `any(k.startswith("task_quantile_metrics.")
    for k in s)` tests whether the message was sent at all.
-   **Misspelled fields are reported, not fatal.** A key that no stage has
    reads as `0`. If its last segment is not a Dataproc field name either
    (`s["stage_metrics.jvm_gc_ms"]`), the report warns that the rule read
    fields no stage has, naming the closest real keys, and the rule still
    runs. Check such a warning before trusting an empty result. A real field
    under the wrong message (`s["stage_metrics.num_tasks"]`) is not caught, so
    copy paths from this section.

--------------------------------------------------------------------------------

## 3. Language and result semantics

A rule is a single Python expression (no statements), evaluated with
ordinary Python semantics. All Python builtins are available, plus these
helpers:

-   `ratio(a, b)`: `a / b`, or `0.0` when `b` is zero. Stage telemetry is full
    of zero denominators, so prefer it to `/`.
-   `mb(n)`, `gb(n)`: bytes to MiB or GiB, rounded to two decimals.
-   `seconds_between(start, end)`: seconds between two timestamps, or `0.0` if
    either is unset.

The expression is not sandboxed: rules are written by the agent for the job
in front of it, and run with the same access as the script. Before it runs,
every free name must be a variable from section 2, a helper or a builtin, so a
misspelled variable is reported up front.

-   **Numbers** are ordinary Python numbers: `int` and `float` mix freely and
    `/` always yields a float. Division by zero raises `ZeroDivisionError`,
    for floats too; guard with `b > 0 and a / b > T`, or use
    `ratio(a, b)`.
-   **Time**: subtracting timestamps yields a `timedelta`, for example
    `(s["completion_time"] - s["submission_time"]).total_seconds() > 300`.
    Guard it with `s["completion_time"] and s["submission_time"] and ...`, or
    use `seconds_between(s["submission_time"], s["completion_time"]) > 300`.
-   **Strings**: `'OutOfMemory' in s["failure_reason"]`,
    `s["name"].startswith("collect")`.

How a rule's result is read:

-   **The rule reads `s`** (a per-stage rule): it is evaluated once per stage,
    with `s` bound to it, and flags every stage for which it is truthy. It may
    also read `stages` and `total_executor_summary`, for example to compare a
    stage against the application:
    `s["num_tasks"] == max(x["num_tasks"] for x in stages)`.
-   **The rule does not read `s`**: it is evaluated once.
    -   **A non-empty list** (or tuple, set or generator): a violation. Its
        stage elements are the violating stages, and `int` elements are read
        as stage IDs, so both `[x for x in stages if ...]` and
        `[x["stage_id"] for x in stages if ...]` work.
    -   **`True`**: an application-level violation, with no stage IDs.
    -   **`False` or an empty list**: no violation.
    -   **Anything else** (a number, a string, ...): no violation. The script
        also prints a warning.
-   **Compile error** (syntax error or unknown name): the rule is skipped with
    a warning.
-   **Evaluation error** (division by zero, an index out of range, ...) on any
    stage: the whole rule is skipped with a warning, never partially applied.

`and` and `or` short-circuit, so `b > 0 and a / b > T` never divides by zero.
Warnings go to stderr, and into the `warnings` field of `--format=json`. A
skipped rule is never reported as a clean result.

--------------------------------------------------------------------------------

## 4. Signals worth writing rules about

These are the standard Spark performance signals, with the fields that expose
them.

- **Task failures**: `s["num_failed_tasks"]` and `s["num_tasks"]`. Causes include unhandled exceptions, bad records, OOM kills and node loss.
- **Killed tasks**: `s["num_killed_tasks"]`. Causes include preemption or spot VM eviction, speculative execution and executor loss.
- **GC pressure**: `s["stage_metrics.jvm_gc_time_millis"]` compared with `executor_run_time_millis`. The heap is too small, or too much data is cached or retained.
- **Memory spill**: `s["stage_metrics.memory_bytes_spilled"]`. Execution memory ran out.
- **Disk spill**: `s["stage_metrics.disk_bytes_spilled"]`. More severe; usually a shuffle or join that does not fit in memory.
- **Shuffle write cost**: `s["stage_metrics.stage_shuffle_write_metrics.write_time_nanos"]` compared with run time (convert nanoseconds with `/ 1e6`).
- **Duration skew**: `s["task_quantile_metrics.duration_millis.maximum"]` compared with `...percentile_50`. Stragglers, caused by data skew or an unevenly loaded node.
- **Input skew**: `s["task_quantile_metrics.input_metrics.bytes_read.maximum"]` compared with `...percentile_50`. Uneven input splits.
- **Output or shuffle skew**: `output_metrics.bytes_written` and `shuffle_write_metrics.write_bytes` quantiles. Hot aggregation or join keys.
- **Oversized partitions**: the `maximum` of any byte quantile above. Raises the risk of spill and GC.
- **Data explosion**: output bytes compared with input bytes. Often an accidental cross join.
- **Tiny-task storm**: a large `s["num_tasks"]` with a small median duration or input. Scheduling overhead dominates the real work.

**Guard ratios with a magnitude.** A ratio says nothing on its own: a stage
that ran for 16 ms with 9 ms of GC has a 56% GC ratio but costs nothing. Add a
floor on the absolute value, for example
`s["stage_metrics.executor_run_time_millis"] > 60000 and ratio(...) > 0.15`, or
`s["task_quantile_metrics.duration_millis.maximum"] > 60000` for skew, so that
findings point at stages worth tuning.

--------------------------------------------------------------------------------

## 5. Example rules

These rules cover common Spark issues. Copy one and adjust its thresholds to
the job; they are not defaults.

```json
[
  {"ruleId": "DATA_SKEW_DURATION_VARIANCE", "description": "Max task duration exceeds 4x median, and 60 s",
   "expression": "s['task_quantile_metrics.duration_millis.maximum'] > 60000 and ratio(s['task_quantile_metrics.duration_millis.maximum'], s['task_quantile_metrics.duration_millis.percentile_50']) > 4"},
  {"ruleId": "EXECUTOR_MEMORY_PRESSURE_SPILL", "description": "Stage spilled to memory or disk",
   "expression": "s['stage_metrics.memory_bytes_spilled'] > 0 or s['stage_metrics.disk_bytes_spilled'] > 0"},
  {"ruleId": "HIGH_GC_OVERHEAD", "description": "GC exceeds 15% of executor run time",
   "expression": "ratio(s['stage_metrics.jvm_gc_time_millis'], s['stage_metrics.executor_run_time_millis']) > 0.15",
   "detail": "f'{ratio(s[\"stage_metrics.jvm_gc_time_millis\"], s[\"stage_metrics.executor_run_time_millis\"]):.0%} of run time in GC'"},
  {"ruleId": "EXECUTOR_OOM_LOST_EXECUTORS", "description": "Killed tasks (preemption, heartbeat timeout, OOM)",
   "expression": "s['num_killed_tasks'] > 0"},
  {"ruleId": "SHUFFLE_IMBALANCE_FETCH_HEAVY", "description": "Max task shuffle write exceeds 4x median",
   "expression": "s['stage_metrics.stage_shuffle_read_metrics.bytes_read'] > 0 and ratio(s['task_quantile_metrics.shuffle_write_metrics.write_bytes.maximum'], s['task_quantile_metrics.shuffle_write_metrics.write_bytes.percentile_50']) > 4"},
  {"ruleId": "STRAGGLER_TASKS_LONG_TAIL", "description": "Max task duration exceeds 5x median, with more than 10 tasks",
   "expression": "s['num_tasks'] > 10 and ratio(s['task_quantile_metrics.duration_millis.maximum'], s['task_quantile_metrics.duration_millis.percentile_50']) > 5"},
  {"ruleId": "DYNAMIC_ALLOCATION_THRASHING", "description": "Over 20 killed tasks (executor churn)",
   "expression": "s['num_killed_tasks'] > 20"},
  {"ruleId": "EXCESSIVE_DISK_SPILL", "description": "Over 1 GiB spilled to disk",
   "expression": "gb(s['stage_metrics.disk_bytes_spilled']) > 1",
   "detail": "f'{gb(s[\"stage_metrics.disk_bytes_spilled\"])} GiB spilled to disk'"},
  {"ruleId": "UNDERPARTITIONED_SPILL", "description": "Disk spill with under 50 tasks",
   "expression": "s['stage_metrics.disk_bytes_spilled'] > 0 and s['num_tasks'] < 50"},
  {"ruleId": "TOO_MANY_SMALL_TASKS", "description": "Over 10,000 tasks with median duration under 100 ms",
   "expression": "s['num_tasks'] > 10000 and 0 < s['task_quantile_metrics.duration_millis.percentile_50'] < 100"},
  {"ruleId": "DRIVER_BOTTLENECK_FAILURE", "description": "Stage has failed tasks",
   "expression": "s['num_failed_tasks'] > 0",
   "detail": "f'{s[\"num_failed_tasks\"]} of {s[\"num_tasks\"]} tasks failed'"},
  {"ruleId": "SERIALIZATION_SHUFFLE_WRITE_BOTTLENECK", "description": "Shuffle write exceeds 10% of task run time",
   "expression": "ratio(s['stage_metrics.stage_shuffle_write_metrics.write_time_nanos'] / 1e6, s['stage_metrics.executor_run_time_millis']) > 0.1"},
  {"ruleId": "HIGH_SCAN_TASK_COUNT_STARVATION", "description": "Scan with over 80,000 tasks",
   "expression": "s['stage_metrics.stage_shuffle_read_metrics.bytes_read'] == 0 and s['stage_metrics.stage_input_metrics.bytes_read'] > 0 and s['num_tasks'] > 80000"}
]
```

**Cheapest-signal-first triage.** Evaluate one composite rule first, to decide
whether deeper stage or log inspection is warranted:

```json
{"ruleId": "COMPOSITE_TRIAGE_ENTRY_POINT", "description": "Any failure, kill, spill, or GC over 15%",
 "expression": "s['num_failed_tasks'] > 0 or s['num_killed_tasks'] > 0 or s['stage_metrics.disk_bytes_spilled'] > 0 or s['stage_metrics.memory_bytes_spilled'] > 0 or ratio(s['stage_metrics.jvm_gc_time_millis'], s['stage_metrics.executor_run_time_millis']) > 0.15"}
```

**Application-level rules** do not read `s` and return a bool, for example
`ratio(total_executor_summary["total_gc_time_millis"],
total_executor_summary["total_duration_millis"]) > 0.1` or
`any(x["num_failed_tasks"] > 3 for x in stages)`.

--------------------------------------------------------------------------------

## 6. Correlating signals

Individual rules describe symptoms. The root cause usually comes from reading
several signals together on the **same stage**. Combine them in one per-stage
rule with `and` / `and not`:

```text
DUR = ratio(s["task_quantile_metrics.duration_millis.maximum"], s["task_quantile_metrics.duration_millis.percentile_50"]) > 5
INP = ratio(s["task_quantile_metrics.input_metrics.bytes_read.maximum"], s["task_quantile_metrics.input_metrics.bytes_read.percentile_50"]) > 5

Data skew (duration AND input skew):              DUR and INP
Non-data straggler (duration skew WITHOUT input): DUR and not (INP)
```

Substitute the predicates textually. To relate a stage to other stages, read
`stages` inside a per-stage rule (`s["num_tasks"] > 10 * min(x["num_tasks"] for x in
stages)`), or return a list of the stages you want flagged from a rule that
does not read `s`.

-   **Spill with high GC** points at memory pressure rather than a tuning nit.
    Check executor memory sizing before touching partition counts.
-   **Duration skew with input or shuffle skew** is *data* skew: salt the key,
    or let AQE split it (`spark.sql.adaptive.enabled=true`). Duration skew with
    even byte counts points at the node: preemption, a noisy neighbour, slow
    local disk, or slow external calls.
-   **Large output partitions with large shuffle partitions** means shuffle
    parallelism is too low. Raise `spark.sql.shuffle.partitions`.
-   **Output bytes far exceeding input bytes**, especially with a long
    duration, is the signature of an accidental cross join.
-   **Many tasks that each read very little** means scheduling overhead
    dominates. Compact the input files; adding executors will not help.

Before recommending AQE or autotuning, check the batch's properties
(`gcloud dataproc batches describe`, `runtimeConfig.properties`) or the
`environment` action of `spark_application_telemetry.py`. Do not recommend a
feature that is already enabled. When several rules fire on one stage, report
the *underlying* cause once rather than listing every symptom.
