# Spark Stage Diagnostic Rules: Authoring Guide

`scripts/spark_stage_diagnostics.py` ships **no rules or thresholds**. You write
the rules; the script evaluates them against the application's stage telemetry
and reports which stages matched.

This is deliberate. What counts as "too much" GC, skew, or spill depends on the
workload. A ratio that is healthy for a long-running nightly ETL job is
pathological for an interactive query. A partition size that is fine on a
32-core executor is too large on a 4-core one. Built-in numbers would produce
confident-looking findings that are wrong for most jobs.

Rules are **CEL expressions** over the application's stage telemetry.

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
  "expression": "stages.filter(s, s.stage_metrics.executor_run_time_millis > 0 && double(s.stage_metrics.jvm_gc_time_millis) / double(s.stage_metrics.executor_run_time_millis) > 0.15)",
  "detail": "string(s.stage_metrics.jvm_gc_time_millis) + ' ms GC of ' + string(s.stage_metrics.executor_run_time_millis) + ' ms run time'"
}
```

- `ruleId` (required): a short identifier, echoed into the report.
- `expression` (required): a CEL expression over the variables in section 2.
  Section 3 explains how its result is read.
- `description` (optional): a one-line explanation, shown in the report heading.
- `remediation` (optional): what to do about the finding.
- `detail` (optional): a second expression, rendered as the text of
  each finding. For stage findings the violating stage is bound to `s`, or to
  the variable of a top-level `stages.filter(x, ...)`. Use it to quote the
  **measured values**: a bare "rule matched" is not actionable. It is CEL,
  with the same variables and functions as `expression`, and should yield a
  string, for example `string(double(s.stage_metrics.disk_bytes_spilled) /
  1073741824.0) + ' GiB spilled'`. A detail that fails to compile or evaluate
  is reported as a warning and the finding falls back to "Rule expression
  matched.".

Both expressions are only ever interpreted as CEL; nothing in a rule is run as
Python. A bare per-stage expression such as `s.num_tasks > 0` is a compile
error (`undeclared reference to 's'`): wrap it as `stages.filter(s, ...)`.

--------------------------------------------------------------------------------

## 2. Data model

Two variables are in scope. Both are typed against the Dataproc v1 protos, and
field names are the proto's `snake_case` names.

1.  **`stages`** (`list<StageData>`): every stage attempt of the application.
    -   `stage_id`, `stage_attempt_id`, `name`, `description`, `details`,
        `failure_reason`, `scheduling_pool`
    -   `num_tasks`, `num_active_tasks`, `num_complete_tasks`,
        `num_failed_tasks`, `num_killed_tasks`, `num_completed_indices`
    -   `status`: the `StageStatus` enum (see below)
    -   `submission_time`, `first_task_launched_time`, `completion_time`
        (timestamps)
    -   `parent_stage_ids`, `job_ids`, `rdd_ids` (`list<int>`); `locality`,
        `killed_tasks_summary` (`map<string, int>`)
    -   `stage_metrics` (`StageMetrics`):
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
    -   `task_quantile_metrics` (`TaskQuantileMetrics`): per-task
        distributions. Each leaf is a `Quantiles` message with `minimum`,
        `percentile_25`, `percentile_50`, `percentile_75`, `maximum`, `sum` and
        `count`:
        -   `duration_millis`, `executor_run_time_millis`,
            `jvm_gc_time_millis`, `scheduler_delay_millis`,
            `peak_execution_memory_bytes`, `memory_bytes_spilled`,
            `disk_bytes_spilled`
        -   `input_metrics.bytes_read`, `output_metrics.bytes_written`
        -   `shuffle_read_metrics.read_bytes`,
            `shuffle_write_metrics.write_bytes`,
            `shuffle_write_metrics.write_time_nanos`
    -   `speculation_summary`, `executor_metrics_distributions`,
        `peak_executor_metrics`, `executor_summary`, `accumulator_updates`
2.  **`total_executor_summary`** (`ConsolidatedExecutorSummary`): application
    totals.
    -   `active_tasks`, `completed_tasks`, `failed_tasks`, `total_tasks`,
        `total_cores`, `count`
    -   `total_duration_millis`, `total_gc_time_millis`, `total_input_bytes`,
        `total_shuffle_read`, `total_shuffle_write`
    -   `memory_used`, `max_memory`, `disk_used`, `memory_metrics.*`

Rules about the data:

-   **Absent fields read as proto3 defaults.** The REST API omits zero values,
    so a missing number reads as `0`, a missing string as `""`, a missing list
    as `[]` and a missing message as an empty message. Stage 0 carries no
    `stage_id`, and reads as `0`.
-   **`has()` follows proto3 presence.** `has(s.task_quantile_metrics)` is true
    when the message was sent. Timestamps (`submission_time`,
    `completion_time`, ...) and the proto's `optional` fields (`StageData`
    `name`, `description`, `details`, `failure_reason`, `scheduling_pool`;
    `TaskData` `duration_millis`, `executor_id`, `host`, `status`,
    `error_message`, `task_locality`) are present once sent, even as `""` or
    `0`. On any other number or string, `has()` is true only when the value is
    non-default. Guard quantile reads with `has(s.task_quantile_metrics)`: the
    quantiles exist only for stages that ran tasks.
-   **Enums are ints.** Compare `s.status` with
    `google.cloud.dataproc.v1.StageStatus.STAGE_STATUS_FAILED` (or `3`). A
    string such as `'STAGE_STATUS_FAILED'` is a type error. The values are
    `UNSPECIFIED` 0, `ACTIVE` 1, `COMPLETE` 2, `FAILED` 3, `PENDING` 4 and
    `SKIPPED` 5.
-   **Unknown field names are compile errors.** The error lists the valid
    fields, so a typo cannot silently turn a rule into a no-op.

--------------------------------------------------------------------------------

## 3. Language and result semantics

The script implements standard CEL with these options:

-   **Operators**: `? :`, `||`, `&&`, `!`, `==`, `!=`, `<`, `<=`, `>`, `>=`,
    `in`, `+`, `-`, `*`, `/`, `%`, field selection and `[index]`.
-   **Macros**: `has`, `filter`, `map` (two or three arguments), `exists`,
    `all` and `exists_one`. Macros work on any list or map, and can be nested
    anywhere in an expression.
-   **Functions**:
    -   `size`; the conversions `int`, `uint`, `double`, `string`, `bool`,
        `bytes`, `dyn`, `timestamp` and `duration`; `type` with the type
        names `int`, `uint`, `double`, `bool`, `string`, `bytes`, `list`,
        `map`, `null_type`, `type` and full message names such as
        `google.cloud.dataproc.v1.StageData`
    -   the string methods `contains`, `startsWith`, `endsWith` and `matches`
    -   the timestamp and duration accessors: `getHours`, `getMinutes`,
        `getSeconds`, `getMilliseconds`, `getFullYear`, `getMonth`,
        `getDayOfMonth`, `getDate`, `getDayOfWeek` and `getDayOfYear`
    -   Nothing else: no string extensions (`lowerAscii`, `split`, ...), no
        `math.*`, no `format`.
-   **Numbers**:
    -   `int`, `uint` and `double` never mix in arithmetic. `s.num_tasks * 1.5`
        is a type error: write `double(s.num_tasks) * 1.5`.
    -   Ordering comparisons may mix them: `s.num_tasks > 10.5` is valid.
    -   Equality and `in` may **not**: `s.num_tasks == 12.0` and
        `2 in [1.0, 2.0]` are type errors. Write the literal in the field's
        type (`s.num_tasks == 12`).
    -   Integer `/` truncates, and integer division by zero or overflow is an
        **error**.
    -   `double(a) / double(b)` follows IEEE, so dividing by zero gives
        infinity or NaN instead of an error. Ratios are therefore written as
        `x > 0 && double(y) / double(x) > T`.
    -   `string(double)` prints like Java: `string(1e7)` is `'1.0E7'`.
-   **Time**: timestamp minus timestamp is a duration. For example,
    `s.completion_time - s.submission_time > duration('5m')`.
    -   On a duration, `getHours()`, `getMinutes()` and `getSeconds()` are
        totals, but `getMilliseconds()` is only the millisecond component
        (0-999). To threshold elapsed time, compare durations
        (`s.completion_time - s.submission_time > duration('45s')`) or use
        `getSeconds()`.
    -   Durations cannot be negated (`-d` is a type error), and a
        duration `+`/`-` whose result is negative with a fractional second
        is an evaluation error.
    -   Time-zone arguments are IANA names (`'America/Los_Angeles'`), `UTC`,
        or offsets (`'+05:30'`).
    -   Durations and timestamps have microsecond precision; Spark's
        telemetry is in milliseconds.
-   **Enum constants** must be fully qualified:
    `google.cloud.dataproc.v1.StageStatus.STAGE_STATUS_FAILED`, not
    `StageStatus.STAGE_STATUS_FAILED`.
-   **null** only compares with messages, timestamps and durations:
    `s.stage_metrics == null` is valid (and false for any stage), but
    `s.name == null` and `s.num_tasks == null` are type errors. Test strings
    with `s.name == ''` or `has(s.name)`.
-   **Mixed literals**: a list or map literal whose elements have different
    types is `dyn`-typed, and both branches of `? :` must have the same type
    (`c ? 1 : null` and `c ? 1 : 'a'` are type errors).
-   **Messages** can be constructed with their full name, for example
    `google.cloud.dataproc.v1.StageData{stage_id: 1}` or
    `google.protobuf.Timestamp{seconds: 0}`. Messages compare with proto
    equality, so presence counts: `StageData{name: ''} != StageData{}`.
    Constructed stages in a result list are reported like any other stage.
-   **Map keys** may have any type, and `1`, `1u`, `1.0` and `true` are
    distinct keys. Reading `{1: 'a'}[1.0]` finds the entry, but `{1.0:
    'a'}[1]` does not; a duplicate key in a literal is an evaluation error.
-   **Regular expressions** (`matches`) are RE2. Constructs that cannot be
    reproduced exactly (`\p{Greek}`-style script classes, and `\p{Lu}`,
    `\p{Ll}`, `\p{Lt}` or `\p{Mn}` under `(?i)`) fail the rule with an error
    instead of matching differently.

How a rule's result is read:

-   **A non-empty list**: a violation. Its `StageData` elements are the
    violating stages. `int` elements are also read as stage IDs, so
    `stages.filter(...).map(s, s.stage_id)` works.
-   **`true`**: an application-level violation, with no stage IDs.
-   **`false` or an empty list**: no violation.
-   **Anything else** (a number, a string, ...): no violation. The script also
    prints a warning.
-   **Compile error** (syntax, unknown field, type mismatch): the rule is
    skipped with a warning.
-   **Evaluation error** (integer division by zero, a missing map key, an index
    out of range, ...): the rule is skipped with a warning.

`&&` and `||` absorb errors the way CEL does: `false && <error>` is `false`.
Guard divisions accordingly. Warnings go to stderr, and into the `warnings`
field of `--format=json`. A skipped rule is never reported as a clean result.

--------------------------------------------------------------------------------

## 4. Signals worth writing rules about

These are the standard Spark performance signals, with the fields that expose
them.

- **Task failures**: `s.num_failed_tasks` and `s.num_tasks`. Causes include unhandled exceptions, bad records, OOM kills and node loss.
- **Killed tasks**: `s.num_killed_tasks`. Causes include preemption or spot VM eviction, speculative execution and executor loss.
- **GC pressure**: `s.stage_metrics.jvm_gc_time_millis` compared with `executor_run_time_millis`. The heap is too small, or too much data is cached or retained.
- **Memory spill**: `s.stage_metrics.memory_bytes_spilled`. Execution memory ran out.
- **Disk spill**: `s.stage_metrics.disk_bytes_spilled`. More severe; usually a shuffle or join that does not fit in memory.
- **Shuffle write cost**: `s.stage_metrics.stage_shuffle_write_metrics.write_time_nanos` compared with run time (convert nanoseconds with `/ 1000000.0`).
- **Duration skew**: `s.task_quantile_metrics.duration_millis.maximum` compared with `.percentile_50`. Stragglers, caused by data skew or an unevenly loaded node.
- **Input skew**: `s.task_quantile_metrics.input_metrics.bytes_read.{maximum, percentile_50}`. Uneven input splits.
- **Output or shuffle skew**: `output_metrics.bytes_written` and `shuffle_write_metrics.write_bytes` quantiles. Hot aggregation or join keys.
- **Oversized partitions**: the `maximum` of any byte quantile above. Raises the risk of spill and GC.
- **Data explosion**: output bytes compared with input bytes. Often an accidental cross join.
- **Tiny-task storm**: a large `s.num_tasks` with a small median duration or input. Scheduling overhead dominates the real work.

**Guard ratios with a magnitude.** A ratio says nothing on its own: a stage
that ran for 16 ms with 9 ms of GC has a 56% GC ratio but costs nothing. Add a
floor on the absolute value, for example
`s.stage_metrics.executor_run_time_millis > 60000 && double(...) / double(...)
> 0.15`, or `s.task_quantile_metrics.duration_millis.maximum > 60000` for skew,
so that findings point at stages worth tuning.

--------------------------------------------------------------------------------

## 5. Example filters

These filters cover common Spark issues. Copy one and adjust its thresholds to
the job; they are not defaults.

```json
[
  {"ruleId": "DATA_SKEW_DURATION_VARIANCE", "description": "Max task duration exceeds 3x median, and 60 s",
   "expression": "stages.filter(s, has(s.task_quantile_metrics) && s.task_quantile_metrics.duration_millis.percentile_50 > 0 && double(s.task_quantile_metrics.duration_millis.maximum - s.task_quantile_metrics.duration_millis.percentile_50) > (double(s.task_quantile_metrics.duration_millis.percentile_50) * 3.0) && s.task_quantile_metrics.duration_millis.maximum > 60000)"},
  {"ruleId": "EXECUTOR_MEMORY_PRESSURE_SPILL", "description": "Stage spilled to memory or disk",
   "expression": "stages.filter(s, s.stage_metrics.memory_bytes_spilled > 0 || s.stage_metrics.disk_bytes_spilled > 0)"},
  {"ruleId": "HIGH_GC_OVERHEAD", "description": "GC exceeds 15% of executor run time",
   "expression": "stages.filter(s, s.stage_metrics.executor_run_time_millis > 0 && double(s.stage_metrics.jvm_gc_time_millis) / double(s.stage_metrics.executor_run_time_millis) > 0.15)"},
  {"ruleId": "EXECUTOR_OOM_LOST_EXECUTORS", "description": "Killed tasks (preemption, heartbeat timeout, OOM)",
   "expression": "stages.filter(s, s.num_killed_tasks > 0)"},
  {"ruleId": "SHUFFLE_IMBALANCE_FETCH_HEAVY", "description": "Max task shuffle write exceeds 4x median",
   "expression": "stages.filter(s, s.stage_metrics.stage_shuffle_read_metrics.bytes_read > 0 && has(s.task_quantile_metrics) && s.task_quantile_metrics.shuffle_write_metrics.write_bytes.percentile_50 > 0 && double(s.task_quantile_metrics.shuffle_write_metrics.write_bytes.maximum) / double(s.task_quantile_metrics.shuffle_write_metrics.write_bytes.percentile_50) > 4.0)"},
  {"ruleId": "STRAGGLER_TASKS_LONG_TAIL", "description": "Max task duration exceeds 5x median, with more than 10 tasks",
   "expression": "stages.filter(s, s.num_tasks > 10 && has(s.task_quantile_metrics) && s.task_quantile_metrics.duration_millis.percentile_50 > 0 && double(s.task_quantile_metrics.duration_millis.maximum) / double(s.task_quantile_metrics.duration_millis.percentile_50) > 5.0)"},
  {"ruleId": "DYNAMIC_ALLOCATION_THRASHING", "description": "Over 20 killed tasks (executor churn)",
   "expression": "stages.filter(s, s.num_killed_tasks > 20)"},
  {"ruleId": "EXCESSIVE_DISK_SPILL", "description": "Over 1 GiB spilled to disk",
   "expression": "stages.filter(s, s.stage_metrics.disk_bytes_spilled > 1073741824)"},
  {"ruleId": "UNDERPARTITIONED_SPILL", "description": "Disk spill with under 50 tasks",
   "expression": "stages.filter(s, s.stage_metrics.disk_bytes_spilled > 0 && s.num_tasks < 50)"},
  {"ruleId": "TOO_MANY_SMALL_TASKS", "description": "Over 10,000 tasks with median duration under 100 ms",
   "expression": "stages.filter(s, s.num_tasks > 10000 && has(s.task_quantile_metrics) && s.task_quantile_metrics.duration_millis.percentile_50 < 100)"},
  {"ruleId": "DRIVER_BOTTLENECK_FAILURE", "description": "Stage has failed tasks",
   "expression": "stages.filter(s, s.num_failed_tasks > 0)"},
  {"ruleId": "SERIALIZATION_SHUFFLE_WRITE_BOTTLENECK", "description": "Shuffle write exceeds 10% of task run time",
   "expression": "stages.filter(s, s.stage_metrics.executor_run_time_millis > 0 && (double(s.stage_metrics.stage_shuffle_write_metrics.write_time_nanos) / 1000000.0) / double(s.stage_metrics.executor_run_time_millis) > 0.1)"},
  {"ruleId": "HIGH_SCAN_TASK_COUNT_STARVATION", "description": "Scan with over 80,000 tasks",
   "expression": "stages.filter(s, s.stage_metrics.stage_shuffle_read_metrics.bytes_read == 0 && s.stage_metrics.stage_input_metrics.bytes_read > 0 && s.num_tasks > 80000)"}
]
```

**Cheapest-signal-first triage.** Evaluate one composite filter first, to decide
whether deeper stage or log inspection is warranted:

```json
{"ruleId": "COMPOSITE_TRIAGE_ENTRY_POINT", "description": "Any failure, kill, spill, or GC over 15%",
 "expression": "stages.filter(s, s.num_failed_tasks > 0 || s.num_killed_tasks > 0 || s.stage_metrics.disk_bytes_spilled > 0 || s.stage_metrics.memory_bytes_spilled > 0 || (s.stage_metrics.executor_run_time_millis > 0 && double(s.stage_metrics.jvm_gc_time_millis) / double(s.stage_metrics.executor_run_time_millis) > 0.15))"}
