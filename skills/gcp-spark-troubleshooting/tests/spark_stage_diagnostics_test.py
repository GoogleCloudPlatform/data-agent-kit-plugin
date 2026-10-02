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

"""Unit tests for spark_stage_diagnostics."""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_stage_diagnostics

# Illustrative rules used only by these tests. They are examples of the
# authoring format, not recommended thresholds: real thresholds depend on the
# workload, which is why the evaluator ships none of its own.
_GC_RULE = {
    "ruleId": "EXAMPLE_GC_PRESSURE",
    "description": "GC time is a large share of executor run time",
    "remediation": "Raise executor memory or cache less data.",
    "expression": (
        'ratio(s["stage_metrics.jvm_gc_time_millis"], '
        's["stage_metrics.executor_run_time_millis"]) > 0.10'
    ),
}
_INPUT_SKEW_RULE = {
    "ruleId": "EXAMPLE_INPUT_SKEW",
    "description": "Largest input partition far exceeds the median",
    "expression": (
        'ratio(s["task_quantile_metrics.input_metrics.bytes_read.maximum"], '
        's["task_quantile_metrics.input_metrics.bytes_read.percentile_50"])'
        " > 5"
    ),
}


class SparkStageDiagnosticsTest(unittest.TestCase):

  def test_no_rules_means_no_violations(self):
    """With no rules there is nothing to evaluate.

    `main()` treats this as a fatal error rather than a clean bill of health;
    the library function simply reports nothing.
    """
    stage = [{"stage_id": 0, "num_failed_tasks": 99}]

    self.assertEqual(spark_stage_diagnostics.evaluate_stage_rules(stage), [])
    self.assertEqual(
        spark_stage_diagnostics.evaluate_stage_rules(stage, []), []
    )

  def test_matching_rule_reports_violation_with_metadata(self):
    stage = [{
        "stage_id": 1,
        "stage_metrics": {
            "executor_run_time_millis": 100000,
            "jvm_gc_time_millis": 25000,  # 25%
        },
    }]

    violations = spark_stage_diagnostics.evaluate_stage_rules(stage, [_GC_RULE])

    self.assertEqual(len(violations), 1)
    self.assertEqual(violations[0]["ruleId"], "EXAMPLE_GC_PRESSURE")
    self.assertEqual(violations[0]["remediation"], _GC_RULE["remediation"])
    self.assertEqual(violations[0]["violating_stages"][0]["stage_id"], 1)

  def test_non_matching_rule_is_silent(self):
    stage = [{
        "stage_id": 2,
        "stage_metrics": {
            "executor_run_time_millis": 100000,
            "jvm_gc_time_millis": 1000,  # 1%
        },
    }]

    self.assertEqual(
        spark_stage_diagnostics.evaluate_stage_rules(stage, [_GC_RULE]), []
    )

  def _to_camel_case(self, obj):
    """Recursively rewrites dict keys into the REST API's camelCase form."""
    if isinstance(obj, dict):
      return {
          spark_stage_diagnostics._snake_to_camel(k): self._to_camel_case(v)  # pylint: disable=protected-access
          for k, v in obj.items()
      }
    if isinstance(obj, list):
      return [self._to_camel_case(v) for v in obj]
    return obj

  def test_camel_case_payload_yields_identical_violations(self):
    """The Dataproc REST API returns camelCase; gcloud/protos return snake_case.

    Both spellings must produce the same diagnosis. Quantile lookups once
    lacked a camelCase fallback, which silently disabled skew rules against
    real API responses.
    """
    stage = {
        "stage_id": 3,
        "stage_metrics": {
            "executor_run_time_millis": 100000,
            "jvm_gc_time_millis": 25000,
        },
        "task_quantile_metrics": {
            "input_metrics": {
                "bytes_read": {
                    "percentile_50": 50 * 1024 * 1024,
                    "maximum": 1000 * 1024 * 1024,  # 20x
                }
            },
        },
    }
    rules = [_GC_RULE, _INPUT_SKEW_RULE]

    snake_ids = {
        v["ruleId"]
        for v in spark_stage_diagnostics.evaluate_stage_rules([stage], rules)
    }
    camel_ids = {
        v["ruleId"]
        for v in spark_stage_diagnostics.evaluate_stage_rules(
            [self._to_camel_case(stage)], rules
        )
    }

    self.assertEqual(snake_ids, camel_ids)
    # Guard against both spellings being equally (and silently) broken.
    self.assertIn("EXAMPLE_GC_PRESSURE", camel_ids)
    self.assertIn("EXAMPLE_INPUT_SKEW", camel_ids)

  def test_camel_case_telemetry_reads_as_snake_case_paths(self):
    stage = {
        "stageId": 9,
        "stageMetrics": {
            "executorRunTimeMillis": 1000,
            "jvmGcTimeMillis": 900,
        },
    }
    rules = [{
        "ruleId": "EXAMPLE_STRICT_GC_CHECK",
        "description": "GC ratio above 15%",
        "expression": (
            's["stage_metrics.jvm_gc_time_millis"] / '
            's["stage_metrics.executor_run_time_millis"] > 0.15'
        ),
    }]

    violations = spark_stage_diagnostics.evaluate_stage_rules([stage], rules)
    self.assertIn("EXAMPLE_STRICT_GC_CHECK", {v["ruleId"] for v in violations})

  def test_detail_expression_renders_measured_values(self):
    """Findings should quote the numbers that triggered them.

    A bare "rule matched" is not actionable; the operator needs the value.
    """
    stage = [{
        "stage_id": 4,
        "stage_metrics": {"memory_bytes_spilled": 2 * 1024 * 1024 * 1024},
    }]
    rules = [{
        "ruleId": "EXAMPLE_SPILL",
        "description": "Stage spilled memory",
        "expression": 's["stage_metrics.memory_bytes_spilled"] > 0',
        "detail": """f'{gb(s["stage_metrics.memory_bytes_spilled"])} GiB'""",
    }]

    violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)
    self.assertEqual(violations[0]["violating_stages"][0]["detail"], "2.0 GiB")

  def test_broken_detail_expression_still_reports_the_finding(self):
    """A cosmetic failure must not suppress a real finding."""
    stage = [{"stage_id": 5, "num_failed_tasks": 3}]
    rules = [{
        "ruleId": "EXAMPLE_FAILURES",
        "description": "Tasks failed",
        "expression": 's["num_failed_tasks"] > 0',
        "detail": "this is not valid Python (",
    }]

    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)

    self.assertEqual(
        violations[0]["violating_stages"],
        [{"stage_id": 5, "detail": "Rule expression matched."}],
    )
    self.assertIn("detail of rule 'EXAMPLE_FAILURES'", err.getvalue())
    self.assertIn("invalid Python expression", err.getvalue())

  def test_detail_errors_are_reported(self):
    stage = [{"stage_id": 5, "num_failed_tasks": 3}]
    for detail, message in (
        ('str(s["num_failed_tasks"] / 0)', "ZeroDivisionError"),
        ('s["num_failed"]', "did you mean num_failed_tasks"),
        (7, "'detail' must be an expression string"),
    ):
      rules = [{
          "ruleId": "R",
          "expression": 's["num_failed_tasks"] > 0',
          "detail": detail,
      }]
      with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
        violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)
      self.assertEqual(_ids(violations), {"R": [5]}, detail)
      self.assertIn(message, err.getvalue(), detail)

  def test_absent_section_has_no_keys_and_zero_scalar_is_zero(self):
    stage = {"stageId": 11, "stageMetrics": {"memoryBytesSpilled": 0}}
    rules = [
        {
            "ruleId": "SCALAR",
            "expression": 's["stage_metrics.memory_bytes_spilled"]',
        },
        {
            "ruleId": "MESSAGE",
            "expression": 'any(k.startswith("stage_metrics.") for k in s)',
        },
        {
            "ruleId": "ABSENT",
            "expression": (
                'any(k.startswith("task_quantile_metrics.") for k in s)'
            ),
        },
    ]

    violations = spark_stage_diagnostics.evaluate_stage_rules([stage], rules)
    self.assertEqual(_ids(violations), {"MESSAGE": [11]})

  def test_malformed_rule_is_skipped_not_fatal(self):
    """One broken rule must not take down the rest of the run."""
    stage = [{
        "stage_id": 1,
        "stage_metrics": {
            "executor_run_time_millis": 100000,
            "jvm_gc_time_millis": 25000,
        },
    }]
    rules = [
        {
            "ruleId": "BROKEN",
            "description": "Unknown field",
            "expression": '[x["nope"].deeper for x in stages]',
        },
        _GC_RULE,
    ]

    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)

    rule_ids = {v["ruleId"] for v in violations}
    self.assertNotIn("BROKEN", rule_ids)
    self.assertIn("EXAMPLE_GC_PRESSURE", rule_ids)
    self.assertIn("BROKEN", err.getvalue())

  def test_rule_without_expression_is_skipped_with_warning(self):
    stage = [{"stage_id": 1, "num_failed_tasks": 1}]
    rules = [{"ruleId": "NO_EXPRESSION", "description": "malformed"}]

    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)

    self.assertEqual(violations, [])
    self.assertIn("NO_EXPRESSION", err.getvalue())

  def test_unknown_field_is_reported(self):
    """A typo must not silently turn a rule into a no-op."""
    stage = [{"stage_id": 1, "stage_metrics": {"jvm_gc_time_millis": 5}}]
    for expression, message in (
        # A misspelled field: reported with the closest field.
        (
            's["stage_metrics.jvm_gc_ms"] > 0',
            "stage_metrics.jvm_gc_ms (did you mean"
            " stage_metrics.jvm_gc_time_millis?)",
        ),
        # An unknown leaf under a real message.
        ('s["stage_metrics.gc_millis"] > 0', "no stage has"),
        # A misspelled variable is refused before anything runs.
        ('stage["num_tasks"] > 0', "unknown name 'stage'"),
    ):
      rules = [{"ruleId": "TYPO", "expression": expression}]
      with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
        violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)
      self.assertEqual(violations, [], expression)
      self.assertIn(message, err.getvalue(), expression)

  def test_non_object_rules_and_missing_ids_are_handled(self):
    stage = [{"stage_id": 1, "num_tasks": 3}]
    rules = ['s["num_tasks"] > 0', {"expression": "True"}]
    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)
    self.assertEqual([v["ruleId"] for v in violations], ["UNNAMED_RULE_2"])
    self.assertIn("rule '#1'", err.getvalue())
    self.assertIn("must be a JSON object", err.getvalue())

  def test_broken_rule_is_reported_once_not_per_stage(self):
    stages = [{"stage_id": i} for i in range(5)]
    for expression in (
        's["nope"].deeper > (',
        's["num_tasks"] / s["stage_id"] > 1',
    ):
      rules = [{"ruleId": "BROKEN", "expression": expression}]

      with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
        spark_stage_diagnostics.evaluate_stage_rules(stages, rules)

      self.assertEqual(err.getvalue().count("BROKEN"), 1, expression)


