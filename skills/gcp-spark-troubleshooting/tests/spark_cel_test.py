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

"""Unit tests for spark_cel."""

import datetime
import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_cel as cel

_STAGES = [
    {
        "stageId": "3",
        "name": "count at job.py:12",
        "numTasks": 20,
        "numFailedTasks": 2,
        "status": "STAGE_STATUS_FAILED",
        "submissionTime": "2026-09-25T18:21:41.359Z",
        "completionTime": "2026-09-25T18:23:17.010Z",
        "stageMetrics": {
            "executorRunTimeMillis": "1000",
            "jvmGcTimeMillis": "300",
        },
        "taskQuantileMetrics": {
            "durationMillis": {"percentile50": "1000", "maximum": "100000"}
        },
        "locality": {"PROCESS_LOCAL": "5"},
        "parentStageIds": ["1", "2"],
    },
    {"numTasks": 5, "stageMetrics": {}},
]
_EXECUTORS = {"failedTasks": 2, "completedTasks": 10}


def _eval(expression, stages=None, executors=None):
  program = cel.compile_expression(expression)
  return program.evaluate({
      "stages": _STAGES if stages is None else stages,
      "total_executor_summary": _EXECUTORS if executors is None else executors,
  })


class LiteralsAndOperatorsTest(unittest.TestCase):

  def test_literals(self):
    cases = {
        "1": 1,
        "-9223372036854775808": -(2**63),
        "0x1F": 31,
        "1u": 1,
        "1.5": 1.5,
        "1e3": 1000.0,
        ".5": 0.5,
        "'a\\tb'": "a\tb",
        '"\\u00e9"': "\u00e9",
        "'\\x41\\X42'": "AB",
        "b'\\xff'": b"\xff",  # \xHH in bytes is a raw byte, not UTF-8.
        "r'\\d+'": "\\d+",
        "'''multi\nline'''": "multi\nline",
        "b'ab'": b"ab",
        "true": True,
        "null": None,
        "[1, 2,]": [1, 2],
        "{'a': 1}": cel.CelMap([("a", 1)]),
    }
    for expression, expected in cases.items():
      self.assertEqual(_eval(expression), expected, expression)
    self.assertIsInstance(_eval("1u"), cel.UInt)

  def test_int_arithmetic_truncates_and_checks(self):
    self.assertEqual(_eval("7 / 2"), 3)
    self.assertEqual(_eval("-7 / 2"), -3)
    self.assertEqual(_eval("-7 % 2"), -1)
    self.assertEqual(_eval("7 % -2"), 1)
    for expression, message in (
        ("1 / 0", "division by zero"),
        ("1 % 0", "modulus by zero"),
        ("9223372036854775807 + 1", "overflow"),
        ("-9223372036854775808 / -1", "overflow"),
    ):
      with self.assertRaisesRegex(cel.CelEvalError, message):
        _eval(expression)

  def test_double_arithmetic_is_ieee(self):
    self.assertEqual(_eval("1.0 / 0.0"), math.inf)
    self.assertEqual(_eval("-1.0 / 0.0"), -math.inf)
    self.assertTrue(math.isnan(_eval("0.0 / 0.0")))
    self.assertFalse(_eval("0.0 / 0.0 > 1.0"))
    self.assertFalse(_eval("0.0 / 0.0 == 0.0 / 0.0"))

  def test_heterogeneous_numeric_comparison(self):
    self.assertTrue(_eval("1 < 1.5"))
    self.assertTrue(_eval("1u < 2"))
    self.assertTrue(_eval("2.0 <= 2"))
    # Equality is heterogeneous only at runtime, through dyn.
    self.assertTrue(_eval("dyn(2) == 2.0"))
    self.assertTrue(_eval("dyn(2) in [1.0, 2.0]"))
    self.assertTrue(_eval("2.0 in [1, 2.0, 'x']"))

  def test_mixed_numeric_equality_is_a_type_error_like_cel_java(self):
    for expression in (
        "2 == 2.0",
        "1u == 1",
        "2 != 3.0",
        "2 in [1.0, 2.0]",
        "1.0 in {1: 'a'}",
        "{1: 'a'}[1.0] == 'a'",
        "{1: 'a'}[1u] == 'a'",
        "[1] == [1.0]",
        "stages[0].num_tasks == 12.0",
    ):
      with self.assertRaisesRegex(
          cel.CelTypeError,
          "no matching overload|map key must be",
          msg=expression,
      ):
        cel.compile_expression(expression)
    with self.assertRaisesRegex(cel.CelTypeError, "rather than 12.0"):
      cel.compile_expression("stages[0].num_tasks == 12.0")
    with self.assertRaisesRegex(cel.CelTypeError, "list index must be int"):
      cel.compile_expression("stages[0u]")

  def test_mixed_arithmetic_is_a_type_error(self):
    for expression in ("1 + 1.0", "1u + 1", "2.0 % 1.0"):
      with self.assertRaises(cel.CelTypeError, msg=expression):
        cel.compile_expression(expression)

  def test_strings_lists_and_maps(self):
    self.assertEqual(_eval("'a' + 'b'"), "ab")
    self.assertEqual(_eval("[1] + [2]"), [1, 2])
    self.assertTrue(_eval("'b' < 'c'"))
    self.assertTrue(_eval("'a' in {'a': 1}"))
    self.assertEqual(_eval("{'a': {'b': 2}}.a.b"), 2)
    self.assertEqual(_eval("[[1, 2]][0][1]"), 2)
    self.assertTrue(_eval("[1, [2]] == [1, [2.0]]"))
    with self.assertRaisesRegex(cel.CelEvalError, "no such key"):
      _eval("{'a': 1}['b']")
    with self.assertRaisesRegex(cel.CelEvalError, "index out of range"):
      _eval("[1][3]")

  def test_logical_operators_absorb_errors_like_cel(self):
    self.assertFalse(_eval("1 / 0 == 1 && false"))
    self.assertFalse(_eval("false && 1 / 0 == 1"))
    self.assertTrue(_eval("1 / 0 == 1 || true"))
    with self.assertRaises(cel.CelEvalError):
      _eval("1 / 0 == 1 && true")
    self.assertTrue(_eval("!false"))

  def test_logical_operators_reject_non_bool_dyn_operands(self):
    # dyn passes the type checker, so a non-bool operand fails at runtime
    # unless the other operand decides the result.
    self.assertFalse(_eval("dyn(1) && false"))
    self.assertTrue(_eval("dyn(1) || true"))
    for expression, type_name in (
        ("dyn(1) && true", "int"),
        ("true && dyn('a')", "string"),
        ("dyn(1.5) || false", "double"),
    ):
      with self.assertRaisesRegex(
          cel.CelEvalError,
          f"logical operand must be bool, not {type_name}",
          msg=expression,
      ):
        _eval(expression)

  def test_conditional(self):
    self.assertEqual(_eval("size(stages) > 1 ? 'many' : 'few'"), "many")
    self.assertEqual(_eval("true ? 1 : 1 / 0"), 1)

  def test_precedence(self):
    self.assertEqual(_eval("1 + 2 * 3"), 7)
    self.assertTrue(_eval("1 < 2 == true"))
    self.assertTrue(_eval("true || false && false"))
    self.assertEqual(_eval("-(1 + 2)"), -3)
    self.assertEqual(_eval("false ? 1 : true ? 2 : 3"), 2)


