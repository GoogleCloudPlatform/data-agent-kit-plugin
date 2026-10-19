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

"""Unit tests for gcp_job_monitor."""

import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.parse

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import gcp_job_monitor


class _FakeTokens:
  """Token provider double."""

  def __init__(self, sources=("adc-token", "user-token")):
    self.sources = list(sources)
    self.index = 0

  def token(self):
    return self.sources[self.index]

  def fallback(self):
    if self.index + 1 >= len(self.sources):
      return False
    self.index += 1
    return True


class _FakeResponse:
  """Context-manager response double for urllib.request.urlopen."""

  def __init__(self, body_bytes: bytes):
    self._body = body_bytes

  def read(self) -> bytes:
    return self._body

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False


class _FakeUrlopen:
  """Replays canned (status, body) responses and records every Request."""

  def __init__(self, responses):
    self.responses = list(responses)
    self.requests = []

  def __call__(self, request, timeout=None, context=None):
    del timeout, context
    self.requests.append(request)
    status, body = self.responses.pop(0)
    if not isinstance(body, bytes):
      body = json.dumps(body).encode("utf-8")
    if status >= 400:
      raise urllib.error.HTTPError(
          url=request.full_url,
          code=status,
          msg=f"HTTP {status}",
          hdrs=None,
          fp=io.BytesIO(body),
      )
    return _FakeResponse(body)

  def query(self, i):
    return urllib.parse.parse_qs(
        urllib.parse.urlsplit(self.requests[i].full_url).query
    )

  def path(self, i):
    return urllib.parse.urlsplit(self.requests[i].full_url).path


def _sample_bq_job(
    job_id="job_1",
    user_email="alice@example.com",
    state="DONE",
    start_ms=1700000000000,
    end_ms=1700000005000,
    bytes_billed=10737418240,  # 10 GiB
    slot_ms=25000,
    query="SELECT * FROM `p.d.t`",
    error_message=None,
):
  raw = {
      "jobReference": {
          "projectId": "test-proj",
          "jobId": job_id,
          "location": "US",
      },
      "user_email": user_email,
      "status": {"state": state},
      "configuration": {
          "jobType": "QUERY",
          "query": {"query": query},
      },
      "statistics": {
          "creationTime": str(start_ms),
          "startTime": str(start_ms),
          "endTime": str(end_ms),
          "totalSlotMs": str(slot_ms),
          "totalBytesProcessed": str(bytes_billed),
          "query": {
              "totalBytesBilled": str(bytes_billed),
              "totalBytesProcessed": str(bytes_billed),
              "totalSlotMs": str(slot_ms),
              "statementType": "SELECT",
              "cacheHit": False,
              "referencedTables": [
                  {"projectId": "p", "datasetId": "d", "tableId": "t"}
              ],
              "queryPlan": [{
                  "id": "0",
                  "name": "S00: Input",
                  "status": "COMPLETE",
                  "recordsRead": "1000",
                  "recordsWritten": "10",
                  "slotMs": "25000",
                  "waitMsMax": "12",
                  "computeMsMax": "450",
                  "shuffleOutputBytesSpilled": "0",
              }],
          },
      },
  }
  if error_message:
    raw["status"]["errorResult"] = {
        "reason": "invalidQuery",
        "message": error_message,
    }
  return raw