# Stages shaped exactly like `searchStages` REST output: camelCase, int64 as
# strings, zero-valued fields omitted (stage 0 has no `stageId`).
_API_STAGES = [
    {  # Stage 0: healthy; every metric omitted except run time.
        "status": "STAGE_STATUS_COMPLETE",
        "numTasks": 2,
        "stageMetrics": {"executorRunTimeMillis": "1000"},
    },
    {  # Stage 1: GC heavy, spills, skewed task durations.
        "stageId": "1",
        "status": "STAGE_STATUS_COMPLETE",
        "numTasks": 8,
        "stageMetrics": {
            "executorRunTimeMillis": "1000",
            "jvmGcTimeMillis": "200",
            "memoryBytesSpilled": "10",
            "diskBytesSpilled": "5",
        },
        "taskQuantileMetrics": {
            "durationMillis": {
                "count": "8",
                "minimum": "1",
                "percentile50": "10",
                "maximum": "100",
                "sum": "200",
            },
        },
    },
    {  # Stage 2: failed tasks; no quantiles.
        "stageId": "2",
        "status": "STAGE_STATUS_FAILED",
        "numTasks": 4,
        "numFailedTasks": 4,
        "numKilledTasks": 1,
    },
]
_EXECUTORS = {
    "totalDurationMillis": "5000",
    "totalInputBytes": "2048",
    "completedTasks": 10,
    "failedTasks": 4,
    "totalGcTimeMillis": "1000",
}


