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

r"""A standard-library CEL engine for Spark stage diagnostic rules.

Implements the subset of the Common Expression Language
(https://github.com/google/cel-spec) that the Dataproc Data Worker Agent's
`GetSparkStageDiagnostics` tool evaluates rules with: the standard operators,
functions and macros, type-checked against the Dataproc `StageData` and
`ConsolidatedExecutorSummary` protos, with heterogeneous numeric ordering
comparisons enabled. A rule written for that tool compiles, fails to compile,
evaluates and fails to evaluate the same way here; this was checked by
differential testing against that tool's CEL-Java evaluator, including its
quirks (see `_time_arithmetic`, `_time_accessor`, `_format_double`).

Supported:

* Literals: int, uint (`1u`), double, string (quoted, triple-quoted, raw),
  bytes (`b'..'`), bool, null, lists and maps. Map keys may be of any type
  and compare like Java objects (see `CelMap`).
* Message construction with fully qualified names:
  `google.cloud.dataproc.v1.StageData{stage_id: 1}` and
  `google.protobuf.Timestamp{seconds: 0}`. Constructed messages follow proto3
  presence and compare with proto equality, as in CEL-Java.
* Operators: `?:`, `||`, `&&`, `!`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`,
  `+`, `-`, `*`, `/`, `%`, field selection and indexing. `&&`/`||` absorb
  errors the way CEL does (`false && <error>` is `false`).
* Macros: `has`, `all`, `exists`, `exists_one`, `filter`, `map` (two- and
  three-argument), on lists and maps. `has()` on a message field follows
  proto3 presence: always-present for message, timestamp and `optional`
  fields once set, non-default for the others.
* Functions: `size`, `int`, `uint`, `double`, `string`, `bool`, `bytes`,
  `dyn`, `type`, `timestamp`, `duration`, `contains`, `startsWith`,
  `endsWith`, `matches`, and the timestamp/duration accessors (`getHours`,
  ...). Type names (`int`, `list`, `google.cloud.dataproc.v1.StageData`, ...).

Not supported (none is available to the Data Worker Agent's rules either):
CEL extension libraries.

Known deviations: timestamps and durations have microsecond, not nanosecond,
precision (sub-microsecond `nanos` are floored), and timestamps outside years
1-9999 fail to evaluate instead of being accepted; `matches` translates RE2 to
Python `re` (see `_Re2Translator`) and rejects the RE2 constructs it cannot
reproduce exactly (`\p{Script}` classes, and `\p{Lu}`/`\p{Ll}`/`\p{Lt}`/
`\p{Mn}` under `(?i)`); Unicode data and time-zone names resolve against the
host's Python and tz database rather than Java's.
"""

import datetime
import decimal
import fractions
import math
import re
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    NoReturn,
    Optional,
    Set,
    Tuple,
)
import unicodedata
import warnings

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# Fields of every message reachable from the rule variables, from
# google/cloud/dataproc/v1/spark_common.proto. Scalar types use CEL names;
# `list<T>` is a repeated field and `map<K,V>` a map field.
_SCHEMA: Dict[str, Dict[str, str]] = {
    "AccumulableInfo": {
        "accumullable_info_id": "int",
        "name": "string",
        "update": "string",
        "value": "string",
    },
    "ConsolidatedExecutorSummary": {
        "active_tasks": "int",
        "completed_tasks": "int",
        "count": "int",
        "disk_used": "int",
        "failed_tasks": "int",
        "is_excluded": "int",
        "max_memory": "int",
        "memory_metrics": "MemoryMetrics",
        "memory_used": "int",
        "rdd_blocks": "int",
        "total_cores": "int",
        "total_duration_millis": "int",
        "total_gc_time_millis": "int",
        "total_input_bytes": "int",
        "total_shuffle_read": "int",
        "total_shuffle_write": "int",
        "total_tasks": "int",
    },
    "ExecutorMetrics": {
        "metrics": "map<string,int>",
    },
    "ExecutorMetricsDistributions": {
        "disk_bytes_spilled": "list<double>",
        "failed_tasks": "list<double>",
        "input_bytes": "list<double>",
        "input_records": "list<double>",
        "killed_tasks": "list<double>",
        "memory_bytes_spilled": "list<double>",
        "output_bytes": "list<double>",
        "output_records": "list<double>",
        "peak_memory_metrics": "ExecutorPeakMetricsDistributions",
        "quantiles": "list<double>",
        "shuffle_read": "list<double>",
        "shuffle_read_records": "list<double>",
        "shuffle_write": "list<double>",
        "shuffle_write_records": "list<double>",
        "succeeded_tasks": "list<double>",
        "task_time_millis": "list<double>",
    },
    "ExecutorPeakMetricsDistributions": {
        "executor_metrics": "list<ExecutorMetrics>",
        "quantiles": "list<double>",
    },
    "ExecutorStageSummary": {
        "disk_bytes_spilled": "int",
        "executor_id": "string",
        "failed_tasks": "int",
        "input_bytes": "int",
        "input_records": "int",
        "is_excluded_for_stage": "bool",
        "killed_tasks": "int",
        "memory_bytes_spilled": "int",
        "output_bytes": "int",
        "output_records": "int",
        "peak_memory_metrics": "ExecutorMetrics",
        "shuffle_read": "int",
        "shuffle_read_records": "int",
        "shuffle_write": "int",
        "shuffle_write_records": "int",
        "stage_attempt_id": "int",
        "stage_id": "int",
        "succeeded_tasks": "int",
        "task_time_millis": "int",
    },
    "InputMetrics": {
        "bytes_read": "int",
        "records_read": "int",
    },
    "InputQuantileMetrics": {
        "bytes_read": "Quantiles",
        "records_read": "Quantiles",
    },
    "MemoryMetrics": {
        "total_off_heap_storage_memory": "int",
        "total_on_heap_storage_memory": "int",
        "used_off_heap_storage_memory": "int",
        "used_on_heap_storage_memory": "int",
    },
    "OutputMetrics": {
        "bytes_written": "int",
        "records_written": "int",
    },
    "OutputQuantileMetrics": {
        "bytes_written": "Quantiles",
        "records_written": "Quantiles",
    },
    "Quantiles": {
        "count": "int",
        "maximum": "int",
        "minimum": "int",
        "percentile_25": "int",
        "percentile_50": "int",
        "percentile_75": "int",
        "sum": "int",
    },
    "ShufflePushReadMetrics": {
        "corrupt_merged_block_chunks": "int",
        "local_merged_blocks_fetched": "int",
        "local_merged_bytes_read": "int",
        "local_merged_chunks_fetched": "int",
        "merged_fetch_fallback_count": "int",
        "remote_merged_blocks_fetched": "int",
        "remote_merged_bytes_read": "int",
        "remote_merged_chunks_fetched": "int",
        "remote_merged_reqs_duration": "int",
    },
    "ShufflePushReadQuantileMetrics": {
        "corrupt_merged_block_chunks": "Quantiles",
        "local_merged_blocks_fetched": "Quantiles",
        "local_merged_bytes_read": "Quantiles",
        "local_merged_chunks_fetched": "Quantiles",
        "merged_fetch_fallback_count": "Quantiles",
        "remote_merged_blocks_fetched": "Quantiles",
        "remote_merged_bytes_read": "Quantiles",
        "remote_merged_chunks_fetched": "Quantiles",
        "remote_merged_reqs_duration": "Quantiles",
    },
    "ShuffleReadMetrics": {
        "fetch_wait_time_millis": "int",
        "local_blocks_fetched": "int",
        "local_bytes_read": "int",
        "records_read": "int",
        "remote_blocks_fetched": "int",
        "remote_bytes_read": "int",
        "remote_bytes_read_to_disk": "int",
        "remote_reqs_duration": "int",
        "shuffle_push_read_metrics": "ShufflePushReadMetrics",
    },
    "ShuffleReadQuantileMetrics": {
        "fetch_wait_time_millis": "Quantiles",
        "local_blocks_fetched": "Quantiles",
        "read_bytes": "Quantiles",
        "read_records": "Quantiles",
        "remote_blocks_fetched": "Quantiles",
        "remote_bytes_read": "Quantiles",
        "remote_bytes_read_to_disk": "Quantiles",
        "remote_reqs_duration": "Quantiles",
        "shuffle_push_read_metrics": "ShufflePushReadQuantileMetrics",
        "total_blocks_fetched": "Quantiles",
    },
    "ShuffleWriteMetrics": {
        "bytes_written": "int",
        "records_written": "int",
        "write_time_nanos": "int",
    },
    "ShuffleWriteQuantileMetrics": {
        "write_bytes": "Quantiles",
        "write_records": "Quantiles",
        "write_time_nanos": "Quantiles",
    },
    "SpeculationStageSummary": {
        "num_active_tasks": "int",
        "num_completed_tasks": "int",
        "num_failed_tasks": "int",
        "num_killed_tasks": "int",
        "num_tasks": "int",
        "stage_attempt_id": "int",
        "stage_id": "int",
    },
    "StageData": {
        "accumulator_updates": "list<AccumulableInfo>",
        "completion_time": "timestamp",
        "description": "string",
        "details": "string",
        "executor_metrics_distributions": "ExecutorMetricsDistributions",
        "executor_summary": "map<string,ExecutorStageSummary>",
        "failure_reason": "string",
        "first_task_launched_time": "timestamp",
        "is_shuffle_push_enabled": "bool",
        "job_ids": "list<int>",
        "killed_tasks_summary": "map<string,int>",
        "locality": "map<string,int>",
        "name": "string",
        "num_active_tasks": "int",
        "num_complete_tasks": "int",
        "num_completed_indices": "int",
        "num_failed_tasks": "int",
        "num_killed_tasks": "int",
        "num_tasks": "int",
        "parent_stage_ids": "list<int>",
        "peak_executor_metrics": "ExecutorMetrics",
        "rdd_ids": "list<int>",
        "resource_profile_id": "int",
        "scheduling_pool": "string",
        "shuffle_mergers_count": "int",
        "speculation_summary": "SpeculationStageSummary",
        "stage_attempt_id": "int",
        "stage_id": "int",
        "stage_metrics": "StageMetrics",
        "status": "enum:StageStatus",
        "submission_time": "timestamp",
        "task_quantile_metrics": "TaskQuantileMetrics",
        "tasks": "map<int,TaskData>",
    },
    "StageInputMetrics": {
        "bytes_read": "int",
        "records_read": "int",
    },
    "StageMetrics": {
        "disk_bytes_spilled": "int",
        "executor_cpu_time_nanos": "int",
        "executor_deserialize_cpu_time_nanos": "int",
        "executor_deserialize_time_millis": "int",
        "executor_run_time_millis": "int",
        "jvm_gc_time_millis": "int",
        "memory_bytes_spilled": "int",
        "peak_execution_memory_bytes": "int",
        "result_serialization_time_millis": "int",
        "result_size": "int",
        "stage_input_metrics": "StageInputMetrics",
        "stage_output_metrics": "StageOutputMetrics",
        "stage_shuffle_read_metrics": "StageShuffleReadMetrics",
        "stage_shuffle_write_metrics": "StageShuffleWriteMetrics",
    },
    "StageOutputMetrics": {
        "bytes_written": "int",
        "records_written": "int",
    },
    "StageShufflePushReadMetrics": {
        "corrupt_merged_block_chunks": "int",
        "local_merged_blocks_fetched": "int",
        "local_merged_bytes_read": "int",
        "local_merged_chunks_fetched": "int",
        "merged_fetch_fallback_count": "int",
        "remote_merged_blocks_fetched": "int",
        "remote_merged_bytes_read": "int",
        "remote_merged_chunks_fetched": "int",
        "remote_merged_reqs_duration": "int",
    },
    "StageShuffleReadMetrics": {
        "bytes_read": "int",
        "fetch_wait_time_millis": "int",
        "local_blocks_fetched": "int",
        "local_bytes_read": "int",
        "records_read": "int",
        "remote_blocks_fetched": "int",
        "remote_bytes_read": "int",
        "remote_bytes_read_to_disk": "int",
        "remote_reqs_duration": "int",
        "stage_shuffle_push_read_metrics": "StageShufflePushReadMetrics",
    },
    "StageShuffleWriteMetrics": {
        "bytes_written": "int",
        "records_written": "int",
        "write_time_nanos": "int",
    },
    "TaskData": {
        "accumulator_updates": "list<AccumulableInfo>",
        "attempt": "int",
        "duration_millis": "int",
        "error_message": "string",
        "executor_id": "string",
        "executor_logs": "map<string,string>",
        "getting_result_time_millis": "int",
        "has_metrics": "bool",
        "host": "string",
        "index": "int",
        "launch_time": "timestamp",
        "partition_id": "int",
        "result_fetch_start": "timestamp",
        "scheduler_delay_millis": "int",
        "speculative": "bool",
        "stage_attempt_id": "int",
        "stage_id": "int",
        "status": "string",
        "task_id": "int",
        "task_locality": "string",
        "task_metrics": "TaskMetrics",
    },
    "TaskMetrics": {
        "disk_bytes_spilled": "int",
        "executor_cpu_time_nanos": "int",
        "executor_deserialize_cpu_time_nanos": "int",
        "executor_deserialize_time_millis": "int",
        "executor_run_time_millis": "int",
        "input_metrics": "InputMetrics",
        "jvm_gc_time_millis": "int",
        "memory_bytes_spilled": "int",
        "output_metrics": "OutputMetrics",
        "peak_execution_memory_bytes": "int",
        "result_serialization_time_millis": "int",
        "result_size": "int",
        "shuffle_read_metrics": "ShuffleReadMetrics",
        "shuffle_write_metrics": "ShuffleWriteMetrics",
    },
    "TaskQuantileMetrics": {
        "disk_bytes_spilled": "Quantiles",
        "duration_millis": "Quantiles",
        "executor_cpu_time_nanos": "Quantiles",
        "executor_deserialize_cpu_time_nanos": "Quantiles",
        "executor_deserialize_time_millis": "Quantiles",
        "executor_run_time_millis": "Quantiles",
        "getting_result_time_millis": "Quantiles",
        "input_metrics": "InputQuantileMetrics",
        "jvm_gc_time_millis": "Quantiles",
        "memory_bytes_spilled": "Quantiles",
        "output_metrics": "OutputQuantileMetrics",
        "peak_execution_memory_bytes": "Quantiles",
        "result_serialization_time_millis": "Quantiles",
        "result_size": "Quantiles",
        "scheduler_delay_millis": "Quantiles",
        "shuffle_read_metrics": "ShuffleReadQuantileMetrics",
        "shuffle_write_metrics": "ShuffleWriteQuantileMetrics",
    },
}

