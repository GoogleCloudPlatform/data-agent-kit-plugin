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

"""Unit tests for spark_applications."""

import io
import json
import os
import shutil
import ssl
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
# pylint: disable=g-import-not-at-top
import spark_applications

_PARENT = "projects/p/locations/us-central1/batches/b1"


class _FakeTokens:
  """Token provider double: one token per credential source."""

  def __init__(self, sources=("user-token", "adc-token")):
    self.sources = list(sources)
    self.index = 0

  def token(self):
    return self.sources[self.index]

  def fallback(self):
    if self.index + 1 >= len(self.sources):
      return False
    self.index += 1
    return True


class _FakeTransport:
  """Replays canned (status, body) responses and records every request."""

  def __init__(self, responses):
    self.responses = list(responses)
    self.requests = []

  def __call__(self, request, timeout):
    del timeout
    self.requests.append(request)
    status, body = self.responses.pop(0)
    if not isinstance(body, bytes):
      body = json.dumps(body).encode()
    return status, body

  def query(self, i):
    return urllib.parse.parse_qs(
        urllib.parse.urlsplit(self.requests[i].full_url).query
    )

  def path(self, i):
    return urllib.parse.urlsplit(self.requests[i].full_url).path


def _client(responses, tokens=None, **kwargs):
  transport = _FakeTransport(responses)
  sleeps = []
  client = spark_applications.SparkApplicationsClient(
      project="p",
      region="us-central1",
      batch_id=kwargs.pop("batch_id", "b1"),
      session_id=kwargs.pop("session_id", None),
      token_provider=tokens or _FakeTokens(),
      transport=transport,
      sleep=sleeps.append,
  )
  return client, transport, sleeps


def _error(status, message, reason="", detail=None):
  details = []
  if reason:
    details.append(
        {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason}
    )
  if detail:
    details.append(
        {"@type": "type.googleapis.com/google.rpc.DebugInfo", "detail": detail}
    )
  return status, {
      "error": {"code": status, "message": message, "details": details}
  }


def _args(**overrides):
  defaults = dict(
      application_id=None,
      format="markdown",
      stage_id=None,
      stage_attempt_id=0,
      stage_status=None,
      task_status=None,
      job_status=None,
      executor_status=None,
      quantiles=False,
      sort="none",
      grep=None,
      limit=50,
      max_fetch=2000,
  )
  defaults.update(overrides)
  return mock.Mock(**defaults)


_APPS = {
    "sparkApplications": [{
        "name": "my-display-name",
        "application": {"applicationId": "app-1", "name": "my-display-name"},
    }]
}


class NormalizationTest(unittest.TestCase):

  def test_int64_strings_become_ints_only_for_int64_fields(self):
    payload = {
        "stageId": "7",
        "executorId": "12",  # A string field that merely looks numeric.
        "host": "10",
        "stageMetrics": {"jvmGcTimeMillis": "1500"},
        "parentStageIds": ["1", "2"],
        "locality": {"PROCESS_LOCAL": "3"},
        "taskQuantileMetrics": {
            "durationMillis": {"percentile50": "10", "maximum": "90"}
        },
    }

    out = spark_applications.normalize_int64(payload)

    self.assertEqual(out["stageId"], 7)
    self.assertEqual(out["executorId"], "12")
    self.assertEqual(out["host"], "10")
    self.assertEqual(out["stageMetrics"]["jvmGcTimeMillis"], 1500)
    self.assertEqual(out["parentStageIds"], [1, 2])
    self.assertEqual(out["locality"], {"PROCESS_LOCAL": 3})
    self.assertEqual(
        out["taskQuantileMetrics"]["durationMillis"],
        {"percentile50": 10, "maximum": 90},
    )

  def test_snake_case_names_are_also_normalized(self):
    out = spark_applications.normalize_int64(
        {"stage_id": "3", "job_ids": ["4"]}
    )
    self.assertEqual(out, {"stage_id": 3, "job_ids": [4]})

  def test_negative_sentinels_and_non_numeric_values_survive(self):
    out = spark_applications.normalize_int64(
        {"durationMillis": "-1", "stageId": "x"}
    )
    self.assertEqual(out, {"durationMillis": -1, "stageId": "x"})

  def test_field_reads_either_spelling_and_defaults_absent_to_zero(self):
    data = {"stageMetrics": {"jvm_gc_time_millis": 5}}
    self.assertEqual(
        spark_applications.field(data, "stage_metrics", "jvm_gc_time_millis"), 5
    )
    self.assertEqual(
        spark_applications.field(data, "stage_metrics", "missing"), 0
    )
    self.assertIsNone(spark_applications.field(data, "nope", default=None))
    self.assertEqual(spark_applications.field("not a dict", "x"), 0)