def _ids(violations):
  return {
      v["ruleId"]: sorted(vs["stage_id"] for vs in v["violating_stages"])
      for v in violations
  }


class RuleSemanticsTest(unittest.TestCase):
  """Result semantics of per-stage and application rules, on REST payloads."""

  def _evaluate(self, expression, stages=None, executors=None, **extra):
    rule = {"ruleId": "R", "expression": expression, **extra}
    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(
          _API_STAGES if stages is None else stages,
          [rule],
          _EXECUTORS if executors is None else executors,
      )
    return violations, err.getvalue()

  def test_per_stage_rule_flags_matching_stages(self):
    violations, err = self._evaluate(
        's["stage_metrics.executor_run_time_millis"] > 0 and '
        's["stage_metrics.jvm_gc_time_millis"] / '
        's["stage_metrics.executor_run_time_millis"] > 0.1'
    )
    self.assertEqual(err, "")
    self.assertEqual(_ids(violations), {"R": [1]})
    self.assertEqual(violations[0]["scope"], "stage")

  def test_list_of_stages_flags_those_stages(self):
    violations, err = self._evaluate(
        '[x for x in stages if x["stage_metrics.memory_bytes_spilled"] > 0]'
    )
    self.assertEqual(err, "")
    self.assertEqual(_ids(violations), {"R": [1]})

  def test_absent_stage_id_reads_as_zero(self):
    violations, _ = self._evaluate('s["num_tasks"] == 2')
    self.assertEqual(_ids(violations), {"R": [0]})

  def test_absent_fields_read_as_proto_defaults_without_errors(self):
    violations, err = self._evaluate(
        's["stage_metrics.stage_input_metrics.bytes_read"] + '
        's["stage_metrics.stage_shuffle_read_metrics.bytes_read"] > 0 and '
        'ratio(s["stage_metrics.stage_output_metrics.bytes_written"], '
        's["stage_metrics.stage_input_metrics.bytes_read"]) > 10'
    )
    # No stage has these fields, but they are real Dataproc fields: no warning.
    self.assertEqual((violations, err), ([], ""))
    violations, err = self._evaluate(
        's["name"] == \'\' and s["parent_stage_ids"] == [] and '
        's["completion_time"] is None'
    )
    self.assertEqual((_ids(violations), err), ({"R": [0, 1, 2]}, ""))

  def test_true_is_an_application_level_violation(self):
    violations, _ = self._evaluate(
        'any(x["num_failed_tasks"] > 0 and x["num_tasks"] != 0 for x in stages)'
    )
    self.assertEqual(len(violations), 1)
    self.assertEqual(violations[0]["scope"], "application")
    self.assertEqual(violations[0]["violating_stages"], [])

  def test_false_and_empty_list_are_not_violations(self):
    for expression in (
        "False",
        '[x for x in stages if x["num_tasks"] > 999]',
        "[]",
        's["num_tasks"] > 999',
    ):
      violations, err = self._evaluate(expression)
      self.assertEqual((violations, err), ([], ""), expression)

  def test_stage_id_list_is_mapped_to_stages(self):
    violations, _ = self._evaluate(
        '[x["stage_id"] for x in stages if x["num_failed_tasks"] > 0]',
        detail="""f'{s["num_failed_tasks"]} failed'""",
    )
    self.assertEqual(
        violations[0]["violating_stages"],
        [{"stage_id": 2, "detail": "4 failed"}],
    )

  def test_generator_result_is_accepted(self):
    violations, _ = self._evaluate(
        '(x for x in stages if x["num_failed_tasks"] > 0)'
    )
    self.assertEqual(_ids(violations), {"R": [2]})

  def test_list_without_stages_is_an_unattributed_violation(self):
    violations, _ = self._evaluate('[x["name"] for x in stages]')
    self.assertEqual(len(violations), 1)
    self.assertEqual(violations[0]["scope"], "application")
    self.assertIn("3 value(s)", violations[0]["detail"])

  def test_non_bool_non_list_result_is_reported(self):
    violations, err = self._evaluate("len(stages)")
    self.assertEqual(violations, [])
    self.assertIn("must yield a bool or a list", err)

  def test_evaluation_error_skips_the_rule(self):
    violations, err = self._evaluate(
        's["num_tasks"] / s["num_failed_tasks"] > 1'
    )
    self.assertEqual(violations, [])
    self.assertIn("ZeroDivisionError", err)

  def test_status_compares_as_the_enum_name(self):
    violations, err = self._evaluate('s["status"] == \'STAGE_STATUS_FAILED\'')
    self.assertEqual(err, "")
    self.assertEqual(_ids(violations), {"R": [2]})

  def test_application_scope_rule_uses_total_executor_summary(self):
    violations, _ = self._evaluate(
        'ratio(total_executor_summary["total_gc_time_millis"], '
        'total_executor_summary["total_duration_millis"]) > 0.1',
        detail=(
            """f'{100 * total_executor_summary["total_gc_time_millis"] //"""
            """ total_executor_summary["total_duration_millis"]}%'"""
        ),
    )
    self.assertEqual(len(violations), 1)
    self.assertEqual(violations[0]["scope"], "application")
    self.assertEqual(violations[0]["detail"], "20%")

  def test_stage_detail_is_not_rendered_for_application_findings(self):
    violations, _ = self._evaluate(
        "len(stages) > 0", detail="""f'{s["num_tasks"]} tasks'"""
    )
    self.assertEqual(violations[0]["detail"], "Rule expression matched.")

  def test_per_stage_rule_can_compare_against_all_stages(self):
    violations, err = self._evaluate(
        's["num_tasks"] == max(x["num_tasks"] for x in stages)'
    )
    self.assertEqual(err, "")
    self.assertEqual(_ids(violations), {"R": [1]})

  def test_no_built_in_rules(self):
    self.assertFalse(hasattr(spark_stage_diagnostics, "DEFAULT_RULES"))

  def test_warnings_are_collected(self):
    warnings = []
    with mock.patch("sys.stderr", new_callable=io.StringIO):
      spark_stage_diagnostics.evaluate_stage_rules(
          _API_STAGES, [{"ruleId": "BAD", "expression": "1 +"}], None, warnings
      )
    self.assertEqual(len(warnings), 1)
    self.assertIn("'BAD'", warnings[0])


