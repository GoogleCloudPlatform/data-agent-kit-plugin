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

Evaluates caller-supplied expression rules over Dataproc Spark stage and
quantile metrics. The evaluator ships no built-in thresholds; see
`references/diagnostic_rules_catalog.md` for rule-authoring guidelines and
worked examples.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set


def _snake_to_camel(name: str) -> str:
  """Converts a snake_case proto field name to its JSON camelCase spelling."""
  head, *rest = name.split("_")
  return head + "".join(word.capitalize() for word in rest)


def _get(data: Any, key: str, default: Any = 0) -> Any:
  """Reads `key` from `data`, accepting either JSON spelling of the field.

  The Dataproc REST API emits camelCase field names (`taskQuantileMetrics`),
  while the protos and `gcloud ... --format=json` emit snake_case
  (`task_quantile_metrics`). Callers always pass the canonical snake_case proto
  name and this helper transparently falls back to the camelCase spelling, so a
  missing fallback can no longer silently disable a rule.

  Args:
    data: The mapping to read from. Non-mappings yield `default`.
    key: The canonical snake_case field name.
    default: Value returned when the field is absent under either spelling.

  Returns:
    The field value, or `default` if it is absent.
  """
  if not isinstance(data, dict):
    return default
  if key in data:
    return data[key]
  return data.get(_snake_to_camel(key), default)


class _CelView:
  """Read-only attribute view over a telemetry dict, for custom rules.

  Rules are conventionally written with dotted field paths, e.g.
  `s.stage_metrics.jvm_gc_time_millis > 0`. Plain dicts do not support
  attribute access, so such an expression would raise `AttributeError`. This
  wrapper accepts the dotted form, resolves either JSON spelling of each field
  via `_get`, and returns nested mappings as further views so arbitrarily deep
  paths work.

  Absent fields resolve to `None` rather than raising, so `has(s.foo)` behaves
  like the CEL macro and comparisons against a missing field fail the rule
  instead of aborting the run.
  """

  __slots__ = ("_data",)

  def __init__(self, data: Any):
    object.__setattr__(self, "_data", data if isinstance(data, dict) else {})

  def __getattr__(self, name: str) -> Any:
    value = _get(object.__getattribute__(self, "_data"), name, None)
    return _CelView(value) if isinstance(value, dict) else value

  def __getitem__(self, key: str) -> Any:
    return self.__getattr__(key)

  def __contains__(self, key: str) -> bool:
    return self.__getattr__(key) is not None

  def __bool__(self) -> bool:
    return bool(object.__getattribute__(self, "_data"))

  def __eq__(self, other: Any) -> bool:
    if isinstance(other, _CelView):
      other = object.__getattribute__(other, "_data")
    return object.__getattribute__(self, "_data") == other

  def __hash__(self) -> int:
    return id(self)

  def __repr__(self) -> str:
    return f"_CelView({object.__getattribute__(self, '_data')!r})"


def _cel_has(value: Any) -> bool:
  """Mirrors the CEL `has()` macro: true when a field is present and non-empty.

  Args:
    value: The resolved field value. Absent fields arrive as `None`.

  Returns:
    False for an absent field or an empty message, True otherwise. Scalars are
    always treated as present so that a legitimate `0` metric is never mistaken
    for a missing one.
  """
  if value is None:
    return False
  if isinstance(value, (dict, _CelView)):
    return bool(value)
  return True


def _ratio(numerator: Any, denominator: Any) -> float:
  """Divides two metrics, yielding 0.0 instead of raising on a zero divisor.

  Stage telemetry is full of legitimately-zero denominators (a stage that ran
  no tasks, read no bytes, or spent no time in GC). Without this helper every
  ratio rule would need its own guard clause, and a forgotten guard would abort
  the rule rather than simply not matching.

  Args:
    numerator: Dividend. `None` is treated as 0.
    denominator: Divisor. `None` or 0 yields 0.0.

  Returns:
    The quotient, or 0.0 when the divisor is absent or zero.
  """
  try:
    bottom = float(denominator or 0)
    if bottom == 0:
      return 0.0
    return float(numerator or 0) / bottom
  except (TypeError, ValueError):
    return 0.0


def _mb(num_bytes: Any) -> float:
  """Converts bytes to mebibytes for readable rule detail strings."""
  try:
    return round(float(num_bytes or 0) / (1024 * 1024), 2)
  except (TypeError, ValueError):
    return 0.0