_ENUMS: Dict[str, Dict[str, int]] = {
    "StageStatus": {
        "STAGE_STATUS_UNSPECIFIED": 0,
        "STAGE_STATUS_ACTIVE": 1,
        "STAGE_STATUS_COMPLETE": 2,
        "STAGE_STATUS_FAILED": 3,
        "STAGE_STATUS_PENDING": 4,
        "STAGE_STATUS_SKIPPED": 5,
    },
}

_PROTO_PACKAGE = "google.cloud.dataproc.v1"

# Scalar fields declared `optional` in the proto. Like message and timestamp
# fields they track presence: has() is true once set, even to the default,
# and presence takes part in message equality.
_EXPLICIT_PRESENCE: Dict[str, FrozenSet[str]] = {
    "AccumulableInfo": frozenset(
        {"accumullable_info_id", "name", "update", "value"}
    ),
    "StageData": frozenset(
        {"description", "details", "failure_reason", "name", "scheduling_pool"}
    ),
    "TaskData": frozenset({
        "duration_millis",
        "error_message",
        "executor_id",
        "host",
        "status",
        "task_locality",
    }),
}

# int32 fields (for map fields: int32 values). Constructing a message with an
# out-of-range value fails, as it does in CEL-Java. Enum fields are int32 too.
_INT32_FIELDS: Dict[str, FrozenSet[str]] = {
    "ConsolidatedExecutorSummary": frozenset({
        "active_tasks",
        "completed_tasks",
        "count",
        "failed_tasks",
        "is_excluded",
        "rdd_blocks",
        "total_cores",
        "total_tasks",
    }),
    "ExecutorStageSummary": frozenset(
        {"failed_tasks", "killed_tasks", "stage_attempt_id", "succeeded_tasks"}
    ),
    "SpeculationStageSummary": frozenset({
        "num_active_tasks",
        "num_completed_tasks",
        "num_failed_tasks",
        "num_killed_tasks",
        "num_tasks",
        "stage_attempt_id",
    }),
    "StageData": frozenset({
        "killed_tasks_summary",
        "num_active_tasks",
        "num_complete_tasks",
        "num_completed_indices",
        "num_failed_tasks",
        "num_killed_tasks",
        "num_tasks",
        "resource_profile_id",
        "shuffle_mergers_count",
        "stage_attempt_id",
    }),
    "TaskData": frozenset(
        {"attempt", "index", "partition_id", "stage_attempt_id"}
    ),
}
_INT32_MIN, _INT32_MAX = -(2**31), 2**31 - 1

# The fields of google.protobuf.Timestamp, which rules may construct.
_TIMESTAMP_MESSAGE = "google.protobuf.Timestamp"
_TIMESTAMP_FIELDS = {"seconds": "int", "nanos": "int"}

# Enum constants must be fully qualified: the 1P environment sets no
# container, so `StageStatus.X` does not resolve there.
_ENUM_CONSTANTS: Dict[str, int] = {}
for _enum, _values in _ENUMS.items():
  for _name, _number in _values.items():
    _ENUM_CONSTANTS[f"{_PROTO_PACKAGE}.{_enum}.{_name}"] = _number

# The variables a Spark stage diagnostic rule is evaluated over.
STAGE_RULE_DECLARATIONS: Dict[str, str] = {
    "stages": "list<StageData>",
    "total_executor_summary": "ConsolidatedExecutorSummary",
}

_INT64_MIN, _INT64_MAX = -(2**63), 2**63 - 1
_UINT64_MAX = 2**64 - 1
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
_DYN = "dyn"
# An unbound type parameter: the element type of an empty `[]` or `{}`.
_FREE = "free"


class CelError(Exception):
  """Base class for every CEL failure."""


class CelSyntaxError(CelError):
  """The expression does not parse."""


class CelTypeError(CelError):
  """The expression parses but fails type-checking."""


class CelEvalError(CelError):
  """Evaluation failed (division by zero, missing map key, overflow, ...)."""


class UInt(int):
  """A CEL `uint` value; distinct from `int` for overload resolution."""

  def __repr__(self) -> str:
    return f"{int(self)}u"


class CelType:
  """A CEL type value, as returned by `type(x)` or named by `int`, `list`..."""

  __slots__ = ("name",)

  def __init__(self, name: str):
    self.name = name

  def __eq__(self, other: Any) -> bool:
    return isinstance(other, CelType) and other.name == self.name

  def __hash__(self) -> int:
    return hash(self.name)

  def __repr__(self) -> str:
    return self.name


# Type identifiers usable in expressions (`type(x) == int`). Messages are
# named by their full proto name; google.protobuf.Duration is deliberately
# absent because, as in the 1P environment, no declared field uses it.
_TYPE_IDENTIFIERS = frozenset(
    {
        "int",
        "uint",
        "double",
        "bool",
        "string",
        "bytes",
        "list",
        "map",
        "null_type",
        "type",
        "dyn",
        "google.protobuf.Timestamp",
    }
    | {f"{_PROTO_PACKAGE}.{name}" for name in _SCHEMA}
)


class Message:
  """A proto message value.

  Messages read from telemetry are backed by their JSON (snake_case or
  camelCase) form and convert fields on access; messages constructed by an
  expression (`built`) hold CEL values, with unset fields absent.
  """

  __slots__ = ("type_name", "data", "built")

  def __init__(
      self,
      type_name: str,
      data: Optional[Dict[str, Any]] = None,
      built: bool = False,
  ):
    self.type_name = type_name
    self.data = data if isinstance(data, dict) else {}
    self.built = built

  def raw(self, field: str) -> Tuple[bool, Any]:
    """Returns (present, raw JSON value) for a snake_case field name."""
    if field in self.data:
      return self.data[field] is not None, self.data[field]
    camel = _snake_to_camel(field)
    if camel in self.data:
      return self.data[camel] is not None, self.data[camel]
    return False, None

  def _field(self, field: str) -> str:
    field_type = _field_type(self.type_name, field)
    if field_type is None:
      raise CelEvalError(f"no such field '{field}' on {self.type_name}")
    return field_type

  def get(self, field: str) -> Any:
    field_type = self._field(field)
    if self.built:
      if field in self.data:
        return self.data[field]
      return default_value(field_type)
    present, raw = self.raw(field)
    return convert(raw, field_type) if present else default_value(field_type)

  def has(self, field: str) -> bool:
    """Proto3 presence: set (explicit presence) or non-default (implicit)."""
    field_type = self._field(field)
    repeated = field_type.startswith(("list<", "map<"))
    if self.built:
      if field not in self.data:
        return False
      value = self.data[field]
      if repeated:
        return len(value) > 0
    else:
      present, value = self.raw(field)
      if not present:
        return False
      if repeated:
        return bool(value)
    if _has_presence(self.type_name, field, field_type):
      return True
    if not self.built:
      value = convert(value, field_type)
    return value != default_value(field_type)

  def proto_key(self) -> Tuple[Any, ...]:
    """A hashable form under which equal protos (Java equals) are equal."""
    return tuple(
        (field, _key_of(self.get(field)))
        for field in sorted(_SCHEMA[self.type_name])
        if self.has(field)
    )

  def __eq__(self, other: Any) -> bool:
    # Proto equality, as CEL-Java uses for messages: presence counts, and
    # doubles compare like java.lang.Double (NaN equals NaN, 0.0 != -0.0).
    return (
        isinstance(other, Message)
        and other.type_name == self.type_name
        and other.proto_key() == self.proto_key()
    )

  def __hash__(self) -> int:
    return hash(self.type_name)

  def __repr__(self) -> str:
    return f"{self.type_name}({self.data!r})"


def _has_presence(message: str, field: str, field_type: str) -> bool:
  return (
      field_type in _SCHEMA
      or field_type == "timestamp"
      or field in _EXPLICIT_PRESENCE.get(message, ())
  )


class CelMap:
  """A CEL map.

  Keys may be of any type and compare like Java objects, as in CEL-Java:
  `1`, `1u`, `1.0` and `true` are distinct keys, NaN equals NaN and 0.0
  differs from -0.0. Iteration follows insertion order.
  """

  __slots__ = ("_entries",)

  def __init__(self, items: Iterable[Tuple[Any, Any]] = ()):
    self._entries: Dict[Any, Tuple[Any, Any]] = {}
    for key, value in items:
      self._entries[_key_of(key)] = (key, value)

  def insert(self, key: Any, value: Any) -> bool:
    """Adds an entry; returns False (and changes nothing) for a duplicate."""
    hashed = _key_of(key)
    if hashed in self._entries:
      return False
    self._entries[hashed] = (key, value)
    return True

  def get_exact(self, key: Any) -> Any:
    """The value stored under exactly `key`, or _MISSING."""
    entry = self._entries.get(_key_of(key))
    return _MISSING if entry is None else entry[1]

  def keys(self) -> List[Any]:
    return [key for key, _ in self._entries.values()]

  def items(self) -> List[Tuple[Any, Any]]:
    return list(self._entries.values())

  def __len__(self) -> int:
    return len(self._entries)

  def __eq__(self, other: Any) -> bool:
    # Java Map.equals; CEL's `==` on maps is _equals, not this.
    return isinstance(other, CelMap) and _key_of(self) == _key_of(other)

  __hash__ = None  # Mutable.

  def __repr__(self) -> str:
    return "{" + ", ".join(f"{k!r}: {v!r}" for k, v in self.items()) + "}"


def _key_of(value: Any) -> Tuple[Any, ...]:
  """A hashable form of a CEL value under Java `equals` semantics."""
  if isinstance(value, bool):
    return ("bool", value)
  if isinstance(value, UInt):
    return ("uint", int(value))
  if isinstance(value, int):
    return ("int", value)
  if isinstance(value, float):
    return ("double", "nan" if math.isnan(value) else value.hex())
  if value is None:
    return ("null",)
  if isinstance(value, (str, bytes)):
    return (type(value).__name__, value)
  if isinstance(value, datetime.datetime):
    return ("timestamp", _micros(value - _EPOCH))
  if isinstance(value, datetime.timedelta):
    return ("duration", _micros(value))
  if isinstance(value, CelType):
    return ("type", value.name)
  if isinstance(value, list):
    return ("list", tuple(_key_of(v) for v in value))
  if isinstance(value, CelMap):
    return (
        "map",
        frozenset((_key_of(k), _key_of(v)) for k, v in value.items()),
    )
  if isinstance(value, Message):
    return ("message", value.type_name, value.proto_key())
  raise CelEvalError(f"unsupported value {value!r}")


def _snake_to_camel(name: str) -> str:
  head, *rest = name.split("_")
  return head + "".join(word.capitalize() for word in rest)


def _field_type(message: str, field: str) -> Optional[str]:
  return _SCHEMA.get(message, {}).get(field)


def _split_generic(type_name: str) -> List[str]:
  """Splits the parameters of `list<..>` / `map<..,..>` at top level."""
  inner = type_name[type_name.index("<") + 1 : -1]
  parts: List[str] = []
  depth = start = 0
  for i, char in enumerate(inner):
    if char == "<":
      depth += 1
    elif char == ">":
      depth -= 1
    elif char == "," and depth == 0:
      parts.append(inner[start:i])
      start = i + 1
  parts.append(inner[start:])
  return parts


def default_value(type_name: str) -> Any:
  """The proto3 default of a field of `type_name`."""
  if type_name.startswith("list<"):
    return []
  if type_name.startswith("map<"):
    return CelMap()
  if type_name in _SCHEMA:
    return Message(type_name)
  return {
      "int": 0,
      "uint": UInt(0),
      "double": 0.0,
      "bool": False,
      "string": "",
      "bytes": b"",
      "timestamp": _EPOCH,
      "duration": datetime.timedelta(0),
  }.get(type_name, 0 if type_name.startswith("enum:") else None)


_INT_STRING = re.compile(r"[+-]?\d+\Z")


def convert(raw: Any, type_name: str) -> Any:
  """Converts a JSON value into the CEL value of a field of `type_name`."""
  if raw is None:
    return default_value(type_name)
  if type_name.startswith("list<"):
    element = _split_generic(type_name)[0]
    return [convert(v, element) for v in raw] if isinstance(raw, list) else []
  if type_name.startswith("map<"):
    params = _split_generic(type_name)
    key_type, value_type = params[0], params[1]
    if not isinstance(raw, dict):
      return CelMap()
    return CelMap(
        (convert(k, key_type), convert(v, value_type)) for k, v in raw.items()
    )
  if type_name in _SCHEMA:
    return Message(type_name, raw if isinstance(raw, dict) else {})
  if type_name in ("int", "uint"):
    if isinstance(raw, str) and _INT_STRING.match(raw.strip()):
      raw = int(raw)
    if isinstance(raw, float) and raw.is_integer():
      raw = int(raw)
    if isinstance(raw, bool) or not isinstance(raw, int):
      raise CelEvalError(f"cannot read {raw!r} as {type_name}")
    return UInt(raw) if type_name == "uint" else raw
  if type_name == "double":
    if isinstance(raw, str):
      try:
        return float(raw)  # "NaN", "Infinity" and "-Infinity" included.
      except ValueError as e:
        raise CelEvalError(f"cannot read {raw!r} as double") from e
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
      raise CelEvalError(f"cannot read {raw!r} as double")
    return float(raw)
  if type_name.startswith("enum:"):
    values = _ENUMS[type_name[5:]]
    if isinstance(raw, str):
      if raw in values:
        return values[raw]
      if _INT_STRING.match(raw):
        return int(raw)
      raise CelEvalError(f"unknown {type_name[5:]} value {raw!r}")
    return int(raw)
  if type_name == "timestamp":
    return _parse_timestamp(raw)
  if type_name == "bool":
    return bool(raw)
  if type_name == "string":
    return str(raw)
  if type_name == "bytes":
    import base64  # pylint: disable=g-import-not-at-top

    return base64.b64decode(raw) if isinstance(raw, str) else bytes(raw)
  return raw


def from_json(value: Any) -> Any:
  """Converts an untyped JSON value (no schema) into a CEL value."""
  if isinstance(value, dict):
    return CelMap((k, from_json(v)) for k, v in value.items())
  if isinstance(value, list):
    return [from_json(v) for v in value]
  return value


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

