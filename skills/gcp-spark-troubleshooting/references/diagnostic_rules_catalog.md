# Spark Stage Diagnostic Rules: Authoring Guide

`scripts/spark_stage_diagnostics.py` ships **no built-in rules or thresholds**.
You supply the rules; the script evaluates them against stage telemetry and
reports which stages matched.

This is deliberate. What counts as "too much" GC, skew, or spill is
workload-specific — a ratio that is perfectly healthy for a long-running nightly
ETL job is pathological for an interactive query, and a partition size that is
fine on a 32-core executor is not fine on a 4-core one. Fixed built-in numbers
would produce confident-looking findings that are wrong for most jobs.

Everything below is an **illustrative starting point**. Read the stage telemetry
first, then pick thresholds that fit the job in front of you.

--------------------------------------------------------------------------------

## 1. Rule format

A rule is a JSON object. Pass a list of them via `--rules_file <path>` or
`--custom_rule '<json>'` (the latter accepts inline JSON or a file path).

```json
{
  "ruleId": "GC_PRESSURE",
  "description": "GC time is a large share of executor run time",
  "remediation": "Raise spark.executor.memory, or cache/persist less data.",
  "expression": "ratio(s.stage_metrics.jvm_gc_time_millis, s.stage_metrics.executor_run_time_millis) > 0.10",
  "detail": "'GC is ' + str(round(100 * ratio(s.stage_metrics.jvm_gc_time_millis, s.stage_metrics.executor_run_time_millis), 1)) + '% of run time'"
}
```

- `ruleId` (Required): Short identifier echoed into the report.
- `expression` (Required): Evaluated per stage. Truthy result ⇒ that stage is reported.
- `description` (Optional): One-line explanation shown in the report heading.
- `remediation` (Optional): What to do about it.
- `detail` (Optional): Second expression, evaluated per matching stage, rendered as the finding text. Use it to quote the **actual measured values** — a bare "rule matched" is not actionable.

### Expression language

Expressions are **Python**, not CEL. Use `and` / `or` / `not`, not `&&` / `||` /
`!`. Builtins are withheld; only the following names are in scope:

- `s`: The stage. Supports dotted access: `s.stage_metrics.jvm_gc_time_millis`.
- `has(x)`: True when a field is *set* (a `0` value is still set; `None` and `{}` are not).
- `ratio(a, b)`: `a / b`, yielding `0.0` when `b` is zero or missing. **Prefer this over `/`** — zero denominators are extremely common in stage telemetry.
- `mb(n)`, `gb(n)`: Bytes to MiB / GiB, rounded, for readable `detail` strings.
- `double`, `int`, `str`, `size`, `abs`, `max`, `min`, `round`: Standard conversions and arithmetic.

Field names may be written in either `snake_case` or `camelCase`; both spellings
resolve. (The REST API returns camelCase, while protos and `gcloud ...
--format=json` return snake_case.) Absent fields resolve to `None` rather than
raising, so guard with `has(...)` when a field may be missing.

A rule that fails to evaluate is reported once on stderr and skipped — it never
aborts the run, and it is never silently swallowed.

--------------------------------------------------------------------------------

## 2. Signals worth writing rules about

These are the standard Spark performance signals, with the telemetry fields that
expose them. Thresholds are intentionally omitted: derive them from the job's
own baseline, or start loose and tighten.

- **Task failures**: `s.num_failed_tasks`, `s.num_tasks`. Indicates unhandled exceptions, bad records, OOM kills, node loss.
- **Killed tasks**: `s.num_killed_tasks`. Indicates preemption / spot VM eviction, speculative execution, executor loss.
- **GC pressure**: `s.stage_metrics.jvm_gc_time_millis` vs `executor_run_time_millis`. Indicates heap too small, or too much cached/retained data. GC time is CPU time not spent on your job.
- **Memory spill**: `s.stage_metrics.memory_bytes_spilled`. Indicates execution memory exhausted; data pushed to storage memory.
- **Disk spill**: `s.stage_metrics.disk_bytes_spilled`. More severe: data written to local disk. Usually a shuffle or join that does not fit.
- **Shuffle write cost**: `s.stage_metrics.stage_shuffle_write_metrics.write_time_nanos` vs run time. Indicates shuffle write is the bottleneck; check partition counts and disk I/O.
- **Duration skew**: `s.task_quantile_metrics.duration_millis.maximum` vs `.percentile_50`. Indicates stragglers. Either data skew or an unevenly loaded node.
- **Input skew**: `s.task_quantile_metrics.input_metrics.bytes_read.{maximum,percentile_50}`. Indicates uneven input splits — a few huge files, or an unbalanced partition key.
- **Output skew**: `s.task_quantile_metrics.output_metrics.bytes_written.{maximum,percentile_50}`. Indicates skewed aggregation or hash-partition keys.
- **Shuffle skew**: `s.task_quantile_metrics.shuffle_write_metrics.write_bytes.{maximum,percentile_50}`. Indicates hot keys in a join or `groupBy`.
- **Oversized partitions**: the `maximum` of any of the byte quantiles above. Indicates partitions too large for executor memory; raises spill and GC risk.
- **Data explosion**: `s.stage_metrics.stage_output_metrics.bytes_written` vs `stage_input_metrics.bytes_read`. Indicates output far larger than input often means an unintended cross join.
- **Tiny-task storm**: large `s.num_tasks` with small input per task. Indicates small-files problem; scheduling overhead dominates real work.