def _gb(num_bytes: Any) -> float:
  """Converts bytes to gibibytes for readable rule detail strings."""
  try:
    return round(float(num_bytes or 0) / (1024 * 1024 * 1024), 2)
  except (TypeError, ValueError):
    return 0.0


def _rule_context(stage: Any) -> Dict[str, Any]:
  """Builds the namespace a rule expression is evaluated in.

  Args:
    stage: A single stage telemetry mapping.

  Returns:
    The variables and helper functions available to rule authors. Anything not
    listed here is unavailable to an expression, because builtins are withheld
    at evaluation time.
  """
  return {
      "s": _CelView(stage),
      "has": _cel_has,
      "ratio": _ratio,
      "mb": _mb,
      "gb": _gb,
      "double": float,
      "int": int,
      "str": str,
      "size": len,
      "abs": abs,
      "max": max,
      "min": min,
      "round": round,
  }


def _warn_once(seen: Set[str], rule_id: str, message: str) -> None:
  """Reports a broken rule once, to stderr.

  A rule that cannot be evaluated must never abort the run, but it must not be
  silently dropped either: an empty report would otherwise be misread as "no
  problems found".

  Args:
    seen: Rule IDs already reported; mutated in place.
    rule_id: The offending rule.
    message: Why it was skipped.
  """
  if rule_id in seen:
    return
  seen.add(rule_id)
  print(
      f"Warning: rule '{rule_id}' could not be evaluated and was skipped:"
      f" {message}",
      file=sys.stderr,
  )


def evaluate_stage_rules(
    stages: List[Dict[str, Any]],
    rules: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
  """Evaluates caller-supplied expression rules against stage telemetry.

  This evaluator deliberately ships no built-in rules or thresholds. What
  counts as "too much" GC, skew, or spill is workload-specific: a ratio that is
  healthy for a long-running ETL job is pathological for an interactive query.
  Baking in fixed numbers would produce confident-looking findings that are
  wrong for most jobs, so the caller always supplies the rules. See
  `references/diagnostic_rules_catalog.md` for authoring guidelines and
  worked examples.

  Args:
    stages: Stage telemetry mappings, in either snake_case or camelCase.
    rules: Rule objects. Each requires `ruleId` and `expression`. Optional
      `description` and `remediation` are echoed into the report, and an
      optional `detail` expression is evaluated per matching stage to render a
      human-readable explanation with the actual measured values.

  Returns:
    One entry per rule that matched at least one stage.
  """
  results = []
  failed_rule_ids: Set[str] = set()

  for rule in rules or []:
    rule_id = rule.get("ruleId", "UNNAMED_RULE")
    expression = rule.get("expression")
    if not expression:
      _warn_once(
          failed_rule_ids, rule_id, "rule is missing an 'expression' field"
      )
      continue

    detail_expr = rule.get("detail")
    violating_stages = []

    for s in stages:
      context_vars = _rule_context(s)
      try:
        # The expression comes from the operator's own rule input, not from
        # untrusted data. Builtins are withheld to limit blast radius, but
        # this is a convenience evaluator, not a security sandbox.
        # pylint: disable=eval-used
        matched = eval(expression, {"__builtins__": {}}, context_vars)
      except Exception as e:  # pylint: disable=broad-except
        # The rule is broken for every stage, not just this one, so stop
        # re-evaluating it rather than emitting the same warning N times.
        _warn_once(failed_rule_ids, rule_id, f"{type(e).__name__}: {e}")
        break

      if not matched:
        continue

      detail = "Rule expression matched."
      if detail_expr:
        try:
          # pylint: disable=eval-used
          detail = str(eval(detail_expr, {"__builtins__": {}}, context_vars))
        except Exception as e:  # pylint: disable=broad-except
          # A broken detail expression must not suppress the finding itself.
          _warn_once(
              failed_rule_ids,
              f"{rule_id} (detail)",
              f"{type(e).__name__}: {e}",
          )
          detail_expr = None

      violating_stages.append({
          "stage_id": _get(s, "stage_id", -1),
          "detail": detail,
      })

    if violating_stages:
      results.append({
          "ruleId": rule_id,
          "description": rule.get("description", ""),
          "remediation": rule.get(
              "remediation", "Review stage execution metrics."
          ),
          "violating_stages": violating_stages,
      })

  return results


def fetch_batch_telemetry_via_gcloud(
    batch_id: str, region: str
) -> List[Dict[str, Any]]:
  """Fetches Spark stages telemetry for a Dataproc batch using gcloud.

  Args:
    batch_id: The Dataproc Serverless batch ID.
    region: The GCP region hosting the batch.

  Returns:
    The list of stage telemetry dicts. May legitimately be empty for a batch
    that has not scheduled any stage yet.

  Raises:
    RuntimeError: If the batch could not be described or its payload could not
      be parsed. This is deliberately distinct from an empty result so that a
      failed fetch is never reported as a clean bill of health.
  """
  cmd = [
      "gcloud",
      "dataproc",
      "batches",
      "describe",
      batch_id,
      f"--region={region}",
      "--format=json",
  ]
  try:
    proc = subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=120
    )
  except (OSError, subprocess.SubprocessError) as e:
    raise RuntimeError(
        f"Could not run 'gcloud dataproc batches describe': {e}. Is the "
        "Google Cloud CLI installed and on PATH?"
    ) from e

  if proc.returncode != 0:
    detail = (proc.stderr or "").strip() or f"exit code {proc.returncode}"
    raise RuntimeError(
        f"Failed to describe batch '{batch_id}' in region '{region}': {detail}"
    )

  try:
    batch = json.loads(proc.stdout)
  except (ValueError, json.JSONDecodeError) as e:
    raise RuntimeError(
        f"Could not parse the JSON describing batch '{batch_id}': {e}"
    ) from e

  applications = batch.get("sparkApplications") or batch.get(
      "spark_applications"
  )
  if not applications:
    raise RuntimeError(
        f"Batch '{batch_id}' exposes no Spark application telemetry. The batch "
        "may still be pending, or the Persistent History Server may not be "
        "configured for it."
    )

  stages = _get(applications[0], "stages", None)
  return stages if isinstance(stages, list) else []


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