# A synthetic application with one stage per issue in the "Top Spark Issues"
# catalog (REST shape: camelCase, int64 strings, zero values omitted).
_CATALOG_STAGES = [
    {"numTasks": 2, "stageMetrics": {"executorRunTimeMillis": "1000"}},
    {  # GC heavy, spills, 10x duration skew over 8 tasks.
        "stageId": "1",
        "numTasks": 8,
        "stageMetrics": {
            "executorRunTimeMillis": "1000",
            "jvmGcTimeMillis": "200",
            "memoryBytesSpilled": "10",
            "diskBytesSpilled": "5",
        },
        "taskQuantileMetrics": {
            "durationMillis": {"percentile50": "10", "maximum": "100"}
        },
    },
    {  # Failed and killed tasks.
        "stageId": "2",
        "status": "STAGE_STATUS_FAILED",
        "numTasks": 4,
        "numFailedTasks": 4,
        "numKilledTasks": 1,
    },
    {  # Long-tail data skew on 50 tasks; 2 GiB disk spill; input skew.
        "stageId": "3",
        "numTasks": 50,
        "stageMetrics": {"diskBytesSpilled": "2147483648"},
        "taskQuantileMetrics": {
            "durationMillis": {"percentile50": "10000", "maximum": "100000"},
            "inputMetrics": {
                "bytesRead": {"percentile50": "10", "maximum": "100"}
            },
        },
    },
    {  # Shuffle-heavy: write imbalance, slow shuffle writes, 25 kills.
        "stageId": "4",
        "numTasks": 20,
        "numKilledTasks": 25,
        "stageMetrics": {
            "executorRunTimeMillis": "1000",
            "stageShuffleReadMetrics": {"bytesRead": "1000"},
            "stageShuffleWriteMetrics": {"writeTimeNanos": "200000000"},
        },
        "taskQuantileMetrics": {
            "shuffleWriteMetrics": {
                "writeBytes": {"percentile50": "100", "maximum": "1000"}
            }
        },
    },
    {  # 12k tiny tasks.
        "stageId": "5",
        "numTasks": 12000,
        "taskQuantileMetrics": {
            "durationMillis": {"percentile50": "50", "maximum": "60"}
        },
    },
    {  # 90k-task scan.
        "stageId": "6",
        "numTasks": 90000,
        "stageMetrics": {"stageInputMetrics": {"bytesRead": "100"}},
    },
    {  # Under-partitioned spill with 20x duration skew over 10 tasks.
        "stageId": "7",
        "numTasks": 10,
        "stageMetrics": {"diskBytesSpilled": "100"},
        "taskQuantileMetrics": {
            "durationMillis": {"percentile50": "1", "maximum": "20"}
        },
    },
]