> Quantile fields (`minimum`, `percentile_25`, `percentile_50`, `percentile_75`,
> `maximum`, `sum`, `count`) are only populated when the telemetry source
> includes task quantile metrics. Guard with `has(...)` if you are unsure.

--------------------------------------------------------------------------------

## 3. Worked examples

Copy these and adjust the numbers. They are examples of the *format*, not
recommended thresholds.

```json
[
  {
    "ruleId": "GC_PRESSURE",
    "description": "GC exceeds 10% of executor run time",
    "remediation": "Increase executor memory, or reduce cached/retained data.",
    "expression": "ratio(s.stage_metrics.jvm_gc_time_millis, s.stage_metrics.executor_run_time_millis) > 0.10",
    "detail": "str(round(100 * ratio(s.stage_metrics.jvm_gc_time_millis, s.stage_metrics.executor_run_time_millis), 1)) + '% of run time in GC'"
  },
  {
    "ruleId": "DISK_SPILL",
    "description": "Stage spilled to local disk",
    "remediation": "Increase executor memory or raise the shuffle partition count to shrink each partition.",
    "expression": "s.stage_metrics.disk_bytes_spilled > 0",
    "detail": "str(gb(s.stage_metrics.disk_bytes_spilled)) + ' GiB spilled to disk'"
  },
  {
    "ruleId": "DURATION_SKEW",
    "description": "Slowest task takes more than 5x the median",
    "remediation": "Check for a hot key; consider salting, repartitioning, or enabling AQE skew join handling.",
    "expression": "ratio(s.task_quantile_metrics.duration_millis.maximum, s.task_quantile_metrics.duration_millis.percentile_50) > 5",
    "detail": "str(round(ratio(s.task_quantile_metrics.duration_millis.maximum, s.task_quantile_metrics.duration_millis.percentile_50), 1)) + 'x median task duration'"
  },
  {
    "ruleId": "LARGE_INPUT_PARTITION",
    "description": "Largest input partition exceeds 512 MiB",
    "remediation": "Split large input files, or lower spark.sql.files.maxPartitionBytes.",
    "expression": "s.task_quantile_metrics.input_metrics.bytes_read.maximum > 512 * 1024 * 1024",
    "detail": "'largest input partition ' + str(mb(s.task_quantile_metrics.input_metrics.bytes_read.maximum)) + ' MiB'"
  },
  {
    "ruleId": "TASK_FAILURES",
    "description": "Stage had failed tasks",
    "remediation": "Search executor logs around the failure timestamps for stack traces.",
    "expression": "s.num_failed_tasks > 0",
    "detail": "str(s.num_failed_tasks) + ' of ' + str(s.num_tasks) + ' tasks failed'"
  }
]
```

--------------------------------------------------------------------------------

## 4. Correlating signals

Individual rules describe symptoms. Root cause usually comes from reading
several together on the **same stage**. Some useful pairings:

-   **Spill together with high GC** points at memory pressure rather than a
    tuning nit: the executor is both short on heap and paying to reclaim it.
    Look at executor memory sizing before touching partition counts.

-   **Duration skew together with input or shuffle skew** distinguishes *data*
    skew from *infrastructure* stragglers. If the slow task also read far more
    bytes than the median, the data is skewed — salt the key or let AQE split
    it. If the byte counts are even and only the duration is skewed, suspect the
    node: preemption, a noisy neighbor, or slow local disk.

-   **Skew with few, very large partitions** is an under-parallelization
    problem, not a hot-key problem. Raising the shuffle partition count helps
    here, whereas it does nothing for a genuine hot key.

-   **Output bytes far exceeding input bytes**, especially alongside a long
    duration, is the classic signature of an accidental cross join. Check the
    join condition before tuning anything.

-   **Many tasks each reading very little** means the cost is scheduling
    overhead, not computation. Compact the input files; adding executors will
    not help.

When several rules fire on one stage, report the *underlying* cause once rather
than listing every symptom separately.