class FunctionsAndMacrosTest(unittest.TestCase):

  def test_conversions(self):
    self.assertEqual(_eval("int(3.9)"), 3)
    self.assertEqual(_eval("int(-3.9)"), -3)
    self.assertEqual(_eval("int('42')"), 42)
    self.assertEqual(_eval("double(3)"), 3.0)
    self.assertEqual(_eval("string(3)"), "3")
    self.assertEqual(_eval("string(true)"), "true")
    self.assertEqual(_eval("uint(3)"), 3)
    self.assertTrue(_eval("bool('true')"))
    self.assertEqual(_eval("size('héllo')"), 5)
    self.assertEqual(_eval("[1, 2].size()"), 2)
    self.assertEqual(_eval("dyn(1) + 1"), 2)
    with self.assertRaises(cel.CelEvalError):
      _eval("int('x')")

  def test_string_methods(self):
    self.assertTrue(_eval("'abc'.contains('b')"))
    self.assertTrue(_eval("'abc'.startsWith('ab')"))
    self.assertTrue(_eval("'abc'.endsWith('bc')"))
    self.assertTrue(_eval("'abc'.matches('^a.c$')"))
    self.assertTrue(_eval("matches('abc', 'b')"))
    self.assertEqual(
        _eval("stages.filter(s, s.name.contains('job.py')).size()"), 1
    )

  def test_macros(self):
    self.assertTrue(_eval("[1, 2, 3].all(x, x > 0)"))
    self.assertTrue(_eval("[1, 2, 3].exists(x, x > 2)"))
    self.assertTrue(_eval("[1, 2, 3].exists_one(x, x > 2)"))
    self.assertFalse(_eval("[1, 2, 3].exists_one(x, x > 1)"))
    self.assertEqual(_eval("[1, 2, 3].filter(x, x % 2 == 1)"), [1, 3])
    self.assertEqual(_eval("[1, 2, 3].map(x, x * 2)"), [2, 4, 6])
    self.assertEqual(_eval("[1, 2, 3].map(x, x > 1, x * 2)"), [4, 6])
    self.assertEqual(_eval("{'a': 1, 'b': 2}.filter(k, k == 'b')"), ["b"])
    self.assertTrue(_eval("[].all(x, x > 0)"))
    self.assertFalse(_eval("[].exists(x, x > 0)"))

  def test_exists_and_all_ignore_errors_when_decided(self):
    self.assertTrue(_eval("[0, 1].exists(x, 1 / x == 1)"))
    self.assertFalse(_eval("[0, 1].all(x, 1 / x == 0)"))
    with self.assertRaises(cel.CelEvalError):
      _eval("[0, 1].all(x, 1 / x == 1)")

  def test_macro_variable_is_scoped(self):
    self.assertEqual(
        _eval("[1, 2].map(x, [10, 20].map(x, x + 1))"),
        [[11, 21], [11, 21]],
    )

  def test_timestamps_and_durations(self):
    elapsed = "(stages[0].completion_time - stages[0].submission_time)"
    # 95.651s: getSeconds() is the total, getMilliseconds() the component.
    self.assertEqual(_eval(f"{elapsed}.getSeconds()"), 95)
    self.assertEqual(_eval(f"{elapsed}.getMilliseconds()"), 651)
    self.assertEqual(_eval(f"{elapsed}.getMinutes()"), 1)
    self.assertTrue(_eval(f"{elapsed} > duration('1m')"))
    self.assertEqual(_eval("duration('1h30m').getMinutes()"), 90)
    self.assertEqual(_eval("duration('26h').getHours()"), 26)
    self.assertEqual(_eval("duration('90061.5s').getMilliseconds()"), 500)
    self.assertEqual(_eval("timestamp('2026-01-02T03:04:05Z').getHours()"), 3)
    self.assertEqual(_eval("timestamp('2026-01-02T03:04:05Z').getMonth()"), 0)
    self.assertEqual(_eval("int(timestamp('1970-01-01T00:01:00Z'))"), 60)
    self.assertEqual(_eval("int(timestamp('1969-12-31T23:59:59.5Z'))"), -1)
    self.assertEqual(
        _eval("int(timestamp('2964-04-11T04:19:03.999999Z'))"), 31376348343
    )
    self.assertEqual(
        _eval("stages[1].submission_time"),
        datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc),
    )

  def test_negative_duration_accessors_match_cel_java(self):
    # getSeconds/getMilliseconds truncate; getMinutes/getHours floor the
    # seconds first (java.time.Duration), then truncate.
    self.assertEqual(_eval("duration('-59.999999s').getSeconds()"), -59)
    self.assertEqual(_eval("duration('-59.999999s').getMilliseconds()"), -999)
    self.assertEqual(_eval("duration('-59.999999s').getMinutes()"), -1)
    self.assertEqual(_eval("duration('-59s').getMinutes()"), 0)
    self.assertEqual(_eval("duration('-119s').getMinutes()"), -1)
    self.assertEqual(_eval("duration('-3599.9s').getHours()"), -1)

  def test_string_formatting_matches_cel_java(self):
    for expression, expected in (
        ("string(duration('1.5s'))", "1.500s"),
        ("string(duration('-1.5s'))", "-1.500s"),
        ("string(duration('1h'))", "3600s"),
        ("string(duration('0.000001s'))", "0.000001s"),
        (
            "string(timestamp('2026-01-01T00:00:00.5Z'))",
            "2026-01-01T00:00:00.500Z",
        ),
        (
            "string(timestamp('2026-01-01T02:00:00+02:00'))",
            "2026-01-01T00:00:00Z",
        ),
        ("string(1.5)", "1.5"),
        ("string(2.0)", "2.0"),
        ("string(1e7)", "1.0E7"),
        ("string(9999999.0)", "9999999.0"),
        ("string(0.001)", "0.001"),
        ("string(0.0001)", "1.0E-4"),
        ("string(123456789.0)", "1.23456789E8"),
        ("string(-12345678.9)", "-1.23456789E7"),
        ("string(1.0 / 3.0)", "0.3333333333333333"),
        ("string(4.9e-324)", "4.9E-324"),
        ("string(1e-323)", "9.9E-324"),
        ("string(1e23)", "1.0E23"),
        ("string(-0.0)", "-0.0"),
        ("string(0.0 / 0.0)", "NaN"),
        ("string(-1.0 / 0.0)", "-Infinity"),
    ):
      self.assertEqual(_eval(expression), expected, msg=expression)

  def test_time_arithmetic_edge_cases_match_cel_java(self):
    self.assertTrue(
        _eval("duration('1s') - duration('0.5s') == duration('0.5s')")
    )
    self.assertTrue(_eval("duration('0s') - duration('1s') == duration('-1s')"))
    self.assertTrue(
        _eval(
            "timestamp('2026-01-01T00:00:01Z') + duration('-0.5s') =="
            " timestamp('2026-01-01T00:00:00.5Z')"
        )
    )
    for expression in (
        # A negative, fractional duration±duration result fails in CEL-Java.
        "duration('1s') - duration('2.5s') < duration('0s')",
        "duration('-1.5s') + duration('0s') < duration('0s')",
        "duration('315576000000s') + duration('1s') > duration('0s')",
        # Timestamp differences are int64 nanoseconds in CEL-Java.
        (
            "timestamp('2026-01-01T00:00:00Z') -"
            " timestamp('1733-01-01T00:00:00Z') > duration('0s')"
        ),
        "timestamp('9999-12-31T23:59:59Z') + duration('1s') > timestamp(0)",
        "timestamp(253402300800) > timestamp(0)",
    ):
      with self.assertRaises(cel.CelEvalError, msg=expression):
        _eval(expression)
    with self.assertRaisesRegex(cel.CelTypeError, "no matching overload"):
      cel.compile_expression("-duration('1s')")

  def test_duration_and_timestamp_parsing_match_cel_java(self):
    for expression in (
        "duration('0') == duration('0s')",
        "duration('+1s') == duration('1s')",
        "duration('1\u00b5s') == duration('1us')",
        "duration('1h1m1s1ms1us') == duration('3661.001001s')",
        "duration('1.0000000009s') == duration('1s')",
        (
            "timestamp('2026-01-01t00:00:00z') =="
            " timestamp('2026-01-01T00:00:00Z')"
        ),
        "timestamp('2026-01-01T00:00Z') == timestamp('2026-01-01T00:00:00Z')",
        (
            "timestamp('2026-01-01T00:00:00.Z') =="
            " timestamp('2026-01-01T00:00:00Z')"
        ),
        (
            "timestamp('2026-01-01T01:00:00+01') =="
            " timestamp('2026-01-01T00:00:00Z')"
        ),
        (
            "timestamp('2026-01-01T00:00:00+18:00') <"
            " timestamp('2026-01-01T00:00:00Z')"
        ),
    ):
      self.assertTrue(_eval(expression), msg=expression)
    for text in (
        "1.s",
        ".5s",
        " 1s",
        "1s ",
        "1S",
        "--1s",
        "",
        "1e3s",
        "1.5",
        "315576000000.5s",
    ):
      with self.assertRaises(cel.CelEvalError, msg=text):
        _eval(f"duration('{text}')")
    for text in (
        "2026-01-01 00:00:00Z",
        " 2026-01-01T00:00:00Z",
        "2026-01-01T00:00:00",
        "2026-01-01T00:00:00+0000",
        "2026-01-01T00:00:00+1:00",
        "2026-01-01T00:00:00+18:01",
        "2026-01-01T00:00:00.1234567891Z",
        "2026-02-29T00:00:00Z",
        "2026-01-01T00:00:60Z",
        "0001-01-01T00:59:59+01:00",
        "0000-01-01T00:00:00Z",
    ):
      with self.assertRaises(cel.CelEvalError, msg=text):
        _eval(f"timestamp('{text}')")

  def test_time_zones_match_cel_java(self):
    stamp = "timestamp('2026-01-01T00:00:00Z')"
    for zone, hours in (
        ("+5:30", 5),
        ("05:30", 5),
        ("-5:30", 18),
        ("000:00", 0),
        ("+1:5", 1),
        ("18:00", 18),
        ("+05", 5),
        ("+0530", 5),
        ("Z", 0),
        ("UT", 0),
        ("UTC", 0),
        ("GMT", 0),
        ("GMT+1", 1),
        ("UTC-05:00", 19),
        ("UT+2", 2),
        ("America/Los_Angeles", 16),
        ("Asia/Kolkata", 5),
    ):
      self.assertEqual(_eval(f"{stamp}.getHours('{zone}')"), hours, msg=zone)
    for zone in (
        "utc",
        "Utc",
        "EST",
        "HST",
        "MST",
        "ROC",
        "23:00",
        "+19:00",
        "+01:60",
        "+123",
        " UTC",
        "",
        "America/new_york",
        "posix/UTC",
        "localtime",
    ):
      with self.assertRaises(cel.CelEvalError, msg=zone):
        _eval(f"{stamp}.getHours('{zone}')")

  def test_type_values(self):
    for expression in (
        "type(1) == int",
        "type(1u) == uint",
        "type(1.0) == double",
        "type('a') == string",
        "type(b'a') == bytes",
        "type(true) == bool",
        "type([1]) == list",
        "type({1: 2}) == map",
        "type(null) == null_type",
        "type(int) == type",
        "type(stages[0]) == google.cloud.dataproc.v1.StageData",
        "type(stages[0].status) == int",
        "type(timestamp('2026-01-01T00:00:00Z')) == google.protobuf.Timestamp",
        (
            "type(total_executor_summary) =="
            " google.cloud.dataproc.v1.ConsolidatedExecutorSummary"
        ),
        "int in [int, uint]",
        "type(dyn(1)) == int",
    ):
      self.assertTrue(_eval(expression), msg=expression)
    self.assertFalse(_eval("int == double"))
    for expression in (
        "type(1) == 1",
        "string(type(1))",
        "type(stages[0]) == StageData",
        "type(duration('1s')) == google.protobuf.Duration",
    ):
      with self.assertRaises(cel.CelTypeError, msg=expression):
        cel.compile_expression(expression)

  def test_regular_expressions_follow_re2(self):
    # Expectations verified against CEL-Java, which uses RE2J.
    matching = (
        ("x\nabc", r"(?m)^abc$"),
        ("aB", r"a(?i)b|C"),
        ("C", r"a(?i)b|C"),
        ("A", r"\x{41}"),
        ("a.b", r"^a\Q.\Eb$"),
        ("1", r"^[[:^alpha:]]$"),
        ("a{,5}", r"^a{,5}$"),
        ("\n", r"\12"),
        ("A", r"\101"),
        ("1", r"\PL"),
        ("a", r"[^\PL]"),
        ("a\nb", r"(?s)a.b"),
        ("AB", r"(?i)(?-i:A)b"),
        ("ab", r"a\Bb"),
        ("{", r"{"),
        ("]", r"[]a]"),
        ("K", r"(?i)k"),
        ("\u017f", r"(?i)s"),
        ("\u00bd", r"\pN"),
        ("x", r"(?U)x+"),
        ("xX", r"^(?i)x(?-i)X$"),
        ("-", r"^[\D-z]$"),
        ("A", r"(?i)^[^\W]$"),
        ("y", r"^[^[:^alpha:]x]$"),
        ("^", r"[\D^]"),
        ("\u00e9", r"(?i)^[^\PL]$"),
        ("abc", r"(?P<x>a)bc"),
        ("abc", r"(?<x>a)bc"),
        ("a b", r"\bb"),
        ("abc", r""),
    )
    for text, pattern in matching:
      self.assertTrue(cel._matches(text, pattern), msg=pattern)
    not_matching = (
        ("\u0663", r"\d"),
        ("\u00e9", r"^\w$"),
        ("\u000b", r"^\s$"),
        ("\u00a0", r"\s"),
        ("abc\n", r"abc$"),
        ("abc\n", r"abc\z"),
        ("a\nb", r"a.b"),
        ("x\nabc", r"^abc$"),
        ("xc", r"^(?:a(?i)b|c)$"),
        ("AB", r"(?i:A)b"),
        ("\u00e9", "\\b\u00e9"),
        ("1", r"[\D]"),
        ("A", r"\p{^Lu}"),
        ("xx", r"^(?i)x(?-i)X$"),
        ("A", r"(?i)^[^a\D]$"),
        ("5", r"^[^\D\S]$"),
        ("1", r"^[^[:^alpha:]x]$"),
        ("\n", r"[^\s]"),
        ("\u000b", r"[\s]"),
        ("b", r"(?i)[^\x{41}-\x{5A}]"),
    )
    for text, pattern in not_matching:
      self.assertFalse(cel._matches(text, pattern), msg=pattern)
    for pattern in (
        r"(?=a)abc",
        r"a(?!x)bc",
        r"(a)\1",
        r"(?>a)bc",
        r"(",
        r"[",
        r"abc\Z",
        r"a++",
        r"a{1001}",
        r"\u0041",
        r"(a)?(?(1)a|b)",
        r"a**",
        r"[z-a]",
        r"\p{Foo}",
        r"x{2,1}",
        r"(?#comment)x",
        r"\8",
        r"[[:foo:]]",
        r"\C",
        r"\X",
        r"\R",
        r"(?x) x ",
        r"(?P<n>a)(?P<n>b)",
    ):
      with self.assertRaises(cel.CelEvalError, msg=pattern):
        cel._matches("abc", pattern)

  def test_unsupported_regular_expressions_fail_loudly(self):
    # Scripts and the case-folded Lu/Ll/Lt/Mn classes need RE2J's own
    # Unicode tables; failing beats silently returning a different answer.
    for pattern in (r"\p{Greek}", r"(?i)\p{Lu}", r"(?i)[^\P{Ll}]"):
      with self.assertRaisesRegex(cel.CelEvalError, "not supported|Unicode"):
        cel._matches("a", pattern)
    self.assertTrue(cel._matches("a", r"\p{Ll}"))
    self.assertTrue(cel._matches("a", r"(?i)\pL"))


