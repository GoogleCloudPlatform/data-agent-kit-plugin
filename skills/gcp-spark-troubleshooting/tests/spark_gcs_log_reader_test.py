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

# Add scripts directory to path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_gcs_log_reader


class SparkGcsLogReaderTest(unittest.TestCase):

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


if __name__ == "__main__":
  unittest.main()