class BigQueryJobMonitorTest(unittest.TestCase):

  def test_fetch_bq_jobs_falls_back_when_all_users_forbidden(self):
    forbidden = {
        "error": {
            "code": 403,
            "message": "Access Denied: BigQuery BigQuery: Permission denied",
        }
    }
    ok_body = {"jobs": [_sample_bq_job(job_id="j_own")]}
    urlopen = _FakeUrlopen([(403, forbidden), (200, ok_body)])
    client = gcp_job_monitor.RestClient(
        token_provider=_FakeTokens(), urlopen=urlopen
    )

    jobs, fell_back = gcp_job_monitor.fetch_bq_jobs(
        client, "test-proj", max_results=5, all_users=True
    )

    self.assertTrue(fell_back)
    self.assertEqual(len(jobs), 1)
    self.assertEqual(jobs[0]["jobId"], "j_own")
    self.assertEqual(urlopen.query(0).get("allUsers"), ["true"])
    self.assertIsNone(urlopen.query(1).get("allUsers"))

  def test_rank_top_cost_and_slowest_bq_jobs(self):
    cheap_slow = gcp_job_monitor.normalize_bq_job(
        _sample_bq_job(
            job_id="cheap_slow",
            start_ms=1700000000000,
            end_ms=1700000060000,  # 60s
            bytes_billed=1024 * 1024,  # 1 MiB
            slot_ms=5000,
        )
    )
    expensive_fast = gcp_job_monitor.normalize_bq_job(
        _sample_bq_job(
            job_id="expensive_fast",
            start_ms=1700000000000,
            end_ms=1700000002000,  # 2s
            bytes_billed=1024**4,  # 1 TiB ($6.25)
            slot_ms=90000,
        )
    )
    jobs = [cheap_slow, expensive_fast]

    by_cost = sorted(
        jobs,
        key=lambda j: (j["bytesBilled"], j["slotMs"]),
        reverse=True,
    )
    by_duration = sorted(jobs, key=lambda j: j["durationMs"], reverse=True)

    self.assertEqual(by_cost[0]["jobId"], "expensive_fast")
    self.assertAlmostEqual(by_cost[0]["estimatedUsd"], 6.25, places=2)
    self.assertEqual(by_duration[0]["jobId"], "cheap_slow")
    self.assertEqual(by_duration[0]["durationMs"], 60000)

  def test_fetch_bq_job_detail_parses_location_prefix_and_renders_stages(self):
    urlopen = _FakeUrlopen([(200, _sample_bq_job(job_id="bquxjob_123"))])
    client = gcp_job_monitor.RestClient(
        token_provider=_FakeTokens(), urlopen=urlopen
    )

    detail = gcp_job_monitor.fetch_bq_job_detail(
        client, "default-proj", "custom-proj:us-central1.bquxjob_123"
    )
    self.assertEqual(
        urlopen.path(0),
        "/bigquery/v2/projects/custom-proj/jobs/bquxjob_123",
    )
    self.assertEqual(urlopen.query(0).get("location"), ["us-central1"])

    md = gcp_job_monitor.render_bq_detail_markdown(detail)
    self.assertIn("`bquxjob_123`", md)
    self.assertIn("`S00: Input`", md)
    self.assertIn("`p.d.t`", md)