```

**Application-level rules** return a bool, for example
`double(total_executor_summary.total_gc_time_millis) /
double(total_executor_summary.total_duration_millis) > 0.1`.

--------------------------------------------------------------------------------

## 6. Correlating signals

Individual rules describe symptoms. The root cause usually comes from reading
several signals together on the **same stage**. Combine them in one rule with a
set intersection (`id in ...`) or a set difference (`!(id in ...)`) over stage
IDs:

```text
DUR = has(s.task_quantile_metrics) && s.task_quantile_metrics.duration_millis.percentile_50 > 0 && double(s.task_quantile_metrics.duration_millis.maximum) / double(s.task_quantile_metrics.duration_millis.percentile_50) > 5.0
INP = has(s.task_quantile_metrics) && s.task_quantile_metrics.input_metrics.bytes_read.percentile_50 > 0 && double(s.task_quantile_metrics.input_metrics.bytes_read.maximum) / double(s.task_quantile_metrics.input_metrics.bytes_read.percentile_50) > 5.0

Data skew (duration AND input skew):
  stages.filter(s, DUR).map(s, s.stage_id).filter(id, id in stages.filter(s, INP).map(s, s.stage_id))
Non-data straggler (duration skew WITHOUT input skew):
  stages.filter(s, DUR).map(s, s.stage_id).filter(id, !(id in stages.filter(s, INP).map(s, s.stage_id)))
```

Substitute the predicates textually. Simple conjunctions can also be written
directly, as in `stages.filter(s, DUR && INP)`. `size()`, `? :` and `[0]` are
available for guards, as in `size(stages.filter(s, P)) > 0 ?
stages.filter(s, P)[0].num_failed_tasks > 3 : false`.

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
