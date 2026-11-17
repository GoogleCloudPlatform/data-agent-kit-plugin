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
"""Zero-dependency CLI to validate, deploy, promote, roll back, and export BQCA DataAgents.

Targets the Gemini Data Analytics v1 REST API using only the Python 3 standard
library (plus `gcloud` for OAuth access tokens during live API calls and `bq`
when `--bq-dry-run` is requested).
"""

import argparse
from collections.abc import Callable, Mapping, Sequence
import copy
import dataclasses
import json
import os
import re
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEFAULT_API_ENDPOINT = "https://geminidataanalytics.googleapis.com/v1"

MAX_DISPLAY_NAME_CHARS = 256
MAX_DESCRIPTION_CHARS = 1024
MAX_SYSTEM_INSTRUCTION_BYTES = 250_000
DEFAULT_WARN_INSTRUCTION_BYTES = 8_192
MAX_NL_QUESTION_BYTES = 2_000
MAX_SQL_QUERY_BYTES = 50_000
MAX_GLOSSARY_NAME_BYTES = 256
MAX_GLOSSARY_DESCRIPTION_BYTES = 5_000
_MAX_INT64 = (1 << 63) - 1

_NL = chr(10)
_BS = chr(92)

_AGENT_ID_RE = re.compile(r"\A[a-z]([a-z0-9-]{0,61}[a-z0-9])?\Z")
_LOCATION_RE = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_PROJECT_ID_RE = re.compile(r"\A[a-z0-9][a-z0-9.:-]{0,62}\Z")
_GDA_HOST_RE = re.compile(
    r"\Ageminidataanalytics(?:-[a-z0-9-]+|\.[a-z0-9]+\.rep)?\.googleapis\.com\Z"
)
_KMS_KEY_RE = re.compile(
    r"\Aprojects/[^/]+/locations/([^/]+)/keyRings/[^/]+/cryptoKeys/[^/]+\Z"
)
_PLACEHOLDER_RE = re.compile("[{][{]([^{}]+?)[}][}]")
_SQL_SYSTEM_VAR_RE = re.compile("@@[A-Za-z_][A-Za-z0-9_.]*")
_SQL_PARAM_RE = re.compile("(?<![@A-Za-z0-9_])@([A-Za-z_][A-Za-z0-9_]*)")

VALID_BQ_PARAM_TYPES = frozenset({
    "STRING",
    "INT64",
    "INTEGER",
    "FLOAT64",
    "FLOAT",
    "NUMERIC",
    "DECIMAL",
    "BIGNUMERIC",
    "BIGDECIMAL",
    "BOOL",
    "BOOLEAN",
    "DATE",
    "DATETIME",
    "TIME",
    "TIMESTAMP",
    "BYTES",
    "JSON",
    "GEOGRAPHY",
    "INTERVAL",
    "RANGE",
    "ARRAY",
    "STRUCT",
})

_COMPLEX_BQ_DRY_RUN_PARAM_TYPES = frozenset({"ARRAY", "STRUCT", "RANGE"})

_BQ_DRY_RUN_STUBS: Mapping[str, tuple[str, str]] = {
    "STRING": ("STRING", "sample"),
    "INT64": ("INT64", "1"),
    "INTEGER": ("INT64", "1"),
    "FLOAT64": ("FLOAT64", "1.0"),
    "FLOAT": ("FLOAT64", "1.0"),
    "NUMERIC": ("NUMERIC", "1"),
    "DECIMAL": ("NUMERIC", "1"),
    "BIGNUMERIC": ("BIGNUMERIC", "1"),
    "BIGDECIMAL": ("BIGNUMERIC", "1"),
    "BOOL": ("BOOL", "true"),
    "BOOLEAN": ("BOOL", "true"),
    "DATE": ("DATE", "2026-01-01"),
    "DATETIME": ("DATETIME", "2026-01-01 00:00:00"),
    "TIME": ("TIME", "00:00:00"),
    "TIMESTAMP": ("TIMESTAMP", "2026-01-01T00:00:00Z"),
    "BYTES": ("BYTES", "c2FtcGxl"),
    "JSON": ("JSON", "{}"),
    "GEOGRAPHY": ("GEOGRAPHY", "POINT(0 0)"),
    "INTERVAL": ("INTERVAL", "0-0 1 0:0:0"),
}

_OUTPUT_ONLY_AGENT_KEYS = frozenset({
    "createTime",
    "updateTime",
    "deleteTime",
    "purgeTime",
    "create_time",
    "update_time",
    "delete_time",
    "purge_time",
})


class SpecError(ValueError):
  """Raised when an input spec, template variable, or endpoint is invalid."""


@dataclasses.dataclass
class ValidationResult:
  """Aggregated validation errors and non-blocking warnings."""

  errors: list[str] = dataclasses.field(default_factory=list)
  warnings: list[str] = dataclasses.field(default_factory=list)

  @property
  def ok(self) -> bool:
    return not self.errors

  def merge(self, other: "ValidationResult") -> None:
    self.errors.extend(other.errors)
    self.warnings.extend(other.warnings)


@dataclasses.dataclass(frozen=True)
class HttpResponse:
  """Minimal HTTP response container for REST operations."""

  status: int
  body: dict[str, Any]


HttpTransport = Callable[
    [str, str, dict[str, Any] | None, str],
    HttpResponse,
]


def _snake_to_camel(key: str) -> str:
  if "_" not in key:
    return key
  parts = key.split("_")
  return parts[0] + "".join(part.capitalize() for part in parts[1:] if part)


def _normalize_to_camel(obj: Any, *, parent_key: str = "") -> Any:
  """Recursively converts snake_case dict keys to v1 REST camelCase.

  Preserves user-defined map keys under `labels`.

  Args:
    obj: Arbitrary JSON value to normalize.
    parent_key: Immediate parent key name.

  Returns:
    Normalized JSON structure with camelCase keys.
  """
  if isinstance(obj, Mapping):
    if parent_key == "labels":
      return {str(k): v for k, v in obj.items()}
    normalized: dict[str, Any] = {}
    for raw_k, raw_v in obj.items():
      camel_k = _snake_to_camel(str(raw_k))
      normalized[camel_k] = _normalize_to_camel(raw_v, parent_key=camel_k)
    return normalized
  if isinstance(obj, list):
    return [_normalize_to_camel(item, parent_key=parent_key) for item in obj]
  return obj


def _render_templates(
    obj: Any,
    variables: Mapping[str, str],
    unresolved: set[str],
) -> Any:
  """Recursively substitutes `{{var}}` tokens and tracks unresolved names."""
  if isinstance(obj, str):

    def _replace(match: re.Match[str]) -> str:
      var_name = match.group(1).strip()
      if var_name in variables:
        return variables[var_name]
      unresolved.add(var_name)
      return match.group(0)

    return _PLACEHOLDER_RE.sub(_replace, obj)
  if isinstance(obj, Mapping):
    return {
        k: _render_templates(v, variables, unresolved) for k, v in obj.items()
    }
  if isinstance(obj, list):
    return [_render_templates(item, variables, unresolved) for item in obj]
  return obj


def _parse_positive_int64(value: Any) -> int | None:
  """Parses a positive int64 from int, numeric string, or Int64Value wrapper."""
  if isinstance(value, bool) or value is None:
    return None
  if isinstance(value, Mapping) and "value" in value:
    value = value["value"]
  if isinstance(value, bool) or value is None:
    return None
  if isinstance(value, int):
    return value if 0 < value <= _MAX_INT64 else None
  if isinstance(value, str):
    stripped = value.strip()
    if stripped.isdigit():
      parsed = int(stripped)
      return parsed if 0 < parsed <= _MAX_INT64 else None
  return None