_PUNCTUATION = (
    "&&",
    "||",
    "==",
    "!=",
    "<=",
    ">=",
    "<",
    ">",
    "!",
    "+",
    "-",
    "*",
    "/",
    "%",
    "?",
    ":",
    ".",
    ",",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
)
_RESERVED = frozenset({
    "as",
    "break",
    "const",
    "continue",
    "else",
    "for",
    "function",
    "if",
    "import",
    "let",
    "loop",
    "package",
    "namespace",
    "return",
    "var",
    "void",
    "while",
})
_NUMBER = re.compile(
    r"0[xX][0-9a-fA-F]+[uU]?" r"|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[uU]?"
)
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SIMPLE_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "`": "`",
    "?": "?",
}


class _Token:
  __slots__ = ("kind", "value", "pos")

  def __init__(self, kind: str, value: Any, pos: int):
    self.kind, self.value, self.pos = kind, value, pos

  def __repr__(self) -> str:
    return f"{self.kind}:{self.value!r}"


def _unescape(body: str, raw: bool, is_bytes: bool, pos: int) -> Any:
  """Decodes the escape sequences of a CEL string or bytes literal."""
  if raw:
    return body.encode("utf-8") if is_bytes else body
  out: List[str] = []
  i = 0
  while i < len(body):
    char = body[i]
    if char != "\\":
      out.append(char)
      i += 1
      continue
    if i + 1 >= len(body):
      raise CelSyntaxError(f"invalid escape at offset {pos + i}")
    esc = body[i + 1]
    if esc in _SIMPLE_ESCAPES:
      out.append(_SIMPLE_ESCAPES[esc])
      i += 2
    elif esc in "xX" and re.fullmatch(r"[0-9a-fA-F]{2}", body[i + 2 : i + 4]):
      out.append(chr(int(body[i + 2 : i + 4], 16)))
      i += 4
    elif esc == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", body[i + 2 : i + 6]):
      out.append(chr(int(body[i + 2 : i + 6], 16)))
      i += 6
    elif esc == "U" and re.fullmatch(r"[0-9a-fA-F]{8}", body[i + 2 : i + 10]):
      out.append(chr(int(body[i + 2 : i + 10], 16)))
      i += 10
    elif re.fullmatch(r"[0-3][0-7]{2}", body[i + 1 : i + 4]):
      out.append(chr(int(body[i + 1 : i + 4], 8)))
      i += 4
    else:
      raise CelSyntaxError(f"invalid escape '\\{esc}' at offset {pos + i}")
  text = "".join(out)
  if not is_bytes:
    return text
  try:
    return text.encode("latin-1")  # \xHH and octal escapes are raw bytes.
  except UnicodeEncodeError:
    return text.encode("utf-8")


def _tokenize(text: str) -> List[_Token]:
  """Splits CEL source text into tokens."""
  tokens: List[_Token] = []
  i, n = 0, len(text)
  while i < n:
    char = text[i]
    if char.isspace():
      i += 1
      continue
    if text.startswith("//", i):
      end = text.find("\n", i)
      i = n if end < 0 else end + 1
      continue
    # String and bytes literals, with optional r/b prefixes.
    match = re.search(r"^([rRbB]{0,2})('''|\"\"\"|'|\")", text[i:])
    if match and (
        not match.group(1) or set(match.group(1).lower()) <= {"r", "b"}
    ):
      prefix, quote = match.group(1).lower(), match.group(2)
      start = i + len(match.group(0))
      j = start
      while True:
        if j >= n:
          raise CelSyntaxError(f"unterminated string starting at offset {i}")
        if text.startswith(quote, j):
          break
        if text[j] == "\\" and "r" not in prefix:
          j += 2
          continue
        if text[j] == "\n" and len(quote) == 1:
          raise CelSyntaxError(f"newline in string starting at offset {i}")
        j += 1
      value = _unescape(text[start:j], "r" in prefix, "b" in prefix, start)
      tokens.append(_Token("bytes" if "b" in prefix else "string", value, i))
      i = j + len(quote)
      continue
    match = _NUMBER.match(text, i)
    if match and (char.isdigit() or (char == "." and match.end() > i + 1)):
      literal = match.group(0)
      unsigned = literal[-1] in "uU"
      body = literal[:-1] if unsigned else literal
      if body.lower().startswith("0x"):
        value: Any = int(body, 16)
      elif not unsigned and re.search(r"[.eE]", body):
        value = float(body)
      elif re.search(r"[.eE]", body):
        raise CelSyntaxError(f"invalid uint literal '{literal}'")
      else:
        value = int(body)
      if unsigned:
        if value > _UINT64_MAX:
          raise CelSyntaxError(f"uint literal out of range: {literal}")
        tokens.append(_Token("uint", UInt(value), i))
      elif isinstance(value, float):
        tokens.append(_Token("double", value, i))
      else:
        tokens.append(_Token("int", value, i))
      i = match.end()
      continue
    match = _IDENT.match(text, i)
    if match:
      word = match.group(0)
      if word in ("true", "false"):
        tokens.append(_Token("bool", word == "true", i))
      elif word == "null":
        tokens.append(_Token("null", None, i))
      elif word == "in":
        tokens.append(_Token("op", "in", i))
      else:
        tokens.append(_Token("ident", word, i))
      i = match.end()
      continue
    for punct in _PUNCTUATION:
      if text.startswith(punct, i):
        tokens.append(_Token("op", punct, i))
        i += len(punct)
        break
    else:
      raise CelSyntaxError(f"unexpected character {char!r} at offset {i}")
  tokens.append(_Token("eof", None, n))
  return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
#
# AST nodes are tuples whose first element is the node kind:
#   ("lit", value)                 ("ident", name)
#   ("select", operand, field)     ("index", operand, key)
#   ("call", name, target, args)   ("list", elements)
#   ("map", [(key, value), ...])   ("cond", test, if_true, if_false)
#   ("and", left, right)           ("or", left, right)
#   ("not", operand)               ("neg", operand)
#   ("binop", op, left, right)     ("has", select_node)
#   ("comprehension", macro, range, var, args)

_MACROS = {
    "all": (2,),
    "exists": (2,),
    "exists_one": (2,),
    "filter": (2,),
    "map": (2, 3),
}
_RELATIONS = ("==", "!=", "<", "<=", ">", ">=", "in")
_MAX_DEPTH = 250


class _Parser:
  """A recursive-descent parser for the CEL grammar."""

  def __init__(self, text: str):
    self._tokens = _tokenize(text)
    self._pos = 0
    self._depth = 0

  def parse(self) -> Tuple[Any, ...]:
    node = self._expr()
    token = self._peek()
    if token.kind != "eof":
      raise CelSyntaxError(f"unexpected {token.value!r} at offset {token.pos}")
    return node

  def _peek(self) -> _Token:
    return self._tokens[self._pos]

  def _next(self) -> _Token:
    token = self._tokens[self._pos]
    self._pos += 1
    return token

  def _accept(self, op: str) -> bool:
    token = self._peek()
    if token.kind == "op" and token.value == op:
      self._pos += 1
      return True
    return False

  def _expect(self, op: str) -> None:
    if not self._accept(op):
      token = self._peek()
      found = "end of expression" if token.kind == "eof" else repr(token.value)
      raise CelSyntaxError(
          f"expected '{op}' but found {found} at offset {token.pos}"
      )

  def _expr(self) -> Tuple[Any, ...]:
    """Parses a conditional expression (the lowest precedence level)."""
    self._depth += 1
    if self._depth > _MAX_DEPTH:
      raise CelSyntaxError("expression is nested too deeply")
    try:
      test = self._or()
      if self._accept("?"):
        if_true = self._or()
        self._expect(":")
        if_false = self._expr()
        return ("cond", test, if_true, if_false)
      return test
    finally:
      self._depth -= 1

  def _or(self) -> Tuple[Any, ...]:
    node = self._and()
    while self._accept("||"):
      node = ("or", node, self._and())
    return node

  def _and(self) -> Tuple[Any, ...]:
    node = self._relation()
    while self._accept("&&"):
      node = ("and", node, self._relation())
    return node

  def _relation(self) -> Tuple[Any, ...]:
    node = self._addition()
    while True:
      token = self._peek()
      if token.kind == "op" and token.value in _RELATIONS:
        self._pos += 1
        node = ("binop", token.value, node, self._addition())
      else:
        return node

  def _addition(self) -> Tuple[Any, ...]:
    node = self._multiplication()
    while True:
      token = self._peek()
      if token.kind == "op" and token.value in ("+", "-"):
        self._pos += 1
        node = ("binop", token.value, node, self._multiplication())
      else:
        return node

  def _multiplication(self) -> Tuple[Any, ...]:
    node = self._unary()
    while True:
      token = self._peek()
      if token.kind == "op" and token.value in ("*", "/", "%"):
        self._pos += 1
        node = ("binop", token.value, node, self._unary())
      else:
        return node

  def _unary(self) -> Tuple[Any, ...]:
    """Parses `!` and unary `-` prefixes."""
    if self._accept("!"):
      return ("not", self._unary())
    if self._accept("-"):
      token = self._peek()
      # Fold negative literals so that -9223372036854775808 is representable.
      if token.kind in ("int", "double"):
        after = self._tokens[self._pos + 1]
        if not (after.kind == "op" and after.value in (".", "[")):
          self._pos += 1
          value = -token.value
          if token.kind == "int" and value < _INT64_MIN:
            raise CelSyntaxError(f"int literal out of range at {token.pos}")
          return ("lit", value)
      return ("neg", self._unary())
    return self._member()

  def _member(self) -> Tuple[Any, ...]:
    """Parses field selections, indexing and method calls."""
    node = self._primary()
    while True:
      if self._accept("."):
        token = self._next()
        if token.kind != "ident":
          raise CelSyntaxError(f"expected a field name at offset {token.pos}")
        if self._accept("("):
          args = self._arguments(")")
          node = self._call(token.value, node, args, token.pos)
        else:
          node = ("select", node, token.value)
      elif self._accept("["):
        key = self._expr()
        self._expect("]")
        node = ("index", node, key)
      else:
        return node

  def _arguments(self, close: str) -> List[Tuple[Any, ...]]:
    args: List[Tuple[Any, ...]] = []
    if self._accept(close):
      return args
    while True:
      args.append(self._expr())
      if self._accept(close):
        return args
      self._expect(",")
      if close == "]" and self._accept(close):  # Trailing comma.
        return args

  def _call(
      self,
      name: str,
      target: Optional[Tuple[Any, ...]],
      args: List[Tuple[Any, ...]],
      pos: int,
  ) -> Tuple[Any, ...]:
    """Builds the node for a function or method call, expanding macros."""
    if target is None and name == "has":
      if len(args) != 1 or args[0][0] != "select":
        raise CelSyntaxError(
            f"has() requires a single field selection argument (offset {pos})"
        )
      return ("has", args[0])
    if target is not None and name in _MACROS and len(args) in _MACROS[name]:
      var = args[0]
      if var[0] != "ident":
        raise CelSyntaxError(
            f"{name}() requires a variable name as its first argument"
            f" (offset {pos})"
        )
      return ("comprehension", name, target, var[1], args[1:])
    return ("call", name, target, args)

  def _message_name(self, first: str) -> Optional[str]:
    """Consumes `.b.C{` after identifier `first` if it starts a message.

    Args:
      first: The identifier just consumed.

    Returns:
      The dotted message name, with the opening brace consumed; None (and
      nothing consumed) when no message construction follows.
    """
    parts, pos = [first], self._pos
    tokens = self._tokens
    while (
        tokens[pos].kind == "op"
        and tokens[pos].value == "."
        and tokens[pos + 1].kind == "ident"
    ):
      parts.append(tokens[pos + 1].value)
      pos += 2
    if tokens[pos].kind == "op" and tokens[pos].value == "{":
      self._pos = pos + 1
      return ".".join(parts)
    return None

  def _field_inits(self) -> List[Tuple[str, Tuple[Any, ...]]]:
    """Parses `field: expr, ...}` of a message construction."""
    fields: List[Tuple[str, Tuple[Any, ...]]] = []
    if self._accept("}"):
      return fields
    while True:
      token = self._next()
      if token.kind != "ident":
        raise CelSyntaxError(f"expected a field name at offset {token.pos}")
      self._expect(":")
      fields.append((token.value, self._expr()))
      if self._accept("}"):
        return fields
      self._expect(",")
      if self._accept("}"):  # Trailing comma.
        return fields

  def _primary(self) -> Tuple[Any, ...]:
    """Parses literals, identifiers, calls, messages, lists and maps."""
    token = self._next()
    if token.kind in ("int", "uint", "double", "string", "bytes", "bool"):
      if token.kind == "int" and token.value > _INT64_MAX:
        raise CelSyntaxError(f"int literal out of range at {token.pos}")
      return ("lit", token.value)
    if token.kind == "null":
      return ("lit", None)
    if token.kind == "op" and token.value == ".":
      token = self._next()
      if token.kind != "ident":
        raise CelSyntaxError(f"expected an identifier at offset {token.pos}")
    if token.kind == "ident":
      if token.value in _RESERVED:
        raise CelSyntaxError(
            f"reserved identifier '{token.value}' at offset {token.pos}"
        )
      if self._accept("("):
        return self._call(token.value, None, self._arguments(")"), token.pos)
      name = self._message_name(token.value)
      if name is not None:
        return ("msg", name, self._field_inits())
      return ("ident", token.value)
    if token.kind == "op" and token.value == "(":
      node = self._expr()
      self._expect(")")
      return node
    if token.kind == "op" and token.value == "[":
      return ("list", self._arguments("]"))
    if token.kind == "op" and token.value == "{":
      entries = []
      if not self._accept("}"):
        while True:
          key = self._expr()
          self._expect(":")
          entries.append((key, self._expr()))
          if self._accept("}"):
            break
          self._expect(",")
          if self._accept("}"):
            break
      return ("map", entries)
    found = "end of expression" if token.kind == "eof" else repr(token.value)
    raise CelSyntaxError(f"unexpected {found} at offset {token.pos}")


# ---------------------------------------------------------------------------
# Type checker
# ---------------------------------------------------------------------------

_NUMERIC = frozenset({"int", "uint", "double"})
_ORDERING = ("<", "<=", ">", ">=")
_ORDERED = frozenset({
    "int",
    "uint",
    "double",
    "string",
    "bytes",
    "bool",
    "timestamp",
    "duration",
})

