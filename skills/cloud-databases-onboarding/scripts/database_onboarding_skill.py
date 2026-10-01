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

"""Database Onboarding Skill validation and context utilities.

This module provides helper utilities to validate the skill reference files,
parse discovery questions from the recommendation matrix, and format reference
prompts for the database onboarding skill workflow.
"""

import argparse
import json
import os
import re
import sys


def _read_file_safe(relative_path: str) -> str:
  """Safely reads a reference file with descriptive standard error reporting."""
  current_dir = os.path.dirname(os.path.abspath(__file__))
  skill_root = os.path.dirname(current_dir)
  file_path = os.path.join(skill_root, relative_path)

  try:
    with open(file_path, "r", encoding="utf-8") as f:
      return f.read()
  except FileNotFoundError as e:
    err_msg = (
        f"[ERROR] Critical reference file missing: '{file_path}'.\n"
        "Self-Correction Action: Verify that the skill directory structure is"
        " intact and '{relative_path}' exists under '{skill_root}'.\n"
    )
    sys.stderr.write(err_msg)
    raise FileNotFoundError(err_msg) from e
  except IOError as e:
    err_msg = (
        f"[ERROR] Failed to read reference file '{file_path}': {e}.\n"
        "Self-Correction Action: Check local filesystem read permissions for"
        " the workspace.\n"
    )
    sys.stderr.write(err_msg)
    raise IOError(err_msg) from e


def _parse_discovery_questions(matrix_text: str) -> dict[str, list[str]]:
  """Parses discovery questions from the text proto matrix."""
  blocks = matrix_text.split("source_recommendations {")
  questions_map = {}

  for block in blocks[1:]:
    source_match = re.search(
        r"source:\s*\[?([A-Z0-9_, ]+?)\]?\s*(?:#.*)?\n", block
    )
    if not source_match:
      continue
    sources = [s.strip() for s in source_match.group(1).split(",")]

    dq_match = re.search(r"discovery_questions:\s*\[(.*?)\]", block, re.DOTALL)
    if dq_match:
      questions = re.findall(r'"(.*?)"', dq_match.group(1))
      for s in sources:
        questions_map[s] = questions
  return questions_map


def get_onboarding_system_instruction() -> str:
  """Returns the formatted onboarding discovery instructions."""
  instruction_template = _read_file_safe("references/onboarding_prompts.md")
  try:
    matrix_text = get_recommendation_matrix_context()
    discovery_dict = _parse_discovery_questions(matrix_text)
    discovery_questions_by_source = json.dumps(discovery_dict, indent=2)

    return instruction_template.format(
        resource_creation_agent_name="resource_creation_tool",
        database_selection_agent_name="database_selection_tool",
        discovery_questions_by_source=discovery_questions_by_source,
    )
  except KeyError as e:
    err_msg = (
        "[ERROR] Formatting error in 'references/onboarding_prompts.md':"
        f" Missing expected placeholder or unescaped brace {e}.\n"
        "Self-Correction Action: Ensure all literal curly braces in"
        " 'onboarding_prompts.md' are escaped appropriately or placeholders"
        " match `format(...)` keys.\n"
    )
    sys.stderr.write(err_msg)
    raise KeyError(err_msg) from e


def get_recommendation_matrix_context() -> str:
  """Returns the raw recommendation matrix as structured text format."""
  return _read_file_safe("references/recommendation_matrix.txt")


def get_database_selection_instruction(num_recommendations: int = 1) -> str:
  """Returns the instruction for performing database selection with the embedded matrix."""
  instruction_template = _read_file_safe("references/selection_prompts.md")
  try:
    return instruction_template.format(
        num_recommendations=num_recommendations,
        recommendation_matrix=get_recommendation_matrix_context(),
    )
  except KeyError as e:
    err_msg = (
        "[ERROR] Formatting error in 'references/selection_prompts.md':"
        f" Missing expected placeholder {e}.\n"
        "Self-Correction Action: Verify that `{num_recommendations}` and"
        " `{recommendation_matrix}` exist inside 'selection_prompts.md'.\n"
    )
    sys.stderr.write(err_msg)
    raise KeyError(err_msg) from e


def get_skill_definition() -> dict[str, str | dict[str, str]]:
  """Returns a dictionary representation of the skill components and reference context."""
  return {
      "name": "cloud-databases-onboarding",
      "description": (
          "Guides users through discovering their database requirements, "
          "recommends a GCP database based on a recommendation matrix, and "
          "assists in database creation by analyzing the workspace for "
          "Terraform scripts, validating infrastructure with "
          "Plan-Validate-Execute, and creating a Change List (CL) or Pull "
          "Request for the user."
      ),
      "onboarding_instruction": get_onboarding_system_instruction(),
      "context_data": {
          "recommendation_matrix": get_recommendation_matrix_context(),
      },
      "sub_tasks": {
          "selection_task_instruction": get_database_selection_instruction(),
      },
  }


def main():
  """CLI entrypoint to execute the skill script directly."""
  parser = argparse.ArgumentParser(
      description="Execute Database Onboarding Skill components and validation."
  )
  parser.add_argument(
      "--verify",
      action="store_true",
      help="Verify that all reference files exist and formatting succeeds.",
  )
  parser.add_argument(
      "--onboarding-prompt",
      action="store_true",
      help="Output the onboarding instruction prompts (Phases 1-3).",
  )
  parser.add_argument(
      "--selection-prompt",
      action="store_true",
      help="Output the database selection matrix instruction.",
  )
  parser.add_argument(
      "--definition",
      action="store_true",
      help="Output the JSON definition of the entire skill.",
  )

  args = parser.parse_args()

  try:
    if args.verify:
      get_onboarding_system_instruction()
      get_database_selection_instruction()
      print(
          "[SUCCESS] All database onboarding skill components and reference"
          " templates verified successfully."
      )
      sys.exit(0)
    elif args.onboarding_prompt:
      print(get_onboarding_system_instruction())
    elif args.selection_prompt:
      print(get_database_selection_instruction())
    elif args.definition:
      print(json.dumps(get_skill_definition(), indent=2))
    else:
      parser.print_help()
  except Exception as e:  # pylint: disable=broad-exception-caught
    sys.stderr.write(f"[FATAL] Skill execution failed: {e}\n")
    sys.exit(1)


if __name__ == "__main__":
  main()
