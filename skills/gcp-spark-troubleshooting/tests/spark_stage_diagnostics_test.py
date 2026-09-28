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
import os
import sys
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
        "ratio(s.stage_metrics.jvm_gc_time_millis,"
        " s.stage_metrics.executor_run_time_millis) > 0.10"
    ),
}
_INPUT_SKEW_RULE = {
    "ruleId": "EXAMPLE_INPUT_SKEW",
    "description": "Largest input partition far exceeds the median",
    "expression": (
        "ratio(s.task_quantile_metrics.input_metrics.bytes_read.maximum,"
        " s.task_quantile_metrics.input_metrics.bytes_read.percentile_50) > 5"
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

  def test_rule_accepts_dotted_paths_against_camel_case_payload(self):
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
            "has(s.stage_metrics) and"
            " double(s.stage_metrics.jvm_gc_time_millis) /"
            " double(s.stage_metrics.executor_run_time_millis) > 0.15"
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
        "expression": "s.stage_metrics.memory_bytes_spilled > 0",
        "detail": "str(gb(s.stage_metrics.memory_bytes_spilled)) + ' GiB'",
    }]

    violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)
    self.assertEqual(violations[0]["violating_stages"][0]["detail"], "2.0 GiB")

  def test_broken_detail_expression_still_reports_the_finding(self):
    """A cosmetic failure must not suppress a real finding."""
    stage = [{"stage_id": 5, "num_failed_tasks": 3}]
    rules = [{
        "ruleId": "EXAMPLE_FAILURES",
        "description": "Tasks failed",
        "expression": "s.num_failed_tasks > 0",
        "detail": "this is not valid python (",
    }]

    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      violations = spark_stage_diagnostics.evaluate_stage_rules(stage, rules)

    self.assertIn("EXAMPLE_FAILURES", {v["ruleId"] for v in violations})
    self.assertIn("detail", err.getvalue())

  def test_cel_has_treats_zero_as_present_but_empty_message_as_absent(self):
    """`has()` must not collapse into a plain truthiness check.

    CEL's has() macro asks whether a field is *set*, not whether it is
    non-zero. A stage that legitimately reports `0` spilled bytes is still
    reporting the field, so a rule guarded on `has(...)` must keep firing.
    Rewriting the guard as `bool(x)` would silently disable every such rule.
    """
    self.assertTrue(spark_stage_diagnostics._cel_has(0))
    self.assertTrue(spark_stage_diagnostics._cel_has(""))
    self.assertTrue(spark_stage_diagnostics._cel_has({"a": 1}))
    self.assertFalse(spark_stage_diagnostics._cel_has(None))
    self.assertFalse(spark_stage_diagnostics._cel_has({}))
    self.assertFalse(
        spark_stage_diagnostics._cel_has(spark_stage_diagnostics._CelView({}))
    )
    self.assertTrue(
        spark_stage_diagnostics._cel_has(
            spark_stage_diagnostics._CelView({"a": 1})
        )
    )

  def test_rule_guarded_on_has_fires_for_zero_valued_metric(self):
    stage = {"stageId": 11, "stageMetrics": {"memoryBytesSpilled": 0}}
    rules = [{
        "ruleId": "EXAMPLE_SPILL_FIELD_PRESENT",
        "description": "Spill metric reported at all",
        "expression": "has(s.stage_metrics.memory_bytes_spilled)",
    }]

    violations = spark_stage_diagnostics.evaluate_stage_rules([stage], rules)
    self.assertIn(
        "EXAMPLE_SPILL_FIELD_PRESENT", {v["ruleId"] for v in violations}
    )

  def test_ratio_helper_tolerates_zero_and_missing_operands(self):
    """Ratio rules must not abort on the very common zero denominator."""
    self.assertEqual(spark_stage_diagnostics._ratio(10, 0), 0.0)
    self.assertEqual(spark_stage_diagnostics._ratio(10, None), 0.0)
    self.assertEqual(spark_stage_diagnostics._ratio(None, 10), 0.0)
    self.assertEqual(spark_stage_diagnostics._ratio("x", 10), 0.0)
    self.assertEqual(spark_stage_diagnostics._ratio(10, 4), 2.5)

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
            "description": "Unsupported CEL macro",
            "expression": "stages.filter(x, x.nope)",
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

  def test_broken_rule_is_reported_once_not_per_stage(self):
    stages = [{"stage_id": i} for i in range(5)]
    rules = [{"ruleId": "BROKEN", "expression": "s.nope.deeper > ("}]

    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      spark_stage_diagnostics.evaluate_stage_rules(stages, rules)

    self.assertEqual(err.getvalue().count("BROKEN"), 1)


if __name__ == "__main__":
  unittest.main()