_DURATION_SKEW = (
    'ratio({v}["task_quantile_metrics.duration_millis.maximum"], '
    '{v}["task_quantile_metrics.duration_millis.percentile_50"]) > 5'
)
_INPUT_SKEW = (
    'ratio({v}["task_quantile_metrics.input_metrics.bytes_read.maximum"], '
    '{v}["task_quantile_metrics.input_metrics.bytes_read.percentile_50"]) > 5'
)

# The example rules of references/diagnostic_rules_catalog.md, with the stages
# each must flag on `_CATALOG_STAGES`. Test data only: the evaluator ships no
# rules.
_CATALOG_EXAMPLES = {
    "DATA_SKEW_DURATION_VARIANCE": (
        (
            's["task_quantile_metrics.duration_millis.maximum"] > 60000 and '
            'ratio(s["task_quantile_metrics.duration_millis.maximum"], '
            's["task_quantile_metrics.duration_millis.percentile_50"]) > 4'
        ),
        [3],
    ),
    "EXECUTOR_MEMORY_PRESSURE_SPILL": (
        (
            's["stage_metrics.memory_bytes_spilled"] > 0 or '
            's["stage_metrics.disk_bytes_spilled"] > 0'
        ),
        [1, 3, 7],
    ),
    "HIGH_GC_OVERHEAD": (
        (
            'ratio(s["stage_metrics.jvm_gc_time_millis"], '
            's["stage_metrics.executor_run_time_millis"]) > 0.15'
        ),
        [1],
    ),
    "EXECUTOR_OOM_LOST_EXECUTORS": ('s["num_killed_tasks"] > 0', [2, 4]),
    "SHUFFLE_IMBALANCE_FETCH_HEAVY": (
        (
            's["stage_metrics.stage_shuffle_read_metrics.bytes_read"] > 0 and '
            "ratio("
            's["task_quantile_metrics.shuffle_write_metrics.write_bytes'
            '.maximum"], s["task_quantile_metrics.shuffle_write_metrics'
            '.write_bytes.percentile_50"]) > 4'
        ),
        [4],
    ),
    "STRAGGLER_TASKS_LONG_TAIL": (
        's["num_tasks"] > 10 and ' + _DURATION_SKEW.format(v="s"),
        [3],
    ),
    "DYNAMIC_ALLOCATION_THRASHING": ('s["num_killed_tasks"] > 20', [4]),
    "EXCESSIVE_DISK_SPILL": (
        'gb(s["stage_metrics.disk_bytes_spilled"]) > 1',
        [3],
    ),
    "UNDERPARTITIONED_SPILL": (
        's["stage_metrics.disk_bytes_spilled"] > 0 and s["num_tasks"] < 50',
        [1, 7],
    ),
    "TOO_MANY_SMALL_TASKS": (
        (
            's["num_tasks"] > 10000 and '
            '0 < s["task_quantile_metrics.duration_millis.percentile_50"] < 100'
        ),
        [5],
    ),
    "DRIVER_BOTTLENECK_FAILURE": ('s["num_failed_tasks"] > 0', [2]),
    "SERIALIZATION_SHUFFLE_WRITE_BOTTLENECK": (
        (
            "ratio("
            's["stage_metrics.stage_shuffle_write_metrics.write_time_nanos"]'
            ' / 1e6, s["stage_metrics.executor_run_time_millis"]) > 0.1'
        ),
        [4],
    ),
    "HIGH_SCAN_TASK_COUNT_STARVATION": (
        (
            's["stage_metrics.stage_shuffle_read_metrics.bytes_read"] == 0 '
            'and s["stage_metrics.stage_input_metrics.bytes_read"] > 0 and '
            's["num_tasks"] > 80000'
        ),
        [6],
    ),
    "COMPOSITE_TRIAGE_ENTRY_POINT": (
        (
            's["num_failed_tasks"] > 0 or s["num_killed_tasks"] > 0 or '
            's["stage_metrics.disk_bytes_spilled"] > 0 or '
            's["stage_metrics.memory_bytes_spilled"] > 0 or '
            'ratio(s["stage_metrics.jvm_gc_time_millis"], '
            's["stage_metrics.executor_run_time_millis"]) > 0.15'
        ),
        [1, 2, 3, 4, 7],
    ),
    # Correlated signals.
    "CLEAR_DATA_SKEW": (
        _DURATION_SKEW.format(v="s") + " and " + _INPUT_SKEW.format(v="s"),
        [3],
    ),
    "NON_DATA_SKEW_BOTTLENECK": (
        (
            f"[x for x in stages if {_DURATION_SKEW.format(v='x')}"
            f" and not ({_INPUT_SKEW.format(v='x')})]"
        ),
        [1, 7],
    ),
    "ANY_STAGE_SEVERELY_FAILED": (
        'any(x["num_failed_tasks"] > 3 for x in stages)',
        [],
    ),
}