class SparkWorkloadMonitorTest(unittest.TestCase):

  def test_fetch_spark_workloads_merges_serverless_and_cluster_jobs(self):
    batches_resp = {
        "batches": [{
            "name": "projects/p/locations/us-central1/batches/batch-1",
            "state": "SUCCEEDED",
            "createTime": "2026-10-14T10:00:00Z",
            "stateTime": "2026-10-14T10:05:00Z",
            "creator": "alice@example.com",
            "pysparkBatch": {"mainPythonFileUri": "gs://b/etl.py"},
            "runtimeInfo": {
                "approximateUsage": {
                    "milliDcuSeconds": "3600000",
                    "shuffleStorageGbSeconds": "120",
                }
            },
        }]
    }
    cluster_jobs_resp = {
        "jobs": [{
            "reference": {"projectId": "p", "jobId": "cluster-job-1"},
            "placement": {"clusterName": "analytics-cluster"},
            "status": {
                "state": "ERROR",
                "stateStartTime": "2026-10-14T11:02:00Z",
                "details": "Container exited with non-zero exit code 1",
            },
            "statusHistory": [
                {"state": "PENDING", "stateStartTime": "2026-10-14T11:00:00Z"},
                {"state": "RUNNING", "stateStartTime": "2026-10-14T11:00:10Z"},
            ],
            "sparkJob": {"mainClass": "com.example.Main"},
            "driverOutputResourceUri": "gs://b/driveroutput.000000000",
        }]
    }
    urlopen = _FakeUrlopen([(200, batches_resp), (200, cluster_jobs_resp)])
    client = gcp_job_monitor.RestClient(
        token_provider=_FakeTokens(), urlopen=urlopen
    )

    items, warnings = gcp_job_monitor.fetch_spark_workloads(
        client, "p", "us-central1", max_results=10
    )

    self.assertEqual(warnings, [])
    self.assertEqual(len(items), 2)
    # Cluster job is newer (11:00 vs 10:00), so it appears first in list
    self.assertEqual(items[0]["id"], "cluster-job-1")
    self.assertEqual(items[0]["kind"], "CLUSTER_JOB")
    self.assertEqual(items[0]["durationMs"], 120000)
    self.assertEqual(items[1]["id"], "batch-1")
    self.assertEqual(items[1]["kind"], "SERVERLESS_BATCH")
    self.assertEqual(items[1]["durationMs"], 300000)
    self.assertEqual(items[1]["milliDcuSeconds"], 3600000)

  def test_fetch_spark_workload_detail_falls_back_from_batch_to_cluster_job(
      self,
  ):
    not_found = {"error": {"code": 404, "message": "Batch not found"}}
    cluster_job = {
        "reference": {"projectId": "p", "jobId": "spark-job-99"},
        "placement": {"clusterName": "prod-spark-cluster"},
        "status": {
            "state": "DONE",
            "stateStartTime": "2026-10-14T12:10:00Z",
        },
        "statusHistory": [
            {"state": "PENDING", "stateStartTime": "2026-10-14T12:00:00Z"},
            {"state": "RUNNING", "stateStartTime": "2026-10-14T12:00:05Z"},
        ],
        "pysparkJob": {"mainPythonFileUri": "gs://bucket/jobs/train.py"},
        "driverOutputResourceUri": "gs://bucket/logs/driveroutput.000000000",
    }
    urlopen = _FakeUrlopen([(404, not_found), (200, cluster_job)])
    client = gcp_job_monitor.RestClient(
        token_provider=_FakeTokens(), urlopen=urlopen
    )

    detail = gcp_job_monitor.fetch_spark_workload_detail(
        client, "p", "spark-job-99", region="us-central1"
    )

    self.assertEqual(detail["id"], "spark-job-99")
    self.assertEqual(detail["kind"], "CLUSTER_JOB")
    self.assertEqual(detail["workloadType"], "PYSPARK")
    self.assertEqual(detail["clusterName"], "prod-spark-cluster")
    self.assertEqual(detail["durationMs"], 600000)
    md = gcp_job_monitor.render_spark_detail_markdown(detail)
    self.assertIn("`spark-job-99`", md)
    self.assertIn("`gs://bucket/jobs/train.py`", md)
    self.assertIn("`gs://bucket/logs/driveroutput.000000000`", md)

  def test_cli_flags_project_id_alias_days_state_and_multi_region(self):
    parser = gcp_job_monitor.build_parser()
    args = parser.parse_args([
        "--action=bq_top_cost",
        "--project_id=my-proj",
        "--days=30",
        "--state=FAILED",
        "--region=us-central1,us-east1",
        "--workload_type=cluster_job",
    ])
    self.assertEqual(args.project, "my-proj")
    self.assertEqual(args.days, 30.0)
    self.assertEqual(args.state, "FAILED")
    self.assertEqual(args.region, "us-central1,us-east1")
    self.assertEqual(args.workload_type, "cluster_job")

  def test_aggregate_bq_summary_and_hot_tables(self):
    j1 = gcp_job_monitor.normalize_bq_job(
        _sample_bq_job(
            job_id="j1",
            user_email="alice@example.com",
            bytes_billed=1024**3,  # 1 GiB
            slot_ms=10000,
        )
    )
    j2 = gcp_job_monitor.normalize_bq_job(
        _sample_bq_job(
            job_id="j2",
            user_email="bob@example.com",
            state="DONE",
            bytes_billed=0,
            slot_ms=0,
            error_message="Dataset looker_scratch not found",
        )
    )
    summary = gcp_job_monitor.aggregate_bq_summary([j1, j2])
    self.assertEqual(summary["totalJobsAnalyzed"], 2)
    self.assertEqual(summary["byUser"][0]["userEmail"], "alice@example.com")
    self.assertEqual(summary["byUser"][0]["succeededJobs"], 1)
    self.assertEqual(summary["topErrors"][0]["errorReason"], "invalidQuery")
    self.assertEqual(summary["topErrors"][0]["count"], 1)

    hot = gcp_job_monitor.aggregate_bq_hot_tables([j1, j2])
    self.assertEqual(hot["hotTables"][0]["table"], "p.d.t")
    self.assertEqual(hot["hotTables"][0]["queryCount"], 2)
    self.assertEqual(hot["hotTables"][0]["totalBytesBilled"], 1024**3)

  def test_remote_cli_mcp_client_routes_bq_and_spark_calls(self):
    recorded_cmds = []

    def fake_runner(cmd):
      recorded_cmds.append(list(cmd))
      server = cmd[2]
      tool = cmd[3]
      if server == "bigquery" and tool == "execute_sql_readonly":
        args_json = json.loads(cmd[5])
        self.assertEqual(args_json.get("project_id"), "p")
        return (
            0,
            json.dumps({
                "tool": "execute_sql_readonly",
                "isError": False,
                "result": {
                    "jobComplete": True,
                    "schema": {
                        "fields": [
                            {"name": "job_id", "type": "STRING"},
                            {"name": "project_id", "type": "STRING"},
                            {"name": "user_email", "type": "STRING"},
                            {"name": "job_type", "type": "STRING"},
                            {"name": "statement_type", "type": "STRING"},
                            {"name": "state", "type": "STRING"},
                            {"name": "priority", "type": "STRING"},
                            {"name": "reservation_id", "type": "STRING"},
                            {"name": "edition", "type": "STRING"},
                            {"name": "creation_ms", "type": "STRING"},
                            {"name": "start_ms", "type": "STRING"},
                            {"name": "end_ms", "type": "STRING"},
                            {"name": "total_bytes_billed", "type": "STRING"},
                            {"name": "total_bytes_processed", "type": "STRING"},
                            {"name": "total_slot_ms", "type": "STRING"},
                            {"name": "cache_hit", "type": "BOOLEAN"},
                            {"name": "query", "type": "STRING"},
                            {"name": "error_reason", "type": "STRING"},
                            {"name": "error_message", "type": "STRING"},
                            {
                                "name": "referenced_tables_json",
                                "type": "STRING",
                            },
                            {"name": "labels_json", "type": "STRING"},
                        ]
                    },
                    "rows": [{
                        "f": [
                            {"v": "bqjob_mcp_1"},
                            {"v": "p"},
                            {"v": "alice@example.com"},
                            {"v": "QUERY"},
                            {"v": "SELECT"},
                            {"v": "DONE"},
                            {"v": "INTERACTIVE"},
                            {"v": "res-1"},
                            {"v": "ENTERPRISE"},
                            {"v": "1791990000000"},
                            {"v": "1791990000100"},
                            {"v": "1791990005100"},
                            {"v": str(1024**3)},
                            {"v": str(1024**3)},
                            {"v": "15000"},
                            {"v": "false"},
                            {"v": "SELECT * FROM `p.d.t`"},
                            {"v": ""},
                            {"v": ""},
                            {
                                "v": json.dumps([{
                                    "project_id": "p",
                                    "dataset_id": "d",
                                    "table_id": "t",
                                }])
                            },
                            {"v": "[]"},
                        ]
                    }],
                },
            }),
            "",
        )
      if server == "google-managed-apache-spark" and tool == "list_batches":
        return (
            0,
            json.dumps({
                "tool": "list_batches",
                "isError": False,
                "result": {
                    "batches": [{
                        "batch_name": (
                            "projects/p/locations/us-central1/batches/b1"
                        ),
                        "state": "SUCCEEDED",
                        "create_time": "2026-10-14T10:00:00Z",
                        "state_time": "2026-10-14T10:02:00Z",
                        "pysparkBatch": {"mainPythonFileUri": "gs://b/m.py"},
                    }]
                },
            }),
            "",
        )
      if server == "google-managed-apache-spark" and tool == "list_jobs":
        return (0, json.dumps({"jobs": []}), "")
      return (1, "", "unexpected tool")

    mcp_client = gcp_job_monitor.RemoteCliMcpClient(
        runner=fake_runner, billing_project="p"
    )
    bq_jobs, fell_back = gcp_job_monitor.fetch_bq_jobs(
        mcp_client, "p", max_results=5
    )
    self.assertFalse(fell_back)
    self.assertEqual(len(bq_jobs), 1)
    self.assertEqual(bq_jobs[0]["jobId"], "bqjob_mcp_1")
    self.assertEqual(bq_jobs[0]["bytesBilled"], 1024**3)
    self.assertEqual(bq_jobs[0]["referencedTables"], ["p.d.t"])

    spark_items, warnings = gcp_job_monitor.fetch_spark_workloads(
        mcp_client, "p", "us-central1", max_results=5
    )
    self.assertEqual(warnings, [])
    self.assertEqual(len(spark_items), 1)
    self.assertEqual(spark_items[0]["id"], "b1")
    self.assertEqual(len(recorded_cmds), 3)

  def test_remote_cli_mcp_client_get_job_403_sql_fallback(self):
    def fake_runner(cmd):
      server = cmd[2]
      tool = cmd[3]
      args = json.loads(cmd[5])
      if server == "bigquery" and tool == "get_job":
        return (
            0,
            json.dumps({
                "tool": "get_job",
                "isError": True,
                "result": (
                    "Access Denied: Project target-proj: User does not have"
                    " mcp.tools.call permission in project target-proj."
                ),
            }),
            "",
        )
      if server == "bigquery" and tool == "execute_sql_readonly":
        self.assertEqual(args.get("project_id"), "billing-proj")
        if "JOBS_BY_PROJECT" in args.get("query", ""):
          return (
              0,
              json.dumps({
                  "tool": "execute_sql_readonly",
                  "isError": True,
                  "result": (
                      "Access Denied: Table"
                      " target-proj:region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT"
                  ),
              }),
              "",
          )
        return (
            0,
            json.dumps({
                "tool": "execute_sql_readonly",
                "isError": False,
                "result": {
                    "schema": {
                        "fields": [
                            {"name": "job_id", "type": "STRING"},
                            {"name": "project_id", "type": "STRING"},
                            {"name": "user_email", "type": "STRING"},
                            {"name": "job_type", "type": "STRING"},
                            {"name": "statement_type", "type": "STRING"},
                            {"name": "state", "type": "STRING"},
                            {"name": "priority", "type": "STRING"},
                            {"name": "reservation_id", "type": "STRING"},
                            {"name": "edition", "type": "STRING"},
                            {"name": "creation_ms", "type": "STRING"},
                            {"name": "start_ms", "type": "STRING"},
                            {"name": "end_ms", "type": "STRING"},
                            {"name": "total_bytes_billed", "type": "STRING"},
                            {"name": "total_bytes_processed", "type": "STRING"},
                            {"name": "total_slot_ms", "type": "STRING"},
                            {"name": "cache_hit", "type": "BOOLEAN"},
                            {"name": "query", "type": "STRING"},
                            {"name": "error_reason", "type": "STRING"},
                            {"name": "error_message", "type": "STRING"},
                            {
                                "name": "referenced_tables_json",
                                "type": "STRING",
                            },
                            {"name": "labels_json", "type": "STRING"},
                            {"name": "job_stages_json", "type": "STRING"},
                        ]
                    },
                    "rows": [{
                        "f": [
                            {"v": "job_fallback_1"},
                            {"v": "target-proj"},
                            {"v": "testuser@example.com"},
                            {"v": "QUERY"},
                            {"v": "SELECT"},
                            {"v": "DONE"},
                            {"v": "INTERACTIVE"},
                            {"v": ""},
                            {"v": ""},
                            {"v": "1791990000000"},
                            {"v": "1791990000100"},
                            {"v": "1791990002100"},
                            {"v": "2048"},
                            {"v": "2048"},
                            {"v": "500"},
                            {"v": "false"},
                            {"v": "SELECT 42"},
                            {"v": ""},
                            {"v": ""},
                            {"v": "[]"},
                            {"v": "[]"},
                            {
                                "v": json.dumps([{
                                    "id": 0,
                                    "name": "S00: Input",
                                    "status": "COMPLETE",
                                    "records_read": 10,
                                    "records_written": 1,
                                    "slot_ms": 500,
                                }])
                            },
                        ]
                    }],
                },
            }),
            "",
        )
      return (1, "", "unexpected tool")

    mcp_client = gcp_job_monitor.RemoteCliMcpClient(
        runner=fake_runner, billing_project="billing-proj"
    )
    job = gcp_job_monitor.fetch_bq_job_detail(
        mcp_client, "target-proj", "job_fallback_1"
    )
    self.assertEqual(job["jobId"], "job_fallback_1")
    self.assertEqual(job["projectId"], "target-proj")
    self.assertEqual(job["query"], "SELECT 42")
    self.assertEqual(len(job["stages"]), 1)
    self.assertEqual(job["stages"][0]["name"], "S00: Input")
    self.assertEqual(job["stages"][0]["slotMs"], 500)


if __name__ == "__main__":
  unittest.main()
