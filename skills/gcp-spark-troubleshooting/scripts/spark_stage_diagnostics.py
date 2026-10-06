#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Spark Stage Diagnostics rule evaluator.

Evaluates caller-supplied rules over Dataproc Spark stage and quantile metrics.
The evaluator applies no built-in rules or thresholds; see
`references/diagnostic_rules_catalog.md` for rule-authoring guidelines and
worked examples.

Stage data is fetched the same way the Dataproc Data Worker Agent's
`GetSparkStageDiagnostics` tool fetches it: `sparkApplications:search` to find
the application, `summarizeExecutors` for the executor totals, then every page
of `searchStages` with `summary_metrics_mask=task_quantile_metrics`.

Rules are Python expressions over `stages` (a list of StageData records),
`total_executor_summary` (a ConsolidatedExecutorSummary record) and, for
per-stage rules, `s` (one stage). Records are flat dicts keyed by dotted
snake_case field paths, such as `s["stage_metrics.jvm_gc_time_millis"]`;
absent fields read as proto3 defaults. A per-stage rule flags every stage it
is truthy for; any other rule flags the stages in the list it returns, or the
whole application when it returns `True`. A rule that fails to compile or evaluate is skipped with a
warning.
"""

import argparse
import ast
import builtins
import copy
import difflib
import json
import os
import re
import sys
import types
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# pylint: disable=g-import-not-at-top
# The sibling scripts are importable because Python puts the running script's
# directory on sys.path (and the tests/BUILD add scripts/ explicitly).
import spark_applications


def _snake_to_camel(name: str) -> str:
  """Converts a snake_case proto field name to its JSON camelCase spelling."""
  head, *rest = name.split("_")
  return head + "".join(word.capitalize() for word in rest)


def _get(data: Any, key: str, default: Any = 0) -> Any:
  """Reads `key` from `data`, accepting either JSON spelling of the field.

  The Dataproc REST API emits camelCase field names (`taskQuantileMetrics`),
  while the protos and `gcloud ... --format=json` emit snake_case
  (`task_quantile_metrics`). Callers normally pass the canonical snake_case
  proto name and this helper transparently falls back to the camelCase
  spelling (and vice versa), so a missing fallback can no longer silently
  disable a rule.

  Args:
    data: The mapping to read from. Non-mappings yield `default`.
    key: The field name, preferably in canonical snake_case.
    default: Value returned when the field is absent under either spelling.

  Returns:
    The field value, or `default` if it is absent.
  """
  if not isinstance(data, dict):
    return default
  if key in data:
    return data[key]
  camel = _snake_to_camel(key)
  if camel in data:
    return data[camel]
  return data.get(re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower(), default)


_SKIPPED_PREFIX = "rule '"


def count_skipped_rules(warnings: List[str]) -> int:
  """Counts the rules `evaluate_stage_rules` skipped, from its warnings."""
  return sum(w.startswith(_SKIPPED_PREFIX) for w in warnings)


class _RuleWarnings:
  """Reports broken rules and details, to stderr and to the report.

  A rule that cannot be evaluated must never abort the run, but it must not be
  silently dropped either: an empty report would otherwise be misread as "no
  problems found". Each skipped rule, and each rule whose `detail` could not
  be rendered, is reported exactly once.
  """

  def __init__(self):
    self.messages: List[str] = []

  def _emit(self, text: str) -> None:
    self.messages.append(text)
    print(f"Warning: {text}", file=sys.stderr)

  def warn(self, rule_id: str, message: str) -> None:
    """Reports a rule that was skipped. Called at most once per rule."""
    self._emit(
        f"{_SKIPPED_PREFIX}{rule_id}' could not be evaluated and was"
        f" skipped: {message}"
    )

  def warn_fields(
      self, rule_id: str, fields: List[str], known: Set[str]
  ) -> None:
    """Reports fields a rule read that no record has; the rule still ran."""
    hints = []
    for name in fields:
      close = difflib.get_close_matches(name, sorted(known), n=2, cutoff=0.7)
      hint = f" (did you mean {', '.join(close)}?)" if close else ""
      hints.append(name + hint)
    self._emit(
        f"rule '{rule_id}' read fields that no stage has and that are not"
        f" Dataproc fields, which read as 0: {'; '.join(hints)}. Check the"
        " spelling."
    )

  def warn_detail(self, rule_id: str, message: str) -> None:
    """Reports a `detail` that could not be rendered; the rule still ran."""
    self._emit(
        f"detail of rule '{rule_id}' could not be rendered, so its findings"
        f" use a generic text: {message}"
    )


def _stage_id(stage: Any) -> Any:
  # Proto3 JSON omits a zero stage ID, so absence means stage 0.
  return _get(stage, "stage_id", 0)


def _describe_value(value: Any, limit: int = 200) -> str:
  text = "record" if isinstance(value, Fields) else repr(value)
  return text if len(text) <= limit else text[: limit - 3] + "..."


# ------------------------------------------------------------------------------
# Rule data: flat dicts keyed by dotted snake_case paths
# ------------------------------------------------------------------------------

# The REST API omits zero values. An absent field reads as 0 unless it is one
# of these non-numeric StageData fields.
_DEFAULTS: Dict[str, Any] = {
    "name": "", "description": "", "details": "", "failure_reason": "",
    "scheduling_pool": "", "status": "STAGE_STATUS_UNSPECIFIED",
    "is_shuffle_push_enabled": False,
    "submission_time": None, "first_task_launched_time": None,
    "completion_time": None,
    "job_ids": [], "parent_stage_ids": [], "rdd_ids": [],
    "accumulator_updates": [],
    "executor_summary": {}, "killed_tasks_summary": {}, "locality": {},
    "tasks": {},
}

# Leaf field names that are real Dataproc fields even when no stage sends them
# (the REST API omits zeros): the int64 fields spark_applications converts,
# the non-numeric fields above and the int32 counters. A key whose last
# segment is none of these, and that no record has, is most likely a typo.
_INT32_FIELDS = frozenset({
    "stage_attempt_id", "num_tasks", "num_active_tasks", "num_complete_tasks",
    "num_failed_tasks", "num_killed_tasks", "num_completed_indices",
    "active_tasks", "completed_tasks", "failed_tasks", "total_tasks",
    "total_cores", "rdd_blocks",
})

# Map fields: their keys are data (executor IDs, locality levels), so they are
# kept as dicts instead of being flattened into the path.
_MAP_FIELDS = frozenset({
    "executor_summary", "killed_tasks_summary", "locality", "tasks",
    "metrics", "executor_logs",
})


_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[a-z])(?=[0-9])")


def _snake(name: str) -> str:
  """camelCase (REST) to snake_case: `percentile50` -> `percentile_50`."""
  return _WORD_BOUNDARY.sub("_", name).lower()


def _value(key: str, value: Any) -> Any:
  if key.endswith("_time") and isinstance(value, str):
    return spark_applications.parse_timestamp(value)
  if isinstance(value, dict):
    return {_snake(k): _value(_snake(k), v) for k, v in value.items()}
  if isinstance(value, list):
    return [_value(key, v) for v in value]
  return value


def flatten(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
  """Flattens nested messages into `{"a.b.c": value}` with snake_case keys.

  Map fields stay dicts (with snake_case keys inside their values), lists stay
  lists, and `*_time` strings become timezone-aware datetimes.

  Args:
    data: A decoded message, int64 strings already converted.
    prefix: Path of `data` within the enclosing message.

  Returns:
    The flat mapping.
  """
  out: Dict[str, Any] = {}
  for key, value in data.items():
    name = _snake(key)
    path = prefix + name
    if isinstance(value, dict) and name not in _MAP_FIELDS:
      out.update(flatten(value, path + "."))
    elif isinstance(value, dict):
      out[path] = {k: _value(name, v) for k, v in value.items()}
    else:
      out[path] = _value(name, value)
  return out


class Fields(dict):
  """A flat telemetry record whose absent fields read as proto3 defaults.

  Reads of absent fields are recorded in `reads`, so that fields no record has
  (most likely typos) can be reported.
  """

  def __init__(self, data: Dict[str, Any], reads: Set[str]):
    super().__init__(data)
    self.reads = reads

  def __missing__(self, key: str) -> Any:
    self.reads.add(key)
    return copy.copy(_DEFAULTS.get(key, 0))

  def __hash__(self):  # Records are compared by identity in results.
    return id(self)

  __eq__ = object.__eq__


# ------------------------------------------------------------------------------
# Helper functions available to expressions
# ------------------------------------------------------------------------------


def ratio(numerator: Any, denominator: Any) -> float:
  """`numerator / denominator`, or 0.0 when the denominator is 0 or absent."""
  if not denominator:
    return 0.0
  return float(numerator or 0) / float(denominator)


def mb(num_bytes: Any) -> float:
  """Bytes to mebibytes, rounded to two decimals."""
  return round(float(num_bytes or 0) / (1 << 20), 2)


def gb(num_bytes: Any) -> float:
  """Bytes to gibibytes, rounded to two decimals."""
  return round(float(num_bytes or 0) / (1 << 30), 2)


def seconds_between(start: Any, end: Any) -> float:
  """Seconds from `start` to `end`, or 0.0 if either is unset."""
  if start is None or end is None:
    return 0.0
  return (end - start).total_seconds()


FUNCTIONS = {
    "ratio": ratio, "mb": mb, "gb": gb, "seconds_between": seconds_between,
}


class RuleError(ValueError):
  """An expression is not valid Python or reads an unknown name."""


class Expression:
  """A compiled rule expression. Rules come from the agent: not a sandbox."""

  def __init__(self, source: str, variables: Iterable[str]):
    if not isinstance(source, str):
      raise RuleError("an expression must be a string")
    try:
      tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError as e:
      raise RuleError(
          f"invalid Python expression: {e.msg} (column {e.offset})"
      ) from None
    loaded, stored = set(), set()
    for node in ast.walk(tree):
      if isinstance(node, ast.Name):
        (stored if isinstance(node.ctx, ast.Store) else loaded).add(node.id)
    self.free_names = frozenset(loaded - stored)
    known = set(variables) | set(FUNCTIONS) | set(dir(builtins))
    unknown = sorted(self.free_names - known)
    if unknown:
      raise RuleError(
          f"unknown name {unknown[0]!r}; available names are"
          f" {', '.join(sorted(variables))}, the helpers"
          f" {', '.join(sorted(FUNCTIONS))} and the Python builtins"
      )
    self._code = compile(tree, "<rule>", "eval")

  def uses(self, name: str) -> bool:
    return name in self.free_names

  def evaluate(self, variables: Dict[str, Any]) -> Any:
    # Everything goes into globals: comprehensions are nested scopes that can
    # see globals but not the locals mapping of `eval`.
    namespace = {**FUNCTIONS, **variables}
    return eval(self._code, namespace)  # pylint: disable=eval-used


# The variable a per-stage rule reads, and that `detail` sees the violating
# stage as.
_STAGE_VAR = "s"
_RULE_VARIABLES = ("stages", "total_executor_summary", _STAGE_VAR)


def evaluate_stage_rules(
    stages: List[Dict[str, Any]],
    rules: Optional[List[Dict[str, Any]]] = None,
    total_executor_summary: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
  """Evaluates caller-supplied rules against stage telemetry.

  This evaluator deliberately applies no rules or thresholds of its own. What
  counts as "too much" GC, skew, or spill is workload-specific: a ratio that is
  healthy for a long-running ETL job is pathological for an interactive query.
  Baking in fixed numbers would produce confident-looking findings that are
  wrong for most jobs, so the caller always supplies the rules. See
  `references/diagnostic_rules_catalog.md` for authoring guidelines and
  worked examples.

  Rules are Python expressions over flat records keyed by dotted snake_case
  paths, such as `s["stage_metrics.jvm_gc_time_millis"]`:

  * a rule that reads `s` is a per-stage rule: it is evaluated once per
    stage, with `s` bound to it, and flags every stage it is truthy for;
  * any other rule is evaluated once. A non-empty list (or tuple, set or
    generator) is a violation whose stage elements are the violating
    stages (int elements are taken as stage IDs, so
    `[x["stage_id"] for x in stages if ...]` works too); `True` is an
    application-level violation; `False` or an empty list is not a violation;
  * a rule that fails to compile, or raises on any stage, is skipped with a
    warning;
  * a rule that reads a key no stage has, and whose last segment is not a
    known Dataproc field name, gets a warning: the key is most likely
    misspelled.

  Args:
    stages: Stage telemetry mappings, in either snake_case or camelCase. int64
      values serialized as strings are accepted.
    rules: Rule objects. Each requires `ruleId` and `expression`. Optional
      `description` and `remediation` are echoed into the report, and an
      optional `detail` expression is evaluated per matching stage (bound to
      `s`) to render a human-readable explanation with the measured values.
    total_executor_summary: Optional ConsolidatedExecutorSummary, available to
      rules as `total_executor_summary`.
    warnings: If given, messages about skipped rules are appended to it.

  Returns:
    One entry per violated rule. `scope` is "stage" when the rule identified
    stages (listed in `violating_stages`) and "application" otherwise (with
    the rendered `detail`).
  """
  reads: Set[str] = set()
  records = [
      Fields(flatten(spark_applications.normalize_int64(s)), reads)
      for s in stages or []
  ]
  summary = Fields(
      flatten(spark_applications.normalize_int64(total_executor_summary or {})),
      reads,
  )
  seen = set(summary).union(*records) | set(_DEFAULTS)
  known_leaves = (
      {key.rsplit(".", 1)[-1] for key in seen}
      | {_snake(f) for f in spark_applications._INT64_FIELDS}  # pylint: disable=protected-access
      | _INT32_FIELDS
  )
  variables = {"stages": records, "total_executor_summary": summary}
  record_ids = {id(r) for r in records}
  by_id: Dict[int, Fields] = {}
  for record in records:
    by_id.setdefault(record["stage_id"], record)
  results = []
  reporter = _RuleWarnings()

  for index, rule in enumerate(rules or []):
    if not isinstance(rule, dict):
      reporter.warn(
          f"#{index + 1}", f"a rule must be a JSON object, not {rule!r:.100}"
      )
      continue
    rule_id = str(rule.get("ruleId") or f"UNNAMED_RULE_{index + 1}")
    expression = rule.get("expression")
    if not expression or not isinstance(expression, str):
      reporter.warn(rule_id, "rule is missing an 'expression' string")
      continue
    try:
      program = Expression(expression, _RULE_VARIABLES)
    except RuleError as e:
      reporter.warn(rule_id, str(e))
      continue

    reads.clear()
    detail = _DetailRenderer(rule_id, rule.get("detail"), reporter, variables)
    try:
      if program.uses(_STAGE_VAR):
        result = [
            record
            for record in records
            if program.evaluate({**variables, _STAGE_VAR: record})
        ]
      else:
        result = program.evaluate(variables)
        if isinstance(result, (tuple, set, frozenset, types.GeneratorType)):
          result = list(result)
    except Exception as e:  # pylint: disable=broad-except
      reporter.warn(rule_id, f"{type(e).__name__}: {e}")
      continue

    entry = {
        "ruleId": rule_id,
        "description": rule.get("description", ""),
        "remediation": rule.get(
            "remediation", "Review stage execution metrics."
        ),
        "scope": "stage",
        "violating_stages": [],
    }
    if result is True:
      entry["scope"] = "application"
      entry["detail"] = detail.render()
      results.append(entry)
    elif isinstance(result, list) and result:
      for element in result:
        if id(element) in record_ids:
          stage = element
        elif isinstance(element, int) and not isinstance(element, bool):
          stage = by_id.get(element)
          if stage is None:
            entry["violating_stages"].append(
                {"stage_id": element, "detail": _DetailRenderer.FALLBACK}
            )
            continue
        else:
          continue
        entry["violating_stages"].append(
            {"stage_id": stage["stage_id"], "detail": detail.render(stage)}
        )
      if not entry["violating_stages"]:
        # A non-empty list without stages is still a violation, just not
        # attributable to specific stages.
        entry["scope"] = "application"
        entry["detail"] = (
            f"Rule returned {len(result)} value(s): {_describe_value(result)}"
        )
      results.append(entry)
    elif result is not False and not isinstance(result, list):
      reporter.warn(
          rule_id,
          "a rule that does not read `s` must yield a bool or a list, not"
          f" {_describe_value(result)}",
      )
    unseen = sorted(
        key for key in reads - seen
        if key.rsplit(".", 1)[-1] not in known_leaves
    )
    if unseen:
      reporter.warn_fields(rule_id, unseen, seen)

  if warnings is not None:
    warnings.extend(reporter.messages)
  return results


class _DetailRenderer:
  """Evaluates a rule's optional `detail` expression for a finding.

  The expression sees the same variables as rules, with the violating stage
  bound to `s`. A broken detail expression must not suppress the finding
  itself: it is reported once and the finding falls back to a generic text.
  """

  FALLBACK = "Rule expression matched."

  def __init__(
      self,
      rule_id: str,
      expression: Any,
      reporter: _RuleWarnings,
      variables: Dict[str, Any],
  ):
    self._rule_id = rule_id
    self._reporter = reporter
    self._variables = variables
    self._program: Optional[Expression] = None
    if not isinstance(expression, str):
      if expression is not None:
        self._report(TypeError("'detail' must be an expression string"))
      return
    if not expression:
      return
    try:
      self._program = Expression(expression, _RULE_VARIABLES)
    except RuleError as e:
      self._report(e)

  def _report(self, error: Exception) -> None:
    self._reporter.warn_detail(
        self._rule_id, f"{type(error).__name__}: {error}"
    )

  def render(self, stage: Optional[Fields] = None) -> str:
    """Renders the detail text.

    Args:
      stage: The violating stage, or None for an application-level finding.

    Returns:
      The rendered text, or a generic fallback.
    """
    if self._program is None:
      return self.FALLBACK
    if stage is None and self._program.uses(_STAGE_VAR):
      # An application-level finding has no stage to describe.
      return self.FALLBACK
    try:
      value = self._program.evaluate({**self._variables, _STAGE_VAR: stage})
    except Exception as e:  # pylint: disable=broad-except
      self._report(e)
      self._program = None
      return self.FALLBACK
    return value if isinstance(value, str) else _describe_value(value)


_NO_APPLICATION = "No Spark applications found for workload {}"
_FETCH_FAILED = "Failed to retrieve Spark diagnostics via public APIs: {}"


def fetch_workload_stages(
    client: "spark_applications.SparkApplicationsClient",
    application_id: Optional[str] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
  """Fetches sparkApplications stage data exactly as the Data Worker Agent does.

  Args:
    client: A client bound to one batch or session.
    application_id: Optional explicit Spark application ID.

  Returns:
    (application ID, every StageData with task quantile metrics, the
    application's totalExecutorSummary).

  Raises:
    spark_applications.DataprocApiError: If any call fails or the workload has
      no Spark application. This is deliberately distinct from an empty stage
      list so that a failed fetch is never reported as a clean bill of health.
      The message starts with the Data Worker Agent's wording for the same
      failure.
  """
  try:
    app_id, _, _ = client.resolve_application(application_id)
  except spark_applications.DataprocApiError as e:
    if e.status == 404 and str(e).startswith("No Spark application found"):
      raise spark_applications.DataprocApiError(
          _NO_APPLICATION.format(client.workload_id)
          + ". The workload may still be pending, or it failed before the"
          " Spark driver started (check the batch stateMessage and driver"
          " logs instead).",
          e.status,
          e.reason,
      ) from e
    raise spark_applications.DataprocApiError(
        _FETCH_FAILED.format(e), e.status, e.reason
    ) from e
  try:
    executors = client.call("summarizeExecutors", app_id)
    stages = client.paginate(
        "searchStages",
        "sparkApplicationStages",
        app_id,
        {
            "pageSize": spark_applications.MAX_PAGE_SIZE,
            "summaryMetricsMask": "task_quantile_metrics",
        },
    )
  except spark_applications.DataprocApiError as e:
    raise spark_applications.DataprocApiError(
        _FETCH_FAILED.format(e), e.status, e.reason
    ) from e
  return app_id, stages, executors.get("totalExecutorSummary") or {}


def _quantiles(stage: Dict[str, Any], *path: str) -> Optional[Dict[str, Any]]:
  q = spark_applications.field(
      stage, "task_quantile_metrics", *path, default=None
  )
  if not isinstance(q, dict):
    return None
  return {
      "minimum": spark_applications.field(q, "minimum"),
      "percentile50": spark_applications.field(q, "percentile_50"),
      "maximum": spark_applications.field(q, "maximum"),
      "sum": spark_applications.field(q, "sum"),
  }


def violating_stage_info(stage: Dict[str, Any]) -> Dict[str, Any]:
  """Maps a StageData to the Data Worker Agent's ViolatingStageInfo record."""
  f = spark_applications.field
  metrics = f(stage, "stage_metrics", default={})
  task_quantiles = None
  if isinstance(f(stage, "task_quantile_metrics", default=None), dict):
    task_quantiles = {
        "durationMillis": _quantiles(stage, "duration_millis"),
        "inputBytes": _quantiles(stage, "input_metrics", "bytes_read"),
        "outputBytes": _quantiles(stage, "output_metrics", "bytes_written"),
        "shuffleWriteBytes": _quantiles(
            stage, "shuffle_write_metrics", "write_bytes"
        ),
    }
  return {
      "stageId": _stage_id(stage),
      "numTasks": f(stage, "num_tasks"),
      "numKilledTasks": f(stage, "num_killed_tasks"),
      "stageMetrics": {
          "executorRunTimeMillis": f(metrics, "executor_run_time_millis"),
          "jvmGcTimeMillis": f(metrics, "jvm_gc_time_millis"),
          "memoryBytesSpilled": f(metrics, "memory_bytes_spilled"),
          "diskBytesSpilled": f(metrics, "disk_bytes_spilled"),
          "shuffleWriteTimeNanos": f(
              metrics, "stage_shuffle_write_metrics", "write_time_nanos"
          ),
          "inputBytesRead": f(metrics, "stage_input_metrics", "bytes_read"),
          "shuffleReadBytesRead": f(
              metrics, "stage_shuffle_read_metrics", "bytes_read"
          ),
          "outputBytesWritten": f(
              metrics, "stage_output_metrics", "bytes_written"
          ),
          "shuffleWriteBytesWritten": f(
              metrics, "stage_shuffle_write_metrics", "bytes_written"
          ),
      },
      "taskQuantiles": task_quantiles,
  }


def build_diagnostics_output(
    stages: List[Dict[str, Any]],
    violations: List[Dict[str, Any]],
    total_executor_summary: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
  """Builds the Data Worker Agent's `GetSparkStageDiagnostics.Output` shape.

  Every field the agent emits is present under the same name. Additionally,
  each violation carries `remediation`, per-stage `details` and (for
  application-level findings) `detail`, and `warnings` lists rules that were
  skipped and other caveats the agent only logs.

  Args:
    stages: The evaluated stages.
    violations: The result of `evaluate_stage_rules`.
    total_executor_summary: The application's totalExecutorSummary.
    error_message: Set to produce an ERROR result.
    warnings: Caveats to surface alongside the result.

  Returns:
    A JSON-serializable dict with status, errorMessage, violations,
    stageMetrics, summary and warnings.
  """
  if error_message is not None:
    return {
        "status": "ERROR",
        "errorMessage": error_message,
        "violations": [],
        "stageMetrics": [],
        "summary": None,
        "warnings": list(warnings or []),
    }
  stages = [spark_applications.normalize_int64(s) for s in stages]
  executors = spark_applications.normalize_int64(total_executor_summary or {})
  by_id: Dict[Any, Dict[str, Any]] = {}
  for s in stages:
    by_id.setdefault(_stage_id(s), s)
  stage_metrics: Dict[Any, Dict[str, Any]] = {}
  violation_details = []
  for v in violations:
    ids = [vs["stage_id"] for vs in v["violating_stages"]]
    for stage_id in ids:
      if stage_id not in stage_metrics and stage_id in by_id:
        stage_metrics[stage_id] = violating_stage_info(by_id[stage_id])
    detail = {
        "ruleId": v["ruleId"],
        "description": v["description"],
        "violatingStageIds": ids,
        "remediation": v["remediation"],
        "details": [
            {"stageId": vs["stage_id"], "detail": vs["detail"]}
            for vs in v["violating_stages"]
        ],
    }
    if "detail" in v:
      detail["detail"] = v["detail"]
    violation_details.append(detail)
  f = spark_applications.field
  return {
      "status": "FAIL" if violations else "PASS",
      "errorMessage": None,
      "violations": violation_details,
      "stageMetrics": list(stage_metrics.values()),
      "summary": {
          "totalDurationMs": f(executors, "total_duration_millis"),
          "totalInputBytes": f(executors, "total_input_bytes"),
          "activeTasks": f(executors, "active_tasks"),
          "completedTasks": f(executors, "completed_tasks"),
          "failedTasks": f(executors, "failed_tasks"),
          "killedTasks": sum(
              int(f(s, "num_killed_tasks") or 0) for s in stages
          ),
      },
      "warnings": list(warnings or []),
  }


def _load_rules(raw: str, source_flag: str) -> List[Dict[str, Any]]:
  """Parses a rules argument that may be inline JSON or a path to a JSON file.

  Args:
    raw: The flag value: either a JSON list or a path to a file holding one.
    source_flag: Flag name, used only for error messages.

  Returns:
    The parsed rule list.

  Raises:
    ValueError: If the value is neither readable JSON nor a JSON list.
  """
  try:
    if os.path.exists(raw):
      with open(raw, "r") as f:
        parsed = json.load(f)
    else:
      parsed = json.loads(raw)
  except (OSError, ValueError, json.JSONDecodeError) as e:
    raise ValueError(
        f"{source_flag} is neither a readable file nor valid JSON: {e}"
    ) from e

  if not isinstance(parsed, list):
    raise ValueError(
        f"{source_flag} must be a JSON list of"
        ' {"ruleId", "description", "expression"} objects.'
    )
  return parsed


def _load_telemetry_file(
    path: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
  """Reads stages (and optionally the executor summary) from a JSON file.

  Accepts a list of stages, a raw `searchStages` response, or an object with
  `stages` and optionally `totalExecutorSummary` (either spelling).

  Args:
    path: The file to read.

  Returns:
    (stages, totalExecutorSummary).

  Raises:
    ValueError: If the file is missing or not valid JSON.
  """
  if not os.path.exists(path):
    raise ValueError(f"telemetry file not found: {path}")
  try:
    with open(path, "r") as f:
      data = json.load(f)
  except (OSError, ValueError, json.JSONDecodeError) as e:
    raise ValueError(f"could not parse {path}: {e}") from e
  if isinstance(data, list):
    return data, {}
  if isinstance(data, dict):
    executors = _get(data, "total_executor_summary", None) or {}
    for key in ("stages", "spark_application_stages"):
      stages = _get(data, key, None)
      if isinstance(stages, list):
        return stages, executors
    return [data], executors
  return [], {}


def _print_markdown(
    output: Dict[str, Any],
    violations: List[Dict[str, Any]],
    rules_count: int,
    stages_count: int,
    app_id: Optional[str],
) -> None:
  """Renders the report for a human or an agent reading markdown."""
  print("# Spark Stage Diagnostics Report\n")
  if app_id:
    print(f"- **Spark Application**: `{app_id}`")
  print(f"- **Status**: {output['status']}")
  skipped = count_skipped_rules(output.get("warnings") or [])
  print(
      f"- **Rules Evaluated**: {rules_count - skipped}"
      + (f" ({skipped} skipped, see Warnings)" if skipped else "")
  )
  print(f"- **Total Stages Analyzed**: {stages_count}")
  print(f"- **Total Diagnostic Violations Detected**: {len(violations)}")
  summary = output.get("summary")
  if summary:
    print(
        f"- **Tasks**: {summary['completedTasks']} completed,"
        f" {summary['failedTasks']} failed, {summary['killedTasks']} killed,"
        f" {summary['activeTasks']} active"
    )
    print(
        "- **Total Task Time**:"
        f" {spark_applications.human_millis(summary['totalDurationMs'])};"
        " **Input**:"
        f" {spark_applications.human_bytes(summary['totalInputBytes'])}"
    )
  print()

  if output.get("warnings"):
    print("### Warnings\n")
    for warning in output["warnings"]:
      print(f"- {warning}")
    print()

  if not violations:
    if not stages_count:
      print(
          "### Result: No stage telemetry was available. This is NOT a clean"
          " bill of health -- verify the batch ID and region, and confirm the"
          " batch has started executing stages."
      )
    else:
      print(
          "### Result: None of the supplied rules matched. Note that this only"
          " means the rules you provided did not fire; it is not a guarantee"
          " that the job is healthy."
      )
    return

  print("### Diagnostic Rule Violations Summary\n")
  for v in violations:
    print(f"#### [{v['ruleId']}] {v['description']}")
    print(f"- **Remediation / Recommendation**: {v['remediation']}")
    if v["scope"] == "application":
      print(f"- **Application-level finding**: {v.get('detail', '')}")
    else:
      print("- **Violating Stages**:")
      for vs in v["violating_stages"]:
        print(f"  - **Stage {vs['stage_id']}**: {vs['detail']}")
    print()

  if output["stageMetrics"]:
    h_ms, h_b = spark_applications.human_millis, spark_applications.human_bytes
    print("### Violating Stage Metrics\n")
    print(
        "| Stage | Tasks (killed) | Run time | GC | Input | Shuffle R/W |"
        " Output | Spill mem/disk | Task duration p50 / max |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for info in output["stageMetrics"]:
      m = info["stageMetrics"]
      q = (info["taskQuantiles"] or {}).get("durationMillis") or {}
      print(
          f"| {info['stageId']} | {info['numTasks']}"
          f" ({info['numKilledTasks']}) |"
          f" {h_ms(m['executorRunTimeMillis'])} |"
          f" {h_ms(m['jvmGcTimeMillis'])} | {h_b(m['inputBytesRead'])} |"
          f" {h_b(m['shuffleReadBytesRead'])} /"
          f" {h_b(m['shuffleWriteBytesWritten'])} |"
          f" {h_b(m['outputBytesWritten'])} |"
          f" {h_b(m['memoryBytesSpilled'])} / {h_b(m['diskBytesSpilled'])} |"
          f" {h_ms(q.get('percentile50')) if q else 'n/a'} /"
          f" {h_ms(q.get('maximum')) if q else 'n/a'} |"
      )


def main(argv: Optional[List[str]] = None) -> int:
  parser = argparse.ArgumentParser(
      description=(
          "Evaluates Python-expression diagnostic rules against Spark stage"
          " data from the Dataproc sparkApplications API."
          " Applies no rules or thresholds of its own: supply them with"
          " --rules_file or --custom_rule. See"
          " references/diagnostic_rules_catalog.md for the data model,"
          " authoring guidelines and examples."
      )
  )
  spark_applications.add_workload_arguments(parser)
  parser.add_argument(
      "--telemetry_file",
      help="Local JSON file containing exported stage telemetry",
  )
  parser.add_argument(
      "--rules_file",
      help="Path to a JSON file containing a list of diagnostic rules",
  )
  parser.add_argument(
      "--custom_rule",
      help="JSON string (or file path) containing a list of diagnostic rules",
  )
  parser.add_argument(
      "--format",
      choices=["markdown", "json"],
      default="markdown",
      help="markdown report, or the agent's JSON Output shape",
  )

  args = parser.parse_args(argv)

  # Resolve rules before fetching telemetry: with no rules there is nothing to
  # evaluate, and failing first avoids a pointless API round trip.
  rules: List[Dict[str, Any]] = []
  for value, flag in (
      (args.rules_file, "--rules_file"),
      (args.custom_rule, "--custom_rule"),
  ):
    if not value:
      continue
    try:
      rules.extend(_load_rules(value, flag))
    except ValueError as e:
      print(f"Error: {e}", file=sys.stderr)
      return 1

  if not rules:
    # Returning "no violations" here would be actively misleading: it reads as
    # a clean bill of health when in fact nothing was ever checked.
    print(
        "Error: no diagnostic rules supplied. This tool applies no rules or"
        " thresholds of its own, because what counts as unhealthy depends on"
        " the workload.\n"
        "Pass rules with --rules_file <file.json> or --custom_rule"
        " '[{...}]'.\n"
        "See references/diagnostic_rules_catalog.md for authoring guidelines"
        " and worked examples.",
        file=sys.stderr,
    )
    return 1

  app_id: Optional[str] = None
  stages: List[Dict[str, Any]] = []
  executors: Dict[str, Any] = {}
  try:
    if args.telemetry_file:
      stages, executors = _load_telemetry_file(args.telemetry_file)
    elif args.batch_id or args.session_id:
      app_id, stages, executors = fetch_workload_stages(
          spark_applications.build_client(args), args.application_id
      )
    else:
      raise ValueError(
          "Specify one of --batch_id, --session_id or --telemetry_file"
      )
  except (spark_applications.DataprocApiError, ValueError) as e:
    if args.format == "json":
      print(
          json.dumps(
              build_diagnostics_output([], [], error_message=str(e)), indent=2
          )
      )
    else:
      print(f"Error: {e}", file=sys.stderr)
    return 1

  warnings: List[str] = []
  if not stages:
    # The Data Worker Agent reports PASS here too, but a Spark application
    # with no stages usually failed before its first action, so the evidence
    # is in the driver log, not in stage metrics. Say so explicitly.
    warnings.append(
        "No stage telemetry was available, so stage rules had nothing to"
        " match; PASS does not mean healthy. The application probably failed"
        " before running a Spark action -- read the driver log instead."
    )
  violations = evaluate_stage_rules(stages, rules, executors, warnings)
  output = build_diagnostics_output(
      stages, violations, executors, warnings=warnings
  )

  if args.format == "json":
    print(json.dumps({"applicationId": app_id, **output}, indent=2))
  else:
    _print_markdown(output, violations, len(rules), len(stages), app_id)
  return 0


if __name__ == "__main__":
  sys.exit(main())