def _strip_sql_literals_and_comments(sql: str) -> str:
  """Replaces SQL string literals, backtick identifiers, and comments with spaces."""
  out: list[str] = []
  n = len(sql)
  i = 0
  while i < n:
    ch = sql[i]
    # Line comments: -- ... or # ...
    if ch == "#" or (ch == "-" and i + 1 < n and sql[i + 1] == "-"):
      out.append(" ")
      while i < n and sql[i] != _NL:
        i += 1
      continue
    # Block comments: /* ... */
    if ch == "/" and i + 1 < n and sql[i + 1] == "*":
      out.append(" ")
      i += 2
      while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
        i += 1
      i += 2
      continue
    # Backtick-quoted identifiers: `...`
    if ch == "`":
      out.append(" ")
      i += 1
      while i < n and sql[i] != "`":
        if sql[i] == _BS and i + 1 < n:
          i += 2
        else:
          i += 1
      i += 1
      continue
    # String literals, including r'...', b'...', rb'...', '''...''', """..."""
    prefix_len = 0
    if ch in ("r", "R", "b", "B"):
      if i + 1 < n and sql[i + 1] in ("'", '"'):
        prefix_len = 1
      elif (
          i + 2 < n
          and sql[i + 1] in ("r", "R", "b", "B")
          and sql[i + 2] in ("'", '"')
      ):
        prefix_len = 2
    if prefix_len or ch in ("'", '"'):
      i += prefix_len
      quote = sql[i]
      triple = i + 2 < n and sql[i + 1] == quote and sql[i + 2] == quote
      delim = quote * 3 if triple else quote
      step = 3 if triple else 1
      out.append(" ")
      i += step
      while i < n:
        if sql[i] == _BS and i + 1 < n:
          i += 2
          continue
        if triple:
          if sql[i : i + 3] == delim:
            i += 3
            break
        else:
          if sql[i] == quote:
            if i + 1 < n and sql[i + 1] == quote:
              i += 2
              continue
            i += 1
            break
        i += 1
      continue
    out.append(ch)
    i += 1
  return "".join(out)


def extract_sql_parameters(sql: str) -> set[str]:
  """Extracts `@param` names from GoogleSQL, ignoring strings and `@@vars`."""
  without_literals = _strip_sql_literals_and_comments(sql)
  without_sys_vars = _SQL_SYSTEM_VAR_RE.sub(" ", without_literals)
  return set(_SQL_PARAM_RE.findall(without_sys_vars))


def _load_and_render_env(
    env_path: str | None,
) -> tuple[dict[str, Any], dict[str, str], set[str]]:
  """Loads an environment JSON file, builds template vars, and renders overrides."""
  if not env_path:
    return {}, {}, set()
  try:
    with open(env_path, encoding="utf-8") as f:
      loaded_env = json.load(f)
  except (OSError, json.JSONDecodeError) as exc:
    raise SpecError(f"Failed to load env file {env_path!r}: {exc}") from exc
  if not isinstance(loaded_env, Mapping):
    raise SpecError("Environment file root must be a JSON object.")

  env_data = dict(loaded_env)
  raw_vars = env_data.get("vars")
  vars_from_block: dict[str, str] = {}
  if raw_vars is not None:
    if not isinstance(raw_vars, Mapping):
      raise SpecError("`vars` in environment file must be a JSON object.")
    for k, v in raw_vars.items():
      if isinstance(v, (str, int, float)) and not isinstance(v, bool):
        vars_from_block[str(k)] = str(v)

  variables: dict[str, str] = {}
  for scalar_key in (
      "project",
      "location",
      "data_agent_id",
      "dataAgentId",
      "max_billed_bytes",
      "maxBilledBytes",
  ):
    val = env_data.get(scalar_key)
    if isinstance(val, (str, int)) and not isinstance(val, bool):
      prelim_unresolved: set[str] = set()
      rendered_val = _render_templates(
          str(val), vars_from_block, prelim_unresolved
      )
      if not prelim_unresolved:
        variables[scalar_key] = rendered_val
  variables.update(vars_from_block)

  env_unresolved: set[str] = set()
  env_top_raw = {k: v for k, v in env_data.items() if k != "vars"}
  rendered_env_top = _render_templates(env_top_raw, variables, env_unresolved)
  if "vars" in env_data:
    rendered_env_top["vars"] = copy.deepcopy(raw_vars)
  return _normalize_to_camel(rendered_env_top), variables, env_unresolved