class SchemaTest(unittest.TestCase):

  def test_fields_read_from_either_json_spelling_with_int64_strings(self):
    self.assertEqual(_eval("stages[0].stage_metrics.jvm_gc_time_millis"), 300)
    snake = [{"stage_metrics": {"jvm_gc_time_millis": 300}}]
    self.assertEqual(
        _eval("stages[0].stage_metrics.jvm_gc_time_millis", snake), 300
    )

  def test_absent_fields_are_proto_defaults(self):
    self.assertEqual(_eval("stages[1].stage_id"), 0)
    self.assertEqual(_eval("stages[1].name"), "")
    self.assertEqual(
        _eval("stages[1].task_quantile_metrics.duration_millis.maximum"), 0
    )
    self.assertEqual(_eval("stages[1].parent_stage_ids"), [])
    self.assertEqual(_eval("total_executor_summary.active_tasks"), 0)

  def test_has_follows_proto3_presence(self):
    self.assertTrue(_eval("has(stages[0].task_quantile_metrics)"))
    self.assertFalse(_eval("has(stages[1].task_quantile_metrics)"))
    self.assertTrue(_eval("has(stages[1].stage_metrics)"))  # Set, if empty.
    self.assertFalse(_eval("has(stages[1].stage_id)"))
    self.assertTrue(_eval("has(stages[0].parent_stage_ids)"))
    self.assertTrue(_eval("has(stages[0].locality.PROCESS_LOCAL)"))

  def test_convert_reads_bytes_as_proto_json_base64(self):
    self.assertEqual(cel.convert("YWI=", "bytes"), b"ab")
    self.assertEqual(cel.convert([97, 98], "bytes"), b"ab")
    self.assertEqual(cel.convert(None, "bytes"), b"")

  def test_repeated_and_map_fields(self):
    self.assertTrue(_eval("2 in stages[0].parent_stage_ids"))
    self.assertEqual(_eval("stages[0].locality['PROCESS_LOCAL']"), 5)

  def test_optional_and_timestamp_fields_have_explicit_presence(self):
    stages = [{
        "name": "",
        "failureReason": "",
        "completionTime": "1970-01-01T00:00:00Z",
        "tasks": {"1": {"durationMillis": "0", "executorId": ""}},
        "accumulatorUpdates": [{"accumullableInfoId": "0"}],
    }]
    for expression in (
        "has(stages[0].name)",
        "has(stages[0].failure_reason)",
        "has(stages[0].completion_time)",
        "has(stages[0].tasks[1].duration_millis)",
        "has(stages[0].tasks[1].executor_id)",
        "has(stages[0].accumulator_updates[0].accumullable_info_id)",
    ):
      self.assertTrue(_eval(expression, stages), expression)
    self.assertFalse(_eval("has(stages[0].description)", stages))
    self.assertFalse(_eval("has(stages[0].submission_time)", stages))