class FlatRecordTest(unittest.TestCase):

  def test_flatten_uses_dotted_snake_case_paths(self):
    flat = spark_stage_diagnostics.flatten({
        "stageId": 3,
        "stageMetrics": {"stageInputMetrics": {"bytesRead": 7}},
        "taskQuantileMetrics": {"durationMillis": {"percentile50": 5}},
        "executorSummary": {"12": {"failedTasks": 2}},
        "locality": {"PROCESS_LOCAL": 4},
        "parentStageIds": [1, 2],
    })
    self.assertEqual(flat["stage_id"], 3)
    self.assertEqual(flat["stage_metrics.stage_input_metrics.bytes_read"], 7)
    self.assertEqual(
        flat["task_quantile_metrics.duration_millis.percentile_50"], 5
    )
    # Map fields keep their data keys.
    self.assertEqual(flat["executor_summary"], {"12": {"failed_tasks": 2}})
    self.assertEqual(flat["locality"], {"PROCESS_LOCAL": 4})
    self.assertEqual(flat["parent_stage_ids"], [1, 2])

  def test_time_fields_become_datetimes(self):
    flat = spark_stage_diagnostics.flatten({
        "submissionTime": "2026-01-01T00:00:00.000Z",
        "completionTime": "2026-01-01T00:01:30.500Z",
    })
    self.assertEqual(
        (flat["completion_time"] - flat["submission_time"]).total_seconds(),
        90.5,
    )

  def test_absent_fields_read_as_typed_defaults(self):
    reads = set()
    record = spark_stage_diagnostics.Fields({}, reads)
    self.assertEqual(record["stage_id"], 0)
    self.assertEqual(record["stage_metrics.jvm_gc_time_millis"], 0)
    self.assertEqual(record["failure_reason"], "")
    self.assertEqual(record["status"], "STAGE_STATUS_UNSPECIFIED")
    self.assertEqual(record["job_ids"], [])
    self.assertEqual(record["executor_summary"], {})
    self.assertIsNone(record["completion_time"])
    self.assertIn("stage_metrics.jvm_gc_time_millis", reads)
    # Defaults are fresh copies, never shared between reads.
    record["job_ids"].append(1)
    self.assertEqual(record["job_ids"], [])

  def test_string_rules_work_on_absent_fields(self):
    stages = [
        {"stageId": 1, "failureReason": "java.lang.OutOfMemoryError"},
        {"stageId": 2},
    ]
    rules = [{
        "ruleId": "OOM",
        "expression": "'OutOfMemory' in s['failure_reason']",
    }]
    violations = spark_stage_diagnostics.evaluate_stage_rules(stages, rules)
    self.assertEqual(_ids(violations), {"OOM": [1]})


class CatalogExamplesTest(unittest.TestCase):
  """Every example rule in the catalog runs and flags the expected stages."""

  def test_examples_flag_the_expected_stages(self):
    rules = [
        {"ruleId": rule_id, "description": rule_id, "expression": expression}
        for rule_id, (expression, _) in _CATALOG_EXAMPLES.items()
    ]
    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(
          _CATALOG_STAGES, rules, _EXECUTORS
      )
    self.assertEqual(err.getvalue(), "")
    self.assertEqual(
        _ids(violations),
        {
            rule_id: expected
            for rule_id, (_, expected) in _CATALOG_EXAMPLES.items()
        },
    )
    by_rule = {v["ruleId"]: v for v in violations}
    self.assertEqual(
        by_rule["ANY_STAGE_SEVERELY_FAILED"]["scope"], "application"
    )