def load_and_render_spec(
    spec_path: str,
    env_path: str | None = None,
    instruction_path: str | None = None,
    target: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
  """Loads, renders `{{var}}` templates, and normalizes an agent spec to camelCase.

  Args:
    spec_path: Path to the base DataAgent JSON file.
    env_path: Optional path to environment JSON containing `project`,
      `location`, `data_agent_id`, overrides, and `vars`.
    instruction_path: Optional path to a UTF-8 YAML/Markdown `systemInstruction`
      file injected into the active context(s).
    target: Optional context slot (`"staging"` or `"published"`). When set,
      populates the target slot from the sibling slot if needed.

  Returns:
    Tuple of `(rendered_payload_dict, normalized_env_dict)`.

  Raises:
    SpecError: If JSON/files cannot be loaded, `target` is invalid, or any
      `{{var}}` placeholder remains unresolved.
  """
  if target not in (None, "staging", "published"):
    raise SpecError(f"Unsupported target context: {target!r}")

  try:
    with open(spec_path, encoding="utf-8") as f:
      raw_spec = json.load(f)
  except (OSError, json.JSONDecodeError) as exc:
    raise SpecError(f"Failed to load spec file {spec_path!r}: {exc}") from exc

  if not isinstance(raw_spec, Mapping):
    raise SpecError("Agent spec root must be a JSON object.")

  env_camel, variables, env_unresolved = _load_and_render_env(env_path)

  spec_unresolved: set[str] = set()
  rendered = _render_templates(raw_spec, variables, spec_unresolved)
  unresolved = spec_unresolved | env_unresolved
  if unresolved:
    missing = ", ".join(sorted(unresolved))
    source_desc = (
        f"{spec_path!r} / {env_path!r}" if env_unresolved else f"{spec_path!r}"
    )
    raise SpecError(
        f"Unresolved template placeholder(s) in {source_desc}: {missing}"
    )

  payload: dict[str, Any] = _normalize_to_camel(rendered)

  daa = payload.get("dataAnalyticsAgent")
  if not isinstance(daa, dict):
    daa = {}
    payload["dataAnalyticsAgent"] = daa

  if target == "staging":
    if "stagingContext" not in daa and isinstance(
        daa.get("publishedContext"), Mapping
    ):
      daa["stagingContext"] = copy.deepcopy(daa["publishedContext"])
  elif target == "published":
    if "publishedContext" not in daa and isinstance(
        daa.get("stagingContext"), Mapping
    ):
      daa["publishedContext"] = copy.deepcopy(daa["stagingContext"])

  if instruction_path:
    try:
      with open(instruction_path, encoding="utf-8") as f:
        instruction_text = f.read()
    except OSError as exc:
      raise SpecError(
          f"Failed to load instruction file {instruction_path!r}: {exc}"
      ) from exc

    instr_unresolved: set[str] = set()
    instruction_text = _render_templates(
        instruction_text, variables, instr_unresolved
    )
    if instr_unresolved:
      missing = ", ".join(sorted(instr_unresolved))
      raise SpecError(
          f"Unresolved template placeholder(s) in {instruction_path!r}: "
          f"{missing}"
      )

    if target == "staging":
      ctx = daa.setdefault("stagingContext", {})
      if isinstance(ctx, dict):
        ctx["systemInstruction"] = instruction_text
    elif target == "published":
      ctx = daa.setdefault("publishedContext", {})
      if isinstance(ctx, dict):
        ctx["systemInstruction"] = instruction_text
    else:
      populated = [
          slot
          for slot in ("stagingContext", "publishedContext")
          if isinstance(daa.get(slot), dict)
      ]
      if not populated:
        daa["stagingContext"] = {"systemInstruction": instruction_text}
      else:
        for slot in populated:
          daa[slot]["systemInstruction"] = instruction_text

  # Apply optional environment-level overrides.
  if "kmsKey" in env_camel and env_camel["kmsKey"] is not None:
    payload["kmsKey"] = env_camel["kmsKey"]
  if "bigqueryAgentAnalyticsEnabled" in env_camel:
    payload["bigqueryAgentAnalyticsEnabled"] = env_camel[
        "bigqueryAgentAnalyticsEnabled"
    ]
  if "bigqueryAgentAnalyticsTable" in env_camel:
    payload["bigqueryAgentAnalyticsTable"] = env_camel[
        "bigqueryAgentAnalyticsTable"
    ]

  has_env_max_bytes = False
  env_max_bytes: Any = None
  if (
      "bigQueryMaxBilledBytes" in env_camel
      and env_camel["bigQueryMaxBilledBytes"] is not None
  ):
    has_env_max_bytes = True
    env_max_bytes = env_camel["bigQueryMaxBilledBytes"]
  elif (
      "maxBilledBytes" in env_camel and env_camel["maxBilledBytes"] is not None
  ):
    has_env_max_bytes = True
    env_max_bytes = env_camel["maxBilledBytes"]

  if has_env_max_bytes:
    for slot in ("stagingContext", "publishedContext"):
      ctx = daa.get(slot)
      if isinstance(ctx, dict):
        opts = ctx.setdefault("options", {})
        if isinstance(opts, dict):
          ds_opts = opts.setdefault("datasource", {})
          if isinstance(ds_opts, dict):
            ds_opts["bigQueryMaxBilledBytes"] = (
                env_max_bytes
                if isinstance(env_max_bytes, bool)
                else str(env_max_bytes)
            )

  # Normalize Int64Value bigQueryMaxBilledBytes to canonical string form.
  for slot in ("stagingContext", "publishedContext"):
    ctx = daa.get(slot)
    if isinstance(ctx, dict):
      ds_opts = (
          ctx.get("options", {}).get("datasource")
          if isinstance(ctx.get("options"), Mapping)
          else None
      )
      if isinstance(ds_opts, dict) and "bigQueryMaxBilledBytes" in ds_opts:
        parsed_bytes = _parse_positive_int64(ds_opts["bigQueryMaxBilledBytes"])
        if parsed_bytes is not None:
          ds_opts["bigQueryMaxBilledBytes"] = str(parsed_bytes)

  return payload, env_camel


def _validate_identifier_segment(
    label: str, value: str, result: ValidationResult
) -> None:
  """Validates a single GCP resource path segment (`project` or `location`)."""
  if not isinstance(value, str) or not value.strip():
    result.errors.append(f"`{label}` must be a non-empty string.")
    return
  if label == "location":
    if not _LOCATION_RE.match(value):
      result.errors.append(
          f"`location` ({value!r}) must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`."
      )
    return
  if label == "project":
    if not _PROJECT_ID_RE.match(value) or ".." in value:
      result.errors.append(
          f"`project` ({value!r}) must be a valid GCP project identifier "
          "(no slashes, whitespace, query/fragment characters, or `..`)."
      )
    return
  if "/" in value or any(ch.isspace() for ch in value):
    result.errors.append(
        f"`{label}` ({value!r}) must not contain slashes or whitespace."
    )


def _validate_context(
    slot_name: str,
    ctx: Any,
    result: ValidationResult,
    *,
    allow_unbounded_bytes: bool,
    warn_instruction_bytes: int,
) -> None:
  """Validates a single Context object (`stagingContext` or `publishedContext`)."""
  if not isinstance(ctx, Mapping):
    result.errors.append(f"`{slot_name}` must be a JSON object.")
    return

  # 1. systemInstruction byte budget.
  if "systemInstruction" in ctx and ctx["systemInstruction"] is not None:
    instr = ctx["systemInstruction"]
    if not isinstance(instr, str):
      result.errors.append(f"`{slot_name}.systemInstruction` must be a string.")
    else:
      instr_bytes = len(instr.encode("utf-8"))
      if instr_bytes > MAX_SYSTEM_INSTRUCTION_BYTES:
        result.errors.append(
            f"`{slot_name}.systemInstruction` is {instr_bytes} UTF-8 bytes "
            f"(exceeds API limit of {MAX_SYSTEM_INSTRUCTION_BYTES} bytes)."
        )
      elif instr_bytes > warn_instruction_bytes:
        result.warnings.append(
            f"`{slot_name}.systemInstruction` is {instr_bytes} UTF-8 bytes "
            "(exceeds recommended concise threshold of "
            f"{warn_instruction_bytes} bytes; move schema/query/glossary "
            "details into structured fields)."
        )

  # 2. datasourceReferences.bq & searchScope ban.
  ds_refs = ctx.get("datasourceReferences")
  if not isinstance(ds_refs, Mapping):
    result.errors.append(
        f"`{slot_name}.datasourceReferences` is required and must be an object."
    )
  else:
    bq_refs = ds_refs.get("bq")
    if not isinstance(bq_refs, Mapping):
      result.errors.append(
          f"`{slot_name}.datasourceReferences.bq` must be an object for a "
          "BigQuery DataAgent."
      )
    else:
      if bq_refs.get("searchScope") is not None:
        result.errors.append(
            f"`{slot_name}.datasourceReferences.bq.searchScope` is not "
            "supported on persistent DataAgent resources (inline/stateless "
            "chat only). Declare explicit `tableReferences` or "
            "`propertyGraphReferences`."
        )
      table_refs = bq_refs.get("tableReferences")
      graph_refs = bq_refs.get("propertyGraphReferences")
      has_tables = isinstance(table_refs, list) and len(table_refs) > 0
      has_graphs = isinstance(graph_refs, list) and len(graph_refs) > 0
      if not has_tables and not has_graphs:
        result.errors.append(
            f"`{slot_name}.datasourceReferences.bq` must contain at least one "
            "entry in `tableReferences` or `propertyGraphReferences`."
        )
      if table_refs is not None:
        if not isinstance(table_refs, list):
          result.errors.append(
              f"`{slot_name}.datasourceReferences.bq.tableReferences` must be "
              "a list."
          )
        else:
          for idx, tbl in enumerate(table_refs):
            prefix = (
                f"{slot_name}.datasourceReferences.bq.tableReferences[{idx}]"
            )
            if not isinstance(tbl, Mapping):
              result.errors.append(f"`{prefix}` must be an object.")
              continue
            for req_key in ("projectId", "datasetId", "tableId"):
              val = tbl.get(req_key)
              if not isinstance(val, str) or not val.strip():
                result.errors.append(
                    f"`{prefix}.{req_key}` must be a non-empty string."
                )
      if graph_refs is not None:
        if not isinstance(graph_refs, list):
          result.errors.append(
              f"`{slot_name}.datasourceReferences.bq.propertyGraphReferences` "
              "must be a list."
          )
        else:
          for idx, grp in enumerate(graph_refs):
            prefix = (
                f"{slot_name}.datasourceReferences.bq."
                f"propertyGraphReferences[{idx}]"
            )
            if not isinstance(grp, Mapping):
              result.errors.append(f"`{prefix}` must be an object.")
              continue
            for req_key in ("projectId", "datasetId", "propertyGraphId"):
              val = grp.get(req_key)
              if not isinstance(val, str) or not val.strip():
                result.errors.append(
                    f"`{prefix}.{req_key}` must be a non-empty string."
                )

  # 3. options.datasource.bigQueryMaxBilledBytes cost guardrail.
  opts = ctx.get("options")
  raw_max_bytes = None
  if isinstance(opts, Mapping):
    ds_opts = opts.get("datasource")
    if isinstance(ds_opts, Mapping):
      raw_max_bytes = ds_opts.get("bigQueryMaxBilledBytes")

  parsed_max_bytes = _parse_positive_int64(raw_max_bytes)
  if raw_max_bytes is None:
    if allow_unbounded_bytes:
      result.warnings.append(
          f"`{slot_name}.options.datasource.bigQueryMaxBilledBytes` is unset "
          "(`--allow-unbounded-bytes` enabled); queries have no per-job byte "
          "cap."
      )
    else:
      result.errors.append(
          f"`{slot_name}.options.datasource.bigQueryMaxBilledBytes` is "
          "required (pass `--allow-unbounded-bytes` only when explicitly "
          "approved)."
      )
  elif parsed_max_bytes is None:
    result.errors.append(
        f"`{slot_name}.options.datasource.bigQueryMaxBilledBytes` "
        f"({raw_max_bytes!r}) must be a positive integer byte count."
    )

  # 4. exampleQueries byte caps & @param declarations.
  example_queries = ctx.get("exampleQueries")
  if example_queries is not None:
    if not isinstance(example_queries, list):
      result.errors.append(f"`{slot_name}.exampleQueries` must be a list.")
    else:
      for idx, eq in enumerate(example_queries):
        prefix = f"{slot_name}.exampleQueries[{idx}]"
        if not isinstance(eq, Mapping):
          result.errors.append(f"`{prefix}` must be an object.")
          continue
        nlq = eq.get("naturalLanguageQuestion")
        if not isinstance(nlq, str) or not nlq.strip():
          result.errors.append(
              f"`{prefix}.naturalLanguageQuestion` must be a non-empty string."
          )
        elif len(nlq.encode("utf-8")) > MAX_NL_QUESTION_BYTES:
          result.errors.append(
              f"`{prefix}.naturalLanguageQuestion` exceeds "
              f"{MAX_NL_QUESTION_BYTES} UTF-8 bytes."
          )

        sql = eq.get("sqlQuery")
        if not isinstance(sql, str) or not sql.strip():
          result.errors.append(
              f"`{prefix}.sqlQuery` must be a non-empty string."
          )
          continue
        if len(sql.encode("utf-8")) > MAX_SQL_QUERY_BYTES:
          result.errors.append(
              f"`{prefix}.sqlQuery` exceeds {MAX_SQL_QUERY_BYTES} UTF-8 bytes."
          )

        used_params = extract_sql_parameters(sql)
        raw_params = eq.get("parameters") or []
        declared_names: set[str] = set()
        if not isinstance(raw_params, list):
          result.errors.append(f"`{prefix}.parameters` must be a list.")
        else:
          for p_idx, param in enumerate(raw_params):
            p_prefix = f"{prefix}.parameters[{p_idx}]"
            if not isinstance(param, Mapping):
              result.errors.append(f"`{p_prefix}` must be an object.")
              continue
            p_name = param.get("name")
            if not isinstance(p_name, str) or not p_name.strip():
              result.errors.append(
                  f"`{p_prefix}.name` must be a non-empty string."
              )
            else:
              declared_names.add(p_name)
            p_type = param.get("dataType")
            if not isinstance(p_type, str) or not p_type.strip():
              result.errors.append(
                  f"`{p_prefix}.dataType` must be a non-empty BigQuery SQL "
                  "type."
              )
            else:
              base_type = p_type.strip().upper().split("<", 1)[0].strip()
              if base_type not in VALID_BQ_PARAM_TYPES:
                result.errors.append(
                    f"`{p_prefix}.dataType` ({p_type!r}) is not a valid "
                    "BigQuery standard SQL data type."
                )

        undeclared = sorted(used_params - declared_names)
        if undeclared:
          result.errors.append(
              f"`{prefix}.sqlQuery` references undeclared SQL parameter(s): "
              + ", ".join(f"@{name}" for name in undeclared)
          )
        unused = sorted(declared_names - used_params)
        if unused:
          result.warnings.append(
              f"`{prefix}.parameters` declares parameter(s) not referenced in "
              "`sqlQuery`: "
              + ", ".join(unused)
          )

  # 5. glossaryTerms byte caps.
  glossary_terms = ctx.get("glossaryTerms")
  if glossary_terms is not None:
    if not isinstance(glossary_terms, list):
      result.errors.append(f"`{slot_name}.glossaryTerms` must be a list.")
    else:
      for idx, term in enumerate(glossary_terms):
        prefix = f"{slot_name}.glossaryTerms[{idx}]"
        if not isinstance(term, Mapping):
          result.errors.append(f"`{prefix}` must be an object.")
          continue
        d_name = term.get("displayName")
        if not isinstance(d_name, str) or not d_name.strip():
          result.errors.append(
              f"`{prefix}.displayName` must be a non-empty string."
          )
        elif len(d_name.encode("utf-8")) > MAX_GLOSSARY_NAME_BYTES:
          result.errors.append(
              f"`{prefix}.displayName` exceeds {MAX_GLOSSARY_NAME_BYTES} "
              "UTF-8 bytes."
          )
        desc = term.get("description")
        if not isinstance(desc, str) or not desc.strip():
          result.errors.append(
              f"`{prefix}.description` must be a non-empty string."
          )
        elif len(desc.encode("utf-8")) > MAX_GLOSSARY_DESCRIPTION_BYTES:
          result.errors.append(
              f"`{prefix}.description` exceeds "
              f"{MAX_GLOSSARY_DESCRIPTION_BYTES} UTF-8 bytes."
          )

  # 6. schemaRelationships path parity.
  relationships = ctx.get("schemaRelationships")
  if relationships is not None:
    if not isinstance(relationships, list):
      result.errors.append(f"`{slot_name}.schemaRelationships` must be a list.")
    else:
      for idx, rel in enumerate(relationships):
        prefix = f"{slot_name}.schemaRelationships[{idx}]"
        if not isinstance(rel, Mapping):
          result.errors.append(f"`{prefix}` must be an object.")
          continue
        left = rel.get("leftSchemaPaths")
        right = rel.get("rightSchemaPaths")
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
          result.errors.append(
              f"`{prefix}` must include `leftSchemaPaths` and "
              "`rightSchemaPaths`."
          )
          continue
        left_paths = left.get("paths")
        right_paths = right.get("paths")
        if (
            not isinstance(left_paths, list)
            or not isinstance(right_paths, list)
            or not left_paths
            or len(left_paths) != len(right_paths)
        ):
          result.errors.append(
              f"`{prefix}` `leftSchemaPaths.paths` and "
              "`rightSchemaPaths.paths` must be non-empty lists of equal "
              "length."
          )


def validate_agent_spec(
    payload: Mapping[str, Any],
    project: str,
    location: str,
    data_agent_id: str,
    *,
    allow_unbounded_bytes: bool = False,
    warn_instruction_bytes: int = DEFAULT_WARN_INSTRUCTION_BYTES,
) -> ValidationResult:
  """Validates a rendered DataAgent payload against GDA v1 rules and guardrails."""
  norm = _normalize_to_camel(payload)
  result = ValidationResult()

  _validate_identifier_segment("project", project, result)
  _validate_identifier_segment("location", location, result)

  if not isinstance(data_agent_id, str) or not _AGENT_ID_RE.match(
      data_agent_id
  ):
    result.errors.append(
        f"`data_agent_id` ({data_agent_id!r}) must match AIP-122 pattern "
        "`^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$` (1-63 lowercase chars)."
    )

  if "displayName" in norm and norm["displayName"] is not None:
    dn = norm["displayName"]
    if (
        not isinstance(dn, str)
        or not dn.strip()
        or len(dn) > MAX_DISPLAY_NAME_CHARS
    ):
      result.errors.append(
          f"`displayName` must be 1-{MAX_DISPLAY_NAME_CHARS} characters."
      )

  if "description" in norm and norm["description"] is not None:
    desc = norm["description"]
    if not isinstance(desc, str) or len(desc) > MAX_DESCRIPTION_CHARS:
      result.errors.append(
          f"`description` must be at most {MAX_DESCRIPTION_CHARS} characters."
      )

  if "kmsKey" in norm and norm["kmsKey"] is not None:
    kms_key = norm["kmsKey"]
    if not isinstance(kms_key, str):
      result.errors.append("`kmsKey` must be a string.")
    elif kms_key.strip():
      kms_match = _KMS_KEY_RE.match(kms_key.strip())
      if not kms_match:
        result.errors.append(
            f"`kmsKey` ({kms_key!r}) must match "
            "`projects/{project}/locations/{location}/keyRings/{ring}/"
            "cryptoKeys/{key}`."
        )
      loc_clean = location.strip() if isinstance(location, str) else ""
      if loc_clean == "global":
        result.errors.append(
            "CMEK (`kmsKey`) is not supported in the `global` location; use a "
            "regional or multi-regional location such as `us`, `eu`, or "
            "`us-east4`."
        )
      elif kms_match and loc_clean:
        key_loc = kms_match.group(1)
        expected_key_loc = "europe" if loc_clean == "eu" else loc_clean
        if key_loc != expected_key_loc:
          result.errors.append(
              f"`kmsKey` location ({key_loc!r}) must be {expected_key_loc!r} "
              f"for DataAgent location {loc_clean!r}."
          )

  daa = norm.get("dataAnalyticsAgent")
  if not isinstance(daa, Mapping):
    result.errors.append("`dataAnalyticsAgent` must be present and an object.")
  else:
    has_staging = daa.get("stagingContext") is not None
    has_published = daa.get("publishedContext") is not None
    if not has_staging and not has_published:
      result.errors.append(
          "`dataAnalyticsAgent` must define at least one of `stagingContext` "
          "or `publishedContext`."
      )
    if has_staging:
      _validate_context(
          "dataAnalyticsAgent.stagingContext",
          daa["stagingContext"],
          result,
          allow_unbounded_bytes=allow_unbounded_bytes,
          warn_instruction_bytes=warn_instruction_bytes,
      )
    if has_published:
      _validate_context(
          "dataAnalyticsAgent.publishedContext",
          daa["publishedContext"],
          result,
          allow_unbounded_bytes=allow_unbounded_bytes,
          warn_instruction_bytes=warn_instruction_bytes,
      )

  # BigQuery Agent Analytics monitoring checks.
  bqaa_enabled = norm.get("bigqueryAgentAnalyticsEnabled")
  bqaa_table = norm.get("bigqueryAgentAnalyticsTable")
  if bqaa_enabled is not None and not isinstance(bqaa_enabled, bool):
    result.errors.append("`bigqueryAgentAnalyticsEnabled` must be a boolean.")

  if isinstance(bqaa_enabled, bool) and bqaa_enabled:
    if not isinstance(bqaa_table, Mapping):
      result.errors.append(
          "`bigqueryAgentAnalyticsTable` is required when "
          "`bigqueryAgentAnalyticsEnabled` is true."
      )
    else:
      for req_key in ("projectId", "datasetId", "tableId"):
        val = bqaa_table.get(req_key)
        if not isinstance(val, str) or not val.strip():
          result.errors.append(
              f"`bigqueryAgentAnalyticsTable.{req_key}` must be a non-empty "
              "string."
          )
      tbl_project = bqaa_table.get("projectId")
      if (
          isinstance(tbl_project, str)
          and tbl_project.strip()
          and project.strip()
          and tbl_project != project
      ):
        result.errors.append(
            f"`bigqueryAgentAnalyticsTable.projectId` ({tbl_project!r}) must "
            f"match the DataAgent GCP project ({project!r}); cross-project "
            "monitoring tables are rejected with INVALID_ARGUMENT."
        )
      elif isinstance(tbl_project, str) and tbl_project == project:
        ds_id = bqaa_table.get("datasetId", "<dataset>")
        result.warnings.append(
            "BQAA pre-flight reminder: ensure dataset "
            f"`{project}:{ds_id}` exists, grant `roles/bigquery.dataEditor` to "
            "`service-PROJECT_NUMBER@gcp-sa-geminidataanalytics.iam."
            "gserviceaccount.com`, and verify exposed tables have no RLS/CLS/"
            "policy-tags/masking (which silently suppress turn trace logging)."
        )
  elif bqaa_table is not None:
    result.warnings.append(
        "`bigqueryAgentAnalyticsTable` is set while "
        "`bigqueryAgentAnalyticsEnabled` is false/unset; no trace rows will be "
        "written until `bigqueryAgentAnalyticsEnabled` is true."
    )

  return result


def dry_run_example_queries(
    payload: Mapping[str, Any],
    billing_project: str,
    max_billed_bytes: int | None = None,
    *,
    bq_bin: str = "bq",
) -> ValidationResult:
  """Executes `bq query --dry_run` for every `exampleQueries` entry in payload."""
  norm = _normalize_to_camel(payload)
  result = ValidationResult()
  daa = norm.get("dataAnalyticsAgent")
  if not isinstance(daa, Mapping):
    return result

  for slot_name in ("stagingContext", "publishedContext"):
    ctx = daa.get(slot_name)
    if not isinstance(ctx, Mapping):
      continue
    example_queries = ctx.get("exampleQueries")
    if not isinstance(example_queries, list):
      continue

    ctx_cap: int | None = max_billed_bytes
    if ctx_cap is None:
      opts = ctx.get("options")
      if isinstance(opts, Mapping) and isinstance(
          opts.get("datasource"), Mapping
      ):
        ctx_cap = _parse_positive_int64(
            opts["datasource"].get("bigQueryMaxBilledBytes")
        )

    for idx, eq in enumerate(example_queries):
      if not isinstance(eq, Mapping):
        continue
      sql = eq.get("sqlQuery")
      if not isinstance(sql, str) or not sql.strip():
        continue

      prefix = f"dataAnalyticsAgent.{slot_name}.exampleQueries[{idx}]"
      cmd = [
          bq_bin,
          "query",
          "--use_legacy_sql=false",
          "--dry_run",
          "--format=json",
          f"--project_id={billing_project}",
      ]
      raw_params = eq.get("parameters") or []
      complex_params: list[str] = []
      if isinstance(raw_params, list):
        for param in raw_params:
          if not isinstance(param, Mapping):
            continue
          p_name = param.get("name")
          p_type = param.get("dataType")
          if isinstance(p_name, str) and isinstance(p_type, str):
            base_type = p_type.strip().upper().split("<", 1)[0].strip()
            if base_type in _COMPLEX_BQ_DRY_RUN_PARAM_TYPES:
              complex_params.append(f"@{p_name} ({p_type.strip()})")
              continue
            bq_type, stub_val = _BQ_DRY_RUN_STUBS.get(
                base_type, ("STRING", "sample")
            )
            cmd.append(f"--parameter={p_name}:{bq_type}:{stub_val}")

      if complex_params:
        result.warnings.append(
            f"`{prefix}` declares complex parameter type(s) "
            f"({', '.join(complex_params)}); skipping automated `bq query "
            "--dry_run` because `ARRAY`/`STRUCT`/`RANGE` parameters require "
            "typed manual dry-run validation."
        )
        continue

      try:
        proc = subprocess.run(
            cmd,
            input=sql,
            text=True,
            capture_output=True,
            shell=False,
            check=False,
        )
      except OSError as exc:
        result.errors.append(
            f"`{prefix}` failed to execute `{bq_bin}` dry run: {exc}"
        )
        continue

      if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        result.errors.append(
            f"`{prefix}` failed BigQuery dry run (exit {proc.returncode}): "
            f"{detail}"
        )
        continue

      try:
        parsed_out = json.loads(proc.stdout)
        bytes_processed = int(
            parsed_out.get("statistics", {})
            .get("query", {})
            .get("totalBytesProcessed", 0)
        )
      except (json.JSONDecodeError, TypeError, ValueError) as exc:
        result.errors.append(
            f"`{prefix}` returned unparseable `bq --format=json` output: {exc}"
        )
        continue

      if ctx_cap is not None and bytes_processed > ctx_cap:
        result.errors.append(
            f"`{prefix}` dry-run estimate is {bytes_processed} bytes, which "
            f"exceeds `bigQueryMaxBilledBytes` ({ctx_cap} bytes)."
        )

  return result


def validate_https_endpoint(api_endpoint: str) -> str:
  """Ensures `api_endpoint` uses HTTPS and returns the stripped base URL."""
  cleaned = api_endpoint.strip().rstrip("/")
  parsed = urllib.parse.urlparse(cleaned)
  if (
      parsed.scheme != "https"
      or not parsed.netloc
      or not parsed.hostname
      or "\\" in parsed.netloc
      or parsed.username is not None
      or parsed.password is not None
      or parsed.params
      or parsed.fragment
      or any(ch.isspace() for ch in cleaned)
  ):
    raise SpecError(
        f"`--api-endpoint` ({api_endpoint!r}) must be a valid `https://` URL"
        " without userinfo, path parameters, fragments, or whitespace."
    )
  return cleaned


def resolve_api_endpoint(
    location: str,
    api_endpoint: str | None = None,
) -> str:
  """Resolves the GDA v1 HTTPS endpoint from `location` or explicit override."""
  if api_endpoint:
    cleaned = validate_https_endpoint(api_endpoint)
    if urllib.parse.urlparse(cleaned).query:
      raise SpecError(
          f"`--api-endpoint` ({api_endpoint!r}) must not include a query"
          " string."
      )
    return cleaned
  if not isinstance(location, str):
    raise SpecError(f"Invalid `location` ({location!r}): must be a string.")
  loc = location or "global"
  if not _LOCATION_RE.match(loc):
    raise SpecError(
        f"Invalid `location` ({location!r}): must match"
        " `^[a-z0-9]+(?:-[a-z0-9]+)*$`."
    )
  if loc == "global":
    return DEFAULT_API_ENDPOINT
  if "-" in loc:
    candidate = f"https://geminidataanalytics-{loc}.googleapis.com/v1"
  else:
    candidate = f"https://geminidataanalytics.{loc}.rep.googleapis.com/v1"
  cleaned = validate_https_endpoint(candidate)
  parsed = urllib.parse.urlparse(cleaned)
  host = parsed.hostname or ""
  if parsed.query or not _GDA_HOST_RE.match(host):
    raise SpecError(
        f"Resolved API endpoint ({cleaned!r}) has an unexpected host."
    )
  return cleaned


def resolve_access_token() -> str:
  """Resolves an OAuth bearer token from env or `gcloud auth print-access-token`."""
  env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
  if env_token:
    return env_token
  try:
    proc = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )
  except OSError as exc:
    raise SpecError(
        "Failed to invoke `gcloud auth print-access-token` and "
        "`GOOGLE_OAUTH_ACCESS_TOKEN` is unset."
    ) from exc
  token = proc.stdout.strip()
  if proc.returncode != 0 or not token:
    stderr_msg = proc.stderr.strip() or "empty access token"
    raise SpecError(
        f"Unable to obtain GCP access token via gcloud: {stderr_msg}"
    )
  return token


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
  """Disables HTTP 3xx redirects so Bearer tokens are never forwarded."""

  def redirect_request(self, req, fp, code, msg, headers, newurl):
    del req, fp, code, msg, headers, newurl
    return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler())


