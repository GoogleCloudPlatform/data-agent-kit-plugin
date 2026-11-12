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

"""Unit tests for spark_gcs_log_reader."""

import gzip
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

# Add scripts directory to path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_gcs_log_reader


class SparkGcsLogReaderTest(unittest.TestCase):

  def test_gcs_reads_verify_tls_with_the_shared_context(self):
    reader = spark_gcs_log_reader.GcsStreamReader("gs://bucket/logs/app.log")
    context = object()
    with mock.patch.object(
        spark_gcs_log_reader.subprocess, "check_output", return_value="tok\n"
    ), mock.patch.object(
        spark_gcs_log_reader.spark_applications,
        "ssl_context",
        return_value=context,
    ), mock.patch.object(
        spark_gcs_log_reader.urllib.request,
        "urlopen",
        side_effect=lambda *args, **kwargs: io.BytesIO(b"log line\n"),
    ) as urlopen:
      self.assertEqual(reader.open_range_stream(0, 8).read(), b"log line\n")
      self.assertEqual(reader.open_full_stream().read(), b"log line\n")
    self.assertEqual(urlopen.call_count, 2)
    for (request,), kwargs in urlopen.call_args_list:
      self.assertIs(kwargs["context"], context)
      self.assertEqual(request.get_header("Authorization"), "Bearer tok")
    range_request = urlopen.call_args_list[0][0][0]
    self.assertEqual(range_request.get_header("Range"), "bytes=0-8")

  def test_parse_gcs_uri(self):
    bucket, obj = spark_gcs_log_reader.parse_gcs_uri(
        "gs://my-bucket/path/to/driveroutput"
    )
    self.assertEqual(bucket, "my-bucket")
    self.assertEqual(obj, "path/to/driveroutput")

    bucket, obj = spark_gcs_log_reader.parse_gcs_uri(
        "https://storage.googleapis.com/my-bucket/logs/app.log"
    )
    self.assertEqual(bucket, "my-bucket")
    self.assertEqual(obj, "logs/app.log")

    bucket, obj = spark_gcs_log_reader.parse_gcs_uri("/local/path/to/file.log")
    self.assertIsNone(bucket)
    self.assertIsNone(obj)

  def test_tail_local_file(self):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
      for i in range(100):
        f.write(f"Log line {i}\n")
      temp_path = f.name

    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)
      self.assertEqual(reader.get_size(), os.path.getsize(temp_path))

      captured = io.StringIO()
      old_stdout = sys.stdout
      sys.stdout = captured
      try:
        spark_gcs_log_reader.action_tail(reader, num_lines=5)
      finally:
        sys.stdout = old_stdout

      lines = captured.getvalue().splitlines()
      self.assertEqual(len(lines), 5)
      self.assertEqual(lines[-1], "Log line 99")
      self.assertEqual(lines[0], "Log line 95")
    finally:
      os.remove(temp_path)

  def test_search_local_file(self):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
      for i in range(50):
        if i == 25:
          f.write("java.lang.OutOfMemoryError: Java heap space\n")
        else:
          f.write(f"Normal log line {i}\n")
      temp_path = f.name

    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)
      captured = io.StringIO()
      old_stdout = sys.stdout
      sys.stdout = captured
      try:
        spark_gcs_log_reader.action_search(
            reader, substring="OutOfMemoryError", regex=None, context=2
        )
      finally:
        sys.stdout = old_stdout

      output = captured.getvalue()
      self.assertIn("Match #1 at line 26", output)
      self.assertIn("OutOfMemoryError", output)
      self.assertIn("Normal log line 24", output)
    finally:
      os.remove(temp_path)

  def test_summarize_events_gz(self):
    # Field names below are Spark's own JsonProtocol spellings. Do not
    # "simplify" them: an earlier fixture invented `Task End Reason.Exception`
    # and `SparkListenerExecutorRemoved.Reason`, neither of which Spark emits,
    # which hid two parsing defects because the test validated the parser
    # against the parser's own assumptions.
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.1"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "app-test-01",
            "App Name": "TestJob",
            "User": "spark_user",
            "Timestamp": 1000,
        },
        {"Event": "SparkListenerJobStart", "Job ID": 0},
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Name": "count_stage",
                "Number of Tasks": 10,
                "Failure Reason": "Stage failed due to task failures",
                "Accumulables": [{
                    "Name": "internal.metrics.memoryBytesSpilled",
                    "Value": 10485760,
                }],
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Task Info": {
                "Task ID": 5,
                "Index": 0,
                "Attempt": 2,
                "Executor ID": "3",
                "Host": "worker-1",
            },
            "Task Metrics": {"JVM GC Time": 1500},
            "Task End Reason": {
                "Reason": "ExceptionFailure",
                "Class Name": "java.lang.ArithmeticException",
                "Description": "Divide by zero",
                "Stack Trace": [],
            },
        },
        {
            "Event": "SparkListenerExecutorRemoved",
            "Executor ID": "1",
            "Removed Reason": (
                "Container killed by YARN for exceeding memory limits"
            ),
            "Timestamp": 2000,
        },
        {
            "Event": "SparkListenerJobEnd",
            "Job ID": 0,
            "Job Result": {"Result": "JobFailed"},
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 5000},
    ]

    with tempfile.NamedTemporaryFile("wb", suffix=".gz", delete=False) as f:
      with gzip.GzipFile(fileobj=f, mode="wb") as gz:
        for ev in events:
          gz.write((json.dumps(ev) + "\n").encode("utf-8"))
      temp_path = f.name

    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)
      captured = io.StringIO()
      old_stdout = sys.stdout
      sys.stdout = captured
      try:
        spark_gcs_log_reader.action_summarize_events(reader)
      finally:
        sys.stdout = old_stdout

      summary = captured.getvalue()
      self.assertIn("app-test-01", summary)
      self.assertIn("TestJob", summary)
      self.assertIn("3.5.1", summary)
      self.assertIn("Stage 1", summary)
      self.assertIn("Mem Spilled", summary)

      # The exception class must be surfaced alongside the message, and the
      # raw reason dict must never be dumped as a fallback.
      self.assertIn("java.lang.ArithmeticException", summary)
      self.assertIn("Divide by zero", summary)
      self.assertNotIn("'Reason':", summary)

      # Executor loss reason is the primary OOM-vs-preemption signal.
      self.assertIn("Container killed by YARN", summary)
      self.assertNotIn("Reason: `None`", summary)

      # Attribution needed to spot one bad executor failing repeatedly.
      self.assertIn("Attempt 2", summary)
      self.assertIn("Executor 3", summary)

      # Roll-up counters.
      self.assertIn("`1` total, `1` failed", summary)  # jobs
      self.assertIn("**Tasks**: `0` completed, `1` failed", summary)
      self.assertIn("**Total JVM GC Time**: `1500 ms`", summary)
    finally:
      os.remove(temp_path)

  def test_read_range_rejects_unbounded_request(self):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
      f.write("line\n")
      temp_path = f.name

    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)
      with self.assertRaises(ValueError):
        spark_gcs_log_reader.action_read_range(
            reader, start_line=1, end_line=10_000_000
        )
    finally:
      os.remove(temp_path)

  def test_search_is_case_insensitive_when_requested(self):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
      f.write("some line\nJava Heap Space exhausted\nanother line\n")
      temp_path = f.name

    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)

      def run(ignore_case):
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
          spark_gcs_log_reader.action_search(
              reader,
              substring="java heap space",
              regex=None,
              context=0,
              ignore_case=ignore_case,
          )
        finally:
          sys.stdout = old_stdout
        return captured.getvalue()

      self.assertIn("Total matches found: 0", run(False))
      self.assertIn("Total matches found: 1", run(True))
    finally:
      os.remove(temp_path)

  def test_compression_detected_without_extension(self):
    # Dataproc writes event logs as `application_<id>` with no extension but
    # compressed content. Extension-only detection fed the raw bytes to the
    # UTF-8 decoder and produced garbage.
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.1"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "app-noext",
            "App Name": "NoExtJob",
            "User": "u",
            "Timestamp": 1000,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2000},
    ]
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, "application_1700000000000_0001")
    with gzip.open(temp_path, "wb") as gz:
      for ev in events:
        gz.write((json.dumps(ev) + "\n").encode("utf-8"))

    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)
      self.assertTrue(reader.is_compressed())

      captured = io.StringIO()
      old_stdout = sys.stdout
      sys.stdout = captured
      try:
        spark_gcs_log_reader.action_summarize_events(reader)
      finally:
        sys.stdout = old_stdout

      summary = captured.getvalue()
      self.assertIn("app-noext", summary)
      self.assertIn("3.5.1", summary)
    finally:
      os.remove(temp_path)
      os.rmdir(temp_dir)

  def test_plain_file_is_not_reported_as_compressed(self):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
      f.write("plain text log line\n")
      temp_path = f.name
    try:
      reader = spark_gcs_log_reader.GcsStreamReader(temp_path)
      self.assertFalse(reader.is_compressed())
    finally:
      os.remove(temp_path)

  def test_driveroutput_prefix_is_left_alone_for_local_paths(self):
    # Resolution only applies to GCS URIs; local paths pass through unchanged.
    reader = spark_gcs_log_reader.GcsStreamReader("/tmp/driveroutput")
    self.assertEqual(reader.resolve_uri(), "/tmp/driveroutput")

  def test_application_eventlog_prefix_resolves_compressed_object(self):
    reader = spark_gcs_log_reader.GcsStreamReader(
        "gs://my-bucket/eventlogs/application_1700000000000_0001"
    )
    with mock.patch.object(
        spark_gcs_log_reader.subprocess,
        "check_output",
        return_value=(
            "gs://my-bucket/eventlogs/application_1700000000000_0001.zstd\n"
        ),
    ):
      self.assertEqual(
          reader.resolve_uri(),
          "gs://my-bucket/eventlogs/application_1700000000000_0001.zstd",
      )

  def test_summarize_events_surfaces_io_skew_and_sql_metrics(self):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.1"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1700_0009",
            "App Name": "SkewedIngest",
            "User": "spark",
            "Timestamp": 1000,
        },
        {
            "Event": "SparkListenerSQLExecutionStart",
            "executionId": 0,
            "description": "parquet at job.py:20",
            "physicalPlanDescription": (
                "== Physical Plan ==\nExecute InsertIntoHadoopFsRelationCommand"
                " (2)\n+- Scan json (1)\n\n(1) Scan json\nOutput [3]:"
                " [id#1, region#2, payload#3]\nReadSchema:"
                " struct<id:string,region:string,payload:string>\n\n(2) Execute"
                " InsertIntoHadoopFsRelationCommand\nInput [4]: [id#1,"
                " region#2, payload#3, dt#4]\n"
            ),
            "sparkPlanInfo": {
                "nodeName": "Execute InsertIntoHadoopFsRelationCommand",
                "metrics": [
                    {
                        "name": "number of written rows",
                        "accumulatorId": 201,
                        "metricType": "sum",
                    },
                    {
                        "name": "written output",
                        "accumulatorId": 202,
                        "metricType": "size",
                    },
                ],
                "children": [{
                    "nodeName": "Scan json",
                    "metadata": {
                        "ReadSchema": (
                            "struct<id:string,region:string,payload:string>"
                        )
                    },
                    "metrics": [{
                        "name": "number of output rows",
                        "accumulatorId": 101,
                        "metricType": "sum",
                    }],
                    "children": [],
                }],
            },
            "time": 1100,
        },
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "parquet at job.py:20",
                "Number of Tasks": 3,
                "Submission Time": 1200,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {
                "Task ID": 0,
                "Launch Time": 1200,
                "Finish Time": 1300,
            },
            "Task Metrics": {
                "Executor Run Time": 90,
                "JVM GC Time": 5,
                "Input Metrics": {"Bytes Read": 1000, "Records Read": 100},
                "Output Metrics": {"Bytes Written": 500, "Records Written": 95},
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {
                "Task ID": 1,
                "Launch Time": 1200,
                "Finish Time": 1310,
            },
            "Task Metrics": {
                "Executor Run Time": 100,
                "JVM GC Time": 5,
                "Input Metrics": {"Bytes Read": 1000, "Records Read": 100},
                "Output Metrics": {"Bytes Written": 500, "Records Written": 95},
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {
                "Task ID": 2,
                "Launch Time": 1200,
                "Finish Time": 2200,
            },
            "Task Metrics": {
                "Executor Run Time": 950,
                "JVM GC Time": 10,
                "Input Metrics": {"Bytes Read": 8000, "Records Read": 800},
                "Output Metrics": {
                    "Bytes Written": 4000,
                    "Records Written": 760,
                },
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "parquet at job.py:20",
                "Number of Tasks": 3,
                "Submission Time": 1200,
                "Completion Time": 2200,
                "Accumulables": [{
                    "ID": 101,
                    "Name": "number of output rows",
                    "Value": 1000,
                }],
            },
        },
        {
            "Event": "SparkListenerDriverAccumUpdates",
            "executionId": 0,
            "accumUpdates": [[201, 950], [202, 5000]],
        },
        {
            "Event": "SparkListenerSQLExecutionEnd",
            "executionId": 0,
            "time": 2250,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2300},
    ]

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name

    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main([
            f"--uri={temp_path}",
            "--action=summarize_events",
            "--start-line=1",
            "--end-line=10",
            "--max-matches=5",
            "--ignore-case",
        ])
      out = captured.getvalue()
      self.assertIn("`10000` bytes, `1000` rows", out)
      self.assertIn("`5000` bytes, `950` rows", out)
      self.assertIn("100 / 800 (8.0x)", out)
      self.assertIn("number of output rows: 1,000", out)
      self.assertIn("number of written rows: 950", out)
      self.assertIn("written output: 4.9 KiB (5,000 B)", out)
      self.assertIn("`3` columns (`id, region, payload`)", out)
      self.assertIn("`4` columns (`id, region, payload, dt`)", out)
    finally:
      os.remove(temp_path)

  def test_summarize_events_supports_qualified_spark35_sql_events(self):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.3"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1793_0001",
            "App Name": "ClusterIngest",
            "User": "root",
            "Timestamp": 1000,
        },
        {
            "Event": (
                "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart"
            ),
            "executionId": 0,
            "description": "parquet at NativeMethodAccessorImpl.java:0",
            "physicalPlanDescription": (
                "== Physical Plan ==\nExecute"
                " InsertIntoHadoopFsRelationCommand (7)\n+- Scan json (1)\n\n"
                "(1) Scan json\nOutput [2]: [event_id#0, region#2]\nReadSchema:"
                " struct<event_id:string,region:string>\n\n(7) Execute"
                " InsertIntoHadoopFsRelationCommand\nInput: []\nArguments:"
                " gs://b/curated, false, Parquet, [path=gs://b/curated/],"
                " Overwrite, [event_id, region, fp]\n"
            ),
            "sparkPlanInfo": {
                "nodeName": "Execute InsertIntoHadoopFsRelationCommand",
                "metrics": [
                    {
                        "name": "written output",
                        "accumulatorId": 17,
                        "metricType": "size",
                    },
                    {
                        "name": "number of written files",
                        "accumulatorId": 16,
                        "metricType": "sum",
                    },
                ],
                "children": [{
                    "nodeName": "Scan json",
                    "metadata": {
                        "ReadSchema": "struct<event_id:string,region:string>"
                    },
                    "metrics": [{
                        "name": "number of output rows",
                        "accumulatorId": 35,
                        "metricType": "sum",
                    }],
                    "children": [],
                }],
            },
            "time": 1100,
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 1,
                "Submission Time": 1150,
                "Completion Time": 1500,
                "Accumulables": [{
                    "ID": 35,
                    "Name": "number of output rows",
                    "Value": "28500",
                }],
            },
        },
        {
            "Event": (
                "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates"
            ),
            "executionId": 0,
            "accumUpdates": [[16, 3], [17, 658280]],
        },
        {
            "Event": (
                "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd"
            ),
            "executionId": 0,
            "time": 1600,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1700},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name
    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main([
            f"--uri={temp_path}",
            "--action=summarize_events",
        ])
      out = captured.getvalue()
      self.assertIn("### SQL & Connector Executions (1)", out)
      self.assertIn("duration `500 ms`", out)
      self.assertIn("number of output rows: 28,500", out)
      self.assertIn("number of written files: 3", out)
      self.assertIn("written output: 642.9 KiB (658,280 B)", out)
      self.assertIn("`3` columns (`event_id, region, fp`)", out)
    finally:
      os.remove(temp_path)

  def test_rolling_eventlog_v2_directory_streams_all_shards_in_numeric_order(
      self,
  ):
    root_dir = tempfile.mkdtemp()
    v2_dir = os.path.join(root_dir, "eventlog_v2_application_1700_0001")
    os.mkdir(v2_dir)
    shard1 = os.path.join(v2_dir, "events_1_application_1700_0001")
    shard2 = os.path.join(v2_dir, "events_2_application_1700_0001")
    shard10 = os.path.join(v2_dir, "events_10_application_1700_0001")
    appstatus = os.path.join(v2_dir, "appstatus_application_1700_0001")
    try:
      with open(shard1, "w") as f:
        f.write(
            json.dumps({
                "Event": "SparkListenerApplicationStart",
                "App ID": "application_1700_0001",
                "App Name": "RollingV2Job",
                "User": "spark",
                "Timestamp": 1000,
            })
            + "\n"
        )
      with open(shard2, "w") as f:
        f.write(
            json.dumps({
                "Event": "SparkListenerStageSubmitted",
                "Stage Info": {
                    "Stage ID": 0,
                    "Stage Attempt ID": 0,
                    "Stage Name": "scan",
                    "Number of Tasks": 1,
                    "Submission Time": 1100,
                },
            })
            + "\n"
        )
        f.write(
            json.dumps({
                "Event": "SparkListenerTaskEnd",
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Task Info": {"Task ID": 0, "Index": 0},
                "Task Metrics": {
                    "Executor Run Time": 200,
                    "Input Metrics": {"Bytes Read": 4096, "Records Read": 250},
                },
                "Task End Reason": {"Reason": "Success"},
            })
            + "\n"
        )
      with open(shard10, "w") as f:
        f.write(
            json.dumps({
                "Event": "SparkListenerStageCompleted",
                "Stage Info": {
                    "Stage ID": 0,
                    "Stage Attempt ID": 0,
                    "Stage Name": "scan",
                    "Number of Tasks": 1,
                    "Completion Time": 1500,
                },
            })
            + "\n"
        )
        f.write(
            json.dumps({
                "Event": "SparkListenerApplicationEnd",
                "Timestamp": 9000,
            })
            + "\n"
        )
      with open(appstatus, "w"):
        pass

      # Direct v2 directory path and fallback application_<id> path must both
      # order events_2 before events_10 and read across all 3 shards.
      for uri_arg in (
          v2_dir,
          os.path.join(root_dir, "application_1700_0001"),
      ):
        captured = io.StringIO()
        with mock.patch("sys.stdout", captured), mock.patch(
            "sys.stderr", io.StringIO()
        ):
          spark_gcs_log_reader.main([
              f"--uri={uri_arg}",
              "--action=summarize_events",
          ])
        out = captured.getvalue()
        self.assertIn("RollingV2Job", out)
        self.assertIn("`8.00s`", out)
        self.assertIn("`4096` bytes, `250` rows", out)

      gcs_reader = spark_gcs_log_reader.GcsStreamReader(
          "gs://b/logs/eventlog_v2_application_1700_0001/"
      )
      with mock.patch.object(
          spark_gcs_log_reader.subprocess,
          "check_output",
          return_value=(
              "gs://b/logs/eventlog_v2_application_1700_0001/events_10_a\n"
              "gs://b/logs/eventlog_v2_application_1700_0001/events_1_a\n"
              "gs://b/logs/eventlog_v2_application_1700_0001/events_2_a\n"
          ),
      ):
        self.assertEqual(
            gcs_reader.resolve_uris(),
            [
                "gs://b/logs/eventlog_v2_application_1700_0001/events_1_a",
                "gs://b/logs/eventlog_v2_application_1700_0001/events_2_a",
                "gs://b/logs/eventlog_v2_application_1700_0001/events_10_a",
            ],
        )
    finally:
      for p in (shard1, shard2, shard10, appstatus):
        if os.path.exists(p):
          os.remove(p)
      os.rmdir(v2_dir)
      os.rmdir(root_dir)

  def test_summarize_events_deduplicates_retries_speculation_and_wide_schemas(
      self,
  ):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.1"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1700_0099",
            "App Name": "RetryDedupJob",
            "User": "spark",
            "Timestamp": 1000,
        },
        {
            "Event": "SparkListenerSQLExecutionStart",
            "executionId": 0,
            "description": "wide scan",
            "physicalPlanDescription": (
                "== Physical Plan ==\nScan csv (1)\n\n(1) Scan csv\n"
                "Output [40]: [c1#1, c2#2, ... 38 more fields]\n"
            ),
            "sparkPlanInfo": {
                "nodeName": "Scan csv",
                "metadata": {
                    "ReadSchema": "struct<c1:int,c2:string,... 38 more fields>"
                },
                "metrics": [],
                "children": [],
            },
            "time": 1050,
        },
        # Stage 0 attempt 0 fails after reading 400 rows.
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 2,
                "Submission Time": 1100,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {"Task ID": 0, "Index": 0},
            "Task Metrics": {
                "Input Metrics": {"Bytes Read": 4000, "Records Read": 400}
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 2,
                "Failure Reason": "ExecutorLostFailure",
                "Completion Time": 1300,
            },
        },
        # Stage 0 attempt 1 succeeds, including a speculative duplicate Index 0.
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 1,
                "Stage Name": "scan",
                "Number of Tasks": 2,
                "Submission Time": 1350,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 1,
            "Task Info": {"Task ID": 1, "Index": 0, "Attempt": 0},
            "Task Metrics": {
                "Input Metrics": {"Bytes Read": 5000, "Records Read": 500}
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 1,
            "Task Info": {"Task ID": 2, "Index": 0, "Attempt": 1},
            "Task Metrics": {
                "Input Metrics": {"Bytes Read": 5000, "Records Read": 500}
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 1,
            "Task Info": {"Task ID": 3, "Index": 1, "Attempt": 0},
            "Task Metrics": {
                "Input Metrics": {"Bytes Read": 5000, "Records Read": 500}
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 1,
                "Stage Name": "scan",
                "Number of Tasks": 2,
                "Completion Time": 1800,
            },
        },
        {
            "Event": "SparkListenerSQLExecutionEnd",
            "executionId": 0,
            "time": 1850,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2000},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name
    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main([
            f"--uri={temp_path}",
            "--action=summarize_events",
        ])
      out = captured.getvalue()
      self.assertIn("`10000` bytes, `1000` rows", out)
      self.assertIn("Superseded Failed Attempt Input", out)
      self.assertIn("[40 cols: c1, c2, ...]", out)
      self.assertIn("`40` columns (`c1, c2, ...`)", out)
    finally:
      os.remove(temp_path)

  def test_zst_cli_fallback_terminates_process_on_early_generator_close(self):
    raw_stream = io.BufferedReader(io.BytesIO(b"\x28\xb5\x2f\xfdpayload"))
    fake_proc = mock.MagicMock()
    fake_proc.stdout = io.BytesIO(b"line1\nline2\nline3\n")
    fake_proc.poll.return_value = None
    with mock.patch.object(
        spark_gcs_log_reader, "HAS_STDLIB_ZSTD", False
    ), mock.patch.object(
        spark_gcs_log_reader, "HAS_ZSTD", False
    ), mock.patch.object(
        spark_gcs_log_reader.shutil, "which", return_value="/usr/bin/zstd"
    ), mock.patch.object(
        spark_gcs_log_reader.subprocess, "Popen", return_value=fake_proc
    ):
      gen = spark_gcs_log_reader.get_decompressed_line_generator(
          raw_stream, "gs://b/log.zst"
      )
      self.assertEqual(next(gen), "line1\n")
      gen.close()
    self.assertTrue(raw_stream.closed)
    fake_proc.terminate.assert_called_once()
    fake_proc.wait.assert_called()

  def test_summarize_events_excludes_failed_stage_from_committed_io_totals(
      self,
  ):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.1"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1700_0100",
            "App Name": "FailedWriteJob",
            "User": "spark",
            "Timestamp": 1000,
        },
        # Stage 0 (scan) completes with 1,000 rows read.
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 1,
                "Submission Time": 1100,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {"Task ID": 0, "Index": 0},
            "Task Metrics": {
                "Input Metrics": {"Bytes Read": 8192, "Records Read": 1000}
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 1,
                "Completion Time": 1200,
            },
        },
        # Stage 1 (write) has 1 task write 500 rows before task 1 fails and
        # aborts the entire stage without committing.
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Attempt ID": 0,
                "Stage Name": "write",
                "Number of Tasks": 2,
                "Submission Time": 1250,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Stage Attempt ID": 0,
            "Task Info": {"Task ID": 1, "Index": 0},
            "Task Metrics": {
                "Output Metrics": {
                    "Bytes Written": 2048,
                    "Records Written": 500,
                }
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Stage Attempt ID": 0,
            "Task Info": {"Task ID": 2, "Index": 1},
            "Task End Reason": {
                "Reason": "ExceptionFailure",
                "Class Name": "java.lang.IllegalArgumentException",
                "Description": "Schema mismatch on target table",
            },
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Attempt ID": 0,
                "Stage Name": "write",
                "Number of Tasks": 2,
                "Failure Reason": "Job aborted due to stage failure",
                "Completion Time": 1400,
            },
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1500},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name
    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main([
            f"--uri={temp_path}",
            "--action=summarize_events",
        ])
      out = captured.getvalue()
      self.assertIn(
          "- **Input**: 8.0 KiB (1,000 rows) (`8192` bytes, `1000` rows)",
          out,
      )
      self.assertIn("- **Output**: 0 B (`0` bytes, `0` rows)", out)
      self.assertIn(
          "Uncommitted Failed/Incomplete Stage I/O (excluded above)**: input"
          " 0 B, output 2.0 KiB (500 rows)",
          out,
      )
    finally:
      os.remove(temp_path)

  def test_rolling_eventlog_v2_info_sums_shards_and_resolves_attempt_suffix(
      self,
  ):
    root_dir = tempfile.mkdtemp()
    v2_dir = os.path.join(root_dir, "eventlog_v2_application_1700_0002_1")
    os.mkdir(v2_dir)
    s1 = os.path.join(v2_dir, "events_1_app")
    s2 = os.path.join(v2_dir, "events_2_app")
    try:
      with open(s1, "wb") as f:
        f.write(b"a" * 120)
      with open(s2, "wb") as f:
        f.write(b"b" * 230)

      # Fallback from application_1700_0002 (no _1) to eventlog_v2_*_1 shards.
      local_app = spark_gcs_log_reader.GcsStreamReader(
          os.path.join(root_dir, "application_1700_0002")
      )
      self.assertEqual(local_app.resolve_uris(), [s1, s2])

      captured = io.StringIO()
      with mock.patch("sys.stdout", captured), mock.patch(
          "sys.stderr", io.StringIO()
      ), mock.patch.object(
          spark_gcs_log_reader, "LARGE_FILE_THRESHOLD_BYTES", 250
      ):
        spark_gcs_log_reader.main([f"--uri={v2_dir}", "--action=info"])
      info_out = captured.getvalue()
      self.assertIn("Shards: 2 rolling eventlog_v2 files", info_out)
      self.assertIn("Size: 350 bytes", info_out)
      self.assertIn("Is Large File (>20MB): True", info_out)

      # GCS Serverless / YARN-attempt directory resolution.
      serverless_v2 = spark_gcs_log_reader.GcsStreamReader(
          "gs://b/logs/eventlog_v2_spark-serverless-app-1/"
      )
      with mock.patch.object(
          spark_gcs_log_reader.subprocess,
          "check_output",
          return_value=(
              "gs://b/logs/eventlog_v2_spark-serverless-app-1/events_1_x\n"
              "gs://b/logs/eventlog_v2_spark-serverless-app-1/events_2_x\n"
          ),
      ):
        self.assertEqual(
            serverless_v2.resolve_uris(),
            [
                "gs://b/logs/eventlog_v2_spark-serverless-app-1/events_1_x",
                "gs://b/logs/eventlog_v2_spark-serverless-app-1/events_2_x",
            ],
        )
    finally:
      for p in (s1, s2):
        if os.path.exists(p):
          os.remove(p)
      os.rmdir(v2_dir)
      os.rmdir(root_dir)

  def test_resolve_uris_avoids_prefix_collision_and_picks_latest_v2_attempt(
      self,
  ):
    # 1. GCS: application_1700_0001 must NOT collide with application_1700_00010
    # and must select only shards from the highest numeric attempt (_10 > _2).
    reader = spark_gcs_log_reader.GcsStreamReader(
        "gs://b/logs/application_1700_0001"
    )
    ls_outputs = [
        # f"{base}*" returns app #10, not app #1:
        "gs://b/logs/application_1700_00010.zstd\n",
        # exact eventlog_v2_application_1700_0001/events_* is absent:
        "",
        # multi-attempt eventlog_v2_application_1700_0001_*/events_*:
        (
            "gs://b/logs/eventlog_v2_application_1700_0001_1/events_1_a1\n"
            "gs://b/logs/eventlog_v2_application_1700_0001_2/events_1_a2\n"
            "gs://b/logs/eventlog_v2_application_1700_0001_10/events_2_a10\n"
            "gs://b/logs/eventlog_v2_application_1700_0001_10/events_1_a10\n"
        ),
    ]
    with mock.patch.object(
        spark_gcs_log_reader.subprocess, "check_output", side_effect=ls_outputs
    ):
      self.assertEqual(
          reader.resolve_uris(),
          [
              "gs://b/logs/eventlog_v2_application_1700_0001_10/events_1_a10",
              "gs://b/logs/eventlog_v2_application_1700_0001_10/events_2_a10",
          ],
      )

    # 2. Local dir fallback also selects highest numeric attempt (_10 > _2).
    root_dir = tempfile.mkdtemp()
    d2 = os.path.join(root_dir, "eventlog_v2_application_1700_0003_2")
    d10 = os.path.join(root_dir, "eventlog_v2_application_1700_0003_10")
    os.mkdir(d2)
    os.mkdir(d10)
    s2 = os.path.join(d2, "events_1_a2")
    s10 = os.path.join(d10, "events_1_a10")
    try:
      with open(s2, "wb") as f:
        f.write(b"{}\n")
      with open(s10, "wb") as f:
        f.write(b"{}\n")
      local_reader = spark_gcs_log_reader.GcsStreamReader(
          os.path.join(root_dir, "application_1700_0003")
      )
      self.assertEqual(local_reader.resolve_uris(), [s10])
    finally:
      for p in (s2, s10):
        if os.path.exists(p):
          os.remove(p)
      for d in (d2, d10, root_dir):
        if os.path.exists(d):
          os.rmdir(d)

  def test_summarize_events_gc_pct_and_sql_accums_ignore_failed_attempts(self):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.3"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1799_0001",
            "App Name": "RetryJob",
            "User": "spark",
            "Timestamp": 1000,
        },
        {
            "Event": "SparkListenerSQLExecutionStart",
            "executionId": 0,
            "description": "scan retry query",
            "sparkPlanInfo": {
                "nodeName": "Scan parquet",
                "metrics": [{
                    "name": "number of output rows",
                    "accumulatorId": 35,
                    "metricType": "sum",
                }],
                "children": [],
            },
            "time": 1050,
        },
        # Failed task and speculative duplicate task incur heavy GC; succeeded
        # task spends 100 ms GC out of 5000 ms run time (2.0% GC overhead).
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {"Task ID": 0, "Index": 0, "Attempt": 0},
            "Task Metrics": {"Executor Run Time": 9000, "JVM GC Time": 8000},
            "Task End Reason": {
                "Reason": "ExecutorLostFailure",
                "Loss Reason": "Container killed",
            },
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "scan",
                "Number of Tasks": 1,
                "Failure Reason": "Executor lost",
                "Completion Time": 2000,
                "Accumulables": [{
                    "ID": 35,
                    "Name": "number of output rows",
                    "Value": "99999",
                }],
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 1,
            "Task Info": {"Task ID": 1, "Index": 0, "Attempt": 0},
            "Task Metrics": {
                "Executor Run Time": 5000,
                "JVM GC Time": 100,
                "Input Metrics": {"Bytes Read": 4096, "Records Read": 28500},
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 1,
            "Task Info": {"Task ID": 2, "Index": 0, "Attempt": 1},
            "Task Metrics": {
                "Executor Run Time": 4800,
                "JVM GC Time": 500,
                "Input Metrics": {"Bytes Read": 4096, "Records Read": 28500},
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 1,
                "Stage Name": "scan",
                "Number of Tasks": 1,
                "Completion Time": 7000,
                "Accumulables": [{
                    "ID": 35,
                    "Name": "number of output rows",
                    "Value": "28500",
                }],
            },
        },
        {
            "Event": "SparkListenerSQLExecutionEnd",
            "executionId": 0,
            "time": 7100,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 7200},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name
    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main(
            [f"--uri={temp_path}", "--action=summarize_events"]
        )
      out = captured.getvalue()
      self.assertIn("- **Total JVM GC Time**: `8600 ms`", out)
      self.assertIn(
          "- **Executor Run Time**: `5000 ms` (GC overhead: `2.0%`)", out
      )
      self.assertIn("number of output rows: 28,500", out)
      self.assertNotIn("99,999", out)
    finally:
      os.remove(temp_path)

  def test_summarize_events_tracks_superseded_reduce_io_and_trims_node_names(
      self,
  ):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "3.5.3"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1799_0002",
            "App Name": "ReduceRetryJob",
            "User": "spark",
            "Timestamp": 1000,
        },
        {
            "Event": "SparkListenerSQLExecutionStart",
            "executionId": 0,
            "description": "scan json with trailing space",
            "sparkPlanInfo": {
                "nodeName": "Scan json ",
                "metadata": {"ReadSchema": "struct<id:string,region:string>"},
                "metrics": [],
                "children": [],
            },
            "time": 1050,
        },
        # Reduce Stage 1 attempt 0 fails after reading 2048 B shuffle and
        # writing 1024 B partial output (in_bytes == 0).
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Attempt ID": 0,
                "Stage Name": "reduce_write",
                "Number of Tasks": 2,
                "Submission Time": 1100,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Stage Attempt ID": 0,
            "Task Info": {"Task ID": 10, "Index": 0, "Attempt": 0},
            "Task Metrics": {
                "Shuffle Read Metrics": {
                    "Remote Bytes Read": 2048,
                    "Total Records Read": 200,
                },
                "Output Metrics": {
                    "Bytes Written": 1024,
                    "Records Written": 200,
                },
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Attempt ID": 0,
                "Stage Name": "reduce_write",
                "Number of Tasks": 2,
                "Failure Reason": "FetchFailedException",
                "Completion Time": 1300,
            },
        },
        # Reduce Stage 1 attempt 1 succeeds across both partitions.
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Attempt ID": 1,
                "Stage Name": "reduce_write",
                "Number of Tasks": 2,
                "Submission Time": 1350,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Stage Attempt ID": 1,
            "Task Info": {"Task ID": 11, "Index": 0, "Attempt": 0},
            "Task Metrics": {
                "Shuffle Read Metrics": {
                    "Remote Bytes Read": 4096,
                    "Total Records Read": 400,
                },
                "Output Metrics": {
                    "Bytes Written": 2048,
                    "Records Written": 400,
                },
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 1,
                "Stage Attempt ID": 1,
                "Stage Name": "reduce_write",
                "Number of Tasks": 2,
                "Completion Time": 1600,
            },
        },
        {
            "Event": "SparkListenerSQLExecutionEnd",
            "executionId": 0,
            "time": 1650,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 1700},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name
    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main(
            [f"--uri={temp_path}", "--action=summarize_events"]
        )
      out = captured.getvalue()
      self.assertIn("- **Output**: 2.0 KiB (400 rows)", out)
      self.assertIn(
          "- **Superseded Failed Attempt I/O (excluded above)**: input 0 B,"
          " output 1.0 KiB (200 rows), shuffle read 2.0 KiB (200 rows)",
          out,
      )
      self.assertIn("`Scan json` [2 cols: id, region]", out)
      self.assertNotIn("`Scan json `", out)
    finally:
      os.remove(temp_path)

  def test_eventlog_v2_mixed_plain_and_compressed_shards_and_direct_dir_info(
      self,
  ):
    root_dir = tempfile.mkdtemp()
    v2_dir = os.path.join(root_dir, "eventlog_v2_application_1700_0055")
    os.mkdir(v2_dir)
    # Shard 1 is plain uncompressed JSON; shard 2 is gzip-compressed without
    # extension (content-sniffed); shard 3 has a .gz suffix.
    shard1 = os.path.join(v2_dir, "events_1_application_1700_0055")
    shard2 = os.path.join(v2_dir, "events_2_application_1700_0055")
    shard3 = os.path.join(v2_dir, "events_3_application_1700_0055.gz")
    try:
      with open(shard1, "w", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "Event": "SparkListenerApplicationStart",
                "App ID": "application_1700_0055",
                "App Name": "MixedShardV2Job",
                "User": "spark",
                "Timestamp": 1000,
            })
            + "\n"
        )
      with gzip.open(shard2, "wb") as gz:
        gz.write(
            (
                json.dumps({
                    "Event": "SparkListenerStageSubmitted",
                    "Stage Info": {
                        "Stage ID": 0,
                        "Stage Attempt ID": 0,
                        "Stage Name": "scan",
                        "Number of Tasks": 1,
                        "Submission Time": 1100,
                    },
                })
                + "\n"
                + json.dumps({
                    "Event": "SparkListenerTaskEnd",
                    "Stage ID": 0,
                    "Stage Attempt ID": 0,
                    "Task Info": {"Task ID": 0, "Index": 0},
                    "Task Metrics": {
                        "Executor Run Time": 150,
                        "Input Metrics": {
                            "Bytes Read": 2048,
                            "Records Read": 125,
                        },
                    },
                    "Task End Reason": {"Reason": "Success"},
                })
                + "\n"
            ).encode("utf-8")
        )
      with gzip.open(shard3, "wb") as gz:
        gz.write(
            (
                json.dumps({
                    "Event": "SparkListenerStageCompleted",
                    "Stage Info": {
                        "Stage ID": 0,
                        "Stage Attempt ID": 0,
                        "Stage Name": "scan",
                        "Number of Tasks": 1,
                        "Completion Time": 1400,
                    },
                })
                + "\n"
                + json.dumps({
                    "Event": "SparkListenerApplicationEnd",
                    "Timestamp": 5000,
                })
                + "\n"
            ).encode("utf-8")
        )

      expected_bytes = sum(os.path.getsize(p) for p in (shard1, shard2, shard3))

      # Direct GcsStreamReader(v2_dir) must sum shard sizes (not directory
      # inode size) and detect compression across mixed shards.
      direct_reader = spark_gcs_log_reader.GcsStreamReader(v2_dir)
      self.assertEqual(direct_reader.get_size(), expected_bytes)
      self.assertTrue(direct_reader.is_compressed())

      info_out = io.StringIO()
      with mock.patch("sys.stdout", info_out), mock.patch(
          "sys.stderr", io.StringIO()
      ):
        spark_gcs_log_reader.main([f"--uri={v2_dir}", "--action=info"])
      self.assertIn("Shards: 3 rolling eventlog_v2 files", info_out.getvalue())
      self.assertIn(f"Size: {expected_bytes} bytes", info_out.getvalue())
      self.assertIn("Compressed: True", info_out.getvalue())

      sum_out = io.StringIO()
      with mock.patch("sys.stdout", sum_out), mock.patch(
          "sys.stderr", io.StringIO()
      ):
        spark_gcs_log_reader.main(
            [f"--uri={v2_dir}", "--action=summarize_events"]
        )
      summary = sum_out.getvalue()
      self.assertIn("MixedShardV2Job", summary)
      self.assertIn("`4.00s`", summary)
      self.assertIn("`2048` bytes, `125` rows", summary)

      tail_out = io.StringIO()
      with mock.patch("sys.stdout", tail_out), mock.patch(
          "sys.stderr", io.StringIO()
      ):
        spark_gcs_log_reader.main(
            [f"--uri={v2_dir}", "--action=tail", "--lines=1"]
        )
      self.assertIn("SparkListenerApplicationEnd", tail_out.getvalue())
    finally:
      for p in (shard1, shard2, shard3):
        if os.path.exists(p):
          os.remove(p)
      os.rmdir(v2_dir)
      os.rmdir(root_dir)

  def test_gcs_http_401_falls_back_to_application_default_credentials(self):
    reader = spark_gcs_log_reader.GcsStreamReader("gs://bucket/logs/app.log")
    context = object()
    err_401 = spark_gcs_log_reader.urllib.error.HTTPError(
        "https://storage.googleapis.com/bucket/logs/app.log",
        401,
        "Unauthorized",
        {},
        io.BytesIO(b"ACCESS_TOKEN_TYPE_UNSUPPORTED"),
    )
    try:
      with mock.patch.object(
          spark_gcs_log_reader.subprocess,
          "check_output",
          side_effect=["user-tok\n", "adc-tok\n"],
      ) as check_out, mock.patch.object(
          spark_gcs_log_reader.spark_applications,
          "ssl_context",
          return_value=context,
      ), mock.patch.object(
          spark_gcs_log_reader.urllib.request,
          "urlopen",
          side_effect=[err_401, io.BytesIO(b"ok\n")],
      ) as urlopen:
        self.assertEqual(reader.open_full_stream().read(), b"ok\n")
      self.assertEqual(check_out.call_count, 2)
      self.assertEqual(
          check_out.call_args_list[1].args[0],
          ["gcloud", "auth", "application-default", "print-access-token"],
      )
      self.assertEqual(urlopen.call_count, 2)
      self.assertEqual(
          urlopen.call_args_list[1][0][0].get_header("Authorization"),
          "Bearer adc-tok",
      )
    finally:
      err_401.close()

  def test_summarize_events_surfaces_connect_sdp_ops_peak_mem_and_true_avg_file(
      self,
  ):
    events = [
        {"Event": "SparkListenerLogStart", "Spark Version": "4.0.0"},
        {
            "Event": "SparkListenerApplicationStart",
            "App ID": "application_1800_0001",
            "App Name": "SdpPipelineJob",
            "User": "spark",
            "Timestamp": 1000,
        },
        {
            "Event": "SparkListenerExecutorAdded",
            "Timestamp": 1020,
            "Executor ID": "1",
            "Executor Info": {"Host": "10.0.0.5", "Total Cores": 4},
        },
        {
            "Event": (
                "org.apache.spark.sql.connect.service."
                "SparkListenerConnectOperationStarted"
            ),
            "operationId": "op-sdp-1",
            "jobTag": "dcs_sdp_dataset:orders_gold",
            "sessionId": "sess-1",
            "statementText": "CREATE OR REFRESH LIVE TABLE orders_gold",
            "eventTime": 1050,
        },
        {
            "Event": "SparkListenerSQLExecutionStart",
            "executionId": 0,
            "description": "sdp table orders_gold",
            "sparkPlanInfo": {
                "nodeName": "Execute InsertIntoHadoopFsRelationCommand",
                "metrics": [
                    {
                        "name": "written output",
                        "accumulatorId": 10,
                        "metricType": "size",
                    },
                    {
                        "name": "number of written files",
                        "accumulatorId": 11,
                        "metricType": "sum",
                    },
                    {
                        "name": "avg file size written",
                        "accumulatorId": 12,
                        "metricType": "size",
                    },
                ],
                "children": [],
            },
            "time": 1060,
        },
        {
            "Event": "SparkListenerStageSubmitted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "write orders_gold",
                "Number of Tasks": 2,
                "Submission Time": 1100,
            },
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {
                "Task ID": 0,
                "Index": 0,
                "Launch Time": 1100,
                "Finish Time": 1200,
            },
            "Task Metrics": {
                "Executor Run Time": 90,
                "Output Metrics": {
                    "Bytes Written": 329140,
                    "Records Written": 500,
                },
            },
            "Task Executor Metrics": {
                "JVMHeapMemory": 698980624,
                "JVMOffHeapMemory": 113493960,
                "ProcessTreePythonRSSMemory": 67108864,
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 0,
            "Stage Attempt ID": 0,
            "Task Info": {
                "Task ID": 1,
                "Index": 1,
                "Launch Time": 1100,
                "Finish Time": 2100,
            },
            "Task Metrics": {
                "Executor Run Time": 950,
                "Output Metrics": {
                    "Bytes Written": 329140,
                    "Records Written": 500,
                },
            },
            "Task End Reason": {"Reason": "Success"},
        },
        {
            "Event": "SparkListenerStageCompleted",
            "Stage Info": {
                "Stage ID": 0,
                "Stage Attempt ID": 0,
                "Stage Name": "write orders_gold",
                "Number of Tasks": 2,
                "Submission Time": 1100,
                "Completion Time": 2100,
            },
        },
        {
            "Event": "SparkListenerDriverAccumUpdates",
            "executionId": 0,
            "accumUpdates": [[10, 658280], [11, 3], [12, 658280]],
        },
        {
            "Event": "SparkListenerSQLExecutionEnd",
            "executionId": 0,
            "time": 2120,
        },
        {
            "Event": (
                "org.apache.spark.sql.connect.service."
                "SparkListenerConnectOperationFinished"
            ),
            "operationId": "op-sdp-1",
            "jobTag": "dcs_sdp_dataset:orders_gold",
            "producedRowCount": 1000,
            "eventTime": 2150,
        },
        {
            "Event": (
                "org.apache.spark.sql.connect.service."
                "SparkListenerConnectOperationStarted"
            ),
            "operationId": "op-sdp-2",
            "jobTag": "dcs_sdp_dataset:bad_view",
            "sessionId": "sess-1",
            "eventTime": 2200,
        },
        {
            "Event": (
                "org.apache.spark.sql.connect.service."
                "SparkListenerConnectOperationFailed"
            ),
            "operationId": "op-sdp-2",
            "jobTag": "dcs_sdp_dataset:bad_view",
            "errorMessage": "AnalysisException: Table missing_src not found",
            "eventTime": 2250,
        },
        {"Event": "SparkListenerApplicationEnd", "Timestamp": 2300},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
      for ev in events:
        f.write(json.dumps(ev) + "\n")
      temp_path = f.name
    try:
      captured = io.StringIO()
      with mock.patch("sys.stdout", captured):
        spark_gcs_log_reader.main(
            [f"--uri={temp_path}", "--action=summarize_events"]
        )
      out = captured.getvalue()
      self.assertIn("- **Executors Added**: `1` (`4` total cores)", out)
      self.assertIn(
          "- **Peak Task Executor Memory**: JVMHeap: 666.6 MiB, JVMOffHeap:"
          " 108.2 MiB, PyRSS: 64.0 MiB",
          out,
      )
      self.assertIn("Duration-weighted job_skew_score", out)
      self.assertIn("[true avg written output / files: 214.3 KiB]", out)
      self.assertIn("### Spark Connect & SDP Operations (2)", out)
      self.assertIn(
          "Operation `op-sdp-1`** (FINISHED, duration `1.1 s`, jobTag"
          " `dcs_sdp_dataset:orders_gold`, session `sess-1`, rows `1,000`)",
          out,
      )
      self.assertIn("AnalysisException: Table missing_src not found", out)
    finally:
      os.remove(temp_path)


if __name__ == "__main__":
  unittest.main()