class DiagnosticsOutputTest(unittest.TestCase):

  def test_output_matches_agent_shape(self):
    rules = [
        {
            "ruleId": "FAILED",
            "description": "Failed tasks",
            "expression": 's["num_failed_tasks"] > 0',
        },
        {
            "ruleId": "SPILL",
            "description": "Spill",
            "expression": 's["stage_metrics.memory_bytes_spilled"] > 0',
        },
    ]
    violations = spark_stage_diagnostics.evaluate_stage_rules(
        _API_STAGES, rules, _EXECUTORS
    )

    out = spark_stage_diagnostics.build_diagnostics_output(
        _API_STAGES, violations, _EXECUTORS
    )

    self.assertEqual(out["status"], "FAIL")
    self.assertIsNone(out["errorMessage"])
    self.assertEqual(
        out["summary"],
        {
            "totalDurationMs": 5000,
            "totalInputBytes": 2048,
            "activeTasks": 0,
            "completedTasks": 10,
            "failedTasks": 4,
            "killedTasks": 1,
        },
    )
    first = out["violations"][0]
    self.assertEqual(
        set(first),
        {
            "ruleId",
            "description",
            "violatingStageIds",
            "remediation",
            "details",
        },
    )
    self.assertEqual(first["violatingStageIds"], [2])
    by_id = {s["stageId"]: s for s in out["stageMetrics"]}
    self.assertEqual(sorted(by_id), [1, 2])
    self.assertEqual(
        set(by_id[1]),
        {
            "stageId",
            "numTasks",
            "numKilledTasks",
            "stageMetrics",
            "taskQuantiles",
        },
    )
    self.assertEqual(by_id[1]["stageMetrics"]["jvmGcTimeMillis"], 200)
    self.assertEqual(by_id[1]["stageMetrics"]["inputBytesRead"], 0)
    self.assertEqual(
        by_id[1]["taskQuantiles"]["durationMillis"],
        {"minimum": 1, "percentile50": 10, "maximum": 100, "sum": 200},
    )
    self.assertIsNone(by_id[1]["taskQuantiles"]["inputBytes"])
    self.assertIsNone(by_id[2]["taskQuantiles"])
    json.dumps(out)  # Must be serializable.

  def test_pass_and_error(self):
    ok = spark_stage_diagnostics.build_diagnostics_output(_API_STAGES, [], {})
    self.assertEqual((ok["status"], ok["violations"]), ("PASS", []))
    err = spark_stage_diagnostics.build_diagnostics_output(
        [], [], error_message="boom"
    )
    self.assertEqual(
        err,
        {
            "status": "ERROR",
            "errorMessage": "boom",
            "violations": [],
            "stageMetrics": [],
            "summary": None,
            "warnings": [],
        },
    )

  def test_multi_attempt_stage_renders_attempt_specific_detail(self):
    stages = [
        {
            "stageId": 11,
            "stageAttemptId": 0,
            "status": "STAGE_STATUS_FAILED",
            "numTasks": 4,
            "numFailedTasks": 3,
        },
        {
            "stageId": 11,
            "stageAttemptId": 1,
            "status": "STAGE_STATUS_FAILED",
            "numTasks": 4,
            "numFailedTasks": 1,
        },
    ]
    rules = [{
        "ruleId": "MULTI_ATTEMPT",
        "description": "Failed stage attempts",
        "expression": 's["num_failed_tasks"] > 0',
        "detail": (
            """f'attempt={s["stage_attempt_id"]}"""
            """ failed={s["num_failed_tasks"]}'"""
        ),
    }]
    violations = spark_stage_diagnostics.evaluate_stage_rules(stages, rules)
    self.assertEqual(
        violations[0]["violating_stages"],
        [
            {"stage_id": 11, "detail": "attempt=0 failed=3"},
            {"stage_id": 11, "detail": "attempt=1 failed=1"},
        ],
    )


class _FakeClient:
  """Records calls; serves the telemetry of a two-page stage listing."""

  def __init__(self):
    self.calls = []

  def resolve_application(self, app_id=None):
    self.calls.append(("resolve", app_id))
    return app_id or "app-1", {}, 1

  def call(self, method, app_id=None, params=None):
    self.calls.append((method, app_id, params))
    return {"totalExecutorSummary": dict(_EXECUTORS)}

  def paginate(
      self, method, items_key, app_id=None, params=None, max_items=None
  ):
    self.calls.append((method, items_key, app_id, params, max_items))
    return list(_API_STAGES)