# Binary operator overloads, as declared by CEL-Java's standard library with
# heterogeneous numeric ordering enabled: op -> [((left, right), result)].
# `list` stands for list<A> + list<A> -> list<A>.
_ORDERED_OVERLOADS: List[Tuple[Tuple[str, str], str]] = [
    ((t, t), "bool") for t in sorted(_ORDERED)
]
for _left in sorted(_NUMERIC):
  for _right in sorted(_NUMERIC - {_left}):
    _ORDERED_OVERLOADS.append(((_left, _right), "bool"))
_OPERATORS: Dict[str, List[Tuple[Tuple[str, str], str]]] = {
    op: _ORDERED_OVERLOADS for op in _ORDERING
}
_OPERATORS.update({
    "+": [
        (("int", "int"), "int"),
        (("uint", "uint"), "uint"),
        (("double", "double"), "double"),
        (("string", "string"), "string"),
        (("bytes", "bytes"), "bytes"),
        (("list<free>", "list<free>"), "list"),
        (("timestamp", "duration"), "timestamp"),
        (("duration", "timestamp"), "timestamp"),
        (("duration", "duration"), "duration"),
    ],
    "-": [
        (("int", "int"), "int"),
        (("uint", "uint"), "uint"),
        (("double", "double"), "double"),
        (("timestamp", "timestamp"), "duration"),
        (("timestamp", "duration"), "timestamp"),
        (("duration", "duration"), "duration"),
    ],
    "*": [
        (("int", "int"), "int"),
        (("uint", "uint"), "uint"),
        (("double", "double"), "double"),
    ],
    "/": [
        (("int", "int"), "int"),
        (("uint", "uint"), "uint"),
        (("double", "double"), "double"),
    ],
    "%": [(("int", "int"), "int"), (("uint", "uint"), "uint")],
})


# Parameter types of `_FUNCTIONS` keys that are kinds rather than types.
_OVERLOAD_PARAMS = {"list": "list<free>", "map": "map<free,free>"}

# Global functions: name -> {argument type: result type}. `*` matches any.
_FUNCTIONS: Dict[str, Dict[str, str]] = {
    "size": {"string": "int", "bytes": "int", "list": "int", "map": "int"},
    "int": {
        "int": "int",
        "uint": "int",
        "double": "int",
        "string": "int",
        "timestamp": "int",
    },
    "uint": {"int": "uint", "uint": "uint", "double": "uint", "string": "uint"},
    "double": {
        "int": "double",
        "uint": "double",
        "double": "double",
        "string": "double",
    },
    "string": {
        "int": "string",
        "uint": "string",
        "double": "string",
        "string": "string",
        "bytes": "string",
        "bool": "string",
        "timestamp": "string",
        "duration": "string",
    },
    "bool": {"bool": "bool", "string": "bool"},
    "bytes": {"bytes": "bytes", "string": "bytes"},
    "timestamp": {
        "string": "timestamp",
        "timestamp": "timestamp",
        "int": "timestamp",
    },
    "duration": {"string": "duration", "duration": "duration"},
    "dyn": {"*": _DYN},
    "type": {"*": "type"},
}
_STRING_METHODS = {
    "contains": "bool",
    "startsWith": "bool",
    "endsWith": "bool",
    "matches": "bool",
}
_TIME_METHODS = frozenset({
    "getFullYear",
    "getMonth",
    "getDayOfYear",
    "getDayOfMonth",
    "getDate",
    "getDayOfWeek",
    "getHours",
    "getMinutes",
    "getSeconds",
    "getMilliseconds",
})
_DURATION_METHODS = frozenset(
    {"getHours", "getMinutes", "getSeconds", "getMilliseconds"}
)


def _kind(type_name: str) -> str:
  """Collapses parameterized types to their kind (`list`, `map`, `message`)."""
  if type_name.startswith("list<"):
    return "list"
  if type_name.startswith("map<"):
    return "map"
  if type_name.startswith("enum:"):
    return "int"
  if type_name in _SCHEMA:
    return "message"
  return type_name


def _describe(type_name: str) -> str:
  return "int" if type_name.startswith("enum:") else type_name


class _Checker:
  """Infers expression types, rejecting what the CEL type-checker rejects.

  Types are strings: CEL primitive names, message names, `list<T>`,
  `map<K,V>`, `null` and `dyn`. Anything involving `dyn` is accepted and
  checked at evaluation time instead.
  """

  def __init__(self, declarations: Dict[str, str]):
    self._declarations = declarations
    self.free: Set[str] = set()

  def check(self, node: Tuple[Any, ...], scope: Dict[str, str]) -> str:
    kind = node[0]
    method = getattr(self, "_check_" + kind)
    return method(node, scope)

  def _check_lit(self, node, scope) -> str:
    del scope
    return _literal_type(node[1])

  def _check_ident(self, node, scope) -> str:
    name = node[1]
    if name in scope:
      return scope[name]
    if name in self._declarations:
      self.free.add(name)
      return self._declarations[name]
    if name in _TYPE_IDENTIFIERS:
      return "type"
    raise CelTypeError(f"undeclared reference to '{name}'")

  def _check_select(self, node, scope) -> str:
    """Types `a.b`: a field, a map entry, or a qualified name."""
    qualified = _qualified_name(node)
    root = qualified.split(".")[0] if qualified else None
    if root and root not in scope and root not in self._declarations:
      if qualified in _ENUM_CONSTANTS:
        return "int"
      if qualified in _TYPE_IDENTIFIERS:
        return "type"
      if any(
          c.startswith(qualified.rsplit(".", 1)[0] + ".")
          for c in _ENUM_CONSTANTS
      ):
        raise CelTypeError(f"undeclared reference to '{qualified}'")
      raise CelTypeError(f"undeclared reference to '{root}'")
    operand = self.check(node[1], scope)
    return _select_type(operand, node[2])

  def _check_has(self, node, scope) -> str:
    select = node[1]
    operand = self.check(select[1], scope)
    _select_type(operand, select[2])
    return "bool"

  def _check_index(self, node, scope) -> str:
    """Types `a[b]` on lists and maps."""
    operand = self.check(node[1], scope)
    key = self.check(node[2], scope)
    kind = _kind(operand)
    if kind == "list":
      if _kind(key) not in ("int", _DYN):
        raise CelTypeError(f"list index must be int, not {_describe(key)}")
      return _bound(_split_generic(operand)[0])
    if kind == "map":
      params = _split_generic(operand)
      key_type, value_type = params[0], params[1]
      if not _unifies(key_type, key):
        raise CelTypeError(
            f"map key must be {_describe(key_type)}, not {_describe(key)}"
        )
      return _bound(value_type)
    if operand == _DYN:
      return _DYN
    raise CelTypeError(f"type '{_describe(operand)}' does not support indexing")

  def _check_list(self, node, scope) -> str:
    types = [self.check(e, scope) for e in node[1]]
    return f"list<{_join(types)}>"

  def _check_map(self, node, scope) -> str:
    # CEL-Java accepts keys of any type (double, list, message, ...).
    keys = [self.check(k, scope) for k, _ in node[1]]
    values = [self.check(v, scope) for _, v in node[1]]
    return f"map<{_join(keys)},{_join(values)}>"

  def _check_msg(self, node, scope) -> str:
    """Types a message construction, checking every field value."""
    _, name, fields = node
    prefix = _PROTO_PACKAGE + "."
    if name == _TIMESTAMP_MESSAGE:
      result, schema = "timestamp", _TIMESTAMP_FIELDS
    elif name.startswith(prefix) and name[len(prefix) :] in _SCHEMA:
      result = name[len(prefix) :]
      schema = _SCHEMA[result]
    else:
      raise CelTypeError(
          f"undeclared reference to message type '{name}' (use the full"
          f" name, e.g. {prefix}StageData)"
      )
    for field, value_node in fields:
      field_type = schema.get(field)
      if field_type is None:
        raise CelTypeError(
            f"undefined field '{field}' on {name}; valid fields:"
            f" {', '.join(sorted(schema))}"
        )
      value_type = self.check(value_node, scope)
      if not _unifies(field_type, value_type):
        raise CelTypeError(
            f"field '{field}' of {name} expects {_describe(field_type)}, not"
            f" {_describe(value_type)}"
        )
    return result

  def _check_cond(self, node, scope) -> str:
    _require_bool(self.check(node[1], scope), "?:")
    if_true = self.check(node[2], scope)
    if_false = self.check(node[3], scope)
    # `_?_:_` is (bool, A, A) -> A: the branches must unify.
    if not _unifies(if_true, if_false):
      raise CelTypeError(
          "no matching overload for '_?_:_' applied to '(bool,"
          f" {_describe(if_true)}, {_describe(if_false)})'"
      )
    return _most_general(if_false, if_true)

  def _check_and(self, node, scope) -> str:
    _require_bool(self.check(node[1], scope), "&&")
    _require_bool(self.check(node[2], scope), "&&")
    return "bool"

  _check_or = _check_and

  def _check_not(self, node, scope) -> str:
    _require_bool(self.check(node[1], scope), "!")
    return "bool"

  def _check_neg(self, node, scope) -> str:
    operand = self.check(node[1], scope)
    if _kind(operand) not in ("int", "double", _DYN):
      raise CelTypeError(
          f"no matching overload for '-_' applied to '{_describe(operand)}'"
      )
    return _describe(operand)

  def _check_binop(self, node, scope) -> str:
    """Types a binary operator by CEL-Java's overload resolution."""
    op = node[1]
    left = self.check(node[2], scope)
    right = self.check(node[3], scope)
    lk, rk = _kind(left), _kind(right)
    signature = f"'_{op}_' applied to '({_describe(left)}, {_describe(right)})'"
    numeric_hint = (
        "; CEL does not mix int, uint and double in ==, != or `in` -- write"
        " the literal in the field's type (e.g. 12 rather than 12.0) or"
        " convert with double(...) / int(...)"
    )
    if op in ("==", "!="):
      if not _unifies(left, right):
        enum = next((t for t in (left, right) if t.startswith("enum:")), None)
        if enum:
          example = next(n for n, v in _ENUMS[enum[5:]].items() if v)
          raise CelTypeError(
              f"no matching overload for {signature}; enum fields are ints"
              f" in CEL: compare with {_PROTO_PACKAGE}.{enum[5:]}.<VALUE>"
              f" (e.g. {_PROTO_PACKAGE}.{enum[5:]}.{example}) or the number"
          )
        hint = numeric_hint if lk in _NUMERIC and rk in _NUMERIC else ""
        raise CelTypeError(f"no matching overload for {signature}{hint}")
      return "bool"
    if op == "in":
      if _is_top(right):
        return "bool"
      if rk not in ("list", "map"):
        raise CelTypeError(f"no matching overload for {signature}")
      element = _params(right)[0]
      if not _unifies(left, element):
        hint = (
            numeric_hint
            if lk in _NUMERIC and _kind(element) in _NUMERIC
            else ""
        )
        raise CelTypeError(f"no matching overload for {signature}{hint}")
      return "bool"
    results = []
    for params, result in _OPERATORS[op]:
      if not (_unifies(params[0], left) and _unifies(params[1], right)):
        continue
      if result == "list":  # list<A> + list<A> -> list<A>
        elements = [_params(t)[0] for t in (left, right) if _kind(t) == "list"]
        if len(elements) == 2 and not _unifies(*elements):
          continue
        if len(elements) == 2:
          result = f"list<{_most_general(elements[1], elements[0])}>"
        else:
          result = f"list<{elements[0] if elements else _DYN}>"
      results.append(result)
    if not results:
      if op not in _ORDERING and lk in _NUMERIC and rk in _NUMERIC:
        if lk != rk:
          raise CelTypeError(
              f"no matching overload for {signature}; CEL does not mix int,"
              " uint and double in arithmetic -- convert with double(...) or"
              " int(...)"
          )
      raise CelTypeError(f"no matching overload for {signature}")
    # As in CEL-Java: several matching overloads with different result
    # types (possible with dyn or null operands) give dyn.
    return results[0] if len(set(results)) == 1 else _DYN

  def _check_call(self, node, scope) -> str:
    """Types a global function or method call."""
    _, name, target, args = node
    arg_types = [self.check(a, scope) for a in args]
    if target is None:
      if name == "matches" and len(args) == 2:
        for t in arg_types:
          if _kind(t) not in ("string", _DYN):
            raise CelTypeError("matches() expects (string, string)")
        return "bool"
      overloads = _FUNCTIONS.get(name)
      if overloads is None:
        raise CelTypeError(f"undeclared reference to function '{name}'")
      if len(args) != 1:
        raise CelTypeError(f"{name}() takes exactly one argument")
      if "*" in overloads:
        return overloads["*"]
      results = {
          result
          for param, result in overloads.items()
          if _unifies(_OVERLOAD_PARAMS.get(param, param), arg_types[0])
      }
      if not results:
        raise CelTypeError(
            f"no matching overload for '{name}' applied to"
            f" '({_describe(arg_types[0])})'"
        )
      return results.pop() if len(results) == 1 else _DYN
    target_type = self.check(target, scope)
    tk = _kind(target_type)
    if name == "size" and not args:
      if tk not in ("string", "bytes", "list", "map", _DYN):
        raise CelTypeError(
            f"no matching overload for 'size' on '{_describe(target_type)}'"
        )
      return "int"
    if name in _STRING_METHODS:
      if tk not in ("string", _DYN) or len(args) != 1:
        raise CelTypeError(
            f"{name}() is a string method taking one string argument"
        )
      if _kind(arg_types[0]) not in ("string", _DYN):
        raise CelTypeError(f"{name}() expects a string argument")
      return _STRING_METHODS[name]
    # A null receiver matches the timestamp (and duration) overloads.
    if name in _TIME_METHODS and tk in ("timestamp", "duration", _DYN, "null"):
      if tk == "duration" and (name not in _DURATION_METHODS or args):
        raise CelTypeError(f"no matching overload for '{name}' on duration")
      if len(args) > 1 or (
          args and _kind(arg_types[0]) not in ("string", _DYN)
      ):
        raise CelTypeError(f"{name}() takes an optional time zone string")
      return "int"
    raise CelTypeError(
        f"undeclared reference to function '{name}' on"
        f" '{_describe(target_type)}'"
    )

  def _check_comprehension(self, node, scope) -> str:
    """Types a macro, binding its variable in a nested scope."""
    _, macro, range_node, var, args = node
    range_type = self.check(range_node, scope)
    rk = _kind(range_type)
    if rk in ("list", "map"):
      element = _bound(_split_generic(range_type)[0])
    elif range_type == _DYN:
      element = _DYN
    else:
      raise CelTypeError(
          f"{macro}() needs a list or map, not {_describe(range_type)}"
      )
    inner = dict(scope)
    inner[var] = element
    if macro == "map":
      if len(args) == 2:
        _require_bool(self.check(args[0], inner), "map filter")
      return f"list<{self.check(args[-1], inner)}>"
    _require_bool(self.check(args[0], inner), macro)
    if macro == "filter":
      return f"list<{element}>"
    return "bool"