def _default_http_transport(
    method: str,
    url: str,
    body: dict[str, Any] | None,
    access_token: str,
) -> HttpResponse:
  """Executes an HTTPS JSON request against the Gemini Data Analytics API."""
  validate_https_endpoint(url)
  data = json.dumps(body).encode("utf-8") if body is not None else None
  headers = {
      "Authorization": f"Bearer {access_token}",
      "Accept": "application/json",
  }
  if data is not None:
    headers["Content-Type"] = "application/json; charset=utf-8"

  req = urllib.request.Request(
      url=url, data=data, headers=headers, method=method
  )
  try:
    with _NO_REDIRECT_OPENER.open(req, timeout=120) as resp:
      raw_text = resp.read().decode("utf-8")
      parsed = json.loads(raw_text) if raw_text.strip() else {}
      return HttpResponse(status=resp.status, body=parsed)
  except urllib.error.HTTPError as exc:
    err_body = exc.read().decode("utf-8", errors="replace")
    try:
      parsed_err = json.loads(err_body) if err_body.strip() else {}
    except json.JSONDecodeError:
      parsed_err = {"error": {"message": err_body}}
    return HttpResponse(status=exc.code, body=parsed_err)


def _require_valid_coordinates(
    project: str,
    location: str,
    data_agent_id: str,
) -> None:
  """Validates `project`, `location`, and `data_agent_id`, raising SpecError."""
  id_check = ValidationResult()
  _validate_identifier_segment("project", project, id_check)
  _validate_identifier_segment("location", location, id_check)
  if not isinstance(data_agent_id, str) or not _AGENT_ID_RE.match(
      data_agent_id
  ):
    id_check.errors.append(f"Invalid `data_agent_id`: {data_agent_id!r}")
  if not id_check.ok:
    raise SpecError("; ".join(id_check.errors))