class FetchAndMainTest(unittest.TestCase):

  def test_fetch_follows_the_agent_call_sequence(self):
    client = _FakeClient()

    app_id, stages, executors = (
        spark_stage_diagnostics.fetch_workload_telemetry(client)
    )

    self.assertEqual(app_id, "app-1")
    self.assertEqual(len(stages), 3)
    self.assertEqual(executors, _EXECUTORS)
    self.assertEqual(
        client.calls,
        [
            ("resolve", None),
            ("summarizeExecutors", "app-1", None),
            (
                "searchStages",
                "sparkApplicationStages",
                "app-1",
                {
                    "pageSize": 100,
                    "summaryMetricsMask": "task_quantile_metrics",
                },
                None,
            ),
        ],
    )

  def test_fetch_errors_use_the_agent_wording(self):
    api_error = spark_stage_diagnostics.telemetry.DataprocApiError
    client = _FakeClient()
    client.workload_id = "batch-1"
    client.resolve_application = mock.Mock(
        side_effect=api_error("No Spark application found for x.", 404)
    )
    with self.assertRaises(api_error) as ctx:
      spark_stage_diagnostics.fetch_workload_telemetry(client)
    self.assertTrue(
        str(ctx.exception).startswith(
            "No Spark applications found for workload batch-1."
        )
    )

    client = _FakeClient()
    client.call = mock.Mock(
        side_effect=api_error("summarizeExecutors failed with HTTP 403", 403)
    )
    with self.assertRaises(api_error) as ctx:
      spark_stage_diagnostics.fetch_workload_telemetry(client)
    self.assertEqual(
        str(ctx.exception),
        "Failed to retrieve Spark diagnostics via public APIs:"
        " summarizeExecutors failed with HTTP 403",
    )
    self.assertEqual(ctx.exception.status, 403)

  def _main(self, argv):
    with mock.patch("sys.stdout", new_callable=io.StringIO) as out, mock.patch(
        "sys.stderr", new_callable=io.StringIO
    ) as err:
      code = spark_stage_diagnostics.main(argv)
    return code, out.getvalue(), err.getvalue()

  def _telemetry_file(self, payload):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, dir=self.create_tempdir_path()
    )
    with handle:
      json.dump(payload, handle)
    return handle.name

  def create_tempdir_path(self):
    path = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path

  def test_main_without_rules_is_an_error(self):
    code, _, err = self._main(["--telemetry_file", "/nonexistent"])
    self.assertEqual(code, 1)
    self.assertIn("no diagnostic rules supplied", err)

  def test_default_rules_flag_is_gone(self):
    with mock.patch("sys.stderr", new_callable=io.StringIO):
      with self.assertRaises(SystemExit):
        spark_stage_diagnostics.main(
            ["--telemetry_file", "/nonexistent", "--default_rules"]
        )

  def test_main_json_with_rules_file(self):
    path = self._telemetry_file({
        "sparkApplicationStages": _API_STAGES,
        "totalExecutorSummary": _EXECUTORS,
    })
    rules = self._telemetry_file([
        {
            "ruleId": "FAILED",
            "description": "Failed tasks",
            "expression": 's["num_failed_tasks"] > 0',
        },
        {"ruleId": "BROKEN", "expression": 's["nope"] > 0'},
    ])
    code, out, _ = self._main(
        ["--telemetry_file", path, "--rules_file", rules, "--format", "json"]
    )
    self.assertEqual(code, 0)
    payload = json.loads(out)
    self.assertEqual(payload["status"], "FAIL")
    self.assertEqual(payload["summary"]["failedTasks"], 4)
    self.assertEqual(
        [(v["ruleId"], v["violatingStageIds"]) for v in payload["violations"]],
        [("FAILED", [2])],
    )
    self.assertEqual(len(payload["warnings"]), 1)
    self.assertIn("BROKEN", payload["warnings"][0])

  def test_main_markdown_with_custom_rule(self):
    path = self._telemetry_file(_API_STAGES)
    rule = json.dumps([{
        "ruleId": "FAILED",
        "description": "Failed tasks",
        "expression": 's["num_failed_tasks"] > 0',
        "detail": """f'{s["num_failed_tasks"]} failed'""",
    }])
    code, out, _ = self._main(["--telemetry_file", path, "--custom_rule", rule])
    self.assertEqual(code, 0)
    self.assertIn("**Status**: FAIL", out)
    self.assertIn("[FAILED] Failed tasks", out)
    self.assertIn("**Stage 2**: 4 failed", out)
    self.assertIn("### Violating Stage Metrics", out)
    self.assertIn("| 2 | 4 (1) |", out)
    self.assertIn("**Rules Evaluated**: 1\n", out)

  def test_main_markdown_counts_skipped_rules(self):
    path = self._telemetry_file(_API_STAGES)
    rule = json.dumps([
        {"ruleId": "OK", "expression": 's["num_tasks"] > 0'},
        {"ruleId": "BAD", "expression": "s.num_tasks >"},
        {
            "ruleId": "BAD_DETAIL",
            "expression": 's["num_failed_tasks"] > 0',
            "detail": 's["num_tasks"] / 0',
        },
    ])
    code, out, _ = self._main(["--telemetry_file", path, "--custom_rule", rule])
    self.assertEqual(code, 0)
    self.assertIn("**Rules Evaluated**: 2 (1 skipped, see Warnings)", out)
    self.assertIn("rule 'BAD' could not be evaluated", out)
    self.assertIn("detail of rule 'BAD_DETAIL' could not be rendered", out)
    self.assertIn("**Stage 2**: Rule expression matched.", out)

  def test_main_zero_stages_passes_like_the_agent_but_warns(self):
    path = self._telemetry_file([])
    rule = json.dumps([{"ruleId": "R", "expression": 's["num_tasks"] > 0'}])
    code, out, _ = self._main(
        ["--telemetry_file", path, "--custom_rule", rule, "--format", "json"]
    )
    self.assertEqual(code, 0)
    payload = json.loads(out)
    self.assertEqual(payload["status"], "PASS")
    self.assertIn("No stage telemetry", payload["warnings"][0])
    code, out, _ = self._main(["--telemetry_file", path, "--custom_rule", rule])
    self.assertIn("NOT a clean bill of health", out)

  def test_main_fetch_error_prints_error_payload_in_json(self):
    with mock.patch.object(
        spark_stage_diagnostics,
        "fetch_workload_telemetry",
        side_effect=spark_stage_diagnostics.telemetry.DataprocApiError(
            "No Spark application found", 404
        ),
    ), mock.patch.object(spark_stage_diagnostics.telemetry, "build_client"):
      code, out, _ = self._main([
          "--batch_id",
          "b",
          "--project",
          "p",
          "--custom_rule",
          '[{"ruleId": "R", "expression": "True"}]',
          "--format",
          "json",
      ])
    self.assertEqual(code, 1)
    payload = json.loads(out)
    self.assertEqual(payload["status"], "ERROR")
    self.assertIn("No Spark application found", payload["errorMessage"])


if __name__ == "__main__":
  unittest.main()