def _select_type(operand: str, field: str) -> str:
  """The type of selecting `field` from a value of type `operand`."""
  kind = _kind(operand)
  if kind == "message":
    field_type = _field_type(operand, field)
    if field_type is None:
      raise CelTypeError(
          f"undefined field '{field}' on {operand}; valid fields:"
          f" {', '.join(sorted(_SCHEMA[operand]))}"
      )
    return field_type
  if kind == "map":
    params = _split_generic(operand)
    key_type, value_type = params[0], params[1]
    if key_type not in ("string", _DYN, _FREE):
      raise CelTypeError(f"cannot select '{field}' from {operand}")
    return _bound(value_type)
  if operand == _DYN:
    return _DYN
  raise CelTypeError(
      f"type '{_describe(operand)}' does not support field selection"
      f" ('.{field}')"
  )


def _require_bool(type_name: str, where: str) -> None:
  if type_name not in ("bool", _DYN):
    raise CelTypeError(
        f"'{where}' requires a bool operand, not {_describe(type_name)}"
    )


def _literal_type(value: Any) -> str:
  """The checker type of a literal value."""
  if value is None:
    return "null"
  if isinstance(value, bool):
    return "bool"
  if isinstance(value, UInt):
    return "uint"
  if isinstance(value, int):
    return "int"
  if isinstance(value, float):
    return "double"
  if isinstance(value, str):
    return "string"
  if isinstance(value, bytes):
    return "bytes"
  return _DYN


def _is_top(type_name: str) -> bool:
  """Whether a type accepts anything: `dyn` or an unbound type parameter."""
  return type_name in (_DYN, _FREE)


def _nullable(type_name: str) -> bool:
  """Whether null is assignable to the type (message and well-known types)."""
  return type_name in ("null", "timestamp", "duration") or type_name in _SCHEMA


def _params(type_name: str) -> List[str]:
  """The type parameters of a list or map type."""
  if type_name in ("list", "map"):
    return [_DYN] * (1 if type_name == "list" else 2)
  return _split_generic(type_name)


def _unifies(a: str, b: str) -> bool:
  """CEL-Java's type assignability between checker types `a` and `b`.

  Decides `==`, `!=`, `in`, map keys, message fields, `?:` branches and
  overload parameters. `int`, `uint` and `double` do not mix (only the
  ordering operators have heterogeneous overloads); null fits only nullable
  types; `dyn` fits anything.

  Args:
    a: A checker type.
    b: A checker type.

  Returns:
    True if the types unify.
  """
  if _is_top(a) or _is_top(b):
    return True
  if "null" in (a, b):
    return _nullable(a) and _nullable(b)
  ka, kb = _kind(a), _kind(b)
  if ka != kb:
    return False
  if ka == "message":
    return a == b
  if ka in ("list", "map"):
    return all(_unifies(x, y) for x, y in zip(_params(a), _params(b)))
  return True


def _less_specific(a: str, b: str) -> bool:
  """CEL-Java's `isEqualOrLessSpecific`."""
  if _is_top(a):
    return True
  if _is_top(b) or _kind(a) != _kind(b):
    return False
  if _kind(a) in ("list", "map"):
    return all(_less_specific(x, y) for x, y in zip(_params(a), _params(b)))
  return True


def _most_general(a: str, b: str) -> str:
  """CEL-Java's `mostGeneral`: `a` if it is no more specific than `b`, else `b`.

  An unbound parameter (the element type of `[]` or `{}`) is bound to the
  other type's corresponding part, as CEL-Java's type inference does.

  Args:
    a: A checker type.
    b: A checker type that unifies with `a`.

  Returns:
    The joined type.
  """
  result, other = (a, b) if _less_specific(a, b) else (b, a)
  return _bind_free(result, other)


def _bind_free(type_name: str, other: str) -> str:
  if type_name == _FREE:
    return other
  kind = _kind(type_name)
  if kind in ("list", "map") and _kind(other) == kind and type_name != kind:
    inner = ",".join(
        _bind_free(x, y) for x, y in zip(_params(type_name), _params(other))
    )
    return f"{kind}<{inner}>"
  return type_name


def _join(types: List[str]) -> str:
  """The element type CEL-Java infers for a list (or map) literal."""
  joined = None
  for type_name in types:
    if joined is None:
      joined = type_name
    elif _unifies(joined, type_name):
      joined = _most_general(joined, type_name)
    else:
      joined = _DYN
  return _FREE if joined is None else joined


def _bound(type_name: str) -> str:
  """An element type as seen by an expression: unbound parameters are dyn."""
  return _DYN if type_name == _FREE else type_name


def _qualified_name(node: Tuple[Any, ...]) -> Optional[str]:
  """`a.b.c` for a select chain rooted at an identifier, else None."""
  parts = []
  while node[0] == "select":
    parts.append(node[2])
    node = node[1]
  if node[0] != "ident":
    return None
  parts.append(node[1])
  return ".".join(reversed(parts))


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _type_name(value: Any) -> str:
  """The CEL type name of a runtime value, for error messages."""
  if isinstance(value, Message):
    return value.type_name
  if isinstance(value, list):
    return "list"
  if isinstance(value, CelMap):
    return "map"
  if isinstance(value, datetime.datetime):
    return "timestamp"
  if isinstance(value, datetime.timedelta):
    return "duration"
  if isinstance(value, CelType):
    return "type"
  return _literal_type(value)


def _type_of(value: Any) -> CelType:
  """CEL's `type(x)`."""
  if isinstance(value, Message):
    return CelType(f"{_PROTO_PACKAGE}.{value.type_name}")
  if isinstance(value, datetime.datetime):
    return CelType("google.protobuf.Timestamp")
  if isinstance(value, datetime.timedelta):
    return CelType("google.protobuf.Duration")
  if value is None:
    return CelType("null_type")
  return CelType(_type_name(value))


def _check_int(value: int) -> int:
  if not _INT64_MIN <= value <= _INT64_MAX:
    raise CelEvalError("int64 overflow")
  return value


def _check_uint(value: int) -> UInt:
  if not 0 <= value <= _UINT64_MAX:
    raise CelEvalError("uint64 overflow")
  return UInt(value)


def _is_int(value: Any) -> bool:
  return isinstance(value, int) and not isinstance(value, (bool, UInt))


def _is_number(value: Any) -> bool:
  return isinstance(value, (int, float)) and not isinstance(value, bool)


def _equals(a: Any, b: Any) -> bool:
  """CEL equality, with heterogeneous numeric equality."""
  if _is_number(a) and _is_number(b):
    return a == b  # Python compares int and float exactly; NaN != NaN.
  if a is None or b is None:
    return a is None and b is None
  if isinstance(a, bool) != isinstance(b, bool):
    return False
  if isinstance(a, list) and isinstance(b, list):
    return len(a) == len(b) and all(_equals(x, y) for x, y in zip(a, b))
  if isinstance(a, CelMap) and isinstance(b, CelMap):
    # As in CEL-Java: each key of `a` is looked up in `b` (so the relation
    # inherits the lookup's numeric conversions and is not symmetric).
    if len(a) != len(b):
      return False
    for key, value in a.items():
      match = _lookup(b, key)
      if match is _MISSING or not _equals(value, match):
        return False
    return True
  if type(a) is not type(b) and not (isinstance(a, str) and isinstance(b, str)):
    return False
  return a == b  # Messages compare as protos (see Message.__eq__).


_MISSING = object()


def _lookup(mapping: CelMap, key: Any) -> Any:
  """Map lookup as in CEL-Java; returns _MISSING if absent.

  The key is first matched exactly (Java equality). Failing that, a double
  with an integral value is tried as an int and then as a uint, an int as a
  uint and a uint as an int. An int is never converted to a double, so
  `{1.0: 'a'}[dyn(1)]` fails while `{1: 'a'}[dyn(1.0)]` succeeds.

  Args:
    mapping: The map.
    key: The key.

  Returns:
    The value, or _MISSING.
  """
  found = mapping.get_exact(key)
  if found is not _MISSING or isinstance(key, bool):
    return found
  candidates: List[Any] = []
  if isinstance(key, float):
    if key.is_integer():
      if _INT64_MIN <= key <= _INT64_MAX:
        candidates.append(int(key))
      if 0 <= key <= _UINT64_MAX:
        candidates.append(UInt(int(key)))
  elif isinstance(key, UInt):
    if key <= _INT64_MAX:
      candidates.append(int(key))
  elif isinstance(key, int) and key >= 0:
    candidates.append(UInt(key))
  for candidate in candidates:
    found = mapping.get_exact(candidate)
    if found is not _MISSING:
      return found
  return _MISSING


def _compare(op: str, a: Any, b: Any) -> bool:
  """Evaluates an ordering operator, with heterogeneous numbers."""
  numbers = _is_number(a) and _is_number(b)
  same = (
      numbers
      or (isinstance(a, str) and isinstance(b, str))
      or (isinstance(a, bytes) and isinstance(b, bytes))
      or (isinstance(a, bool) and isinstance(b, bool))
      or (isinstance(a, datetime.datetime) and isinstance(b, datetime.datetime))
      or (
          isinstance(a, datetime.timedelta)
          and isinstance(b, datetime.timedelta)
      )
  )
  if not same:
    raise CelEvalError(
        f"no such overload: {_type_name(a)} {op} {_type_name(b)}"
    )
  if op == "<":
    return a < b
  if op == "<=":
    return a <= b
  if op == ">":
    return a > b
  return a >= b


def _arithmetic(op: str, a: Any, b: Any) -> Any:
  """Evaluates `+`, `-`, `*`, `/` or `%` with CEL-Java's semantics."""
  if _is_number(a) and _is_number(b):
    if type(a) is not type(b) and not (_is_int(a) and _is_int(b)):
      raise CelEvalError(
          f"no such overload: {_type_name(a)} {op} {_type_name(b)}"
      )
    if isinstance(a, float):
      if op == "+":
        return a + b
      if op == "-":
        return a - b
      if op == "*":
        return a * b
      if op == "/":
        if b == 0:
          if a == 0 or math.isnan(a):
            return math.nan
          return math.copysign(math.inf, a) * math.copysign(1.0, b)
        return a / b
      raise CelEvalError("no such overload: double % double")
    wrap = _check_uint if isinstance(a, UInt) else _check_int
    if op == "+":
      return wrap(a + b)
    if op == "-":
      return wrap(a - b)
    if op == "*":
      return wrap(a * b)
    if b == 0:
      raise CelEvalError("division by zero" if op == "/" else "modulus by zero")
    quotient = abs(a) // abs(b)
    if (a < 0) != (b < 0):
      quotient = -quotient
    if op == "/":
      return wrap(quotient)
    return wrap(a - b * quotient)
  if op == "+":
    if isinstance(a, str) and isinstance(b, str):
      return a + b
    if isinstance(a, bytes) and isinstance(b, bytes):
      return a + b
    if isinstance(a, list) and isinstance(b, list):
      return a + b
  result = _time_arithmetic(op, a, b)
  if result is not None:
    return result
  raise CelEvalError(f"no such overload: {_type_name(a)} {op} {_type_name(b)}")


# google.protobuf.Duration's range: +-10,000 years.
_MAX_DURATION_NANOS = 315_576_000_000 * 1_000_000_000


def _micros(value: datetime.timedelta) -> int:
  return (
      value.days * 86_400_000_000
      + value.seconds * 1_000_000
      + value.microseconds
  )


def _duration(micros: int) -> datetime.timedelta:
  if abs(micros) * 1_000 > _MAX_DURATION_NANOS:
    raise CelEvalError("duration out of range")
  return datetime.timedelta(microseconds=micros)


def _time_arithmetic(op: str, a: Any, b: Any) -> Any:
  """timestamp/duration `+` and `-`; None if no overload applies."""
  stamp, span = datetime.datetime, datetime.timedelta
  try:
    if isinstance(a, stamp) and isinstance(b, span) and op in ("+", "-"):
      return a + b if op == "+" else a - b
    if isinstance(a, span) and isinstance(b, stamp) and op == "+":
      return b + a
    if isinstance(a, stamp) and isinstance(b, stamp) and op == "-":
      micros = _micros(a - b)
      if abs(micros) * 1_000 > _INT64_MAX:
        # CEL-Java computes the difference in int64 nanoseconds.
        raise CelEvalError("timestamp difference overflows int64 nanoseconds")
      return datetime.timedelta(microseconds=micros)
    if isinstance(a, span) and isinstance(b, span) and op in ("+", "-"):
      micros = _micros(a) + (_micros(b) if op == "+" else -_micros(b))
      if micros < 0 and micros % 1_000_000:
        # CEL-Java fails on this: its duration arithmetic yields a
        # non-normalized proto Duration (negative seconds, positive nanos).
        raise CelEvalError(
            "duration arithmetic with a negative, fractional-second result"
            " is not supported"
        )
      return _duration(micros)
  except OverflowError as e:
    raise CelEvalError("timestamp out of range") from e
  return None


_DURATION_UNIT_NANOS = {
    "h": 3_600_000_000_000,
    "m": 60_000_000_000,
    "s": 1_000_000_000,
    "ms": 1_000_000,
    "us": 1_000,
    "µs": 1_000,
    "ns": 1,
}
_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)(ns|us|µs|ms|h|m|s)")


def _parse_duration(text: str) -> datetime.timedelta:
  """Parses `[+-]` followed by `<decimal><unit>` parts, or `0`."""
  body, sign = text, 1
  if body[:1] in ("+", "-"):
    sign = -1 if body[0] == "-" else 1
    body = body[1:]
  if body == "0":
    return datetime.timedelta(0)
  if not body:
    raise CelEvalError(f"invalid duration {text!r}")
  pos, nanos = 0, fractions.Fraction(0)
  while pos < len(body):
    match = _DURATION_PART.match(body, pos)
    if not match:
      raise CelEvalError(f"invalid duration {text!r}")
    nanos += (
        fractions.Fraction(match.group(1))
        * _DURATION_UNIT_NANOS[match.group(2)]
    )
    pos = match.end()
  whole = int(nanos)  # Sub-nanosecond digits are truncated.
  if whole > _MAX_DURATION_NANOS:
    raise CelEvalError(f"duration {text!r} out of range")
  return datetime.timedelta(microseconds=sign * (whole // 1_000))


# ISO-8601 with a mandatory offset, as java.time's ISO_OFFSET_DATE_TIME
# parses it (case-insensitive; seconds, fraction digits and offset minutes
# optional).
_TIMESTAMP = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:\.(\d{0,9}))?)?"
    r"(?:[Zz]|([+-])(\d{2})(?::(\d{2})(?::(\d{2}))?)?)\Z"
)