def _build_deploy_body_and_mask(
    payload: Mapping[str, Any],
    target: str,
    *,
    is_update: bool = False,
    context_only: bool = False,
) -> tuple[dict[str, Any], list[str]]:
  """Builds the targeted DataAgent request body and snake_case updateMask."""
  norm = _normalize_to_camel(payload)
  body: dict[str, Any] = {}
  mask_paths: list[str] = []

  if not context_only:
    if not is_update and "kmsKey" in norm and norm["kmsKey"] is not None:
      body["kmsKey"] = copy.deepcopy(norm["kmsKey"])

    top_level_map = (
        ("displayName", "display_name"),
        ("description", "description"),
        ("labels", "labels"),
        ("bigqueryAgentAnalyticsEnabled", "bigquery_agent_analytics_enabled"),
        ("bigqueryAgentAnalyticsTable", "bigquery_agent_analytics_table"),
    )
    for camel_key, mask_key in top_level_map:
      if camel_key in norm and norm[camel_key] is not None:
        body[camel_key] = copy.deepcopy(norm[camel_key])
        mask_paths.append(mask_key)

  daa = norm.get("dataAnalyticsAgent", {})
  if not isinstance(daa, Mapping):
    daa = {}
  if target == "staging":
    ctx = daa.get("stagingContext")
    if ctx is None:
      raise SpecError("No `stagingContext` available to deploy.")
    body["dataAnalyticsAgent"] = {"stagingContext": copy.deepcopy(ctx)}
    mask_paths.append("data_analytics_agent.staging_context")
  elif target == "published":
    ctx = daa.get("publishedContext")
    if ctx is None:
      raise SpecError("No `publishedContext` available to deploy.")
    body["dataAnalyticsAgent"] = {"publishedContext": copy.deepcopy(ctx)}
    mask_paths.append("data_analytics_agent.published_context")
  else:
    raise SpecError(f"Unsupported deploy target: {target!r}")

  return body, mask_paths