def main():
  parser = argparse.ArgumentParser(
      description=(
          "Evaluates user-supplied diagnostic rules against Spark stage"
          " telemetry. Ships no built-in thresholds: supply rules with"
          " --rules_file or --custom_rule. See"
          " references/diagnostic_rules_catalog.md for authoring guidelines."
      )
  )
  parser.add_argument("--batch_id", help="Dataproc Serverless batch ID")
  parser.add_argument("--region", default="us-central1", help="GCP Region")
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

  args = parser.parse_args()

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
      sys.exit(1)

  if not rules:
    # Returning "no violations" here would be actively misleading: it reads as
    # a clean bill of health when in fact nothing was ever checked.
    print(
        "Error: no diagnostic rules supplied. This tool ships no built-in"
        " thresholds, because what counts as unhealthy depends on the"
        " workload.\n"
        "Pass rules with --rules_file <file.json> or --custom_rule"
        " '[{...}]'.\n"
        "See references/diagnostic_rules_catalog.md for authoring guidelines"
        " and worked examples.",
        file=sys.stderr,
    )
    sys.exit(1)

  stages = []
  if args.telemetry_file:
    if not os.path.exists(args.telemetry_file):
      print(
          f"Error: telemetry file not found: {args.telemetry_file}",
          file=sys.stderr,
      )
      sys.exit(1)
    try:
      with open(args.telemetry_file, "r") as f:
        data = json.load(f)
    except (OSError, ValueError, json.JSONDecodeError) as e:
      print(
          f"Error: could not parse {args.telemetry_file}: {e}", file=sys.stderr
      )
      sys.exit(1)
    if isinstance(data, list):
      stages = data
    elif isinstance(data, dict):
      stages = _get(data, "stages", None) or [data]
  elif args.batch_id:
    try:
      stages = fetch_batch_telemetry_via_gcloud(args.batch_id, args.region)
    except RuntimeError as e:
      print(f"Error: {e}", file=sys.stderr)
      sys.exit(1)
  else:
    print(
        "Error: Specify either --batch_id or --telemetry_file", file=sys.stderr
    )
    sys.exit(1)

  violations = evaluate_stage_rules(stages, rules)

  print("# Spark Stage Diagnostics Report\n")
  print(f"- **Rules Evaluated**: {len(rules)}")
  print(f"- **Total Stages Analyzed**: {len(stages)}")
  print(f"- **Total Diagnostic Violations Detected**: {len(violations)}\n")

  if not stages:
    print(
        "### Result: No stage telemetry was available, so no rules could be"
        " evaluated. This is NOT a clean bill of health -- verify the batch ID"
        " and region, and confirm the batch has started executing stages."
    )
    return

  if not violations:
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
    print("- **Violating Stages**:")
    for vs in v["violating_stages"]:
      print(f"  - **Stage {vs['stage_id']}**: {vs['detail']}")
    print()


if __name__ == "__main__":
  main()