def _offset(
    sign: str, hours: int, minutes: int, seconds: int
) -> datetime.timezone:
  """A fixed UTC offset within java.time.ZoneOffset's +-18:00 range."""
  if minutes > 59 or seconds > 59:
    raise CelEvalError("invalid UTC offset")
  total = hours * 3600 + minutes * 60 + seconds
  if total > 18 * 3600:
    raise CelEvalError("UTC offset out of range (max +-18:00)")
  return datetime.timezone(
      datetime.timedelta(seconds=-total if sign == "-" else total)
  )


def _parse_timestamp(raw: Any) -> datetime.datetime:
  """Parses an RFC 3339 timestamp the way CEL-Java does."""
  if isinstance(raw, datetime.datetime):
    return raw
  match = _TIMESTAMP.match(str(raw))
  if not match:
    raise CelEvalError(f"invalid timestamp {raw!r}")
  (
      year,
      month,
      day,
      hour,
      minute,
      second,
      fraction,
      sign,
      off_h,
      off_m,
      off_s,
  ) = match.groups()
  zone = (
      _offset(sign, int(off_h), int(off_m or 0), int(off_s or 0))
      if sign
      else datetime.timezone.utc
  )
  try:
    local = datetime.datetime(
        int(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second or 0),
        int((fraction or "")[:6].ljust(6, "0")),
        tzinfo=zone,
    )
    return local.astimezone(datetime.timezone.utc)
  except (ValueError, OverflowError) as e:
    raise CelEvalError(f"invalid timestamp {raw!r}: {e}") from e


def _format_nanos(nanos: int) -> str:
  """Fraction digits as protobuf's Durations/Timestamps.toString prints them."""
  if nanos % 1_000_000 == 0:
    return f"{nanos // 1_000_000:03d}"
  if nanos % 1_000 == 0:
    return f"{nanos // 1_000:06d}"
  return f"{nanos:09d}"


def _format_duration(value: datetime.timedelta) -> str:
  micros = (
      value.days * 86_400_000_000
      + value.seconds * 1_000_000
      + value.microseconds
  )
  sign = "-" if micros < 0 else ""
  seconds, remainder = divmod(abs(micros), 1_000_000)
  fraction = f".{_format_nanos(remainder * 1_000)}" if remainder else ""
  return f"{sign}{seconds}{fraction}s"


def _format_timestamp(value: datetime.datetime) -> str:
  utc = value.astimezone(datetime.timezone.utc)
  fraction = (
      f".{_format_nanos(utc.microsecond * 1_000)}" if utc.microsecond else ""
  )
  return (
      f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}T{utc.hour:02d}:"
      f"{utc.minute:02d}:{utc.second:02d}{fraction}Z"
  )


def _format_double(value: float) -> str:
  """Formats like Java's Double.toString (CEL-Java's string(double))."""
  if math.isnan(value):
    return "NaN"
  if math.isinf(value):
    return "Infinity" if value > 0 else "-Infinity"
  if value == 0:
    return "-0.0" if math.copysign(1.0, value) < 0 else "0.0"
  # repr() gives the shortest round-tripping digits, as Java 19+ does.
  mantissa, _, exponent = repr(abs(value)).partition("e")
  digits = mantissa.replace(".", "")
  point = mantissa.index(".") if "." in mantissa else len(mantissa)
  point += int(exponent or 0)
  stripped = digits.lstrip("0")
  point -= len(digits) - len(stripped)
  digits = stripped.rstrip("0") or "0"
  if len(digits) == 1:
    # Java's Double.toString: when the shortest round-tripping decimal has
    # one digit, print the round-tripping 2-digit decimal closest to the
    # exact value instead (e.g. Double.MIN_VALUE -> 4.9E-324, not 5.0E-324).
    best = None
    with decimal.localcontext() as context:
      context.prec = 1100
      exact = decimal.Decimal(abs(value))
      for scale in (point - 1, point - 2, point - 3):
        nearest = int(
            exact.scaleb(-scale).to_integral_value(decimal.ROUND_HALF_EVEN)
        )
        if not 10 <= nearest <= 99:
          continue
        if float(f"{nearest}e{scale}") != abs(value):
          continue
        distance = abs(decimal.Decimal(nearest).scaleb(scale) - exact)
        if best is None or (distance, nearest % 2) < best[:2]:
          best = (distance, nearest % 2, nearest, scale)
    if best is not None:
      digits = str(best[2]).rstrip("0")
      point = best[3] + 2
  sign = "-" if value < 0 else ""
  if 1e-3 <= abs(value) < 1e7:
    if point <= 0:
      return f"{sign}0.{'0' * -point}{digits}"
    whole = digits[:point].ljust(point, "0")
    return f"{sign}{whole}.{digits[point:] or '0'}"
  return f"{sign}{digits[0]}.{digits[1:] or '0'}E{point - 1}"


def _to_int(value: Any) -> int:
  """CEL's `int()` conversion."""
  if isinstance(value, bool):
    raise CelEvalError("no such overload: int(bool)")
  if isinstance(value, int):
    return _check_int(int(value))
  if isinstance(value, float):
    if math.isnan(value) or math.isinf(value):
      raise CelEvalError(f"cannot convert {value} to int")
    return _check_int(int(value))
  if isinstance(value, str):
    if not _INT_STRING.match(value):
      raise CelEvalError(f"cannot convert {value!r} to int")
    return _check_int(int(value))
  if isinstance(value, datetime.datetime):
    delta = value - _EPOCH
    return delta.days * 86_400 + delta.seconds  # Floor, as proto seconds.
  raise CelEvalError(f"no such overload: int({_type_name(value)})")


def _to_uint(value: Any) -> UInt:
  if isinstance(value, bool):
    raise CelEvalError("no such overload: uint(bool)")
  if isinstance(value, float):
    if math.isnan(value) or math.isinf(value):
      raise CelEvalError(f"cannot convert {value} to uint")
    return _check_uint(int(value))
  if isinstance(value, int):
    return _check_uint(int(value))
  if isinstance(value, str) and re.fullmatch(r"\d+", value):
    return _check_uint(int(value))
  raise CelEvalError(f"cannot convert {value!r} to uint")


def _to_double(value: Any) -> float:
  if isinstance(value, bool):
    raise CelEvalError("no such overload: double(bool)")
  if isinstance(value, (int, float)):
    return float(value)
  if isinstance(value, str):
    try:
      return float(value)
    except ValueError as e:
      raise CelEvalError(f"cannot convert {value!r} to double") from e
  raise CelEvalError(f"no such overload: double({_type_name(value)})")


def _to_string(value: Any) -> str:
  """CEL's `string()` conversion, formatting like CEL-Java."""
  if isinstance(value, bool):
    return "true" if value else "false"
  if isinstance(value, float):
    return _format_double(value)
  if isinstance(value, (int, str)):
    return str(int(value)) if isinstance(value, int) else value
  if isinstance(value, bytes):
    try:
      return value.decode("utf-8")
    except UnicodeDecodeError as e:
      raise CelEvalError("invalid UTF-8 in bytes") from e
  if isinstance(value, datetime.datetime):
    return _format_timestamp(value)
  if isinstance(value, datetime.timedelta):
    return _format_duration(value)
  raise CelEvalError(f"no such overload: string({_type_name(value)})")


def _to_bool(value: Any) -> bool:
  if isinstance(value, bool):
    return value
  if isinstance(value, str):
    truthy = ("1", "t", "true", "TRUE", "True")
    falsy = ("0", "f", "false", "FALSE", "False")
    if value in truthy:
      return True
    if value in falsy:
      return False
  raise CelEvalError(f"cannot convert {value!r} to bool")


def _size(value: Any) -> int:
  if isinstance(value, (str, bytes, list, CelMap)):
    return len(value)
  raise CelEvalError(f"no such overload: size({_type_name(value)})")


def _to_timestamp(value: Any) -> datetime.datetime:
  if isinstance(value, datetime.datetime):
    return value
  if _is_int(value):
    try:
      return _EPOCH + datetime.timedelta(seconds=value)
    except OverflowError as e:
      raise CelEvalError(f"timestamp({value}) out of range") from e
  if isinstance(value, str):
    return _parse_timestamp(value)
  raise CelEvalError(f"no such overload: timestamp({_type_name(value)})")


def _to_duration(value: Any) -> datetime.timedelta:
  if isinstance(value, datetime.timedelta):
    return value
  if isinstance(value, str):
    return _parse_duration(value)
  raise CelEvalError(f"no such overload: duration({_type_name(value)})")


def _to_bytes(value: Any) -> bytes:
  if isinstance(value, bytes):
    return value
  if isinstance(value, str):
    return value.encode("utf-8")
  raise CelEvalError(f"no such overload: bytes({_type_name(value)})")


_CONVERSIONS: Dict[str, Callable[[Any], Any]] = {
    "size": _size,
    "int": _to_int,
    "uint": _to_uint,
    "double": _to_double,
    "string": _to_string,
    "bool": _to_bool,
    "bytes": _to_bytes,
    "timestamp": _to_timestamp,
    "duration": _to_duration,
    "dyn": lambda value: value,
    "type": _type_of,
}


def _matches(text: Any, pattern: Any) -> bool:
  """CEL's `matches()`: whether RE2 `pattern` matches part of `text`."""
  if not isinstance(text, str) or not isinstance(pattern, str):
    raise CelEvalError("matches() expects (string, string)")
  compiled = _RE2_CACHE.get(pattern)
  if compiled is None:
    translated = _Re2Translator(pattern).translate()
    try:
      with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        compiled = re.compile(translated)
    except re.error as e:
      raise CelEvalError(f"invalid regular expression {pattern!r}: {e}") from e
    _RE2_CACHE[pattern] = compiled
  return compiled.search(text) is not None


_RE2_CACHE: Dict[str, Any] = {}
_UNICODE_CLASS_CACHE: Dict[str, str] = {}
_RE2_POSIX_CLASSES = {
    "alnum": "0-9A-Za-z",
    "alpha": "A-Za-z",
    "ascii": "\\x00-\\x7f",
    "blank": "\\t ",
    "cntrl": "\\x00-\\x1f\\x7f",
    "digit": "0-9",
    "graph": "!-~",
    "lower": "a-z",
    "print": " -~",
    "punct": "!-/:-@\\[-`{-~",
    "space": "\\t\\n\\v\\f\\r ",
    "upper": "A-Z",
    "word": "0-9A-Za-z_",
    "xdigit": "0-9A-Fa-f",
}
# RE2's Perl classes are ASCII-only (Python's are Unicode-aware).
_RE2_PERL_CLASSES = {"d": "0-9", "s": "\\t\\n\\f\\r ", "w": "0-9A-Za-z_"}
_RE2_WORD = "[0-9A-Za-z_]"
_RE2_GROUP = re.compile(
    r"\(\?(?:P?<([A-Za-z_][A-Za-z0-9_]*)>|([A-Za-z-]*)([:)]))"
)
_RE2_REPEAT = re.compile(r"\{(\d+)(?:(,)(\d*))?\}")


def _unicode_class(name: str) -> str:
  r"""Character-class body for RE2's `\p{name}` (general categories)."""
  if name == "Any":
    return "\\x00-\\U0010ffff"
  cached = _UNICODE_CLASS_CACHE.get(name)
  if cached is not None:
    return cached
  if not re.fullmatch(r"[A-Z][a-z]?", name):
    raise CelEvalError(
        f"unsupported Unicode class \\p{{{name}}}: only general categories"
        " (L, Lu, N, ...) are supported"
    )
  ranges: List[Tuple[int, int]] = []
  start = None
  for code in range(0x110000):
    if unicodedata.category(chr(code)).startswith(name):
      if start is None:
        start = code
    elif start is not None:
      ranges.append((start, code - 1))
      start = None
  if start is not None:
    ranges.append((start, 0x10FFFF))
  if not ranges:
    raise CelEvalError(f"unknown Unicode class \\p{{{name}}}")
  cached = "".join(
      f"\\U{a:08x}" if a == b else f"\\U{a:08x}-\\U{b:08x}" for a, b in ranges
  )
  _UNICODE_CLASS_CACHE[name] = cached
  return cached