def deploy_agent(
    payload: Mapping[str, Any],
    project: str,
    location: str,
    data_agent_id: str,
    *,
    target: str = "staging",
    api_endpoint: str | None = None,
    dry_run: bool = False,
    allow_unbounded_bytes: bool = False,
    transport: HttpTransport = _default_http_transport,
    token_provider: Callable[[], str] = resolve_access_token,
) -> dict[str, Any]:
  """Upserts a DataAgent via `:createSync` (on 404) or `:updateSync` (on 200)."""
  if api_endpoint:
    validate_https_endpoint(api_endpoint)
  create_body, _ = _build_deploy_body_and_mask(payload, target, is_update=False)
  update_body, update_mask_paths = _build_deploy_body_and_mask(
      payload, target, is_update=True
  )

  validation = validate_agent_spec(
      create_body,
      project,
      location,
      data_agent_id,
      allow_unbounded_bytes=allow_unbounded_bytes,
  )
  if not validation.ok:
    bullet_sep = f"{_NL}- "
    raise SpecError(
        f"Validation failed before deploy:{bullet_sep}"
        + bullet_sep.join(validation.errors)
    )

  base_url = resolve_api_endpoint(location, api_endpoint)
  parent_url = (
      f"{base_url}/projects/{urllib.parse.quote(project, safe='')}"
      f"/locations/{urllib.parse.quote(location, safe='')}"
  )
  agent_url = (
      f"{parent_url}/dataAgents/{urllib.parse.quote(data_agent_id, safe='')}"
  )
  req_id = str(uuid.uuid4())
  mask_str = ",".join(update_mask_paths)
  create_url = f"{parent_url}/dataAgents:createSync?" + urllib.parse.urlencode(
      {"dataAgentId": data_agent_id, "requestId": req_id}
  )
  update_url = f"{agent_url}:updateSync?" + urllib.parse.urlencode(
      {"updateMask": mask_str, "requestId": req_id}
  )

  if dry_run:
    return {
        "mode": "dry_run",
        "target": target,
        "agentUrl": agent_url,
        "createUrl": create_url,
        "updateUrl": update_url,
        "updateMask": update_mask_paths,
        "createRequest": {
            "method": "POST",
            "url": create_url,
            "body": create_body,
        },
        "updateRequest": {
            "method": "PATCH",
            "url": update_url,
            "updateMask": update_mask_paths,
            "body": update_body,
        },
        "warnings": validation.warnings,
        "payload": create_body,
    }

  token = token_provider()
  get_resp = transport("GET", agent_url, None, token)
  if get_resp.status == 404:
    mut_resp = transport("POST", create_url, create_body, token)
    operation = "created"
  elif get_resp.status == 200:
    if "kmsKey" in create_body:
      existing_kms = get_resp.body.get("kmsKey", get_resp.body.get("kms_key"))
      if existing_kms != create_body["kmsKey"]:
        raise SpecError(
            "`kms_key` is immutable after creation (`:updateSync` rejects "
            f"`kms_key`; existing={existing_kms!r}, "
            f"requested={create_body['kmsKey']!r}). Provision a new "
            "`data_agent_id` because deleted DataAgents remain soft-deleted "
            "for 30 days (`purge_time`)."
        )
    mut_resp = transport("PATCH", update_url, update_body, token)
    operation = "updated"
  else:
    raise SpecError(
        f"GET {agent_url} failed with HTTP {get_resp.status}: "
        f"{json.dumps(get_resp.body)}"
    )

  if mut_resp.status not in (200, 201):
    raise SpecError(
        f"DataAgent {operation} call failed with HTTP {mut_resp.status}: "
        f"{json.dumps(mut_resp.body)}"
    )

  return {
      "mode": "live",
      "operation": operation,
      "target": target,
      "updateMask": update_mask_paths,
      "warnings": validation.warnings,
      "dataAgent": mut_resp.body,
  }


