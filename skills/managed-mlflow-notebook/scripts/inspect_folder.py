# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Inspects a project folder to pick the managed-mlflow-notebook workflow mode.

Scans .ipynb files (skipping .venv and hidden dirs) and prints JSON with, per
notebook: whether it uses MLflow, its kernelspec, Python version, %pip
packages, and inferred pip packages from imports. The top-level "mode" is:

  - "existing": at least one notebook uses MLflow. Set up the .venv for it;
    don't generate a new notebook unless the user asks.
  - "fresh": no MLflow notebook found. Generate a new Spark Connect notebook.

Uses only the standard library so it runs with any python3.

Example:
  python3 inspect_folder.py ~/my_project
"""

# Keeps `str | None` annotations working on Python 3.9 (macOS /usr/bin/python3).
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from typing import Any

# Import root -> pip distribution, for imports whose names differ or that
# commonly appear in Managed MLflow notebooks.
_IMPORT_TO_PACKAGE = {
    "mlflow": "mlflow",
    "xgboost": "xgboost",
    "sklearn": "scikit-learn",
    "pandas": "pandas",
    "numpy": "numpy",
    "pyspark": "pyspark",
    "lightgbm": "lightgbm",
    "torch": "torch",
    "tensorflow": "tensorflow",
    "keras": "keras",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "scipy": "scipy",
    "transformers": "transformers",
    "google.cloud.dataproc_spark_connect": "dataproc-spark-connect",
    "google.cloud.bigquery": "google-cloud-bigquery",
    "google.cloud.storage": "google-cloud-storage",
    "bigframes": "bigframes",
}

# Package -> pip distributions that already install it as a dependency, so it
# isn't reported missing (and isn't installed separately at a conflicting
# version, e.g. pyspark pinned by dataproc-spark-connect).
_PROVIDED_BY = {
    "mlflow": {"google-cloud-managed-mlflow"},
    "pyspark": {"dataproc-spark-connect"},
    "pandas": {"dataproc-spark-connect", "mlflow", "google-cloud-managed-mlflow"},
    "numpy": {"xgboost", "pandas", "scikit-learn", "mlflow", "google-cloud-managed-mlflow"},
    "scipy": {"xgboost", "scikit-learn"},
}

_PIP_LINE_RE = re.compile(r"^\s*[%!]\s*pip3?\s+install\s+(?P<args>.+)$")
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(?P<from>[\w.]+)\s+import|import\s+(?P<imp>[\w.]+))"
)
_TRACKING_RE = re.compile(r"set_tracking_uri|TRACKING_URI\s*=")
_REGISTRY_RE = re.compile(r"set_registry_uri|REGISTRY_URI\s*=")


def _pip_packages(line: str) -> list[str]:
  """Returns requirement specifiers from a %pip/!pip install line."""
  match = _PIP_LINE_RE.match(line)
  if not match:
    return []
  try:
    tokens = shlex.split(match.group("args"), comments=True)
  except ValueError:
    tokens = match.group("args").split()
  packages = []
  skip_next = False
  for token in tokens:
    if skip_next:
      skip_next = False
      continue
    if token in ("-r", "-c", "-e", "--index-url", "-i", "--extra-index-url"):
      skip_next = True
      continue
    if token.startswith("-"):
      continue
    packages.append(token)
  return packages


def _import_package(module: str) -> str | None:
  for root, package in _IMPORT_TO_PACKAGE.items():
    if module == root or module.startswith(root + "."):
      return package
  return None


def inspect_notebook(path: str) -> dict[str, Any]:
  """Returns a summary of one notebook."""
  with open(path, encoding="utf-8") as f:
    notebook = json.load(f)

  pip_packages: list[str] = []
  imported: set[str] = set()
  has_tracking = has_registry = False
  for cell in notebook.get("cells", []):
    if cell.get("cell_type") != "code":
      continue
    source = cell.get("source", "")
    text = "".join(source) if isinstance(source, list) else source
    has_tracking |= bool(_TRACKING_RE.search(text))
    has_registry |= bool(_REGISTRY_RE.search(text))
    for line in text.splitlines():
      for package in _pip_packages(line):
        if package not in pip_packages:
          pip_packages.append(package)
      match = _IMPORT_RE.match(line)
      if match:
        package = _import_package(match.group("from") or match.group("imp"))
        if package:
          imported.add(package)

  pip_names = {re.split(r"[<>=!~\[ ;]", p, maxsplit=1)[0].lower() for p in pip_packages}
  uses_mlflow = "mlflow" in imported or any(
      "mlflow" in name for name in pip_names
  )
  metadata = notebook.get("metadata", {})
  kernelspec = metadata.get("kernelspec", {})
  version = str(metadata.get("language_info", {}).get("version", ""))
  version_match = re.match(r"^(\d+\.\d+)", version)
  missing = sorted(
      p for p in imported
      if p not in pip_names and not (_PROVIDED_BY.get(p, set()) & pip_names)
  )
  return {
      "path": path,
      "uses_mlflow": uses_mlflow,
      "installs_managed_mlflow_plugin": "google-cloud-managed-mlflow" in pip_names,
      "sets_tracking_uri": has_tracking,
      "sets_registry_uri": has_registry,
      "kernel_name": kernelspec.get("name"),
      "kernel_display_name": kernelspec.get("display_name"),
      "python_version": version_match.group(1) if version_match else None,
      "pip_packages": pip_packages,
      "imported_packages_not_in_pip_cells": missing,
  }


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  parser.add_argument("project_dir")
  args = parser.parse_args()

  root = os.path.abspath(os.path.expanduser(args.project_dir))
  if not os.path.isdir(root):
    sys.exit(f"ERROR: {root} is not a directory.")

  notebooks = []
  for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [
        d for d in dirnames
        if not d.startswith(".") and d not in ("node_modules", "__pycache__")
    ]
    for name in sorted(filenames):
      if name.endswith(".ipynb") and ".ipynb_checkpoints" not in dirpath:
        path = os.path.join(dirpath, name)
        try:
          notebooks.append(inspect_notebook(path))
        except (OSError, ValueError) as e:
          notebooks.append({"path": path, "error": str(e)})

  mlflow_notebooks = [n for n in notebooks if n.get("uses_mlflow")]
  print(json.dumps(
      {
          "project_dir": root,
          "mode": "existing" if mlflow_notebooks else "fresh",
          "has_venv": os.path.isdir(os.path.join(root, ".venv")),
          "mlflow_notebooks": [n["path"] for n in mlflow_notebooks],
          "notebooks": notebooks,
      },
      indent=2,
  ))


if __name__ == "__main__":
  main()
