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

"""Unit tests for spark_applications helper script."""

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
      execution_id=None,
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

  def test_sql_plan_finds_joins_converted_by_aqe(self):
    plan = (
        "== Physical Plan ==\n"
        "AdaptiveSparkPlan (12)\n"
        "+- == Final Plan ==\n"
        "   BroadcastHashJoin Inner BuildRight (8)\n"
        "   :- Scan parquet (1)\n"
        "   +- BroadcastQueryStage (7)\n"
        "      +- BroadcastExchange (6)\n"
        "+- == Initial Plan ==\n"
        "   SortMergeJoin Inner (11)\n"
        "   :- Exchange (9)\n"
        "   +- Exchange (10)\n"
        "\n"
        "(1) Scan parquet\n"
        "Output: [id#1]\n"
    )
    query = {
        "executionData": {
            "executionId": "3",
            "physicalPlanDescription": plan,
            "metricValues": {"41": "total (min, med, max)\n12.0 MiB"},
        }
    }
    graph = {
        "sparkPlanGraph": {
            "nodes": [
                {
                    "cluster": {
                        "nodes": [{
                            "node": {
                                "sparkPlanGraphNodeId": "8",
                                "name": "BroadcastHashJoin",
                            }
                        }]
                    }
                },
                {
                    "node": {
                        "sparkPlanGraphNodeId": "6",
                        "name": "BroadcastExchange",
                        "metrics": [
                            {"name": "data size", "accumulatorId": "41"}
                        ],
                    }
                },
                {"node": {"sparkPlanGraphNodeId": "1", "name": "Scan parquet"}},
            ]
        }
    }
    out, transport = self._run(
        "sql",
        [(200, _APPS), (200, query), (200, graph)],
        execution_id=3,
        format="json",
    )
    result = json.loads(out)
    self.assertEqual(result["initial_joins"], {"SortMergeJoin": 1})
    self.assertEqual(result["final_joins"], {"BroadcastHashJoin": 1})
    self.assertEqual(result["sort_merge_joins_converted_by_aqe"], 1)
    self.assertEqual(
        [(n["node_id"], n["name"]) for n in result["nodes"]],
        [(6, "BroadcastExchange"), (8, "BroadcastHashJoin")],
    )
    self.assertEqual(
        result["nodes"][0]["metrics"],
        {"data size": "total (min, med, max) 12.0 MiB"},
    )
    self.assertTrue(transport.path(1).endswith("app-1:accessSqlQuery"))
    self.assertEqual(transport.query(1)["planDescription"], ["true"])
    self.assertEqual(transport.query(2)["executionId"], ["3"])

  def test_count_joins_without_aqe_reports_one_tree_for_both(self):
    initial, final = spark_applications.count_joins(
        "== Physical Plan ==\n*(5) SortMergeJoin Inner\n:- Exchange\n"
    )
    self.assertEqual(initial, {"SortMergeJoin": 1})
    self.assertEqual(final, initial)

  def test_stages_surfaces_record_counts_and_stage_io_totals(self):
    stages = {
        "sparkApplicationStages": [
            {
                "stageId": "0",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 2,
                "stageMetrics": {
                    "stageInputMetrics": {
                        "bytesRead": "0",
                        "recordsRead": "12000",
                    },
                    "stageShuffleWriteMetrics": {
                        "bytesWritten": "2048",
                        "recordsWritten": "12000",
                    },
                },
                "name": "scan bigquery",
            },
            {
                "stageId": "1",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 4,
                "stageMetrics": {
                    "stageShuffleReadMetrics": {
                        "bytesRead": "2048",
                        "recordsRead": "12000",
                    },
                    "stageOutputMetrics": {
                        "bytesWritten": "4096",
                        "recordsWritten": "12000",
                    },
                },
                "name": "parquet at Job.py:42",
            },
        ]
    }
    out, _ = self._run("stages", [(200, _APPS), (200, stages)])
    self.assertIn(
        "Stage I/O totals (2 completed)**: input 0 B (12,000 rows), output"
        " 4.0 KiB (12,000 rows), shuffle read 2.0 KiB (12,000 rows), shuffle"
        " write 2.0 KiB (12,000 rows)",
        out,
    )
    self.assertIn("| 0.0 | COMPLETE | 2 (0/0) |", out)
    self.assertIn("| 0 B (12,000 rows) | 0 B |", out)
    self.assertIn("| 0 B | 4.0 KiB (12,000 rows) |", out)

  def test_stages_excludes_failed_retry_attempts_from_completed_totals(self):
    retried = {
        "sparkApplicationStages": [
            {
                "stageId": "1",
                "stageAttemptId": "0",
                "status": "STAGE_STATUS_FAILED",
                "numTasks": 4,
                "numFailedTasks": 1,
                "stageMetrics": {
                    "stageInputMetrics": {
                        "bytesRead": "512",
                        "recordsRead": "500",
                    }
                },
                "name": "scan attempt 0",
            },
            {
                "stageId": "1",
                "stageAttemptId": "1",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 4,
                "stageMetrics": {
                    "stageInputMetrics": {
                        "bytesRead": "1024",
                        "recordsRead": "1000",
                    }
                },
                "name": "scan attempt 1",
            },
        ]
    }
    out, _ = self._run("stages", [(200, _APPS), (200, retried)])
    self.assertIn(
        "Stage I/O totals (1 completed)**: input 1.0 KiB (1,000 rows)", out
    )
    self.assertIn(
        "Failed/active attempt I/O (1 non-completed, excluded above to avoid"
        " retry double-counting)**: input 512 B (500 rows)",
        out,
    )

    all_failed = {
        "sparkApplicationStages": [{
            "stageId": "0",
            "stageAttemptId": "0",
            "status": "STAGE_STATUS_FAILED",
            "numTasks": 2,
            "numFailedTasks": 1,
            "stageMetrics": {
                "stageInputMetrics": {
                    "bytesRead": "2048",
                    "recordsRead": "2000",
                }
            },
            "name": "failed scan",
        }]
    }
    failed_out, _ = self._run("stages", [(200, _APPS), (200, all_failed)])
    self.assertIn(
        "Partial stage I/O before failure (0 completed, 1 failed/active)**:"
        " input 2.0 KiB (2,000 rows)",
        failed_out,
    )

  def test_stage_renders_record_quantiles_and_io_summary(self):
    stage = {
        "stageData": {
            "stageId": "1",
            "status": "STAGE_STATUS_COMPLETE",
            "numTasks": 4,
            "stageMetrics": {
                "stageInputMetrics": {"bytesRead": "1024", "recordsRead": "500"}
            },
            "taskQuantileMetrics": {
                "inputMetrics": {
                    "recordsRead": {
                        "count": "4",
                        "minimum": "50",
                        "percentile25": "100",
                        "percentile50": "125",
                        "percentile75": "150",
                        "maximum": "1250",
                    }
                }
            },
        }
    }
    out, _ = self._run("stage", [(200, _APPS), (200, stage)], stage_id=1)
    self.assertIn("- Input: 1.0 KiB (500 rows), output: 0 B", out)
    self.assertIn("| Input records | 50 | 100 | 125 | 150 | 1,250 |", out)

  def test_sql_plan_surfaces_scan_filter_write_metrics_and_schemas(self):
    plan = (
        "== Physical Plan ==\n"
        "Execute InsertIntoHadoopFsRelationCommand (3)\n"
        "+- Filter (2)\n"
        "   +- Scan csv (1)\n"
        "\n"
        "(1) Scan csv\n"
        "Output [3]: [order_id#10, amount#11, meta#12]\n"
        "ReadSchema:"
        " struct<order_id:string,amount:double,meta:struct<a:int,b:string>>\n"
        "Location: InMemoryFileIndex [gs://b/raw/orders]\n"
        "\n"
        "(3) Execute InsertIntoHadoopFsRelationCommand\n"
        "Input [4]: [order_id#10, amount#11, meta#12, ingest_dt#15]\n"
        "Arguments: gs://b/gold/orders, false, Parquet\n"
    )
    query = {
        "executionData": {
            "executionId": "1",
            "physicalPlanDescription": plan,
            "metricValues": {
                "10": "12,500",
                "11": "812.0 KiB",
                "12": "2",
                "20": "12,000",
                "30": "12,000",
                "31": "410.5 KiB",
                "32": "4",
                "99": "0 B",
            },
        }
    }
    graph = {
        "sparkPlanGraph": {
            "nodes": [
                {
                    "node": {
                        "sparkPlanGraphNodeId": "3",
                        "name": "Execute InsertIntoHadoopFsRelationCommand",
                        "metrics": [
                            {
                                "name": "number of written rows",
                                "accumulatorId": "30",
                            },
                            {"name": "written output", "accumulatorId": "31"},
                            {
                                "name": "number of written files",
                                "accumulatorId": "32",
                            },
                        ],
                    }
                },
                {
                    "node": {
                        "sparkPlanGraphNodeId": "2",
                        "name": "Filter",
                        "metrics": [
                            {
                                "name": "number of output rows",
                                "accumulatorId": "20",
                            },
                            {"name": "spill size", "accumulatorId": "99"},
                        ],
                    }
                },
                {
                    "node": {
                        "sparkPlanGraphNodeId": "1",
                        "name": "Scan csv",
                        "metrics": [
                            {
                                "name": "number of output rows",
                                "accumulatorId": "10",
                            },
                            {
                                "name": "size of files read",
                                "accumulatorId": "11",
                            },
                            {
                                "name": "number of files read",
                                "accumulatorId": "12",
                            },
                        ],
                    }
                },
            ]
        }
    }
    out, _ = self._run(
        "sql",
        [(200, _APPS), (200, query), (200, graph)],
        execution_id=1,
        format="json",
    )
    result = json.loads(out)
    by_name = {n["name"]: n["metrics"] for n in result["nodes"]}
    self.assertEqual(
        by_name["Scan csv"],
        {
            "number of output rows": "12,500",
            "size of files read": "812.0 KiB",
            "number of files read": "2",
        },
    )
    self.assertEqual(by_name["Filter"], {"number of output rows": "12,000"})
    self.assertEqual(
        by_name["Execute InsertIntoHadoopFsRelationCommand"],
        {
            "number of written rows": "12,000",
            "written output": "410.5 KiB",
            "number of written files": "4",
        },
    )
    self.assertEqual(len(result["io_operators"]), 2)
    self.assertEqual(result["io_operators"][0]["num_columns"], 3)
    self.assertEqual(
        result["io_operators"][0]["columns"], ["order_id", "amount", "meta"]
    )
    self.assertEqual(result["io_operators"][1]["num_columns"], 4)

  def test_sql_plan_surfaces_unattached_datasource_command_metrics_and_tree_schemas(
      self,
  ):
    plan = (
        "== Physical Plan ==\n"
        "Execute SaveIntoDataSourceCommand\n"
        "   +- SaveIntoDataSourceCommand"
        " com.google.cloud.spark.bigquery.v2.Spark35BigQueryTableProvider@1a,"
        " Map(table -> p.ds.orders_silver, writemethod -> direct), Overwrite\n"
        "         +- RepartitionByExpression [region#2], 4\n"
        "            +- Project [order_id#0, region#2,"
        " round((gross_amount#5 * 0.95), 2) AS net_amount#15]\n"
        "               +- Relation [order_id#0,region#2,gross_amount#5] csv\n"
    )
    query = {
        "executionData": {
            "executionId": "0",
            "physicalPlanDescription": plan,
            "metrics": [
                {"name": "size of files read", "accumulatorId": 33},
                {"name": "number of files read", "accumulatorId": 30},
                {"name": "number of output rows", "accumulatorId": 28},
                {"name": "number of output rows", "accumulatorId": 29},
                {"name": "shuffle bytes written", "accumulatorId": 21},
                {"name": "number of partitions", "accumulatorId": 2},
                {"name": "shuffle memory bytes spilled", "accumulatorId": 25},
            ],
            "metricValues": {
                "33": "909.9 KiB",
                "30": "4",
                "28": "12,500",
                "29": "12,000",
                "21": "356.2 KiB",
                "2": "4",
                "25": "0.0 B",
            },
        }
    }
    graph = {
        "sparkPlanGraph": {
            "nodes": [{"node": {"name": "Execute SaveIntoDataSourceCommand"}}]
        }
    }
    out, _ = self._run(
        "sql",
        [(200, _APPS), (200, query), (200, graph)],
        execution_id=0,
        format="json",
    )
    result = json.loads(out)
    self.assertEqual(len(result["nodes"]), 1)
    self.assertEqual(
        result["nodes"][0]["name"], "Execute SaveIntoDataSourceCommand"
    )
    self.assertEqual(
        result["nodes"][0]["metrics"],
        {
            "number of output rows": "12,500 / 12,000",
            "size of files read": "909.9 KiB",
            "number of files read": "4",
            "shuffle bytes written": "356.2 KiB",
            "number of partitions": "4",
        },
    )
    self.assertEqual(len(result["io_operators"]), 2)
    self.assertEqual(
        result["io_operators"][0]["operator"], "SaveIntoDataSourceCommand"
    )
    self.assertEqual(
        result["io_operators"][0]["columns"],
        ["order_id", "region", "net_amount"],
    )
    self.assertIn("p.ds.orders_silver", result["io_operators"][0]["details"])
    self.assertEqual(result["io_operators"][1]["operator"], "Relation csv")
    self.assertEqual(
        result["io_operators"][1]["columns"],
        ["order_id", "region", "gross_amount"],
    )

  def test_extract_plan_schemas_parses_extended_tree_scans_and_hadoop_insert(
      self,
  ):
    plan = (
        "== Physical Plan ==\n"
        "Execute InsertIntoHadoopFsRelationCommand gs://b/gold, false,"
        " [region#78], Parquet, [path=gs://b/gold/], Overwrite,"
        " [order_id, tier, usd_rate, region]\n"
        "+- WriteFiles\n"
        "   +- *(3) SortMergeJoin [region#2], [region#26], Inner\n"
        "      :- BatchScan orders_silver[order_id#0, region#2] Reading table"
        " [p.ds.orders_silver], Read session Id : s1\n"
        "      +- FileScan csv [region#26,usd_rate#28] Format: CSV, Location:"
        " InMemoryFileIndex(1 paths)[gs://b/fx/rates.csv], PartitionFilters:"
        " [], ReadSchema: struct<region:string,usd_rate:double>\n"
    )
    ops = spark_applications.extract_plan_schemas(plan)
    self.assertEqual(
        [(o["operator"], o["num_columns"], o["columns"]) for o in ops],
        [
            (
                "Execute InsertIntoHadoopFsRelationCommand",
                4,
                ["order_id", "tier", "usd_rate", "region"],
            ),
            ("BatchScan orders_silver", 2, ["order_id", "region"]),
            ("FileScan csv", 2, ["region", "usd_rate"]),
        ],
    )
    self.assertEqual(ops[1]["details"], "Reading table [p.ds.orders_silver]")
    self.assertIn("gs://b/fx/rates.csv", ops[2]["details"])

  def test_extract_plan_schemas_handles_truncated_fields_v2_writes_and_parens(
      self,
  ):
    wide_numbered = (
        "== Physical Plan ==\n"
        "Scan csv (1)\n\n"
        "(1) Scan csv\n"
        "Output [40]: [c1#1, c2#2, ... 38 more fields]\n"
    )
    wide_ops = spark_applications.extract_plan_schemas(wide_numbered)
    self.assertEqual(len(wide_ops), 1)
    self.assertEqual(wide_ops[0]["num_columns"], 40)
    self.assertEqual(wide_ops[0]["columns"], ["c1", "c2"])
    self.assertTrue(wide_ops[0]["columns_truncated"])

    v2_tree = (
        "== Physical Plan ==\n"
        "AppendData RelationV2[order_id#1L, region#2, ... 5 more fields]"
        " spark_catalog.lakehouse.fact_orders\n"
        "+- Filter\n"
        "(isnotnull(order_id#1L) AND (order_id#1L > 0))\n"
        "   +- BatchScan raw_orders[order_id#1L, region#2, ... 5 more fields]"
        " Reading table [p.ds.raw_orders], Read session Id : s9\n"
    )
    v2_ops = spark_applications.extract_plan_schemas(v2_tree)
    self.assertEqual(len(v2_ops), 2)
    self.assertEqual(
        v2_ops[0]["operator"], "AppendData spark_catalog.lakehouse.fact_orders"
    )
    self.assertEqual(v2_ops[0]["num_columns"], 7)
    self.assertEqual(v2_ops[0]["columns"], ["order_id", "region"])
    self.assertTrue(v2_ops[0]["columns_truncated"])
    self.assertEqual(v2_ops[1]["operator"], "BatchScan raw_orders")
    self.assertEqual(v2_ops[1]["num_columns"], 7)

  def test_stages_deduplicates_completed_stage_resubmission(self):
    resubmitted = {
        "sparkApplicationStages": [
            {
                "stageId": "0",
                "stageAttemptId": "0",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 4,
                "stageMetrics": {
                    "stageInputMetrics": {
                        "bytesRead": "1024",
                        "recordsRead": "1000",
                    }
                },
                "name": "map stage attempt 0",
            },
            {
                "stageId": "0",
                "stageAttemptId": "1",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 4,
                "stageMetrics": {
                    "stageInputMetrics": {
                        "bytesRead": "1024",
                        "recordsRead": "1000",
                    }
                },
                "name": "map stage attempt 1 after FetchFailed",
            },
        ]
    }
    out, _ = self._run("stages", [(200, _APPS), (200, resubmitted)])
    self.assertIn(
        "Stage I/O totals (1 completed)**: input 1.0 KiB (1,000 rows)", out
    )
    self.assertIn(
        "Superseded completed attempt I/O (1 earlier attempt(s), excluded"
        " above to avoid resubmission double-counting)**: input 1.0 KiB"
        " (1,000 rows)",
        out,
    )

  def test_extract_plan_schemas_skips_superseded_aqe_initial_plan_blocks(self):
    aqe_plan = (
        "== Physical Plan ==\n"
        "AdaptiveSparkPlan (7)\n"
        "+- == Final Plan ==\n"
        "   Execute InsertIntoHadoopFsRelationCommand (4)\n"
        "   +- Scan parquet default.orders (1)\n"
        "+- == Initial Plan ==\n"
        "   Execute InsertIntoHadoopFsRelationCommand (6)\n"
        "   +- Scan parquet default.orders (5)\n"
        "\n"
        "(1) Scan parquet default.orders\n"
        "Output [2]: [order_id#1L, region#2]\n"
        "ReadSchema: struct<order_id:bigint,region:string>\n"
        "\n"
        "(4) Execute InsertIntoHadoopFsRelationCommand\n"
        "Input [2]: [order_id#1L, region#2]\n"
        "Arguments: gs://b/out, false, Parquet, [path=gs://b/out],"
        " Overwrite, [order_id, region]\n"
        "\n"
        "(5) Scan parquet default.orders\n"
        "Output [2]: [order_id#1L, region#2]\n"
        "ReadSchema: struct<order_id:bigint,region:string>\n"
        "\n"
        "(6) Execute InsertIntoHadoopFsRelationCommand\n"
        "Input [2]: [order_id#1L, region#2]\n"
        "Arguments: gs://b/out, false, Parquet, [path=gs://b/out],"
        " Overwrite, [order_id, region]\n"
    )
    ops = spark_applications.extract_plan_schemas(aqe_plan)
    self.assertEqual(
        [(o["node_id"], o["operator"]) for o in ops],
        [
            (1, "Scan parquet default.orders"),
            (4, "Execute InsertIntoHadoopFsRelationCommand"),
        ],
    )

  def test_sql_plan_ignores_cluster_accumulators_and_keeps_wide_metrics(self):
    long_stat = (
        "total (min, med, max (stageId: taskId)) 1.2 MiB (300.0 KiB, 300.0"
        " KiB, 300.0 KiB (stage 0.0: task 3))"
    )
    query = {
        "executionData": {
            "executionId": "0",
            "physicalPlanDescription": "== Physical Plan ==\nScan csv (1)\n",
            "metrics": [
                {"name": "duration", "accumulatorId": "99"},
                {"name": "number of output rows", "accumulatorId": "10"},
                {"name": "size of files read", "accumulatorId": "11"},
                {"name": "metadata time", "accumulatorId": "12"},
                {"name": "scan time", "accumulatorId": "13"},
                {"name": "number of files read", "accumulatorId": "14"},
                {"name": "number of partitions", "accumulatorId": "15"},
            ],
            "metricValues": {
                "99": "total (min, med, max) 450 ms",
                "10": "42,000",
                "11": long_stat,
                "12": long_stat,
                "13": long_stat,
                "14": long_stat,
                "15": "4",
            },
        }
    }
    graph = {
        "sparkPlanGraph": {
            "nodes": [{
                "cluster": {
                    "sparkPlanGraphNodeId": "2",
                    "name": "WholeStageCodegen (1)",
                    "metrics": [{"name": "duration", "accumulatorId": "99"}],
                    "nodes": [{
                        "node": {
                            "sparkPlanGraphNodeId": "1",
                            "name": "Scan csv",
                            "metrics": [
                                {
                                    "name": "number of output rows",
                                    "accumulatorId": "10",
                                },
                                {
                                    "name": "size of files read",
                                    "accumulatorId": "11",
                                },
                                {
                                    "name": "metadata time",
                                    "accumulatorId": "12",
                                },
                                {"name": "scan time", "accumulatorId": "13"},
                                {
                                    "name": "number of files read",
                                    "accumulatorId": "14",
                                },
                                {
                                    "name": "number of partitions",
                                    "accumulatorId": "15",
                                },
                            ],
                        }
                    }],
                }
            }]
        }
    }
    out, _ = self._run(
        "sql", [(200, _APPS), (200, query), (200, graph)], execution_id=0
    )
    self.assertNotIn("Execution-level metrics", out)
    self.assertIn("number of partitions: 4", out)

  def test_extract_plan_schemas_keeps_active_subquery_scans_and_v2_delta_writes(
      self,
  ):
    dpp_plan = (
        "== Physical Plan ==\n"
        "AdaptiveSparkPlan (12)\n"
        "+- == Final Plan ==\n"
        "   WriteDelta (4)\n"
        "   +- Scan parquet db.fact (1)\n"
        "+- == Initial Plan ==\n"
        "   WriteDelta (11)\n"
        "   +- Scan parquet db.superseded_fact (5)\n"
        "\n"
        "(1) Scan parquet db.fact\n"
        "Output [2]: [id#1L, dt#2]\n"
        "ReadSchema: struct<id:bigint,dt:string>\n"
        "\n"
        "(4) WriteDelta\n"
        "Input [2]: [id#1L, dt#2]\n"
        "Arguments: RelationV2[id#1L, dt#2] ice.db.target\n"
        "\n"
        "(5) Scan parquet db.superseded_fact\n"
        "Output [2]: [id#1L, dt#2]\n"
        "\n"
        "===== Subqueries =====\n"
        "\n"
        "Subquery:1 Hosting operator id = 1 Hosting Expression = dt#2 IN"
        " dynamicpruning#99\n"
        "AdaptiveSparkPlan (9)\n"
        "+- == Final Plan ==\n"
        "   BroadcastExchange (8)\n"
        "   +- Scan parquet db.active_dim (6)\n"
        "+- == Initial Plan ==\n"
        "   BroadcastExchange (8)\n"
        "   +- Scan parquet db.superseded_dim (7)\n"
        "\n"
        "Subquery:2 Hosting operator id = 1 Hosting Expression = region#3\n"
        "BroadcastExchange (13)\n"
        "+- Scan parquet db.countries (10)\n"
        "\n"
        "(6) Scan parquet db.active_dim\n"
        "Output [1]: [dt#20]\n"
        "ReadSchema: struct<dt:string>\n"
        "\n"
        "(7) Scan parquet db.superseded_dim\n"
        "Output [1]: [dt#21]\n"
        "\n"
        "(10) Scan parquet db.countries\n"
        "Output [1]: [code#30]\n"
        "ReadSchema: struct<code:string>\n"
    )
    ops = spark_applications.extract_plan_schemas(dpp_plan)
    self.assertEqual(
        [(o["node_id"], o["operator"], o["columns"]) for o in ops],
        [
            (1, "Scan parquet db.fact", ["id", "dt"]),
            (4, "WriteDelta", ["id", "dt"]),
            (6, "Scan parquet db.active_dim", ["dt"]),
            (10, "Scan parquet db.countries", ["code"]),
        ],
    )

    tree_delta = (
        "== Physical Plan ==\n"
        "DeleteFromTable RelationV2[id#1L, ts#2] ice.db.audit\n"
    )
    tree_ops = spark_applications.extract_plan_schemas(tree_delta)
    self.assertEqual(
        [(o["operator"], o["columns"]) for o in tree_ops],
        [("DeleteFromTable ice.db.audit", ["id", "ts"])],
    )

  def test_sql_plan_preserves_distinct_unattached_accumulators_with_equal_vals(
      self,
  ):
    query = {
        "executionData": {
            "executionId": "2",
            "physicalPlanDescription": (
                "== Physical Plan ==\nExecute SaveIntoDataSourceCommand (1)\n"
            ),
            "metrics": [
                {"name": "number of files read", "accumulatorId": "30"},
                {"name": "number of files read", "accumulatorId": "30"},
                {"name": "number of files read", "accumulatorId": "31"},
                {"name": "number of output rows", "accumulatorId": "32"},
                {"name": "number of output rows", "accumulatorId": "33"},
            ],
            "metricValues": {
                "30": "4",
                "31": "4",
                "32": "1,000",
                "33": "1,000",
            },
        }
    }
    graph = {
        "sparkPlanGraph": {
            "nodes": [{
                "node": {
                    "sparkPlanGraphNodeId": "0",
                    "name": "Execute SaveIntoDataSourceCommand",
                    "metrics": [],
                }
            }]
        }
    }
    out, _ = self._run(
        "sql",
        [(200, _APPS), (200, query), (200, graph)],
        execution_id=2,
        format="json",
    )
    payload = json.loads(out)
    self.assertEqual(
        payload["nodes"][0]["metrics"],
        {
            "number of output rows": "1,000 / 1,000",
            "number of files read": "4 / 4",
        },
    )

  def test_sql_plan_filters_compound_zero_metrics_and_guards_join_tree_schema(
      self,
  ):
    join_tree_without_root_project = (
        "== Physical Plan ==\n"
        "Execute SaveIntoDataSourceCommand\n"
        "   +- SaveIntoDataSourceCommand"
        " com.google.cloud.spark.bigquery.v2.Spark35BigQueryTableProvider@1a,"
        " Map(table -> p.ds.joined_sink, writemethod -> direct), Overwrite\n"
        "      +- *(3) SortMergeJoin [cid#1], [dim_cid#10], Inner\n"
        "         :- *(1) Project [oid#0, cid#1]\n"
        "         :  +- FileScan csv [oid#0,cid#1] Format: CSV, Location:"
        " InMemoryFileIndex(1 paths)[gs://b/orders.csv], PartitionFilters:"
        " [], ReadSchema: struct<oid:string,cid:string>\n"
        "         +- *(2) Project [dim_cid#10, tier#11]\n"
        "            +- BatchScan dim[dim_cid#10, tier#11] Reading table"
        " [p.ds.dim], Read session Id : s2\n"
    )
    query = {
        "executionData": {
            "executionId": "3",
            "physicalPlanDescription": join_tree_without_root_project,
            "metricValues": {
                "10": "12,000",
                "11": (
                    "total (min, med, max (stageId: taskId)) 0.0 B (0.0 B,"
                    " 0.0 B, 0.0 B (stage 4.0: task 16))"
                ),
                "12": (
                    "total (min, med, max (stageId: taskId)) 0 ms (0 ms, 0 ms,"
                    " 0 ms (stage 4.0: task 12))"
                ),
                "13": "97.0 B",
            },
        }
    }
    graph = {
        "sparkPlanGraph": {
            "nodes": [
                {
                    "node": {
                        "sparkPlanGraphNodeId": "5",
                        "name": "SortMergeJoin",
                        "metrics": [
                            {
                                "name": "number of output rows",
                                "accumulatorId": "10",
                            },
                            {"name": "spill size", "accumulatorId": "11"},
                        ],
                    }
                },
                {
                    "node": {
                        "sparkPlanGraphNodeId": "31",
                        "name": "Scan csv ",
                        "metrics": [
                            {
                                "name": "size of files read",
                                "accumulatorId": "13",
                            },
                            {"name": "fetch wait time", "accumulatorId": "12"},
                        ],
                    }
                },
            ]
        }
    }
    out, _ = self._run(
        "sql",
        [(200, _APPS), (200, query), (200, graph)],
        execution_id=3,
        format="json",
    )
    payload = json.loads(out)
    by_name = {n["name"]: n["metrics"] for n in payload["nodes"]}
    self.assertEqual(
        by_name["SortMergeJoin"], {"number of output rows": "12,000"}
    )
    self.assertEqual(by_name["Scan csv"], {"size of files read": "97.0 B"})
    # Sink above an unprojected Join must NOT inherit only the left branch's 2
    # columns ([oid, cid]).
    self.assertEqual(
        payload["io_operators"][0]["operator"], "SaveIntoDataSourceCommand"
    )
    self.assertEqual(payload["io_operators"][0]["num_columns"], 0)
    self.assertEqual(payload["io_operators"][0]["columns"], [])

  def test_numbered_plan_v2_inline_relation_and_pre_join_project_fallback(self):
    numbered_delete = (
        "== Physical Plan ==\n"
        "DeleteFromTable (1)\n\n"
        "(1) DeleteFromTable\n"
        "Arguments: RelationV2[id#1L, ts#2] ice.db.audit, [EqualTo(id, 42)]\n"
    )
    del_ops = spark_applications.extract_plan_schemas(numbered_delete)
    self.assertEqual(
        [(o["node_id"], o["operator"], o["columns"]) for o in del_ops],
        [(1, "DeleteFromTable", ["id", "ts"])],
    )

    numbered_aqe_sink_with_root_project = (
        "== Physical Plan ==\n"
        "AdaptiveSparkPlan (6)\n"
        "+- == Final Plan ==\n"
        "   Execute SaveIntoDataSourceCommand (5)\n"
        "   +- WriteFiles (4)\n"
        "      +- * Project (3)\n"
        "         +- * BroadcastHashJoin Inner BuildRight (2)\n"
        "            :- * Scan parquet db.orders (1)\n"
        "            +- BroadcastExchange (7)\n"
        "               +- * Scan parquet db.dim (8)\n"
        "+- == Initial Plan ==\n"
        "   Execute SaveIntoDataSourceCommand (5)\n"
        "   +- * SortMergeJoin Inner (9)\n\n"
        "(1) Scan parquet db.orders\n"
        "Output [2]: [oid#1L, cid#2L]\n"
        "ReadSchema: struct<oid:bigint,cid:bigint>\n\n"
        "(3) Project [codegen id : 2]\n"
        "Output [3]: [oid#1L, cid#2L, tier#11]\n"
        "Input [4]: [oid#1L, cid#2L, dim_cid#10L, tier#11]\n\n"
        "(4) WriteFiles\n"
        "Input [3]: [oid#1L, cid#2L, tier#11]\n\n"
        "(5) Execute SaveIntoDataSourceCommand\n"
        "Arguments: Provider@1a, Map(table -> p.ds.gold, writemethod ->"
        " direct), Overwrite\n\n"
        "(8) Scan parquet db.dim\n"
        "Output [2]: [dim_cid#10L, tier#11]\n"
        "ReadSchema: struct<dim_cid:bigint,tier:string>\n"
    )
    proj_ops = spark_applications.extract_plan_schemas(
        numbered_aqe_sink_with_root_project
    )
    self.assertEqual(
        [(o["node_id"], o["operator"], o["columns"]) for o in proj_ops],
        [
            (1, "Scan parquet db.orders", ["oid", "cid"]),
            (
                5,
                "Execute SaveIntoDataSourceCommand",
                ["oid", "cid", "tier"],
            ),
            (8, "Scan parquet db.dim", ["dim_cid", "tier"]),
        ],
    )

    numbered_sink_over_unprojected_join = (
        "== Physical Plan ==\n"
        "Execute SaveIntoDataSourceCommand (4)\n"
        "+- * SortMergeJoin Inner (3)\n"
        "   :- * Project (1)\n"
        "   +- * Project (2)\n\n"
        "(1) Project [codegen id : 1]\n"
        "Output [2]: [oid#1L, cid#2L]\n\n"
        "(2) Project [codegen id : 2]\n"
        "Output [2]: [dim_cid#10L, tier#11]\n\n"
        "(4) Execute SaveIntoDataSourceCommand\n"
        "Arguments: Provider@1a, Map(table -> p.ds.gold), Overwrite\n"
    )
    unproj_ops = spark_applications.extract_plan_schemas(
        numbered_sink_over_unprojected_join
    )
    self.assertEqual(unproj_ops[0]["columns"], [])
    self.assertEqual(unproj_ops[0]["num_columns"], 0)

    # Markdown SQL table preserves ~1,000-char unattached metric maps intact.
    long_metrics = [
        {"name": f"metric_{i}", "accumulatorId": str(i)} for i in range(1, 16)
    ]
    long_values = {
        str(i): (
            "total (min, med, max (stageId: taskId)) 356.2 KiB (84.2 KiB,"
            f" 84.3 KiB, 187.6 KiB (stage 2.0: task {i}))"
        )
        for i in range(1, 15)
    }
    long_values["15"] = "172 ms"
    md_out, _ = self._run(
        "sql",
        [
            (200, _APPS),
            (
                200,
                {
                    "executionData": {
                        "executionId": "4",
                        "physicalPlanDescription": "== Physical Plan ==\n",
                        "metrics": long_metrics,
                        "metricValues": long_values,
                    }
                },
            ),
            (
                200,
                {
                    "sparkPlanGraph": {
                        "nodes": [{
                            "node": {
                                "sparkPlanGraphNodeId": "0",
                                "name": "Execute SaveIntoDataSourceCommand",
                                "metrics": [],
                            }
                        }]
                    }
                },
            ),
        ],
        execution_id=4,
    )
    self.assertIn("metric_15: 172 ms", md_out)
    self.assertNotIn("...[truncated]", md_out)

  def test_human_nanos_and_compute_stage_skew_score(self):
    self.assertEqual(spark_applications.human_nanos(None), "n/a")
    self.assertEqual(spark_applications.human_nanos(-1), "n/a")
    self.assertEqual(spark_applications.human_nanos(973_674_258), "974 ms")
    self.assertEqual(spark_applications.human_nanos(3_800_000_000), "3.8 s")
    self.assertEqual(
        spark_applications.compute_stage_skew_score(1071, 5456), 0.02
    )
    self.assertEqual(
        spark_applications.compute_stage_skew_score(100, 1000), 1.0
    )
    self.assertEqual(spark_applications.compute_stage_skew_score(0, 0), 0.0)
    self.assertEqual(spark_applications.compute_stage_skew_score(0, 10), 1.0)
    self.assertIsNone(spark_applications.compute_stage_skew_score(-1, 10))

  def test_stages_quantiles_renders_skew_table_and_job_skew_score(self):
    stages = {
        "sparkApplicationStages": [
            {
                "stageId": "0",
                "stageAttemptId": "0",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 4,
                "submissionTime": "2026-10-28T21:20:00.000Z",
                "completionTime": "2026-10-28T21:20:02.000Z",
                "taskQuantileMetrics": {
                    "durationMillis": {
                        "count": "4",
                        "percentile50": "500",
                        "maximum": "2000",
                    },
                    "inputMetrics": {
                        "recordsRead": {
                            "count": "4",
                            "percentile50": "250",
                            "maximum": "250",
                        }
                    },
                },
                "name": "scan stage",
            },
            {
                "stageId": "1",
                "stageAttemptId": "0",
                "status": "STAGE_STATUS_FAILED",
                "numTasks": 8,
                "submissionTime": "2026-10-28T21:20:02.000Z",
                "completionTime": "2026-10-28T21:20:22.000Z",
                "taskQuantileMetrics": {
                    "durationMillis": {
                        "count": "8",
                        "percentile50": "10",
                        "maximum": "99000",
                    }
                },
                "name": "failed attempt excluded from job_skew_score",
            },
            {
                "stageId": "1",
                "stageAttemptId": "1",
                "status": "STAGE_STATUS_COMPLETE",
                "numTasks": 8,
                "submissionTime": "2026-10-28T21:20:22.000Z",
                "completionTime": "2026-10-28T21:20:30.000Z",
                "taskQuantileMetrics": {
                    "durationMillis": {
                        "count": "8",
                        "percentile50": "100",
                        "maximum": "1000",
                    },
                    "shuffleReadMetrics": {
                        "readRecords": {
                            "count": "8",
                            "maximum": "3001",
                        }
                    },
                },
                "name": "skewed join write",
            },
        ]
    }
    out, _ = self._run(
        "stages", [(200, _APPS), (200, stages)], quantiles=True
    )
    self.assertIn("## Stage Task Skew (--quantiles)", out)
    self.assertIn(
        "| 0.0 | COMPLETE | 500 ms / 2.0 s | 4.0x | 0.00 | 250 / 250 (1.0x) |",
        out,
    )
    self.assertIn(
        "| 1.1 | COMPLETE | 100 ms / 1.0 s | 10.0x | 1.00 | 0 / 3,001"
        " (skewed) |",
        out,
    )
    # Weighted over completed stages: (2000*0.0 + 8000*1.0) / 10000 = 0.80.
    self.assertIn("- **Duration-weighted job_skew_score**: `0.80`", out)

  def test_stage_executors_and_summary_surface_cpu_fetch_wait_and_peak_memory(
      self,
  ):
    stage = {
        "stageData": {
            "stageId": "4",
            "status": "STAGE_STATUS_COMPLETE",
            "numTasks": 8,
            "taskQuantileMetrics": {
                "durationMillis": {
                    "count": "8",
                    "minimum": "100",
                    "percentile25": "100",
                    "percentile50": "100",
                    "percentile75": "500",
                    "maximum": "1000",
                },
                "executorCpuTimeNanos": {
                    "count": "8",
                    "minimum": "50000000",
                    "percentile25": "100000000",
                    "percentile50": "200000000",
                    "percentile75": "750000000",
                    "maximum": "950000000",
                },
                "shuffleReadMetrics": {
                    "fetchWaitTimeMillis": {
                        "count": "8",
                        "minimum": "0",
                        "percentile25": "5",
                        "percentile50": "12",
                        "percentile75": "40",
                        "maximum": "180",
                    }
                },
            },
        }
    }
    stage_out, _ = self._run(
        "stage", [(200, _APPS), (200, stage)], stage_id=4
    )
    self.assertIn(
        "- Task duration skew: median 100 ms, max 1.0 s (10.0x,"
        " stage_skew_score: 1.00)",
        stage_out,
    )
    self.assertIn(
        "| Executor CPU time | 50 ms | 100 ms | 200 ms | 750 ms | 950 ms |",
        stage_out,
    )
    self.assertIn(
        "| Shuffle fetch wait | 0 ms | 5 ms | 12 ms | 40 ms | 180 ms |",
        stage_out,
    )

    executors = {
        "sparkApplicationExecutors": [{
            "executorId": "0",
            "hostPort": "10.0.0.2:34431",
            "isActive": True,
            "totalCores": 4,
            "maxTasks": 4,
            "totalTasks": "13",
            "failedTasks": 0,
            "totalDurationMillis": "30700",
            "totalGcTimeMillis": "447",
            "peakMemoryMetrics": {
                "metrics": {
                    "JVMHeapMemory": "698980624",
                    "JVMOffHeapMemory": "113493960",
                    "ProcessTreePythonRSSMemory": "67108864",
                }
            },
        }]
    }
    exec_out, _ = self._run(
        "executors", [(200, _APPS), (200, executors)]
    )
    self.assertIn("| 4 (4) |", exec_out)
    self.assertIn("666.6 MiB / 108.2 MiB (PyRSS: 64.0 MiB)", exec_out)

    sum_out, _ = self._run(
        "summary",
        [
            (200, _APPS),
            (200, {"jobsSummary": {"completedJobs": 1}}),
            (200, {"stagesSummary": {"numCompletedStages": 2}}),
            (
                200,
                {
                    "totalExecutorSummary": {
                        "count": 2,
                        "totalCores": 8,
                        "maxTasks": 8,
                    }
                },
            ),
        ],
    )
    self.assertIn(
        "- Executors: 2 total, 0 dead; cores: 8, max tasks: 8", sum_out
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

  def test_accepts_kebab_case_and_project_id_flag_aliases(self):
    captured = {}

    def record(client, args):
      captured["parent"] = client.parent
      captured["execution_id"] = args.execution_id
      captured["stage_id"] = args.stage_id
      captured["max_fetch"] = args.max_fetch

    with mock.patch.dict(spark_applications.ACTIONS, {"sql": record}):
      code = spark_applications.main([
          "--project-id=my-proj",
          "--batch-id=my-batch",
          "--action=sql",
          "--execution-id=7",
          "--stage-id=2",
          "--max-fetch=500",
      ])
    self.assertEqual(code, 0)
    self.assertEqual(
        captured["parent"],
        "projects/my-proj/locations/us-central1/batches/my-batch",
    )
    self.assertEqual(captured["execution_id"], 7)
    self.assertEqual(captured["stage_id"], 2)
    self.assertEqual(captured["max_fetch"], 500)


if __name__ == "__main__":
  unittest.main()