def promote_agent(
    project: str,
    location: str,
    data_agent_id: str,
    *,
    payload: Mapping[str, Any] | None = None,
    api_endpoint: str | None = None,
    dry_run: bool = False,
    allow_unbounded_bytes: bool = False,
    transport: HttpTransport = _default_http_transport,
    token_provider: Callable[[], str] = resolve_access_token,
) -> dict[str, Any]:
  """Promotes `stagingContext` to `publishedContext` via `:updateSync`."""
  _require_valid_coordinates(project, location, data_agent_id)
  base_url = resolve_api_endpoint(location, api_endpoint)
  agent_url = (
      f"{base_url}/projects/{urllib.parse.quote(project, safe='')}"
      f"/locations/{urllib.parse.quote(location, safe='')}"
      f"/dataAgents/{urllib.parse.quote(data_agent_id, safe='')}"
  )

  if payload is not None:
    norm = _normalize_to_camel(payload)
    daa = norm.get("dataAnalyticsAgent")
    if not isinstance(daa, Mapping):
      raise SpecError("`dataAnalyticsAgent` must be present and an object.")
    source_ctx = daa.get("stagingContext")
    if source_ctx is None:
      source_ctx = daa.get("publishedContext")
    if source_ctx is None:
      raise SpecError(
          "No `stagingContext` (or fallback `publishedContext`) available to "
          "promote."
      )
    patch_body, mask_paths = _build_deploy_body_and_mask(
        {"dataAnalyticsAgent": {"publishedContext": source_ctx}},
        "published",
        is_update=True,
        context_only=True,
    )
    validation = validate_agent_spec(
        patch_body,
        project,
        location,
        data_agent_id,
        allow_unbounded_bytes=allow_unbounded_bytes,
    )
    if not validation.ok:
      bullet_sep = f"{_NL}- "
      raise SpecError(
          f"Validation failed before promote:{bullet_sep}"
          + bullet_sep.join(validation.errors)
      )

    req_id = str(uuid.uuid4())
    update_url = f"{agent_url}:updateSync?" + urllib.parse.urlencode({
        "updateMask": ",".join(mask_paths),
        "requestId": req_id,
    })
    if dry_run:
      return {
          "mode": "dry_run",
          "operation": "promote",
          "source": "spec",
          "agentUrl": agent_url,
          "updateUrl": update_url,
          "updateMask": mask_paths,
          "warnings": validation.warnings,
          "payload": patch_body,
      }

    token = token_provider()
    patch_resp = transport("PATCH", update_url, patch_body, token)
    if patch_resp.status not in (200, 201):
      raise SpecError(
          f"Promote PATCH failed with HTTP {patch_resp.status}: "
          f"{json.dumps(patch_resp.body)}"
      )
    return {
        "mode": "live",
        "operation": "promoted",
        "source": "spec",
        "updateMask": mask_paths,
        "warnings": validation.warnings,
        "dataAgent": patch_resp.body,
    }

  token = token_provider()
  get_resp = transport("GET", agent_url, None, token)
  if get_resp.status != 200:
    raise SpecError(
        f"GET {agent_url} failed with HTTP {get_resp.status}: "
        f"{json.dumps(get_resp.body)}"
    )

  agent_camel = _normalize_to_camel(get_resp.body)
  staging_ctx = agent_camel.get("dataAnalyticsAgent", {}).get("stagingContext")
  if not isinstance(staging_ctx, Mapping) or not staging_ctx:
    raise SpecError(
        f"DataAgent `{data_agent_id}` has no `stagingContext` to promote."
    )

  patch_body, mask_paths = _build_deploy_body_and_mask(
      {"dataAnalyticsAgent": {"publishedContext": staging_ctx}},
      "published",
      is_update=True,
      context_only=True,
  )
  req_id = str(uuid.uuid4())
  update_url = f"{agent_url}:updateSync?" + urllib.parse.urlencode({
      "updateMask": ",".join(mask_paths),
      "requestId": req_id,
  })
  if dry_run:
    return {
        "mode": "dry_run",
        "operation": "promote",
        "source": "live_staging",
        "agentUrl": agent_url,
        "updateUrl": update_url,
        "updateMask": mask_paths,
        "payload": patch_body,
    }

  patch_resp = transport("PATCH", update_url, patch_body, token)
  if patch_resp.status not in (200, 201):
    raise SpecError(
        f"Promote PATCH failed with HTTP {patch_resp.status}: "
        f"{json.dumps(patch_resp.body)}"
    )
  return {
      "mode": "live",
      "operation": "promoted",
      "source": "live_staging",
      "updateMask": mask_paths,
      "dataAgent": patch_resp.body,
  }


def rollback_agent(
    project: str,
    location: str,
    data_agent_id: str,
    *,
    api_endpoint: str | None = None,
    dry_run: bool = False,
    transport: HttpTransport = _default_http_transport,
    token_provider: Callable[[], str] = resolve_access_token,
) -> dict[str, Any]:
  """Restores `publishedContext` from `lastPublishedContext` via `:updateSync`."""
  _require_valid_coordinates(project, location, data_agent_id)
  base_url = resolve_api_endpoint(location, api_endpoint)

  agent_url = (
      f"{base_url}/projects/{urllib.parse.quote(project, safe='')}"
      f"/locations/{urllib.parse.quote(location, safe='')}"
      f"/dataAgents/{urllib.parse.quote(data_agent_id, safe='')}"
  )
  token = token_provider()
  get_resp = transport("GET", agent_url, None, token)
  if get_resp.status != 200:
    raise SpecError(
        f"GET {agent_url} failed with HTTP {get_resp.status}: "
        f"{json.dumps(get_resp.body)}"
    )

  agent_camel = _normalize_to_camel(get_resp.body)
  last_pub = agent_camel.get("dataAnalyticsAgent", {}).get(
      "lastPublishedContext"
  )
  if not isinstance(last_pub, Mapping) or not last_pub:
    raise SpecError(
        f"DataAgent `{data_agent_id}` has no `lastPublishedContext` to roll "
        "back to."
    )

  patch_body = {
      "dataAnalyticsAgent": {"publishedContext": copy.deepcopy(last_pub)}
  }
  req_id = str(uuid.uuid4())
  update_url = f"{agent_url}:updateSync?" + urllib.parse.urlencode({
      "updateMask": "data_analytics_agent.published_context",
      "requestId": req_id,
  })

  if dry_run:
    return {
        "mode": "dry_run",
        "operation": "rollback",
        "updateUrl": update_url,
        "payload": patch_body,
    }

  patch_resp = transport("PATCH", update_url, patch_body, token)
  if patch_resp.status != 200:
    raise SpecError(
        f"Rollback PATCH failed with HTTP {patch_resp.status}: "
        f"{json.dumps(patch_resp.body)}"
    )
  return {
      "mode": "live",
      "operation": "rolled_back",
      "dataAgent": patch_resp.body,
  }


def export_agent(
    project: str,
    location: str,
    data_agent_id: str,
    *,
    api_endpoint: str | None = None,
    transport: HttpTransport = _default_http_transport,
    token_provider: Callable[[], str] = resolve_access_token,
) -> dict[str, Any]:
  """Fetches a DataAgent and strips output-only timestamps for Git check-in."""
  _require_valid_coordinates(project, location, data_agent_id)
  base_url = resolve_api_endpoint(location, api_endpoint)
  agent_url = (
      f"{base_url}/projects/{urllib.parse.quote(project, safe='')}"
      f"/locations/{urllib.parse.quote(location, safe='')}"
      f"/dataAgents/{urllib.parse.quote(data_agent_id, safe='')}"
  )
  token = token_provider()
  get_resp = transport("GET", agent_url, None, token)
  if get_resp.status != 200:
    raise SpecError(
        f"GET {agent_url} failed with HTTP {get_resp.status}: "
        f"{json.dumps(get_resp.body)}"
    )

  cleaned = {
      k: copy.deepcopy(v)
      for k, v in get_resp.body.items()
      if k not in _OUTPUT_ONLY_AGENT_KEYS and k != "name"
  }
  daa = cleaned.get("dataAnalyticsAgent")
  if isinstance(daa, dict):
    daa.pop("lastPublishedContext", None)
    daa.pop("last_published_context", None)
  return cleaned


def _resolve_target_coordinates(
    args: argparse.Namespace,
    env_camel: Mapping[str, Any],
) -> tuple[str, str, str]:
  project = args.project or env_camel.get("project") or ""
  location = args.location or env_camel.get("location") or "global"
  agent_id = args.agent_id or env_camel.get("dataAgentId") or ""
  return str(project), str(location), str(agent_id)


def _load_standalone_env_camel(env_path: str | None) -> dict[str, Any]:
  """Loads and renders `--env` when invoked without `--spec`."""
  env_camel, _, env_unresolved = _load_and_render_env(env_path)
  if env_unresolved:
    missing = ", ".join(sorted(env_unresolved))
    raise SpecError(
        f"Unresolved template placeholder(s) in {env_path!r}: {missing}"
    )
  return env_camel