_SD = "google.cloud.dataproc.v1.StageData"
_SM = "google.cloud.dataproc.v1.StageMetrics"
_TS = "google.protobuf.Timestamp"


class MessageConstructionTest(unittest.TestCase):

  def test_construction_and_presence(self):
    for expression in (
        f"{_SD}{{stage_id: 1}}.stage_id == 1",
        f"{_SD}{{}}.stage_id == 0",
        f".{_SD}{{stage_id: 1,}}.stage_id == 1",
        f"{_SD}{{stage_id: 1, stage_id: 2}}.stage_id == 2",
        f"!has({_SD}{{stage_id: 0}}.stage_id)",
        f"has({_SD}{{name: ''}}.name)",
        f"has({_SD}{{stage_metrics: {_SM}{{}}}}.stage_metrics)",
        f"!has({_SD}{{stage_metrics: null}}.stage_metrics)",
        f"has({_SD}{{submission_time: timestamp(0)}}.submission_time)",
        f"{_SD}{{status: 3}}.status == 3",
        f"{_SD}{{job_ids: [1, null]}}.job_ids == [1]",
        f"{_SD}{{locality: {{'a': 1, 'b': null}}}}.locality == {{'a': 1}}",
        f"type({_SD}{{}}) == {_SD}",
        f"{_TS}{{}} == timestamp(0)",
        f"{_TS}{{seconds: 1, nanos: 1000000000}} == timestamp(2)",
    ):
      self.assertTrue(_eval(expression), expression)

  def test_message_equality_is_proto_equality(self):
    for expression in (
        f"{_SD}{{stage_id: 0, job_ids: []}} == {_SD}{{}}",
        f"{_SD}{{name: ''}} != {_SD}{{}}",
        f"{_SD}{{stage_metrics: {_SM}{{}}}} != {_SD}{{}}",
        f"{_SD}{{submission_time: timestamp(0)}} != {_SD}{{}}",
        (
            "stages.exists(s, s == google.cloud.dataproc.v1.StageData{"
            "stage_id: 0, num_tasks: 5, stage_metrics:"
            " google.cloud.dataproc.v1.StageMetrics{}})"
        ),
    ):
      self.assertTrue(_eval(expression), expression)

  def test_constructed_stages_can_be_rule_results(self):
    result = _eval(f"[{_SD}{{stage_id: 4}}]")
    self.assertTrue(cel.is_message(result[0], "StageData"))
    self.assertEqual(result[0].get("stage_id"), 4)

  def test_construction_type_errors(self):
    for expression in (
        "StageData{stage_id: 1}",
        "google.protobuf.Duration{}",
        f"{_SD}{{nope: 1}}",
        f"{_SD}{{stage_id: 1.0}}",
        f"{_SD}{{stage_id: 1u}}",
        f"{_SD}{{name: null}}",
        f"{_SD}{{job_ids: null}}",
        f"{_SD}{{job_ids: [null]}}",
        f"{_SD}{{stage_metrics: {{}}}}",
        f"{_SD}{{killed_tasks_summary: {{1: 1}}}}",
        f"{_TS}{{seconds: 1.0}}",
    ):
      with self.assertRaises(cel.CelTypeError, msg=expression):
        cel.compile_expression(expression)

  def test_construction_evaluation_errors(self):
    for expression in (
        f"{_SD}{{num_tasks: 3000000000}}.num_tasks == 0",
        f"{_SD}{{status: 3000000000}}.status == 0",
        (
            f"{_SD}{{killed_tasks_summary: {{'a': 3000000000}}}}"
            ".killed_tasks_summary.size() == 0"
        ),
        f"{_SD}{{stage_id: dyn(1.0)}}.stage_id == 1",
        f"{_SD}{{name: dyn(null)}}.name == ''",
        f"{_SD}{{stage_metrics: dyn({{}})}}.stage_id == 0",
        f"{_SD}{{job_ids: dyn([1u])}}.job_ids == []",
        f"{_TS}{{nanos: 3000000000}} == timestamp(0)",
    ):
      with self.assertRaises(cel.CelEvalError, msg=expression):
        _eval(expression)
    self.assertFalse(
        _eval(f"false && {_SD}{{stage_id: dyn(1.0)}}.stage_id == 1")
    )


