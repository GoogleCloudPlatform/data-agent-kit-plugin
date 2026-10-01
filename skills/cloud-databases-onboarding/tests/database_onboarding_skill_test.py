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

"""Unit tests for the Database Onboarding Skill module."""

import io
import json
import os
import sys
import unittest
from unittest import mock

# Add skill scripts directory to sys.path to allow importing
# database_onboarding_skill.
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKILL_SCRIPTS_DIR = os.path.join(_SKILL_ROOT, "scripts")
if _SKILL_SCRIPTS_DIR not in sys.path:
  sys.path.insert(0, _SKILL_SCRIPTS_DIR)

# pylint: disable=g-import-not-at-top
import database_onboarding_skill

# pylint: enable=g-import-not-at-top


class DatabaseOnboardingSkillTest(unittest.TestCase):

  def test_read_file_safe_success(self):
    content = database_onboarding_skill._read_file_safe(
        "references/recommendation_matrix.txt"
    )
    self.assertIsNotNone(content)
    self.assertIn("Recommendation Matrix", content)

  def test_read_file_safe_file_not_found(self):
    with mock.patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
      with self.assertRaises(FileNotFoundError):
        database_onboarding_skill._read_file_safe("references/non_existent.txt")
      self.assertIn(
          "[ERROR] Critical reference file missing",
          mock_stderr.getvalue(),
      )

  def test_read_file_safe_io_error(self):
    # Mock open to raise IOError
    with mock.patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
      with mock.patch("builtins.open", mock.mock_open()) as mock_file:
        mock_file.side_effect = IOError("Permissions / disk error")
        with self.assertRaises(IOError):
          database_onboarding_skill._read_file_safe(
              "references/onboarding_prompts.md"
          )
        self.assertIn("Failed to read reference file", mock_stderr.getvalue())

  def test_parse_discovery_questions(self):
    dummy_matrix = """
    random header text
    source_recommendations {
      source: MYSQL
      discovery_questions: [
        "What MySQL version?",
        "What is the size of the database?"
      ]
    }
    source_recommendations {
      source: [POSTGRESQL, ORACLE]
      discovery_questions: [
        "Do you need to build Gen AI applications?"
      ]
    }
    """
    parsed = database_onboarding_skill._parse_discovery_questions(dummy_matrix)
    self.assertEqual(
        parsed,
        {
            "MYSQL": [
                "What MySQL version?",
                "What is the size of the database?",
            ],
            "POSTGRESQL": ["Do you need to build Gen AI applications?"],
            "ORACLE": ["Do you need to build Gen AI applications?"],
        },
    )

  def test_parse_discovery_questions_empty_source(self):
    dummy_matrix = """
    source_recommendations {
      discovery_questions: ["Some question?"]
    }
    """
    parsed = database_onboarding_skill._parse_discovery_questions(dummy_matrix)
    self.assertEqual(parsed, {})

  def test_get_onboarding_system_instruction(self):
    instruction = database_onboarding_skill.get_onboarding_system_instruction()
    self.assertIsNotNone(instruction)
    self.assertIn("Database onboarding agent instructions", instruction)
    # Check that placeholders are formatted correctly
    self.assertIn("resource_creation_tool", instruction)
    self.assertIn("database_selection_tool", instruction)
    # Should contain parsed discovery questions JSON structure
    self.assertIn("MYSQL", instruction)

  def test_get_onboarding_system_instruction_key_error(self):
    # Test formatting error propagation
    with mock.patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
      with mock.patch(
          "database_onboarding_skill._read_file_safe", return_callable=mock.Mock
      ) as mock_read:
        # Return a template with an unexpected brace/placeholder,
        # e.g., missing database_selection_agent_name
        mock_read.return_value = "{some_incorrect_placeholder}"
        with self.assertRaises(KeyError):
          database_onboarding_skill.get_onboarding_system_instruction()
        self.assertIn("Formatting error in", mock_stderr.getvalue())

  def test_get_recommendation_matrix_context(self):
    matrix_context = (
        database_onboarding_skill.get_recommendation_matrix_context()
    )
    self.assertIsNotNone(matrix_context)
    self.assertIn("MySQL", matrix_context)
    self.assertIn("PostgreSQL", matrix_context)

  def test_get_database_selection_instruction(self):
    instruction = database_onboarding_skill.get_database_selection_instruction(
        num_recommendations=3
    )
    self.assertIsNotNone(instruction)
    self.assertIn("N=3", instruction)
    self.assertIn("recommendation matrix", instruction.lower())

  def test_get_database_selection_instruction_key_error(self):
    with mock.patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
      with mock.patch(
          "database_onboarding_skill._read_file_safe", return_callable=mock.Mock
      ) as mock_read:
        mock_read.return_value = "{some_incorrect_placeholder}"
        with self.assertRaises(KeyError):
          database_onboarding_skill.get_database_selection_instruction()
        self.assertIn("Formatting error in", mock_stderr.getvalue())

  def test_get_skill_definition(self):
    definition = database_onboarding_skill.get_skill_definition()
    self.assertIsInstance(definition, dict)
    self.assertEqual(definition["name"], "cloud-databases-onboarding")
    self.assertIn("description", definition)
    self.assertIn("onboarding_instruction", definition)
    self.assertIn("context_data", definition)
    self.assertIn("sub_tasks", definition)

  @mock.patch("sys.exit")
  @mock.patch("builtins.print")
  def test_main_verify(self, mock_print, mock_exit):
    with mock.patch.object(
        sys, "argv", ["database_onboarding_skill.py", "--verify"]
    ):
      database_onboarding_skill.main()
    mock_exit.assert_called_once_with(0)
    mock_print.assert_called_with(
        "[SUCCESS] All database onboarding skill components and reference"
        " templates verified successfully."
    )

  @mock.patch("builtins.print")
  def test_main_onboarding_prompt(self, mock_print):
    with mock.patch.object(
        sys, "argv", ["database_onboarding_skill.py", "--onboarding-prompt"]
    ):
      database_onboarding_skill.main()
    mock_print.assert_called()
    printed_content = mock_print.call_args[0][0]
    self.assertIn("Database onboarding agent instructions", printed_content)

  @mock.patch("builtins.print")
  def test_main_selection_prompt(self, mock_print):
    with mock.patch.object(
        sys, "argv", ["database_onboarding_skill.py", "--selection-prompt"]
    ):
      database_onboarding_skill.main()
    mock_print.assert_called()
    printed_content = mock_print.call_args[0][0]
    self.assertIn("expert Database Recommender AI", printed_content)

  @mock.patch("builtins.print")
  def test_main_definition(self, mock_print):
    with mock.patch.object(
        sys, "argv", ["database_onboarding_skill.py", "--definition"]
    ):
      database_onboarding_skill.main()
    mock_print.assert_called()
    printed_content = mock_print.call_args[0][0]
    # Verify that it is valid JSON
    parsed_json = json.loads(printed_content)
    self.assertEqual(parsed_json["name"], "cloud-databases-onboarding")

  @mock.patch("sys.exit")
  @mock.patch("sys.stderr", new_callable=io.StringIO)
  def test_main_exception_handling(self, mock_stderr, mock_exit):
    with mock.patch(
        "database_onboarding_skill.get_onboarding_system_instruction",
        side_effect=Exception("Failed to load"),
    ):
      with mock.patch.object(
          sys, "argv", ["database_onboarding_skill.py", "--verify"]
      ):
        database_onboarding_skill.main()
    self.assertIn(
        "Skill execution failed: Failed to load", mock_stderr.getvalue()
    )
    mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
  unittest.main()
