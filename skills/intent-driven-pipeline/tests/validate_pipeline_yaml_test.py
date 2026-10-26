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
"""Unit tests for validate_pipeline_yaml."""

import contextlib
import copy
import io
import os
import sys
import tempfile
import unittest

import yaml

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
)
import validate_pipeline_yaml  # pylint: disable=g-import-not-at-top

_EXAMPLE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../references/example_customer_orders.pipeline.yaml",
    )
)

_DEPLOYMENT = """
environments:
  dev:
    project: my-dev-project
    region: us-central1
    variables:
      gold_dataset: dev_gold
    pipelines:
      - source: pipelines/customer_orders.pipeline.yaml
  prod:
    project: my-prod-project
    region: us-central1
    variables:
      gold_dataset: prod_gold
    pipelines:
      - source: pipelines/customer_orders.pipeline.yaml
"""


def _load_example():
  with open(_EXAMPLE, encoding="utf-8") as f:
    return yaml.safe_load(f)


class ValidatePipelineYamlTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.repo = tempfile.mkdtemp()
    os.makedirs(os.path.join(self.repo, "pipelines"))
    os.makedirs(os.path.join(self.repo, "dbt_customer_orders"))
    with open(
        os.path.join(self.repo, "dbt_customer_orders", "dbt_project.yml"), "w"
    ) as f:
      f.write("name: customer_orders\n")
    self.deployment = os.path.join(self.repo, "deployment.yaml")
    with open(self.deployment, "w") as f:
      f.write(_DEPLOYMENT)
    self.spec = _load_example()

  def _validate(self, spec):
    return validate_pipeline_yaml.validate(
        spec, repo_root=self.repo, deployment_path=self.deployment
    )

  def test_example_passes(self):
    report = self._validate(self.spec)
    self.assertEqual(report["status"], "PASS", report["errors"])

  def test_missing_goal_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["intent"]["goal"] = "  "
    report = self._validate(spec)
    self.assertEqual(report["status"], "FAIL")
    self.assertTrue(any("intent.goal" in e for e in report["errors"]))

  def test_extra_intent_key_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["intent"]["prompt"] = "raw"
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_continuous_mode_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["execution_mode"] = "CONTINUOUS"
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_out_of_scope_keys_fail(self):
    for key in ("outcomes", "quality_gates", "continuous"):
      spec = copy.deepcopy(self.spec)
      spec[key] = []
      report = self._validate(spec)
      self.assertEqual(report["status"], "FAIL", key)
      self.assertTrue(any("out of scope" in e for e in report["errors"]))

  def test_bad_cron_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["triggers"][0]["inline_trigger"]["schedule"]["interval"] = "daily"
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_missing_time_zone_fails(self):
    spec = copy.deepcopy(self.spec)
    del spec["triggers"][0]["inline_trigger"]["schedule"]["time_zone"]
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_event_trigger_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["triggers"] = [{"inline_trigger": {"event": {"table": "x"}}}]
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_no_triggers_warns(self):
    spec = copy.deepcopy(self.spec)
    del spec["triggers"]
    report = self._validate(spec)
    self.assertEqual(report["status"], "PASS", report["errors"])
    self.assertTrue(report["warnings"])

  def test_ingest_model_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["data_models"].append(
        {"name": "crm_ingest", "ingest": {"source": "kafka://t"}}
    )
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_two_engines_fail(self):
    spec = copy.deepcopy(self.spec)
    spec["data_models"][0]["sdp"] = {"source": "./spark_sdp"}
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_duplicate_model_names_fail(self):
    spec = copy.deepcopy(self.spec)
    spec["data_models"].append(copy.deepcopy(spec["data_models"][0]))
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_missing_dbt_dir_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["data_models"][0]["dbt"]["source"] = "./does_not_exist"
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_sdp_model_passes_with_spec_file(self):
    os.makedirs(os.path.join(self.repo, "spark_sdp"))
    with open(os.path.join(self.repo, "spark_sdp", "spark-pipeline.yml"), "w"):
      pass
    spec = copy.deepcopy(self.spec)
    spec["data_models"].append(
        {"name": "orders_sdp", "sdp": {"source": "./spark_sdp"}}
    )
    report = self._validate(spec)
    self.assertEqual(report["status"], "PASS", report["errors"])

  def test_select_must_be_list(self):
    spec = copy.deepcopy(self.spec)
    spec["data_models"][0]["dbt"]["select"] = "tag:x"
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_undefined_variable_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["parameters"][1]["default"] = "{{ silver_dataset }}"
    report = self._validate(spec)
    self.assertEqual(report["status"], "FAIL")
    self.assertTrue(any("silver_dataset" in e for e in report["errors"]))

  def test_variable_without_deployment_fails(self):
    report = validate_pipeline_yaml.validate(
        self.spec, repo_root=self.repo, deployment_path=None
    )
    self.assertEqual(report["status"], "FAIL")
    self.assertTrue(any("deployment.yaml" in e for e in report["errors"]))

  def test_bad_parameter_type_fails(self):
    spec = copy.deepcopy(self.spec)
    spec["parameters"][0]["type"] = "DATE"
    self.assertEqual(self._validate(spec)["status"], "FAIL")

  def test_main_infers_repo_root_from_pipelines_dir(self):
    path = os.path.join(self.repo, "pipelines", "customer_orders.pipeline.yaml")
    with open(path, "w") as f:
      yaml.safe_dump(self.spec, f)
    with contextlib.redirect_stdout(io.StringIO()) as out:
      rc = validate_pipeline_yaml.main([path])
    self.assertEqual(rc, 0, out.getvalue())
    self.assertIn('"status": "PASS"', out.getvalue())

  def test_main_reports_unreadable_yaml(self):
    path = os.path.join(self.repo, "pipelines", "bad.pipeline.yaml")
    with open(path, "w") as f:
      f.write("intent: [unclosed\n")
    with contextlib.redirect_stdout(io.StringIO()) as out:
      rc = validate_pipeline_yaml.main([path])
    self.assertEqual(rc, 1)
    self.assertIn('"status": "FAIL"', out.getvalue())


if __name__ == "__main__":
  unittest.main()