class FormattingTest(unittest.TestCase):

  def test_negative_metrics_render_as_unavailable(self):
    self.assertEqual(spark_applications.human_bytes(-1), "n/a")
    self.assertEqual(spark_applications.human_millis(-1), "n/a")
    self.assertEqual(spark_applications.human_millis(None), "n/a")

  def test_units(self):
    self.assertEqual(spark_applications.human_bytes(0), "0 B")
    self.assertEqual(spark_applications.human_bytes(1536), "1.5 KiB")
    self.assertEqual(spark_applications.human_bytes(3 * 1024**3), "3.0 GiB")
    self.assertEqual(spark_applications.human_millis(250), "250 ms")
    self.assertEqual(spark_applications.human_millis(2500), "2.5 s")
    self.assertEqual(spark_applications.human_millis(90_000), "1.5 min")

  def test_duration_ignores_epoch_placeholders(self):
    self.assertEqual(
        spark_applications.duration_millis(
            "2026-09-25T18:21:41.359Z", "2026-09-25T18:23:17.010Z"
        ),
        95651,
    )
    self.assertIsNone(
        spark_applications.duration_millis(
            "1970-01-01T00:00:00Z", "2026-09-25T18:23:17Z"
        )
    )
    self.assertIsNone(
        spark_applications.duration_millis(None, "2026-09-25T18:23:17Z")
    )

  def test_summarize_error_keeps_jvm_root_cause(self):
    trace = "\n".join([
        "Job aborted due to stage failure: Task 3 in stage 2.0 failed 4 times",
        (
            "\tat org.apache.spark.scheduler.DAGScheduler.fail(DAGScheduler.scala:1)"
        ),
        "\tat com.example.Divide.run(Divide.java:42)",
        "\tat java.base/java.lang.Thread.run(Thread.java:840)",
        "Caused by: java.lang.RuntimeException: wrapper",
        "Caused by: java.lang.ArithmeticException: / by zero",
    ])

    summary = spark_applications.summarize_error(trace)

    self.assertTrue(summary.startswith("Job aborted"))
    self.assertIn("com.example.Divide.run", summary)
    self.assertIn("ArithmeticException: / by zero", summary)
    self.assertNotIn("DAGScheduler", summary)
    self.assertNotIn("wrapper", summary)

  def test_summarize_error_keeps_python_user_frame_and_exception(self):
    trace = "\n".join([
        "Traceback (most recent call last):",
        '  File "/usr/lib/spark/python/pyspark/worker.py", line 1, in main',
        '  File "/tmp/job.py", line 9, in parse',
        "ValueError: invalid literal for int()",
    ])

    summary = spark_applications.summarize_error(trace)

    self.assertIn('File "/tmp/job.py"', summary)
    self.assertIn("ValueError: invalid literal", summary)
    self.assertNotIn("pyspark/worker.py", summary)

  def test_health_indicators(self):
    indicators = spark_applications.health_indicators({
        "totalExecutorSummary": {
            "totalGcTimeMillis": 50,
            "totalDurationMillis": 1000,
            "count": 4,
        },
        "deadExecutorSummary": {"count": 1},
        "activeExecutorSummary": {"memoryUsed": 1, "maxMemory": 4},
    })
    self.assertEqual(
        indicators,
        {
            "gcOverheadPercentage": 5.0,
            "executorMortalityRate": 25.0,
            "memorySaturationPercentage": 25.0,
        },
    )
    self.assertEqual(
        spark_applications.health_indicators({})["gcOverheadPercentage"], 0.0
    )

  def test_stage_row_flattens_and_treats_missing_stage_id_as_zero(self):
    row = spark_applications.stage_row({
        "status": "STAGE_STATUS_FAILED",
        "numTasks": 4,
        "submissionTime": "2026-09-25T00:00:00Z",
        "completionTime": "2026-09-25T00:00:02Z",
        "stageMetrics": {"stageInputMetrics": {"bytesRead": 10}},
        "failureReason": "boom\nCaused by: java.io.IOException: disk",
    })
    self.assertEqual(row["stageId"], 0)
    self.assertEqual(row["status"], "FAILED")
    self.assertEqual(row["durationMillis"], 2000)
    self.assertEqual(row["inputBytes"], 10)
    self.assertEqual(
        row["failureReason"], "boom | Caused by: java.io.IOException: disk"
    )