class MapKeysTest(unittest.TestCase):

  def test_keys_compare_like_java_objects(self):
    self.assertEqual(_eval("size({1: 'a', 1u: 'b', 1.0: 'c', true: 'd'})"), 4)
    self.assertEqual(_eval("{[1]: 'a'}[[1]]"), "a")
    self.assertEqual(_eval("{1: 'a'}[dyn(1.0)]"), "a")
    self.assertFalse(_eval("2 in {1: 'a'}"))
    for expression in (
        "{[1]: 1, [1]: 2}",
        "{1: 1, 1: 2}",
        "{1.0: 'a'}[dyn(1)] == 'a'",
        "{-0.0: 1}[0.0] == 1",
    ):
      with self.assertRaises(cel.CelEvalError, msg=expression):
        _eval(expression)

  def test_map_equality_is_asymmetric_like_cel_java(self):
    self.assertTrue(_eval("dyn({1.0: 1}) == dyn({1: 1})"))
    self.assertFalse(_eval("dyn({1: 1}) == dyn({1.0: 1})"))


class TypeUnificationTest(unittest.TestCase):

  def test_null_only_unifies_with_nullable_types(self):
    for expression in (
        "stages[0].stage_metrics == null",
        "stages[0].submission_time == null",
        "null in [stages[0]]",
        "[1, null][1] == null",
        "(true ? stages[0] : null) == null",
    ):
      cel.compile_expression(expression)
    for expression in (
        "1 == null",
        "stages[0].name != null",
        "1 in [null]",
        "(true ? 1 : null) == 1",
        "(true ? 1 : 'a') == 1",
        "{'a': 1}[null] == 1",
    ):
      with self.assertRaises(cel.CelTypeError, msg=expression):
        cel.compile_expression(expression)

  def test_literal_and_branch_types_join_like_cel_java(self):
    # The joined type is CEL-Java's mostGeneral, which is order-sensitive.
    cel.compile_expression("[null, stages[0]][1].stage_id == 1")
    cel.compile_expression("[1, null][0] == 'a'")  # list(dyn)
    for expression in (
        "[stages[0], null][0].stage_id == 1",
        "(true ? null : stages[0]).stage_id == 1",
        "[[1], []][0] == ['a']",
        "([] + [1]) == ['a']",
        "[1] + ['a'] == []",
        "(1 + dyn(1)) == 1.0",
    ):
      with self.assertRaises(cel.CelTypeError, msg=expression):
        cel.compile_expression(expression)

  def test_null_operands_match_nullable_overloads(self):
    # These type-check (null fits timestamp/duration parameters) and fail
    # at evaluation, as in CEL-Java.
    for expression in (
        "null < timestamp(0)",
        "(null + duration('1s')) == 1",
        "int(null) == 0",
        "null.getHours() == 0",
    ):
      with self.assertRaises(cel.CelEvalError, msg=expression):
        _eval(expression)

  def test_enum_fields_are_ints(self):
    self.assertEqual(_eval("stages[0].status"), 3)
    self.assertTrue(
        _eval(
            "stages[0].status =="
            " google.cloud.dataproc.v1.StageStatus.STAGE_STATUS_FAILED"
        )
    )
    self.assertTrue(
        _eval(
            "stages[1].status =="
            " google.cloud.dataproc.v1.StageStatus.STAGE_STATUS_UNSPECIFIED"
        )
    )
    # No container is set in the 1P environment, so short names don't resolve.
    with self.assertRaisesRegex(cel.CelTypeError, "undeclared reference"):
      cel.compile_expression(
          "stages[1].status == StageStatus.STAGE_STATUS_UNSPECIFIED"
      )

  def test_type_errors(self):
    for expression, message in (
        ("stages[0].nope", "undefined field 'nope' on StageData"),
        ("total_executor_summary.gc", "undefined field 'gc'"),
        ("stages[0].num_tasks.x", "does not support field selection"),
        ("s.num_tasks > 0", "undeclared reference to 's'"),
        ("foo(1)", "undeclared reference to function 'foo'"),
        ("stages[0].status == 'X'", "enum fields are ints"),
        (
            "google.cloud.dataproc.v1.StageStatus.NOPE",
            (
                "undeclared reference to 'google.cloud.dataproc.v1.StageStatus"
                ".NOPE'"
            ),
        ),
        ("stages.filter(s, s.num_tasks)", "requires a bool"),
        ("stages['a']", "list index must be int"),
        ("1 < 'a'", "no matching overload"),
        ("'a'.contains(1)", "expects a string"),
        ("size(1)", "no matching overload"),
        ("has(stages[0].nope)", "undefined field"),
        ("Msg{a: 1}", "undeclared reference to message type"),
    ):
      with self.assertRaisesRegex(cel.CelTypeError, message, msg=expression):
        cel.compile_expression(expression)

  def test_syntax_errors(self):
    for expression in (
        "1 +",
        "(1",
        "a and b",
        "'unterminated",
        "stages.filter(1, true)",
        "has(1)",
        "1 = 1",
        "if",
    ):
      with self.assertRaises(cel.CelSyntaxError, msg=expression):
        cel.compile_expression(expression)

  def test_top_level_macro_variable(self):
    self.assertEqual(
        cel.compile_expression(
            "stages.filter(x, x.num_tasks > 0)"
        ).top_level_macro_variable(),
        "x",
    )
    self.assertIsNone(
        cel.compile_expression("size(stages) > 0").top_level_macro_variable()
    )

  def test_free_variables(self):
    program = cel.compile_expression(
        "stages.exists(s, s.num_tasks > total_executor_summary.active_tasks)"
    )
    self.assertEqual(
        program.free_variables, {"stages", "total_executor_summary"}
    )

  def test_field_path_validation(self):
    self.assertIsNone(
        cel.field_paths_valid("StageData", ["stage_metrics", "jvmGcTimeMillis"])
    )
    self.assertIn(
        "undefined field 'gc'",
        cel.field_paths_valid("StageData", ["stage_metrics", "gc"]),
    )
    self.assertIsNone(cel.field_paths_valid("StageData", ["name", "upper"]))


if __name__ == "__main__":
  unittest.main()