class _Re2Translator:
  r"""Rewrites an RE2 pattern into an equivalent Python `re` pattern.

  CEL-Java evaluates `matches` with RE2. Python's `re` differs: its `\d`,
  `\w`, `\s` and `\b` are Unicode-aware, `$` also matches before a final
  newline, it lacks POSIX classes, `\pX`, `\x{...}` and `\Q...\E`, rejects
  flags in mid-pattern, and accepts constructs RE2 rejects (lookaround,
  backreferences, possessive quantifiers, `\Z`, `\u`). Rejections raise
  CelEvalError, as the pattern would fail to compile under RE2.
  """

  def __init__(self, pattern: str):
    self._pattern = pattern
    self._out: List[str] = []
    # One entry per open group: the scoped-flag prefixes opened by standalone
    # `(?flags)` at that level, and whether the case-insensitive (i),
    # multi-line (m) and ungreedy (U) modes are on.
    self._levels: List[Dict[str, Any]] = [
        {"scoped": [], "i": False, "m": False, "U": False}
    ]

  def _fail(self, message: str) -> NoReturn:
    raise CelEvalError(
        f"invalid regular expression {self._pattern!r}: {message}"
    )

  def translate(self) -> str:
    """Returns the equivalent Python pattern, or raises CelEvalError."""
    pattern, i = self._pattern, 0
    while i < len(pattern):
      char = pattern[i]
      if char == "\\":
        piece, i = self._escape(i, in_class=False)
        self._out.append(piece)
      elif char == "[":
        piece, i = self._char_class(i)
        self._out.append(piece)
      elif char == "(":
        i = self._open_group(i)
      elif char == ")":
        if len(self._levels) == 1:
          self._fail("unexpected )")
        self._out.append(")" * len(self._levels.pop()["scoped"]) + ")")
        i += 1
      elif char == "|":
        scoped = self._levels[-1]["scoped"]
        self._out.append(")" * len(scoped) + "|" + "".join(scoped))
        i += 1
      elif char in "*+?":
        self._out.append(char)
        i = self._after_repeat(i + 1)
      elif char == "{":
        match = _RE2_REPEAT.match(pattern, i)
        if not match:
          self._out.append("\\{")  # Not a repeat: RE2 reads it literally.
          i += 1
          continue
        low, comma, high = match.groups()
        if int(low) > 1000 or (high and int(high) > 1000):
          self._fail("bad repetition operator (counts are limited to 1000)")
        if high and int(high) < int(low):
          self._fail("bad repetition operator")
        self._out.append(f"{{{low}{comma or ''}{high or ''}}}")
        i = self._after_repeat(match.end())
      elif char == "$":
        self._out.append("$" if self._levels[-1]["m"] else "\\Z")
        i += 1
      else:
        self._out.append(char)
        i += 1
    if len(self._levels) > 1:
      self._fail("missing )")
    self._out.append(")" * len(self._levels[0]["scoped"]))
    return "".join(self._out)

  def _after_repeat(self, i: int) -> int:
    pattern = self._pattern
    lazy = i < len(pattern) and pattern[i] == "?"
    if lazy:
      i += 1
    if lazy != self._levels[-1]["U"]:  # (?U) swaps the meaning of `?`.
      self._out.append("?")
    if i < len(pattern) and (
        pattern[i] in "*+?" or _RE2_REPEAT.match(pattern, i)
    ):
      self._fail("bad repetition operator")
    return i

  def _open_group(self, i: int) -> int:
    """Handles `(`, returning the index after the group's prefix."""
    pattern = self._pattern
    modes = {mode: self._levels[-1][mode] for mode in ("i", "m", "U")}
    if not pattern.startswith("(?", i):
      self._out.append("(")
      self._levels.append({"scoped": [], **modes})
      return i + 1
    match = _RE2_GROUP.match(pattern, i)
    if not match:
      self._fail(
          "unsupported group (lookaround, backreference, atomic group,"
          " conditional or comment)"
      )
    name, flags, closer = match.groups()
    if name is not None:
      self._out.append(f"(?P<{name}>")
      self._levels.append({"scoped": [], **modes})
      return match.end()
    if not re.fullmatch(r"[imsU]*(?:-[imsU]+)?", flags) or (
        closer == ")" and not flags
    ):
      self._fail(f"invalid flags (?{flags}{closer}")
    enabled, _, disabled = flags.partition("-")
    for mode in modes:
      if mode in enabled:
        modes[mode] = True
      if mode in disabled:
        modes[mode] = False
    # Python has no U flag; it is applied in _after_repeat instead.
    enabled, disabled = enabled.replace("U", ""), disabled.replace("U", "")
    prefix = f"(?{enabled}{'-' + disabled if disabled else ''}:"
    self._out.append(prefix)
    if closer == ":":
      self._levels.append({"scoped": [], **modes})
    else:
      # RE2 applies `(?flags)` to the rest of the enclosing group; Python
      # only allows that at the start, so scope it explicitly.
      self._levels[-1]["scoped"].append(prefix)
      self._levels[-1].update(modes)
    return match.end()

  def _char_class(self, i: int) -> Tuple[str, int]:
    """Translates the bracket expression starting at pattern[i]."""
    pattern = self._pattern
    # Plain members are merged into one Python class. Negated or unfolded
    # members (\D, \PL, [:^alpha:], ...) cannot be nested in a Python class,
    # so each becomes a separate alternative. Complements are never computed
    # by hand, which keeps (?i) case folding identical to RE2's.
    positive: List[str] = []
    atoms: List[str] = []
    i += 1
    negated = i < len(pattern) and pattern[i] == "^"
    if negated:
      i += 1
    first = True
    while True:
      if i >= len(pattern):
        self._fail("missing ]")
      char = pattern[i]
      if char == "]" and not first:
        i += 1
        break
      first = False
      if pattern.startswith("[:", i) and pattern.find(":]", i + 2) > 0:
        end = pattern.find(":]", i + 2)
        name = pattern[i + 2 : end]
        member_negated = name.startswith("^")
        name = name.lstrip("^")
        if name not in _RE2_POSIX_CLASSES:
          self._fail(f"invalid character class [:{name}:]")
        body = _RE2_POSIX_CLASSES[name]
        if member_negated:
          atoms.append(f"[^{body}]")
        else:
          positive.append(body)
        i = end + 2
      elif char == "\\":
        named = self._named_class(i)
        if named:
          atom, mergeable, i = named
          if mergeable is None:
            atoms.append(atom)
          else:
            positive.append(mergeable)
        else:
          piece, i = self._escape(i, in_class=True)
          positive.append(piece)
      elif char in "[]&~|^":
        positive.append("\\" + char)  # Literal in RE2; syntax in Python.
        i += 1
      else:
        positive.append(char)
        i += 1
    body = "".join(positive)
    if negated and not atoms:
      return f"[^{body}]", i
    alternatives = ([f"[{body}]"] if body else []) + atoms
    union = (
        alternatives[0]
        if len(alternatives) == 1
        else "(?:" + "|".join(alternatives) + ")"
    )
    if negated:
      return f"(?:(?!{union})(?s:.))", i
    return union, i

  def _named_class(self, i: int) -> Optional[Tuple[str, Optional[str], int]]:
    r"""Parses `\d`-style and `\pX` escapes at pattern[i].

    Args:
      i: Index of the backslash.

    Returns:
      None when the escape is not a named class. Otherwise (a regex atom
      matching the class, the class body if it can be merged into an
      enclosing Python class or None, index after the escape).
    """
    pattern = self._pattern
    char = pattern[i + 1] if i + 1 < len(pattern) else ""
    if char and char in "dDwWsS":
      body = _RE2_PERL_CLASSES[char.lower()]
      if char.isupper():
        return f"[^{body}]", None, i + 2
      return f"[{body}]", body, i + 2
    if not char or char not in "pP":
      return None
    if i + 2 >= len(pattern):
      self._fail("missing Unicode class name")
    if pattern[i + 2] == "{":
      end = pattern.find("}", i + 3)
      if end < 0:
        self._fail("missing } in \\p{...}")
      name, following = pattern[i + 3 : end], end + 1
    else:
      name, following = pattern[i + 2], i + 3
    negated = char == "P"
    if name.startswith("^"):
      negated, name = not negated, name[1:]
    body = _unicode_class(name)
    if not self._levels[-1]["i"]:
      if negated:
        return f"[^{body}]", None, following
      return f"[{body}]", body, following
    # RE2J does not case-fold \p classes; it only adds its own fold table
    # for the class, which exists for Lu, Ll, Lt and Mn and is not derivable
    # from Python's Unicode data.
    if name in ("Lu", "Ll", "Lt", "Mn"):
      self._fail(
          f"\\p{{{name}}} under case-insensitive matching is not supported by"
          " this engine"
      )
    return f"(?-i:[{'^' if negated else ''}{body}])", None, following

  def _escape(self, i: int, in_class: bool) -> Tuple[str, int]:
    """Translates the escape at pattern[i] (a backslash)."""
    pattern = self._pattern
    if i + 1 >= len(pattern):
      self._fail("trailing backslash")
    char = pattern[i + 1]
    named = None if in_class else self._named_class(i)
    if named:
      return named[0], named[2]
    if char in "01234567":
      # RE2: `\0` or two-plus octal digits is a character; `\1`-`\7` alone
      # is a backreference, which RE2 does not support.
      end = i + 2
      while end < len(pattern) and end < i + 4 and pattern[end] in "01234567":
        end += 1
      if char != "0" and end == i + 2:
        self._fail("backreferences are not supported")
      return f"\\U{int(pattern[i + 1 : end], 8):08x}", end
    if char == "x":
      if pattern.startswith("{", i + 2):
        end = pattern.find("}", i + 3)
        digits = pattern[i + 3 : end] if end > 0 else ""
        if (
            not re.fullmatch(r"[0-9A-Fa-f]{1,8}", digits)
            or int(digits, 16) > 0x10FFFF
        ):
          self._fail("invalid \\x{...} escape")
        return f"\\U{int(digits, 16):08x}", end + 1
      digits = pattern[i + 2 : i + 4]
      if not re.fullmatch(r"[0-9A-Fa-f]{2}", digits):
        self._fail("invalid \\x escape")
      return f"\\x{digits}", i + 4
    if char == "Q" and not in_class:
      end = pattern.find("\\E", i + 2)
      literal = pattern[i + 2 :] if end < 0 else pattern[i + 2 : end]
      return re.escape(literal), len(pattern) if end < 0 else end + 2
    if not in_class:
      if char == "A":
        return "\\A", i + 2
      if char == "z":
        return "\\Z", i + 2
      if char == "b":
        word = _RE2_WORD
        return (
            f"(?:(?<!{word})(?={word})|(?<={word})(?!{word}))",
            i + 2,
        )
      if char == "B":
        word = _RE2_WORD
        return (
            f"(?:(?<!{word})(?!{word})|(?<={word})(?={word}))",
            i + 2,
        )
    if char in "afnrtv":
      return "\\" + char, i + 2
    if char.isascii() and not char.isalnum() and char != "_":
      return "\\" + char, i + 2  # Escaped punctuation.
    self._fail(f"invalid escape sequence \\{char}")


_ZONE_OFFSET_FORMATS = (
    re.compile(r"([+-])(\d{1,2})\Z"),
    re.compile(r"([+-])(\d{2}):(\d{2})\Z"),
    re.compile(r"([+-])(\d{2})(\d{2})\Z"),
    re.compile(r"([+-])(\d{2}):(\d{2}):(\d{2})\Z"),
    re.compile(r"([+-])(\d{2})(\d{2})(\d{2})\Z"),
)
# Region IDs present in a Linux tz database but not in java.time's.
_NON_JAVA_ZONES = frozenset(
    {"EST", "HST", "MST", "ROC", "localtime", "posixrules", "Factory"}
)


def _zone_offset_of(text: str) -> datetime.timezone:
  """java.time.ZoneOffset.of: +h, +hh, +hh:mm, +hhmm, +hh:mm:ss, +hhmmss."""
  for pattern in _ZONE_OFFSET_FORMATS:
    match = pattern.match(text)
    if match:
      sign, *parts = match.groups()
      hours, minutes, seconds = (list(map(int, parts)) + [0, 0])[:3]
      return _offset(sign, hours, minutes, seconds)
  raise CelEvalError(f"invalid time zone offset {text!r}")


def _time_zone(args: List[Any]) -> datetime.tzinfo:
  """Resolves a CEL time-zone argument the way CEL-Java does."""
  if not args:
    return datetime.timezone.utc
  name = args[0]
  if not isinstance(name, str):
    raise CelEvalError("time zone must be a string")
  match = re.fullmatch(r"([+-])?(\d+):(\d+)", name)
  if match:
    return _offset(
        match.group(1) or "+", int(match.group(2)), int(match.group(3)), 0
    )
  # Otherwise java.time.ZoneId.of semantics.
  if name == "Z":
    return datetime.timezone.utc
  if name[:1] in ("+", "-"):
    return _zone_offset_of(name)
  for prefix in ("UTC", "GMT", "UT"):
    if name == prefix:
      return datetime.timezone.utc
    if name.startswith(prefix) and name[len(prefix) :][:1] in ("+", "-"):
      return _zone_offset_of(name[len(prefix) :])
  if (
      not re.fullmatch(r"[A-Za-z][A-Za-z0-9~/._+-]+", name)
      or name in _NON_JAVA_ZONES
      or name.startswith(("posix/", "right/"))
  ):
    raise CelEvalError(f"unknown time zone {name!r}")
  try:
    import zoneinfo  # pylint: disable=g-import-not-at-top

    return zoneinfo.ZoneInfo(name)
  except Exception as e:  # pylint: disable=broad-except
    raise CelEvalError(f"unknown time zone {name!r}") from e