class SslContextTest(unittest.TestCase):
  """The TLS trust store must work without certifi or any other install."""

  def setUp(self):
    super().setUp()
    spark_applications.ssl_context.cache_clear()
    self.addCleanup(spark_applications.ssl_context.cache_clear)
    environ = mock.patch.dict(os.environ)
    environ.start()
    self.addCleanup(environ.stop)
    os.environ.pop("SSL_CERT_FILE", None)
    os.environ.pop("SSL_CERT_DIR", None)
    self.tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
    self.missing = os.path.join(self.tmp, "missing.pem")

  def _file(self, *parts):
    path = os.path.join(self.tmp, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
      f.write("-----BEGIN CERTIFICATE-----\n")
    return path

  def _default_context(self, ca_count):
    context = mock.create_autospec(ssl.SSLContext, instance=True)
    context.cert_store_stats.return_value = {"x509_ca": ca_count}
    return context

  def _ssl_context(self, default, bundles, gcloud=None):
    with mock.patch.object(
        spark_applications.ssl, "create_default_context", return_value=default
    ), mock.patch.object(
        spark_applications, "_SYSTEM_CA_BUNDLES", tuple(bundles)
    ), mock.patch.object(
        spark_applications.shutil, "which", return_value=gcloud
    ):
      return spark_applications.ssl_context()

  def test_populated_default_trust_store_is_used_as_is(self):
    default = self._default_context(147)
    context = self._ssl_context(default, [self._file("cert.pem")])
    self.assertIs(context, default)
    default.load_verify_locations.assert_not_called()

  def test_empty_trust_store_loads_the_system_bundle(self):
    # The python.org macOS installer's OpenSSL trusts no CA until its
    # "Install Certificates" step pip-installs certifi.
    default = self._default_context(0)
    bundle = self._file("cert.pem")
    context = self._ssl_context(default, [self.missing, bundle])
    self.assertIs(context, default)
    default.load_verify_locations.assert_called_once_with(cafile=bundle)

  def test_without_a_system_bundle_uses_the_gcloud_bundle(self):
    default = self._default_context(0)
    bundle = self._file("sdk", "lib", "third_party", "certifi", "cacert.pem")
    gcloud = os.path.join(self.tmp, "sdk", "bin", "gcloud")
    self._ssl_context(default, [self.missing], gcloud=gcloud)
    default.load_verify_locations.assert_called_once_with(
        cafile=os.path.realpath(bundle)
    )

  def test_unusable_bundle_is_skipped(self):
    default = self._default_context(0)
    default.load_verify_locations.side_effect = [ssl.SSLError("no CA"), None]
    first, second = self._file("a.pem"), self._file("b.pem")
    self._ssl_context(default, [first, second])
    self.assertEqual(
        default.load_verify_locations.call_args_list,
        [mock.call(cafile=first), mock.call(cafile=second)],
    )

  def test_explicit_ssl_cert_file_or_dir_is_respected(self):
    for name in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
      with self.subTest(name), mock.patch.dict(os.environ, {name: "/corp/ca"}):
        spark_applications.ssl_context.cache_clear()
        default = self._default_context(0)
        self._ssl_context(default, [self._file("cert.pem")])
        default.load_verify_locations.assert_not_called()

  def test_verification_stays_on_even_without_any_bundle(self):
    empty = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # Trusts no CA.
    context = self._ssl_context(empty, [self.missing])
    self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
    self.assertTrue(context.check_hostname)

  def test_transport_verifies_with_the_shared_context(self):
    context = self._default_context(1)
    response = mock.MagicMock()
    response.__enter__.return_value.status = 200
    response.__enter__.return_value.read.return_value = b"{}"
    request = urllib.request.Request("https://dataproc.googleapis.com/v1/x")
    with mock.patch.object(
        spark_applications, "ssl_context", return_value=context
    ), mock.patch.object(
        spark_applications.urllib.request, "urlopen", return_value=response
    ) as urlopen:
      result = spark_applications._urllib_transport(  # pylint: disable=protected-access
          request, 5
      )
    self.assertEqual(result, (200, b"{}"))
    urlopen.assert_called_once_with(request, timeout=5, context=context)


class ClientTest(unittest.TestCase):

  def test_requires_exactly_one_workload(self):
    with self.assertRaises(ValueError):
      spark_applications.SparkApplicationsClient("p", "r")
    with self.assertRaises(ValueError):
      spark_applications.SparkApplicationsClient(
          "p", "r", batch_id="b", session_id="s"
      )

  def test_session_parent(self):
    client, transport, _ = _client(
        [(200, _APPS)], batch_id=None, session_id="s1"
    )
    client.search_applications()
    self.assertEqual(
        transport.path(0),
        "/v1/projects/p/locations/us-central1/sessions/s1/sparkApplications:search",
    )

  def test_call_builds_url_headers_and_parent(self):
    client, transport, _ = _client([(200, {"stageData": {"stageId": "2"}})])

    response = client.call(
        "accessStageAttempt",
        "app-1",
        {"stageId": 2, "stageAttemptId": 0, "details": False, "skip": None},
    )

    self.assertEqual(response, {"stageData": {"stageId": 2}})
    self.assertEqual(
        transport.path(0),
        f"/v1/{_PARENT}/sparkApplications/app-1:accessStageAttempt",
    )
    self.assertEqual(
        transport.query(0),
        {
            "parent": [_PARENT],
            "stageId": ["2"],
            "stageAttemptId": ["0"],
            "details": ["false"],
        },
    )
    request = transport.requests[0]
    self.assertEqual(request.get_header("Authorization"), "Bearer user-token")
    self.assertIn("gcp-spark-troubleshooting", request.get_header("User-agent"))

  def test_non_search_methods_require_app_id(self):
    client, _, _ = _client([])
    with self.assertRaises(ValueError):
      client.call("searchStages")

  def test_paginate_follows_next_page_token(self):
    client, transport, _ = _client([
        (
            200,
            {
                "sparkApplicationStages": [{"stageId": "1"}],
                "nextPageToken": "t1",
            },
        ),
        (200, {"sparkApplicationStages": [{"stageId": "2"}]}),
    ])

    stages = client.paginate("searchStages", "sparkApplicationStages", "app-1")

    self.assertEqual([s["stageId"] for s in stages], [1, 2])
    self.assertEqual(transport.query(0)["pageSize"], ["100"])
    self.assertNotIn("pageToken", transport.query(0))
    self.assertEqual(transport.query(1)["pageToken"], ["t1"])

  def test_paginate_stops_at_max_items(self):
    client, transport, _ = _client([
        (
            200,
            {
                "sparkApplicationStages": [{"stageId": "1"}, {"stageId": "2"}],
                "nextPageToken": "t1",
            },
        ),
    ])
    stages = client.paginate(
        "searchStages", "sparkApplicationStages", "app-1", max_items=1
    )
    self.assertEqual(len(stages), 1)
    self.assertEqual(len(transport.requests), 1)

  def test_401_falls_back_to_next_credential_once(self):
    client, transport, _ = _client([
        _error(
            401,
            "Request had invalid authentication credentials.",
            reason="ACCESS_TOKEN_TYPE_UNSUPPORTED",
        ),
        (200, _APPS),
    ])

    apps = client.search_applications()

    self.assertEqual(len(apps), 1)
    self.assertEqual(
        transport.requests[1].get_header("Authorization"), "Bearer adc-token"
    )

  def test_401_with_no_fallback_left_explains_how_to_fix(self):
    client, _, _ = _client(
        [_error(401, "bad token", reason="ACCESS_TOKEN_TYPE_UNSUPPORTED")],
        tokens=_FakeTokens(sources=("only",)),
    )
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.search_applications()
    self.assertEqual(ctx.exception.status, 401)
    self.assertEqual(ctx.exception.reason, "ACCESS_TOKEN_TYPE_UNSUPPORTED")
    self.assertIn("application-default login", str(ctx.exception))

  def test_retries_transient_errors_with_backoff(self):
    client, transport, sleeps = _client([
        _error(503, "unavailable"),
        _error(429, "slow down"),
        (200, _APPS),
    ])
    client.search_applications()
    self.assertEqual(len(transport.requests), 3)
    self.assertEqual(sleeps, [1.0, 2.0])

  def test_gives_up_after_max_attempts(self):
    client, transport, _ = _client([_error(503, "unavailable")] * 3)
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.search_applications()
    self.assertEqual(ctx.exception.status, 503)
    self.assertEqual(len(transport.requests), 3)

  def test_network_errors_are_retried_then_reported(self):
    client, _, _ = _client([])
    calls = []

    def broken(request, timeout):
      del request, timeout
      calls.append(1)
      raise OSError("connection reset")

    client._transport = broken  # pylint: disable=protected-access
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.search_applications()
    self.assertEqual(len(calls), 3)
    self.assertIn("network error", str(ctx.exception))

  def test_certificate_errors_fail_fast_and_explain_the_fix(self):
    client, _, sleeps = _client([])
    calls = []

    def untrusted(request, timeout):
      del request, timeout
      calls.append(1)
      raise urllib.error.URLError(
          ssl.SSLCertVerificationError(
              1,
              "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:"
              " unable to get local issuer certificate",
          )
      )

    client._transport = untrusted  # pylint: disable=protected-access
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.search_applications()
    self.assertEqual((len(calls), sleeps), (1, []))
    message = str(ctx.exception)
    self.assertIn("search: TLS certificate verification failed", message)
    self.assertIn("unable to get local issuer certificate", message)
    self.assertIn("SSL_CERT_FILE", message)

  def test_non_retryable_error_surfaces_backend_cause_and_hint(self):
    # Shape copied from a live searchStageAttemptTasks?taskStatus= response.
    client, transport, _ = _client([
        _error(
            500,
            "Internal error encountered.",
            detail=(
                "[ORIGINAL ERROR] generic::internal:"
                " com.google.net.rpc3.client.RpcClientException: <eye3"
                " title='/SparkPhsService.ListSparkApplicationStageAttemptTasks,"
                " INVALID_ARGUMENT'/>"
                " APPLICATION_ERROR;cloud.hadoop.services.observability.phs.api.spark/SparkPhsService.ListSparkApplicationStageAttemptTasks;com.google.apps.framework.request.BadRequestException:"
                " Filtering by task status is not supported"
                " yet.;AppErrorCode=3;Deadline(sec)=10.0\n\tSuppressed:"
                " com.google.X$LabeledExecutionException: GraphFuture failed"
            ),
        )
    ])
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.call("searchStageAttemptTasks", "app-1", {"sortRuntime": True})
    message = str(ctx.exception)
    self.assertEqual(
        message,
        "searchStageAttemptTasks failed with HTTP 500: Internal error"
        " encountered. (Filtering by task status is not supported yet.).",
    )
    self.assertEqual(len(transport.requests), 1)
    self.assertEqual(transport.query(0)["sortRuntime"], ["true"])

  def test_backend_not_found_gets_a_hint(self):
    client, _, _ = _client([
        _error(
            500,
            "Internal error encountered.",
            detail=(
                "[ORIGINAL ERROR] generic::internal: x.RpcClientException:"
                " <eye3"
                " title='/SparkPhsService.GetSparkApplicationStageAttempt,"
                " NOT_FOUND'/>"
                " APPLICATION_ERROR;y;com.google.cloud.hadoop.services.common.error.DataprocException:"
                " StageData not found for id: 999 - 0 (NOT_FOUND)"
                " (CONFIG);AppErrorCode=5"
            ),
        )
    ])
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.call("accessStageAttempt", "app-1", {"stageId": 999})
    self.assertIn("(StageData not found for id: 999 - 0)", str(ctx.exception))
    self.assertIn("--action=stages", str(ctx.exception))

  def test_backend_cause_repeating_the_message_is_not_duplicated(self):
    message = "Page size must be in range (0, 100]"
    client, _, _ = _client([
        _error(
            400,
            message,
            detail=(
                "[ORIGINAL ERROR] generic::invalid_argument: com.google.x."
                f"DataprocException: {message} (INVALID_ARGUMENT) (CONFIG)"
                f' [google.rpc.error_details_ext] {{ message: "{message}" }}'
            ),
        )
    ])
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.search_applications()
    self.assertEqual(str(ctx.exception).count("Page size"), 1)

  def test_404_and_403_hints(self):
    for status, needle in (
        (404, "Spark UI data only exists"),
        (403, "roles/dataproc.viewer"),
    ):
      client, _, _ = _client([_error(status, "nope")])
      with self.assertRaises(spark_applications.DataprocApiError) as ctx:
        client.search_applications()
      self.assertIn(needle, str(ctx.exception))

  def test_invalid_json_body_is_an_api_error(self):
    client, _, _ = _client([(200, b"<html>")])
    with self.assertRaises(spark_applications.DataprocApiError):
      client.search_applications()

  def test_non_json_error_body_is_reported(self):
    client, _, _ = _client([(400, b"plain text failure")])
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.search_applications()
    self.assertIn("plain text failure", str(ctx.exception))

  def test_resolve_application_prefers_application_id(self):
    client, transport, _ = _client([(200, _APPS)])
    app_id, info, count = client.resolve_application()
    self.assertEqual(
        (app_id, info["name"], count), ("app-1", "my-display-name", 1)
    )
    self.assertEqual(transport.query(0)["pageSize"], ["10"])

  def test_resolve_application_falls_back_to_name_suffix(self):
    client, _, _ = _client([(
        200,
        {"sparkApplications": [{"name": f"{_PARENT}/sparkApplications/app-9"}]},
    )])
    self.assertEqual(client.resolve_application()[0], "app-9")

  def test_resolve_application_explicit_id_skips_lookup(self):
    client, transport, _ = _client([])
    self.assertEqual(client.resolve_application("app-x")[0], "app-x")
    self.assertEqual(transport.requests, [])

  def test_resolve_application_without_apps_is_a_clear_error(self):
    client, _, _ = _client([(200, {})])
    with self.assertRaises(spark_applications.DataprocApiError) as ctx:
      client.resolve_application()
    self.assertIn("No Spark application found", str(ctx.exception))


class TokenProviderTest(unittest.TestCase):

  def _proc(self, returncode, stdout="", stderr=""):
    return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

  def test_falls_back_to_application_default_credentials(self):
    with mock.patch.object(
        spark_applications.shutil, "which", return_value="/bin/gcloud"
    ), mock.patch.object(
        spark_applications.subprocess,
        "run",
        side_effect=[
            self._proc(1, stderr="Reauthentication required."),
            self._proc(0, stdout="adc\n"),
        ],
    ) as run:
      token = spark_applications.GcloudTokenProvider().token()

    self.assertEqual(token, "adc")
    self.assertEqual(
        run.call_args_list[1].args[0],
        ["/bin/gcloud", "auth", "application-default", "print-access-token"],
    )
    self.assertIs(
        run.call_args_list[0].kwargs["stdin"],
        spark_applications.subprocess.DEVNULL,
    )

  def test_reports_every_failure_when_no_source_works(self):
    with mock.patch.object(
        spark_applications.shutil, "which", return_value="/bin/gcloud"
    ), mock.patch.object(
        spark_applications.subprocess,
        "run",
        side_effect=[
            self._proc(1, stderr="first failure"),
            self._proc(1, stderr="second failure"),
        ],
    ):
      with self.assertRaises(spark_applications.DataprocApiError) as ctx:
        spark_applications.GcloudTokenProvider().token()
    self.assertIn("first failure", str(ctx.exception))
    self.assertIn("second failure", str(ctx.exception))

  def test_missing_gcloud(self):
    with mock.patch.object(
        spark_applications.shutil, "which", return_value=None
    ):
      with self.assertRaises(spark_applications.DataprocApiError) as ctx:
        spark_applications.GcloudTokenProvider().token()
    self.assertIn("not installed", str(ctx.exception))


class ActionsTest(unittest.TestCase):

  def _run(self, action, responses, **arg_overrides):
    client, transport, _ = _client(responses)
    with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
      spark_applications.ACTIONS[action](client, _args(**arg_overrides))
    return out.getvalue(), transport

  def test_tasks_filters_and_sorts_locally(self):
    tasks = {
        "sparkApplicationStageAttemptTasks": [
            {"taskId": "1", "status": "SUCCESS", "durationMillis": "10"},
            {
                "taskId": "2",
                "status": "FAILED",
                "durationMillis": "-1",
                "errorMessage": (
                    "java.lang.ArithmeticException: / by zero\n\tat a.B"
                ),
            },
            {
                "taskId": "3",
                "status": "FAILED",
                "durationMillis": "30",
                "errorMessage": (
                    "java.lang.ArithmeticException: / by zero\n\tat a.B"
                ),
            },
        ]
    }

    out, transport = self._run(
        "tasks",
        [(200, _APPS), (200, tasks)],
        stage_id=2,
        task_status="FAILED",
        sort="duration",
    )

    query = transport.query(1)
    self.assertNotIn("taskStatus", query)
    self.assertNotIn("sortRuntime", query)
    self.assertEqual(query["stageId"], ["2"])
    self.assertEqual(query["stageAttemptId"], ["0"])
    self.assertNotIn("| 1 |", out)
    self.assertLess(out.index("| 3 |"), out.index("| 2 |"))
    self.assertIn("n/a", out)
    # Identical errors collapse into one line listing both tasks.
    self.assertIn("Tasks 3, 2:", out)
    self.assertEqual(out.count("ArithmeticException"), 1)

  def test_tasks_requires_stage_id(self):
    with self.assertRaises(ValueError):
      self._run("tasks", [])

  def test_stages_passes_server_side_filters_and_prints_failure(self):
    stages = {
        "sparkApplicationStages": [{
            "stageId": "2",
            "status": "STAGE_STATUS_FAILED",
            "numTasks": 4,
            "numFailedTasks": 1,
            "name": "count at Job.java:10",
            "failureReason": "Job aborted\nCaused by: java.lang.X: y",
        }]
    }
    out, transport = self._run(
        "stages",
        [(200, _APPS), (200, stages)],
        stage_status="FAILED",
        quantiles=True,
    )
    query = transport.query(1)
    self.assertEqual(query["stageStatus"], ["STAGE_STATUS_FAILED"])
    self.assertEqual(query["summaryMetricsMask"], ["task_quantile_metrics"])
    self.assertIn("| 2.0 | FAILED | 4 (1/0) |", out)
    self.assertIn("Caused by: java.lang.X: y", out)

  def test_stage_renders_quantiles(self):
    stage = {
        "stageData": {
            "stageId": "5",
            "status": "STAGE_STATUS_COMPLETE",
            "taskQuantileMetrics": {
                "durationMillis": {
                    "count": "4",
                    "minimum": "1",
                    "percentile25": "2",
                    "percentile50": "3",
                    "percentile75": "4",
                    "maximum": "90000",
                }
            },
        }
    }
    out, transport = self._run(
        "stage", [(200, _APPS), (200, stage)], stage_id=5
    )
    self.assertEqual(
        transport.query(1)["summaryMetricsMask"], ["task_quantile_metrics"]
    )
    self.assertIn(
        "| Task duration | 1 ms | 2 ms | 3 ms | 4 ms | 1.5 min |", out
    )

  def test_summary_json_includes_failed_stages(self):
    responses = [
        (200, _APPS),
        (200, {"jobsSummary": {"failedJobs": 1}}),
        (200, {"stagesSummary": {"numFailedStages": 1}}),
        (200, {"totalExecutorSummary": {"count": "2"}}),
        (200, {"sparkApplicationStages": [{"stageId": "2"}]}),
    ]
    out, transport = self._run("summary", responses, format="json")
    payload = json.loads(out)
    self.assertEqual(payload["applicationId"], "app-1")
    self.assertEqual(payload["jobs"], {"failedJobs": 1})
    self.assertEqual(payload["failedStages"], [{"stageId": 2}])
    self.assertEqual(transport.query(4)["stageStatus"], ["STAGE_STATUS_FAILED"])

  def test_summary_skips_failed_stage_lookup_when_none_failed(self):
    responses = [
        (200, _APPS),
        (200, {"jobsSummary": {}}),
        (200, {"stagesSummary": {"numCompletedStages": 3}}),
        (200, {}),
    ]
    out, transport = self._run("summary", responses)
    self.assertEqual(len(transport.requests), 4)
    self.assertIn("Completed: 3, failed: 0", out)
    self.assertNotIn("No stage ever ran", out)

  def test_summary_points_to_driver_log_when_no_stage_ran(self):
    responses = [
        (200, _APPS),
        (200, {"jobsSummary": {}}),
        (200, {"stagesSummary": {}}),
        (200, {}),
    ]
    out, _ = self._run("summary", responses)
    self.assertIn("No stage ever ran", out)
    self.assertIn("driver log", out)

  def test_executors_and_jobs_map_status_enums(self):
    _, transport = self._run(
        "executors",
        [(200, _APPS), (200, {"sparkApplicationExecutors": []})],
        executor_status="DEAD",
    )
    self.assertEqual(
        transport.query(1)["executorStatus"], ["EXECUTOR_STATUS_DEAD"]
    )
    _, transport = self._run(
        "jobs",
        [(200, _APPS), (200, {"sparkApplicationJobs": []})],
        job_status="FAILED",
    )
    self.assertEqual(
        transport.query(1)["jobStatus"], ["JOB_EXECUTION_STATUS_FAILED"]
    )

  def test_environment_grep(self):
    env = {
        "applicationEnvironmentInfo": {
            "sparkProperties": {
                "spark.executor.memory": "4g",
                "spark.app.name": "x",
            }
        }
    }
    out, _ = self._run(
        "environment", [(200, _APPS), (200, env)], grep="MEMORY", format="json"
    )
    self.assertEqual(
        json.loads(out)["sparkProperties"], {"spark.executor.memory": "4g"}
    )


class MainTest(unittest.TestCase):

  def test_requires_a_workload(self):
    with mock.patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(
        SystemExit
    ):
      spark_applications.main(["--action", "summary"])

  def test_api_errors_exit_non_zero_with_message(self):
    def fail(client, args):
      del client, args
      raise spark_applications.DataprocApiError("boom", 404)

    with mock.patch.dict(
        spark_applications.ACTIONS, {"summary": fail}
    ), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
      code = spark_applications.main(["--batch_id", "b", "--project", "p"])
    self.assertEqual(code, 1)
    self.assertIn("Error: boom", err.getvalue())


if __name__ == "__main__":
  unittest.main()