def _build_parser() -> argparse.ArgumentParser:
  """Builds the CLI argument parser for bqca_deploy."""
  parser = argparse.ArgumentParser(
      prog="bqca_deploy.py",
      description=(
          "Validate, deploy, promote, roll back, and export BigQuery "
          "Conversational Analytics DataAgents via the GDA v1 REST API."
      ),
  )
  sub = parser.add_subparsers(dest="command", required=True)

  def _add_coord_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--env", help="Path to environment JSON file.")
    p.add_argument("--project", help="GCP project ID hosting the DataAgent.")
    p.add_argument(
        "--location",
        help="DataAgent location (for example: global, us, eu, us-east4).",
    )
    p.add_argument(
        "--agent-id",
        help="DataAgent resource ID (1-63 lowercase chars, AIP-122).",
    )
    p.add_argument(
        "--api-endpoint",
        default=None,
        help=(
            "Optional HTTPS v1 API base URL override. Defaults to automatic "
            "location-based endpoint routing (`global`, `{location}.rep`, or "
            "`-{location}`)."
        ),
    )

  p_val = sub.add_parser(
      "validate",
      help="Validate spec, limits, @param bindings, and optional bq dry runs.",
  )
  p_val.add_argument("--spec", required=True, help="Path to agent JSON spec.")
  p_val.add_argument(
      "--instruction",
      help="Optional path to systemInstruction YAML/Markdown file.",
  )
  p_val.add_argument(
      "--target",
      choices=("staging", "published"),
      default=None,
      help="Optional target context slot when rendering.",
  )
  p_val.add_argument(
      "--allow-unbounded-bytes",
      action="store_true",
      help="Allow missing options.datasource.bigQueryMaxBilledBytes.",
  )
  p_val.add_argument(
      "--bq-dry-run",
      action="store_true",
      help="Run `bq query --dry_run` on every exampleQueries entry.",
  )
  p_val.add_argument(
      "--billing-project",
      help="Billing project for `--bq-dry-run` (defaults to `--project`).",
  )
  _add_coord_flags(p_val)

  p_dep = sub.add_parser(
      "deploy",
      help="Upsert DataAgent into stagingContext or publishedContext.",
  )
  p_dep.add_argument("--spec", required=True, help="Path to agent JSON spec.")
  p_dep.add_argument(
      "--instruction",
      help="Optional path to systemInstruction YAML/Markdown file.",
  )
  p_dep.add_argument(
      "--target",
      choices=("staging", "published"),
      default="staging",
      help="Context slot to deploy (default: staging).",
  )
  p_dep.add_argument(
      "--dry-run",
      action="store_true",
      help="Validate and print planned REST request without mutating GCP.",
  )
  p_dep.add_argument(
      "--allow-unbounded-bytes",
      action="store_true",
      help="Allow missing options.datasource.bigQueryMaxBilledBytes.",
  )
  _add_coord_flags(p_dep)

  p_prom = sub.add_parser(
      "promote",
      help=(
          "Promote stagingContext into publishedContext (from --spec or live "
          "DataAgent) using strict updateMask=data_analytics_agent."
          "published_context."
      ),
  )
  p_prom.add_argument(
      "--spec",
      default=None,
      help=(
          "Optional path to agent JSON spec; if omitted, promotes the live "
          "stagingContext from the existing DataAgent."
      ),
  )
  p_prom.add_argument(
      "--instruction",
      help=(
          "Optional path to systemInstruction YAML/Markdown file "
          "(requires --spec)."
      ),
  )
  p_prom.add_argument(
      "--dry-run",
      action="store_true",
      help="Preview planned promote PATCH without mutating GCP.",
  )
  p_prom.add_argument(
      "--allow-unbounded-bytes",
      action="store_true",
      help="Allow missing options.datasource.bigQueryMaxBilledBytes.",
  )
  _add_coord_flags(p_prom)

  p_rb = sub.add_parser(
      "rollback",
      help="Restore publishedContext from lastPublishedContext.",
  )
  p_rb.add_argument(
      "--dry-run",
      action="store_true",
      help="Fetch agent and preview rollback PATCH without applying it.",
  )
  _add_coord_flags(p_rb)

  p_exp = sub.add_parser(
      "export",
      help="Export an existing DataAgent to clean Git-ready JSON.",
  )
  p_exp.add_argument(
      "--output",
      help="Optional output file path (prints to stdout if omitted).",
  )
  _add_coord_flags(p_exp)

  return parser


def main(argv: Sequence[str] | None = None) -> int:
  parser = _build_parser()
  args = parser.parse_args(argv)

  try:
    if args.command == "validate":
      if args.api_endpoint is not None:
        validate_https_endpoint(args.api_endpoint)
      payload, env_camel = load_and_render_spec(
          args.spec,
          env_path=args.env,
          instruction_path=args.instruction,
          target=args.target,
      )
      project, location, agent_id = _resolve_target_coordinates(args, env_camel)
      res = validate_agent_spec(
          payload,
          project,
          location,
          agent_id,
          allow_unbounded_bytes=args.allow_unbounded_bytes,
      )
      if res.ok:
        resolve_api_endpoint(location, args.api_endpoint)
      if args.bq_dry_run:
        billing_proj = args.billing_project or project
        if not billing_proj:
          res.errors.append(
              "`--bq-dry-run` requires `--billing-project` or `--project`."
          )
        else:
          res.merge(dry_run_example_queries(payload, billing_proj))

      for warning in res.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
      if not res.ok:
        for err in res.errors:
          print(f"ERROR: {err}", file=sys.stderr)
        return 1
      print(
          json.dumps(
              {
                  "status": "ok",
                  "project": project,
                  "location": location,
                  "dataAgentId": agent_id,
                  "warnings": res.warnings,
              },
              indent=2,
          )
      )
      return 0

    if args.command == "deploy":
      payload, env_camel = load_and_render_spec(
          args.spec,
          env_path=args.env,
          instruction_path=args.instruction,
          target=args.target,
      )
      project, location, agent_id = _resolve_target_coordinates(args, env_camel)
      out = deploy_agent(
          payload,
          project,
          location,
          agent_id,
          target=args.target,
          api_endpoint=args.api_endpoint,
          dry_run=args.dry_run,
          allow_unbounded_bytes=args.allow_unbounded_bytes,
      )
      for warning in out.get("warnings", []):
        print(f"WARNING: {warning}", file=sys.stderr)
      print(json.dumps(out, indent=2))
      return 0

    if args.command == "promote":
      if args.spec:
        payload, env_camel = load_and_render_spec(
            args.spec,
            env_path=args.env,
            instruction_path=args.instruction,
            target="staging",
        )
        project, location, agent_id = _resolve_target_coordinates(
            args, env_camel
        )
        out = promote_agent(
            project,
            location,
            agent_id,
            payload=payload,
            api_endpoint=args.api_endpoint,
            dry_run=args.dry_run,
            allow_unbounded_bytes=args.allow_unbounded_bytes,
        )
      else:
        if args.instruction:
          raise SpecError(
              "`--instruction` requires `--spec` when running `promote`."
          )
        env_camel = _load_standalone_env_camel(args.env)
        project, location, agent_id = _resolve_target_coordinates(
            args, env_camel
        )
        out = promote_agent(
            project,
            location,
            agent_id,
            payload=None,
            api_endpoint=args.api_endpoint,
            dry_run=args.dry_run,
            allow_unbounded_bytes=args.allow_unbounded_bytes,
        )
      for warning in out.get("warnings", []):
        print(f"WARNING: {warning}", file=sys.stderr)
      print(json.dumps(out, indent=2))
      return 0

    if args.command == "rollback":
      env_camel = _load_standalone_env_camel(args.env)
      project, location, agent_id = _resolve_target_coordinates(args, env_camel)
      out = rollback_agent(
          project,
          location,
          agent_id,
          api_endpoint=args.api_endpoint,
          dry_run=args.dry_run,
      )
      print(json.dumps(out, indent=2))
      return 0

    if args.command == "export":
      env_camel = _load_standalone_env_camel(args.env)
      project, location, agent_id = _resolve_target_coordinates(args, env_camel)
      exported = export_agent(
          project,
          location,
          agent_id,
          api_endpoint=args.api_endpoint,
      )
      formatted = json.dumps(exported, indent=2) + _NL
      if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
          f.write(formatted)
      else:
        sys.stdout.write(formatted)
      return 0

  except (SpecError, OSError, json.JSONDecodeError) as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1

  return 2


if __name__ == "__main__":
  sys.exit(main())