def _time_accessor(value: Any, name: str, args: List[Any]) -> int:
  """Evaluates a timestamp or duration accessor such as getHours()."""
  if isinstance(value, datetime.timedelta):
    if name not in _DURATION_METHODS or args:
      raise CelEvalError(f"no such overload: duration.{name}()")
    micros = _micros(value)
    sign = -1 if micros < 0 else 1
    if name == "getMilliseconds":
      # The millisecond component (-999..999), as in CEL-Java; not a total.
      return sign * ((abs(micros) // 1_000) % 1_000)
    if name == "getSeconds":
      return sign * (abs(micros) // 1_000_000)
    # CEL-Java goes through java.time.Duration here, whose seconds are
    # floored (-59.5s is -60s + 0.5s), then divides truncating toward zero.
    floored = micros // 1_000_000
    divisor = 3_600 if name == "getHours" else 60
    return (1 if floored >= 0 else -1) * (abs(floored) // divisor)
  if not isinstance(value, datetime.datetime):
    raise CelEvalError(f"no such overload: {_type_name(value)}.{name}()")
  try:
    local = value.astimezone(_time_zone(args))
  except OverflowError as e:
    raise CelEvalError("timestamp out of range in time zone") from e
  return {
      "getFullYear": lambda: local.year,
      "getMonth": lambda: local.month - 1,
      "getDayOfYear": lambda: local.timetuple().tm_yday - 1,
      "getDayOfMonth": lambda: local.day - 1,
      "getDate": lambda: local.day,
      "getDayOfWeek": lambda: (local.weekday() + 1) % 7,
      "getHours": lambda: local.hour,
      "getMinutes": lambda: local.minute,
      "getSeconds": lambda: local.second,
      "getMilliseconds": lambda: local.microsecond // 1000,
  }[name]()


def _build_timestamp(values: List[Tuple[str, Any]]) -> datetime.datetime:
  """Evaluates `google.protobuf.Timestamp{seconds: s, nanos: n}`."""
  parts = {"seconds": 0, "nanos": 0}
  for field, value in values:
    if value is None or not _is_int(value):
      raise CelEvalError(
          f"field '{field}' of {_TIMESTAMP_MESSAGE} expects int, not"
          f" {_type_name(value)}"
      )
    parts[field] = value
  if not _INT32_MIN <= parts["nanos"] <= _INT32_MAX:
    raise CelEvalError("int32 overflow in field 'nanos'")
  # Nanoseconds are normalized into seconds; sub-microsecond precision is
  # truncated toward negative infinity (timestamps hold microseconds here).
  micros = (parts["seconds"] * 1_000_000_000 + parts["nanos"]) // 1_000
  try:
    return _EPOCH + datetime.timedelta(microseconds=micros)
  except OverflowError as e:
    raise CelEvalError("timestamp out of range") from e


def _proto_field_value(
    message: str, field: str, field_type: str, value: Any
) -> Any:
  """Converts a value assigned in a message construction to the field's type.

  Mirrors CEL-Java: null leaves a message or timestamp field unset (and is an
  error elsewhere), int32 fields are range-checked, ints widen to double,
  null list elements and null map values are dropped, and other map values
  are stored as given.

  Args:
    message: The message being constructed, e.g. "StageData".
    field: The field name.
    field_type: The field's schema type.
    value: The evaluated value.

  Returns:
    The value to store, or _MISSING to leave the field unset.

  Raises:
    CelEvalError: If the value cannot be assigned to the field.
  """
  where = f"field '{field}' of {message}"
  if value is None:
    if field_type in _SCHEMA or field_type == "timestamp":
      return _MISSING
    raise CelEvalError(f"{where} cannot be null")
  if field_type.startswith("list<"):
    if not isinstance(value, list):
      raise CelEvalError(f"{where} expects a list, not {_type_name(value)}")
    element = _split_generic(field_type)[0]
    return [
        _proto_element(where, element, v, int32=False)
        for v in value
        if v is not None
    ]
  if field_type.startswith("map<"):
    if not isinstance(value, CelMap):
      raise CelEvalError(f"{where} expects a map, not {_type_name(value)}")
    value_type = _split_generic(field_type)[1]
    int32 = field in _INT32_FIELDS.get(message, ())
    result = CelMap()
    for key, entry in value.items():
      if entry is None:
        continue
      if value_type in _SCHEMA or (int32 and _is_int(entry)):
        entry = _proto_element(where, value_type, entry, int32=int32)
      result.insert(key, entry)
    return result
  int32 = field_type.startswith("enum:") or field in _INT32_FIELDS.get(
      message, ()
  )
  return _proto_element(where, field_type, value, int32=int32)


def _proto_element(where: str, field_type: str, value: Any, int32: bool) -> Any:
  """Converts one non-null scalar or message value to `field_type`."""
  if field_type == "int" or field_type.startswith("enum:"):
    if _is_int(value):
      if int32 and not _INT32_MIN <= value <= _INT32_MAX:
        raise CelEvalError(f"int32 overflow in {where}")
      return value
  elif field_type == "uint":
    if isinstance(value, UInt):
      return value
  elif field_type == "double":
    if isinstance(value, float):
      return value
    if _is_int(value):
      return float(value)
  elif field_type == "bool":
    if isinstance(value, bool):
      return value
  elif field_type == "string":
    if isinstance(value, str):
      return value
  elif field_type == "bytes":
    if isinstance(value, bytes):
      return value
  elif field_type == "timestamp":
    if isinstance(value, datetime.datetime):
      return value
  elif field_type in _SCHEMA:
    if isinstance(value, Message) and value.type_name == field_type:
      return value
  raise CelEvalError(
      f"{where} expects {_describe(field_type)}, not {_type_name(value)}"
  )


class Program:
  """A compiled, type-checked CEL expression."""

  def __init__(
      self,
      expression: str,
      declarations: Optional[Dict[str, str]] = None,
  ):
    """Parses and type-checks `expression`.

    Args:
      expression: CEL source text.
      declarations: Variable name -> type (see `STAGE_RULE_DECLARATIONS`).

    Raises:
      CelSyntaxError: If the expression does not parse.
      CelTypeError: If it references undeclared variables, functions or
        fields, or applies an operator to types it has no overload for.
    """
    self.expression = expression
    self.declarations = dict(
        STAGE_RULE_DECLARATIONS if declarations is None else declarations
    )
    self.ast = _Parser(expression).parse()
    checker = _Checker(self.declarations)
    self.result_type = checker.check(self.ast, {})
    self.free_variables = frozenset(checker.free)

  def evaluate(self, activation: Dict[str, Any]) -> Any:
    """Evaluates the expression.

    Args:
      activation: Variable name -> value. Values of message-typed variables may
        be JSON dicts (camelCase or snake_case); they are wrapped according to
        the declared type.

    Returns:
      The CEL result (bool, int, float, str, list, dict, Message, ...).

    Raises:
      CelEvalError: If evaluation fails.
    """
    env = {}
    for name, type_name in self.declarations.items():
      if name in activation:
        value = activation[name]
        env[name] = (
            value if isinstance(value, Message) else _bind(value, type_name)
        )
    try:
      return _Evaluator(env).eval(self.ast)
    except RecursionError as e:
      raise CelEvalError("expression is nested too deeply") from e

  def top_level_macro_variable(self) -> Optional[str]:
    """The variable of a whole-expression `stages.filter(x, ...)` macro."""
    node = self.ast
    if (
        node[0] == "comprehension"
        and node[1] in ("filter", "exists", "all", "exists_one")
        and node[2] == ("ident", "stages")
    ):
      return node[3]
    return None


def _bind(value: Any, type_name: str) -> Any:
  if type_name.startswith("list<"):
    element = _split_generic(type_name)[0]
    return [
        v if isinstance(v, Message) else _bind(v, element) for v in value or []
    ]
  if type_name in _SCHEMA:
    return Message(type_name, value if isinstance(value, dict) else {})
  if type_name == _DYN:
    return from_json(value)
  return convert(value, type_name)


class _Evaluator:
  """Tree-walking evaluator over parser output."""

  def __init__(self, env: Dict[str, Any]):
    self._env = env

  def eval(self, node: Tuple[Any, ...]) -> Any:
    return getattr(self, "_eval_" + node[0])(node)

  def _eval_lit(self, node) -> Any:
    return node[1]

  def _eval_ident(self, node) -> Any:
    name = node[1]
    if name in self._env:
      return self._env[name]
    if name in _TYPE_IDENTIFIERS:
      return CelType(name)
    raise CelEvalError(f"no value bound for '{name}'")

  def _eval_select(self, node) -> Any:
    qualified = _qualified_name(node)
    if qualified and qualified.split(".")[0] not in self._env:
      if qualified in _ENUM_CONSTANTS:
        return _ENUM_CONSTANTS[qualified]
      if qualified in _TYPE_IDENTIFIERS:
        return CelType(qualified)
    operand = self.eval(node[1])
    return _select(operand, node[2])

  def _eval_has(self, node) -> bool:
    select = node[1]
    operand = self.eval(select[1])
    if isinstance(operand, Message):
      return operand.has(select[2])
    if isinstance(operand, CelMap):
      return _lookup(operand, select[2]) is not _MISSING
    raise CelEvalError(f"has() is not supported on '{_type_name(operand)}'")

  def _eval_index(self, node) -> Any:
    """Evaluates `a[b]` on lists and maps."""
    operand = self.eval(node[1])
    key = self.eval(node[2])
    if isinstance(operand, list):
      if isinstance(key, float) and key.is_integer():
        key = int(key)
      if isinstance(key, bool) or not isinstance(key, int):
        raise CelEvalError(f"list index must be int, not {_type_name(key)}")
      if not 0 <= key < len(operand):
        raise CelEvalError(
            f"index out of range: {key} (list size {len(operand)})"
        )
      return operand[key]
    if isinstance(operand, CelMap):
      value = _lookup(operand, key)
      if value is _MISSING:
        raise CelEvalError(f"no such key: {key!r}")
      return value
    raise CelEvalError(
        f"type '{_type_name(operand)}' does not support indexing"
    )

  def _eval_list(self, node) -> List[Any]:
    return [self.eval(e) for e in node[1]]

  def _eval_map(self, node) -> CelMap:
    result = CelMap()
    for key_node, value_node in node[1]:
      key = self.eval(key_node)
      if not result.insert(key, self.eval(value_node)):
        raise CelEvalError(f"duplicate map key {key!r}")
    return result

  def _eval_msg(self, node) -> Any:
    """Evaluates a message construction."""
    _, name, field_nodes = node
    values = [(field, self.eval(value)) for field, value in field_nodes]
    if name == _TIMESTAMP_MESSAGE:
      return _build_timestamp(values)
    message = name[len(_PROTO_PACKAGE) + 1 :]
    data: Dict[str, Any] = {}
    for field, value in values:  # A repeated field: the last value wins.
      stored = _proto_field_value(
          message, field, _field_type(message, field), value
      )
      if stored is _MISSING:
        data.pop(field, None)
      else:
        data[field] = stored
    return Message(message, data, built=True)

  def _eval_cond(self, node) -> Any:
    test = self.eval(node[1])
    if not isinstance(test, bool):
      raise CelEvalError(f"'?:' condition must be bool, not {_type_name(test)}")
    return self.eval(node[2] if test else node[3])

  def _logical(self, node, absorbing: bool) -> bool:
    """Evaluates `&&` (absorbing False) or `||` (absorbing True)."""
    # CEL's && and || are commutative over errors: `false && <error>` and
    # `<error> && false` are both false.
    errors = []
    for operand in (node[1], node[2]):
      try:
        value = self.eval(operand)
      except CelEvalError as e:
        errors.append(e)
        continue
      if value is absorbing:
        return absorbing
      if not isinstance(value, bool):
        errors.append(
            CelEvalError(
                f"logical operand must be bool, not {_type_name(value)}"
            )
        )
    if errors:
      raise errors[0]
    return not absorbing

  def _eval_and(self, node) -> bool:
    return self._logical(node, False)

  def _eval_or(self, node) -> bool:
    return self._logical(node, True)

  def _eval_not(self, node) -> bool:
    value = self.eval(node[1])
    if not isinstance(value, bool):
      raise CelEvalError(f"'!' requires bool, not {_type_name(value)}")
    return not value

  def _eval_neg(self, node) -> Any:
    value = self.eval(node[1])
    if isinstance(value, float):
      return -value
    if _is_int(value):
      return _check_int(-value)
    raise CelEvalError(f"no such overload: -{_type_name(value)}")

  def _eval_binop(self, node) -> Any:
    """Evaluates a binary operator."""
    op = node[1]
    left = self.eval(node[2])
    right = self.eval(node[3])
    if op == "==":
      return _equals(left, right)
    if op == "!=":
      return not _equals(left, right)
    if op == "in":
      if isinstance(right, list):
        return any(_equals(left, element) for element in right)
      if isinstance(right, CelMap):
        return _lookup(right, left) is not _MISSING
      raise CelEvalError(f"no such overload: _ in {_type_name(right)}")
    if op in ("<", "<=", ">", ">="):
      return _compare(op, left, right)
    return _arithmetic(op, left, right)

  def _eval_call(self, node) -> Any:
    """Evaluates a global function or method call."""
    _, name, target, arg_nodes = node
    args = [self.eval(a) for a in arg_nodes]
    if target is None:
      if name == "matches":
        return _matches(*args)
      return _CONVERSIONS[name](args[0])
    value = self.eval(target)
    if name == "size":
      return _size(value)
    if name in _STRING_METHODS:
      if not isinstance(value, str) or not isinstance(args[0], str):
        raise CelEvalError(f"{name}() expects string operands")
      if name == "contains":
        return args[0] in value
      if name == "startsWith":
        return value.startswith(args[0])
      if name == "endsWith":
        return value.endswith(args[0])
      return _matches(value, args[0])
    return _time_accessor(value, name, args)

  def _eval_comprehension(self, node) -> Any:
    """Evaluates a macro over a list or the keys of a map."""
    _, macro, range_node, var, args = node
    collection = self.eval(range_node)
    if isinstance(collection, CelMap):
      items = list(collection.keys())
    elif isinstance(collection, list):
      items = collection
    else:
      raise CelEvalError(
          f"{macro}() needs a list or map, not {_type_name(collection)}"
      )
    saved = self._env.get(var, _MISSING)
    try:
      return self._comprehend(macro, items, var, args)
    finally:
      if saved is _MISSING:
        self._env.pop(var, None)
      else:
        self._env[var] = saved

  def _predicate(self, node) -> bool:
    value = self.eval(node)
    if not isinstance(value, bool):
      raise CelEvalError(f"predicate must be bool, not {_type_name(value)}")
    return value

  def _comprehend(self, macro, items, var, args) -> Any:
    """Runs a macro's loop over `items`."""
    if macro in ("filter", "map"):
      result = []
      for item in items:
        self._env[var] = item
        if macro == "filter":
          if self._predicate(args[0]):
            result.append(item)
        elif len(args) == 1 or self._predicate(args[0]):
          result.append(self.eval(args[-1]))
      return result
    if macro == "exists_one":
      count = 0
      for item in items:
        self._env[var] = item
        if self._predicate(args[0]):
          count += 1
      return count == 1
    # all / exists: short-circuit on the deciding value; errors only matter
    # if no element decides the result, as in CEL.
    deciding = macro == "exists"
    error: Optional[CelEvalError] = None
    for item in items:
      self._env[var] = item
      try:
        if self._predicate(args[0]) is deciding:
          return deciding
      except CelEvalError as e:
        error = error or e
    if error is not None:
      raise error
    return not deciding


def _select(operand: Any, field: str) -> Any:
  if isinstance(operand, Message):
    return operand.get(field)
  if isinstance(operand, CelMap):
    value = _lookup(operand, field)
    if value is _MISSING:
      raise CelEvalError(f"no such key: '{field}'")
    return value
  raise CelEvalError(
      f"type '{_type_name(operand)}' does not support field selection"
  )


def compile_expression(
    expression: str, declarations: Optional[Dict[str, str]] = None
) -> Program:
  """Parses and type-checks a CEL expression. See `Program`."""
  return Program(expression, declarations)


def field_paths_valid(message: str, path: List[str]) -> Optional[str]:
  """Validates a dotted field path against the schema.

  Args:
    message: The message the path starts from, e.g. "StageData".
    path: Field names, outermost first.

  Returns:
    None if every step names a field, otherwise an error message.
  """
  current = message
  for i, field in enumerate(path):
    if current not in _SCHEMA:
      return None  # Past a scalar/map/list: not statically checkable here.
    field_type = _field_type(current, _camel_to_snake(field))
    if field_type is None:
      where = ".".join(path[:i]) or message
      return (
          f"undefined field '{field}' on {current} ({where}); valid fields:"
          f" {', '.join(sorted(_SCHEMA[current]))}"
      )
    current = field_type
  return None


def _camel_to_snake(name: str) -> str:
  return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def is_message(value: Any, type_name: str) -> bool:
  return isinstance(value, Message) and value.type_name == type_name
