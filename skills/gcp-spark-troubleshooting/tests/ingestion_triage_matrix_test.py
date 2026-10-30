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

"""Structural and invariant tests for platform mechanics docs and SKILL.md."""

import os
import re
import unittest

_HERE = os.path.dirname(__file__)
_REFS_DIR = os.path.abspath(os.path.join(_HERE, "../references"))
_MATRIX_PATH = os.path.join(_REFS_DIR, "ingestion_triage_matrix.md")
_CATALOG_PATH = os.path.join(_REFS_DIR, "diagnostic_rules_catalog.md")
_SKILL_PATH = os.path.abspath(os.path.join(_HERE, "../SKILL.md"))

_MARKDOWN_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_SCENARIO_ID_RE = re.compile(r"\b((?:managed_)?spark_ingestion_\d+|ING-\d+)\b")


class IngestionTriageMatrixTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    with open(_MATRIX_PATH, "r", encoding="utf-8") as f:
      self.matrix_text = f.read()
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
      self.catalog_text = f.read()
    with open(_SKILL_PATH, "r", encoding="utf-8") as f:
      self.skill_text = f.read()

  def test_no_bundled_json_rule_thresholds_in_references(self):
    self.assertIn("ships **no rules or thresholds**", self.catalog_text)
    json_files = [
        name for name in os.listdir(_REFS_DIR) if name.endswith(".json")
    ]
    self.assertEqual(json_files, [])
    self.assertNotIn("ingestion_stage_rules.json", self.skill_text)
    self.assertNotIn("ingestion_stage_rules.json", self.matrix_text)

  def test_no_markdown_tables_or_scenario_ids_in_skill_or_reference(self):
    for label, text in (
        ("ingestion_triage_matrix.md", self.matrix_text),
        ("SKILL.md", self.skill_text),
    ):
      for idx, line in enumerate(text.splitlines(), 1):
        self.assertIsNone(
            _MARKDOWN_TABLE_ROW_RE.match(line),
            msg=f"{label}:{idx} contains a prohibited Markdown table row",
        )
        self.assertIsNone(
            _SCENARIO_ID_RE.search(line),
            msg=f"{label}:{idx} contains a hardcoded benchmark scenario ID",
        )

  def test_size_budgets_and_no_circular_skill_refs(self):
    self.assertLessEqual(len(self.matrix_text.splitlines()), 295)
    self.assertLessEqual(len(self.skill_text.splitlines()), 800)
    self.assertLessEqual(len(self.skill_text.encode("utf-8")), 46080)
    for label, text in (
        ("ingestion_triage_matrix.md", self.matrix_text),
        ("SKILL.md", self.skill_text),
    ):
      self.assertNotIn("@skill:gcp-spark\n", text, msg=label)
      self.assertNotIn("@skill:gcp-spark ", text, msg=label)
      self.assertNotIn("@skill:gcp-spark-observability", text, msg=label)

  def test_baseline_skill_sections_preserved(self):
    baseline_headings = [
        "### Role & Persona",
        "### CRITICAL RULES (MUST FOLLOW):",
        "## Tooling Prerequisites",
        "## Evidence Flow by Workload Type",
        "## Direct Log Reading & Analysis Workflow (GCS / HTTPS URLs)",
        "## Spark Applications Workflow (Serverless Batches & Sessions)",
        "## Spark Code Inspection Workflow (Scripts, JARs & Bytecode)",
        "## Task Execution Process for Troubleshooting Workloads",
        "## Troubleshooting Scenarios Catalog",
        "## Important Constraints",
    ]
    for heading in baseline_headings:
      self.assertIn(heading, self.skill_text)

  def test_architectural_planes_and_stage_mechanics_documented(self):
    expected_sections = [
        "## 1. Identity, Credential Delegation & Encryption Planes",
        "## 2. VPC Routing, Name Resolution, Capacity & Perimeters",
        "## 3. Runtime Versions, JVM Classloading & Executor Isolation",
        "## 4. Connector Contracts, Data Framing & Schema Evolution",
        "## 5. Stage Telemetry Mechanics & End-to-End Conservation",
    ]
    for section in expected_sections:
      self.assertIn(section, self.matrix_text)
    expected_stage_topics = [
        "Single-Task Root Scans",
        "Partition Skew & Python `@udf` Serialization",
        "Memory & Disk Spill Pressure",
        "Small-File & Tiny-Task Storms",
        "Post-Read Zero-Output Conservation & Full-Script Verification",
        "references/diagnostic_rules_catalog.md",
    ]
    for topic in expected_stage_topics:
      self.assertIn(topic, self.matrix_text)

  def test_skill_md_references_companion_resources_and_guardrails(self):
    self.assertIn("scripts/spark_env_inspector.py", self.skill_text)
    self.assertIn("references/diagnostic_rules_catalog.md", self.skill_text)
    self.assertIn("references/ingestion_triage_matrix.md", self.skill_text)
    self.assertIn(
        "Cloud Mutation & Least-Privilege Guardrails", self.skill_text
    )
    self.assertIn(
        "No Remediation Execution on Follow-Up Confirmation", self.skill_text
    )
    self.assertIn("batches submit", self.skill_text)
    self.assertIn("jobs submit", self.skill_text)
    self.assertIn("Untrusted Log & Telemetry Content", self.skill_text)
    self.assertIn("Execution Engine Scope", self.skill_text)
    for sample_id in (
        "ING-01",
        "spark_ingestion_01",
        "managed_spark_ingestion_14",
    ):
      self.assertRegex(sample_id, _SCENARIO_ID_RE)


if __name__ == "__main__":
  unittest.main()
