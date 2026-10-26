# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validates a declarative data pipeline YAML against the pinned MVP format.

Prints a JSON report to stdout: {"status": "PASS"|"FAIL", "errors": [...],
"warnings": [...]}. Exits 0 on PASS and 1 on FAIL.

Example:
  python3 validate_pipeline_yaml.py pipelines/customer_orders.pipeline.yaml \
      --repo-root .
"""

import argparse
import json
import os
import re
import sys

try:
  import yaml  # PyYAML ships with dbt-core.
except ImportError:  # pragma: no cover - exercised only on user machines.
  yaml = None

_TOP_LEVEL_KEYS = frozenset(
    {"intent", "execution_mode", "triggers", "parameters", "data_models"}
)
_OUT_OF_SCOPE_TOP_LEVEL_KEYS = frozenset(
    {"outcomes", "quality_gates", "continuous"}
)
_MODEL_ENGINES = frozenset({"dbt", "sdp"})
_OUT_OF_SCOPE_ENGINES = frozenset({"ingest", "bigquery_sql"})
_PARAMETER_TYPES = frozenset({"STRING", "INT64", "FLOAT64", "BOOL"})
_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
_VARIABLE_REF = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_CRON_FIELD = re.compile(r"^[0-9A-Za-z*/,\-?LW#]+$")
_ENV_LEVEL_VARIABLES = frozenset({"project", "region"})
_SDP_SPEC_FILES = ("spark-pipeline.yml", "spark-pipeline.yaml")


def _is_valid_cron(expr):
  fields = expr.split()
  return len(fields) == 5 and all(_CRON_FIELD.match(f) for f in fields)


def _collect_variable_refs(node, refs):
  """Collects every {{ var }} reference in string values of a YAML tree."""
  if isinstance(node, str):
    refs.update(_VARIABLE_REF.findall(node))
  elif isinstance(node, dict):
    for value in node.values():
      _collect_variable_refs(value, refs)
  elif isinstance(node, list):
    for value in node:
      _collect_variable_refs(value, refs)


def _validate_intent(spec, errors):
  intent = spec.get("intent")
  if not isinstance(intent, dict):
    errors.append("`intent` is required and must be a mapping with `goal`.")
    return
  extra = sorted(set(intent) - {"goal"})
  if extra:
    errors.append(
        f"`intent` only allows `goal` in the MVP; found extra keys: {extra}."
    )
  goal = intent.get("goal")
  if not isinstance(goal, str) or not goal.strip():
    errors.append("`intent.goal` is required and must be a non-empty string.")


def _validate_triggers(spec, errors, warnings):
  if "triggers" not in spec:
    warnings.append(
        "No `triggers`: the pipeline only runs manually or from an"
        " orchestration pipeline."
    )
    return
  triggers = spec["triggers"]
  if not isinstance(triggers, list) or not triggers:
    errors.append("`triggers` must be a non-empty list when present.")
    return
  for i, trigger in enumerate(triggers):
    where = f"triggers[{i}]"
    inline = (
        trigger.get("inline_trigger") if isinstance(trigger, dict) else None
    )
    if not isinstance(inline, dict) or set(inline) != {"schedule"}:
      errors.append(
          f"`{where}` must be `inline_trigger: {{schedule: ...}}`; only"
          " schedule triggers are in scope."
      )
      continue
    schedule = inline["schedule"]
    if not isinstance(schedule, dict):
      errors.append(f"`{where}.inline_trigger.schedule` must be a mapping.")
      continue
    extra = sorted(set(schedule) - {"interval", "time_zone"})
    if extra:
      errors.append(
          f"`{where}.inline_trigger.schedule` has unknown keys: {extra}."
      )
    interval = schedule.get("interval")
    if not isinstance(interval, str) or not _is_valid_cron(interval):
      errors.append(
          f"`{where}.inline_trigger.schedule.interval` must be a 5-field cron"
          f" string; found {interval!r}."
      )
    time_zone = schedule.get("time_zone")
    if not isinstance(time_zone, str) or not time_zone:
      errors.append(
          f"`{where}.inline_trigger.schedule.time_zone` is required (for"
          ' example "UTC").'
      )


def _validate_parameters(spec, errors):
  if "parameters" not in spec:
    return
  parameters = spec["parameters"]
  if not isinstance(parameters, list):
    errors.append("`parameters` must be a list.")
    return
  seen = set()
  for i, param in enumerate(parameters):
    where = f"parameters[{i}]"
    if not isinstance(param, dict):
      errors.append(f"`{where}` must be a mapping.")
      continue
    extra = sorted(set(param) - {"name", "type", "default"})
    if extra:
      errors.append(f"`{where}` has unknown keys: {extra}.")
    name = param.get("name")
    if not isinstance(name, str) or not _SNAKE_CASE.match(name):
      errors.append(f"`{where}.name` must be lower_snake_case; found {name!r}.")
    elif name in seen:
      errors.append(f"Duplicate parameter name {name!r}.")
    else:
      seen.add(name)
    if param.get("type") not in _PARAMETER_TYPES:
      errors.append(
          f"`{where}.type` must be one of {sorted(_PARAMETER_TYPES)}; found"
          f" {param.get('type')!r}."
      )


def _validate_source_dir(where, source, repo_root, marker_files, errors):
  if not isinstance(source, str) or not source.strip():
    errors.append(f"`{where}.source` is required and must be a path string.")
    return
  if os.path.isabs(source):
    errors.append(f"`{where}.source` must be relative to the repository root.")
    return
  if repo_root is None:
    return
  path = os.path.normpath(os.path.join(repo_root, source))
  if not os.path.isdir(path):
    errors.append(
        f"`{where}.source` directory {source!r} does not exist under the"
        f" repository root {repo_root!r}."
    )
    return
  if not any(os.path.isfile(os.path.join(path, m)) for m in marker_files):
    errors.append(
        f"`{where}.source` {source!r} has none of {list(marker_files)}."
    )


def _validate_data_models(spec, repo_root, errors):
  models = spec.get("data_models")
  if not isinstance(models, list) or not models:
    errors.append("`data_models` is required and must be a non-empty list.")
    return
  seen = set()
  for i, model in enumerate(models):
    where = f"data_models[{i}]"
    if not isinstance(model, dict):
      errors.append(f"`{where}` must be a mapping.")
      continue
    name = model.get("name")
    if not isinstance(name, str) or not _SNAKE_CASE.match(name):
      errors.append(f"`{where}.name` must be lower_snake_case; found {name!r}.")
    elif name in seen:
      errors.append(f"Duplicate data model name {name!r}.")
    else:
      seen.add(name)
    out_of_scope = sorted(set(model) & _OUT_OF_SCOPE_ENGINES)
    if out_of_scope:
      errors.append(
          f"`{where}` uses {out_of_scope}, which is out of scope for the MVP;"
          " use `dbt` or `sdp`."
      )
    engines = sorted(set(model) & _MODEL_ENGINES)
    if len(engines) != 1:
      errors.append(f"`{where}` must have exactly one of `dbt` or `sdp`.")
      continue
    extra = sorted(
        set(model) - _MODEL_ENGINES - _OUT_OF_SCOPE_ENGINES - {"name"}
    )
    if extra:
      errors.append(f"`{where}` has unknown keys: {extra}.")
    engine = engines[0]
    config = model[engine]
    if not isinstance(config, dict):
      errors.append(f"`{where}.{engine}` must be a mapping.")
      continue
    if engine == "dbt":
      unknown = sorted(set(config) - {"source", "select"})
      if unknown:
        errors.append(f"`{where}.dbt` has unknown keys: {unknown}.")
      select = config.get("select")
      if select is not None and (
          not isinstance(select, list)
          or not all(isinstance(s, str) and s for s in select)
      ):
        errors.append(f"`{where}.dbt.select` must be a list of strings.")
      _validate_source_dir(
          f"{where}.dbt",
          config.get("source"),
          repo_root,
          ("dbt_project.yml",),
          errors,
      )
    else:
      unknown = sorted(set(config) - {"source"})
      if unknown:
        errors.append(f"`{where}.sdp` has unknown keys: {unknown}.")
      _validate_source_dir(
          f"{where}.sdp",
          config.get("source"),
          repo_root,
          _SDP_SPEC_FILES,
          errors,
      )


def _validate_variables(spec, deployment_path, errors, warnings):
  refs = set()
  _collect_variable_refs(spec, refs)
  if not refs:
    return
  if deployment_path is None or not os.path.isfile(deployment_path):
    errors.append(
        f"Variables {sorted(refs)} are referenced but no deployment.yaml was"
        " found. Do not create it here; set up orchestration first."
    )
    return
  with open(deployment_path, encoding="utf-8") as f:
    deployment = yaml.safe_load(f) or {}
  environments = deployment.get("environments")
  if not isinstance(environments, dict) or not environments:
    errors.append(f"{deployment_path} has no `environments` mapping.")
    return
  for env_name, env in environments.items():
    env = env or {}
    defined = set((env.get("variables") or {}).keys())
    defined |= {k for k in _ENV_LEVEL_VARIABLES if k in env}
    missing = sorted(refs - defined)
    if missing:
      errors.append(
          f"Environment {env_name!r} in deployment.yaml does not define"
          f" variables {missing}."
      )
  pipelines = [
      p.get("source")
      for env in environments.values()
      for p in (env or {}).get("pipelines") or []
      if isinstance(p, dict)
  ]
  if not pipelines:
    warnings.append("deployment.yaml lists no `pipelines` entries.")


def validate(spec, repo_root=None, deployment_path=None):
  """Validates a parsed pipeline spec.

  Args:
    spec: The parsed YAML document.
    repo_root: Repository root used to resolve model `source` paths. When None,
      path existence checks are skipped.
    deployment_path: Path to deployment.yaml, used to check `{{ var }}`
      references. When None, any variable reference is an error.

  Returns:
    A dict with `status`, `errors`, and `warnings`.
  """
  errors = []
  warnings = []
  if not isinstance(spec, dict):
    errors.append("The pipeline file must be a YAML mapping.")
  else:
    out_of_scope = sorted(set(spec) & _OUT_OF_SCOPE_TOP_LEVEL_KEYS)
    if out_of_scope:
      errors.append(
          f"Keys {out_of_scope} are out of scope for the MVP; describe the"
          " requirement in `intent.goal` and implement checks in code."
      )
    unknown = sorted(set(spec) - _TOP_LEVEL_KEYS - _OUT_OF_SCOPE_TOP_LEVEL_KEYS)
    if unknown:
      errors.append(f"Unknown top-level keys: {unknown}.")
    _validate_intent(spec, errors)
    if spec.get("execution_mode") != "TRIGGERED":
      errors.append(
          "`execution_mode` must be `TRIGGERED`; found"
          f" {spec.get('execution_mode')!r}."
      )
    _validate_triggers(spec, errors, warnings)
    _validate_parameters(spec, errors)
    _validate_data_models(spec, repo_root, errors)
    _validate_variables(spec, deployment_path, errors, warnings)
  return {
      "status": "FAIL" if errors else "PASS",
      "errors": errors,
      "warnings": warnings,
  }


def main(argv=None):
  parser = argparse.ArgumentParser(
      description=(
          "Validate a declarative data pipeline YAML against the pinned MVP"
          " format. Prints a JSON report; exits 1 on FAIL."
      )
  )
  parser.add_argument("pipeline_yaml", help="Path to the .pipeline.yaml file.")
  parser.add_argument(
      "--repo-root",
      default=None,
      help=(
          "Repository root (directory with deployment.yaml). Defaults to the"
          " parent of the pipelines/ directory that holds the file."
      ),
  )
  parser.add_argument(
      "--deployment",
      default=None,
      help="Path to deployment.yaml. Defaults to <repo-root>/deployment.yaml.",
  )
  args = parser.parse_args(argv)

  if yaml is None:
    print(
        json.dumps(
            {
                "status": "FAIL",
                "errors": [
                    "PyYAML is not installed. Install it with `pip install"
                    " pyyaml` in the project's virtual environment."
                ],
                "warnings": [],
            },
            indent=2,
        )
    )
    return 1

  pipeline_path = os.path.abspath(args.pipeline_yaml)
  repo_root = args.repo_root
  if repo_root is None:
    parent = os.path.dirname(pipeline_path)
    repo_root = (
        os.path.dirname(parent)
        if os.path.basename(parent) == "pipelines"
        else parent
    )
  repo_root = os.path.abspath(repo_root)
  deployment_path = args.deployment or os.path.join(
      repo_root, "deployment.yaml"
  )

  try:
    with open(pipeline_path, encoding="utf-8") as f:
      spec = yaml.safe_load(f)
  except (OSError, yaml.YAMLError) as e:
    print(
        json.dumps(
            {
                "status": "FAIL",
                "errors": [f"Cannot read YAML: {e}"],
                "warnings": [],
            },
            indent=2,
        )
    )
    return 1

  report = validate(spec, repo_root=repo_root, deployment_path=deployment_path)
  print(json.dumps(report, indent=2))
  return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
  sys.exit(main())
