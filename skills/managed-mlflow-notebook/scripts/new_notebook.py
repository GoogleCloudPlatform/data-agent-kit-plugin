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

"""Generates a Managed MLflow notebook wired to user-supplied URIs.

Every notebook starts with an install cell, a config cell holding the tracking
and registry URIs, and an MLflow setup cell. Templates:

  - spark-connect (default): adds Managed Spark Connect cells
    (google-cloud-spark-connect's ManagedSparkSession) that
    train SparkXGBClassifier across executors, log the booster, register it
    with an @champion alias, and score it locally and with a @pandas_udf.
  - basic: stops after the MLflow setup cell; append workload cells yourself.

The Spark session defaults to Managed Spark serverless runtime 4.0 (Python
3.13) on the "default" subnetwork. Pass --runtime-version 3.0 --python-version
3.12 only when the user says they aren't using runtime 4.0.

Uses only the standard library so it runs with any python3 >= 3.9 (including
macOS /usr/bin/python3).

Example:
  python3 new_notebook.py --output ~/demo/train.ipynb \
    --tracking-uri https://mlflow.googleapis.com/v1alpha/projects/p/locations/us-central1/namespaces/ns \
    --registry-uri https://mlflow.googleapis.com/v1alpha/projects/p/locations/us-central1/registries/reg \
    --experiment-name my-exp --kernel-name my-kernel --spark-region us-central1
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

_URI_TEMPLATE = (
    r"^https://(?P<endpoint>[A-Za-z0-9.-]+)/(?P<api_version>v[0-9][A-Za-z0-9]*)"
    r"/projects/(?P<project>[^/\s]+)/locations/(?P<location>[^/\s]+)"
    r"/{collection}/(?P<resource_id>[^/\s]+)$"
)
_TRACKING_URI_RE = re.compile(_URI_TEMPLATE.format(collection="namespaces"))
_REGISTRY_URI_RE = re.compile(_URI_TEMPLATE.format(collection="registries"))

_PLUGIN_PACKAGE = "google-cloud-managed-mlflow"

# Packages the spark-connect template imports. google-cloud-spark-connect is
# the Managed Spark Connect client (ManagedSparkSession); [client] pulls the
# JVM-free pyspark-client, [interactive] the notebook extras (%%sparksql,
# %dpip). xgboost>=3.4 matches runtime 4.0 and provides xgboost.spark with
# Spark 4 support; pandas<3 keeps the client on pandas 2.
_SPARK_CONNECT_PACKAGE = "google-cloud-spark-connect[interactive,client]"
_SPARK_PACKAGES = (_SPARK_CONNECT_PACKAGE, "xgboost>=3.4.0", "pandas<3")

# Managed Spark session IDs: 4-63 chars of [a-z0-9-], starting with a letter
# and not ending with a hyphen.
_SESSION_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,61}[a-z0-9]$")

# Dataproc Serverless runtime -> executor Python. 4.0 = Spark 4.2 + Python 3.13
# (the default); 3.0 = Spark 4.0 + Python 3.12. The local kernel must use the
# same Python minor version for @pandas_udf to deserialize.
_DEFAULT_RUNTIME_VERSION = "4.0"
_SPARK_RUNTIME_PYTHON = {"4.0": "3.13", "3.0": "3.12"}

# Runtime 4.0 requires a subnetwork on every session; it must be IPv4-only
# (dual-stack and IPv6-only aren't supported). Default to the project's
# "default" VPC subnetwork in the Spark region. See
# https://docs.cloud.google.com/managed-spark/docs/concepts/versions/spark-runtime-4.0
_DEFAULT_SUBNETWORK = "default"
_RUNTIMES_REQUIRING_SUBNETWORK = ("4.0",)

_SPARK_CELLS = (
    """
# 4. Create (or reuse) a Managed Spark Connect session (Barrier Mode ready)
import time
from google.cloud.dataproc_v1 import Session
from google.cloud.managed_spark_connect import ManagedSparkSession

session_config = Session()
# The runtime's Python must match the local kernel's (runtime 4.0 = 3.13, 3.0 = 3.12).
__SESSION_ENVIRONMENT__
props = session_config.runtime_config.properties
props["spark.executor.cores"] = str(EXECUTOR_CORES)
props["spark.executor.instances"] = str(NUM_EXECUTORS)
props["spark.dynamicAllocation.enabled"] = "false"  # Required by SparkXGBClassifier barrier mode
props["spark.sql.adaptive.enabled"] = "false"       # Keeps AQE from coalescing barrier partitions
props["spark.sql.shuffle.partitions"] = str(NUM_PARTITIONS)

# An active session with SPARK_SESSION_ID is reused as is and session_config is
# ignored. To apply config changes, run spark.stop(terminate=True) first or
# change SPARK_SESSION_ID.
t0 = time.time()
spark = (
    ManagedSparkSession.builder
    .projectId(SPARK_PROJECT_ID)
    .location(SPARK_REGION)
    .sessionId(SPARK_SESSION_ID)
    .sessionConfig(session_config)
    .idleTtlSeconds(1800)
    .getOrCreate()
)
print(f"Spark Connect session ready in {time.time() - t0:.0f}s (Spark {spark.version})")
""",
    """
# 5. Build training & test data on the cluster (replace with your own table)
from pyspark.sql import functions as F

feature_cols = [f"f{i}" for i in range(NUM_FEATURES)]
df = spark.range(0, NUM_ROWS, numPartitions=NUM_PARTITIONS)
for i, c in enumerate(feature_cols):
    df = df.withColumn(c, F.randn(seed=i))

logit = 1.5 * F.col("f0") - 2.0 * F.col("f1") + F.col("f2") * F.col("f3") + 0.3 * F.randn(seed=999)
df = (
    df.withColumn("label", (logit > 0).cast("double"))
    .withColumn("features", F.array(*[F.col(c) for c in feature_cols]))
    .drop("id")
)
train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
train_df, test_df = train_df.cache(), test_df.cache()
print(f"Train rows: {train_df.count():,}, Test rows: {test_df.count():,}")
""",
    """
# 6. Distributed SparkXGBClassifier training + log the booster to Managed MLflow
import mlflow.xgboost
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from xgboost.spark import SparkXGBClassifier

params = {"n_estimators": 50, "max_depth": 5, "learning_rate": 0.1}

with mlflow.start_run(run_name="spark_connect_xgboost") as run:
    model = SparkXGBClassifier(
        features_col="features",
        label_col="label",
        num_workers=NUM_EXECUTORS,
        **params,
    ).fit(train_df)
    predictions = model.transform(test_df)
    accuracy = MulticlassClassificationEvaluator(
        labelCol="label", predictionCol="prediction", metricName="accuracy"
    ).evaluate(predictions)

    mlflow.log_params({**params, "num_workers": NUM_EXECUTORS, "num_rows": NUM_ROWS})
    mlflow.log_metric("accuracy", accuracy)
    # Log the collected booster with the pure-Python xgboost flavor:
    # mlflow.spark.log_model needs a JVM Hadoop filesystem that Spark Connect
    # clients don't have.
    model_info = mlflow.xgboost.log_model(xgb_model=model.get_booster(), name="model")

print(f"Test accuracy: {accuracy:.4f} | run_id={run.info.run_id}")
print("Logged model URI:", model_info.model_uri)
""",
    """
# 7. Register the model in the Managed MLflow registry & set @champion
mv = mlflow.register_model(model_uri=model_info.model_uri, name=REGISTERED_MODEL_NAME)
client.set_registered_model_alias(name=REGISTERED_MODEL_NAME, alias="champion", version=mv.version)
print(f"Registered {REGISTERED_MODEL_NAME} v{mv.version} (alias=@champion)")
""",
    """
# 8. Load from the registry: local inference + distributed @pandas_udf scoring
import pandas as pd
import xgboost as xgb
from pyspark.sql import types as T

champion_uri = f"models:/{REGISTERED_MODEL_NAME}@champion"
booster = mlflow.xgboost.load_model(champion_uri)

sample_pdf = test_df.select(*feature_cols).limit(5).toPandas()
print("Local predictions:", booster.predict(xgb.DMatrix(sample_pdf)))


@F.pandas_udf(T.DoubleType())
def predict_udf(*cols: pd.Series) -> pd.Series:
    batch = pd.concat(cols, axis=1).to_numpy()
    return pd.Series(booster.predict(xgb.DMatrix(batch)))


scored_df = test_df.limit(10).withColumn("udf_prediction", predict_udf(*[F.col(c) for c in feature_cols]))
scored_df.select("label", "udf_prediction").show(10)
""",
    """
# 9. Terminate the Spark Connect session
# spark.stop() alone only disconnects from a named session and leaves it
# running (and billing) until its idle TTL; terminate=True shuts it down.
if "spark" in globals() and spark is not None:
    spark.stop(terminate=True)
    print(f"Spark session {SPARK_SESSION_ID} terminated.")
""",
)


def _lines(text: str) -> list[str]:
  """Splits text into nbformat source lines (each keeps its newline)."""
  lines = text.strip("\n").split("\n")
  return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def _markdown_cell(text: str) -> dict[str, Any]:
  return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def _code_cell(text: str) -> dict[str, Any]:
  return {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {},
      "outputs": [],
      "source": _lines(text),
  }


def _shell_quote(package: str) -> str:
  """Quotes a requirement specifier for a %pip line if it has shell chars."""
  # Brackets (extras) are glob characters, so they get quoted too.
  if re.fullmatch(r"[A-Za-z0-9._\-,=]+", package):
    return package
  return '"' + package.replace('"', '\\"') + '"'


def _default_session_id(experiment_name: str) -> str:
  """Derives a valid Managed Spark session ID from the experiment name."""
  session_id = re.sub(r"[^a-z0-9-]+", "-", experiment_name.lower()).strip("-")
  if not session_id[:1].isalpha():
    session_id = "mlflow-" + session_id
  session_id = session_id[:63].rstrip("-")
  if len(session_id) < 4:
    session_id = (session_id + "-session").lstrip("-")
  return session_id


def _parse_uri(
    uri: str, pattern: re.Pattern[str], flag: str, kind: str
) -> re.Match[str]:
  match = pattern.match(uri)
  if not match:
    collection = "namespaces" if kind == "tracking" else "registries"
    sys.exit(
        f"ERROR: {flag} {uri!r} is not a Managed MLflow {kind} URI. Expected"
        " https://{endpoint}/{api_version}/projects/{project}/locations/"
        f"{{location}}/{collection}/{{id}}"
    )
  return match


def _dedupe_packages(packages: list[str]) -> list[str]:
  """Drops the plugin and duplicate distributions, keeping first occurrence."""
  seen = {_PLUGIN_PACKAGE}
  result = []
  for package in packages:
    name = re.split(r"[<>=!~\[ ;]", package, maxsplit=1)[0].lower()
    if name not in seen:
      seen.add(name)
      result.append(package)
  return result


def build_notebook(args: argparse.Namespace) -> dict[str, Any]:
  """Returns the nbformat 4 notebook dict for the given arguments."""
  tracking = _parse_uri(
      args.tracking_uri, _TRACKING_URI_RE, "--tracking-uri", "tracking"
  )
  _parse_uri(args.registry_uri, _REGISTRY_URI_RE, "--registry-uri", "registry")
  spark = args.template == "spark-connect"

  packages = list(args.packages) + (list(_SPARK_PACKAGES) if spark else [])
  extra = _dedupe_packages(packages)
  install = (
      "# 1. Install the Google Cloud Managed MLflow plugin\n"
      f"%pip install {_PLUGIN_PACKAGE}"
  )
  if extra:
    install += (
        "\n\n# Workload dependencies\n"
        f"%pip install -q -U {' '.join(_shell_quote(p) for p in extra)}"
    )

  config = f"""
# 2. Configuration: Managed MLflow tracking (namespace) & registry URIs
TRACKING_URI = "{args.tracking_uri}"
REGISTRY_URI = "{args.registry_uri}"

PROJECT_ID = "{tracking.group("project")}"
MLFLOW_LOCATION = "{tracking.group("location")}"
EXPERIMENT_NAME = "{args.experiment_name}"
"""
  if spark:
    config += f"""REGISTERED_MODEL_NAME = "{args.registered_model_name}"

# Managed Spark Connect session (google-cloud-spark-connect)
SPARK_PROJECT_ID = "{args.spark_project or tracking.group("project")}"
SPARK_REGION = "{args.spark_region}"
SPARK_SESSION_ID = "{args.session_id}"  # Reused across reruns and kernel restarts until its TTL
NUM_EXECUTORS = 4
EXECUTOR_CORES = 4
NUM_PARTITIONS = 32
NUM_ROWS = 200_000
NUM_FEATURES = 10
"""
  config += """
print("TRACKING_URI:", TRACKING_URI)
print("REGISTRY_URI:", REGISTRY_URI)
"""

  title = args.title or (
      f"Spark Connect + Managed MLflow: {args.experiment_name}"
      if spark
      else f"Managed MLflow: {args.experiment_name}"
  )
  intro = (
      "Trains a distributed `SparkXGBClassifier` on a Managed Service for"
      " Apache Spark session over Spark Connect (`google-cloud-spark-connect`),"
      " logs it to a Google Cloud Managed MLflow namespace, registers"
      " it in a Managed MLflow registry, and scores it locally and on the"
      " cluster, using the"
      if spark
      else "Logs runs to a Google Cloud Managed MLflow namespace and registers"
      " models in a Managed MLflow registry using the"
  )
  cells = [
      _markdown_cell(f"""
# {title}

{intro} `{_PLUGIN_PACKAGE}` plugin.

> **Prerequisites:** select the `{args.display_name}` kernel (the project
> `.venv`) and authenticate once with `gcloud auth application-default login`.
> Restart the kernel after the install cell runs for the first time.
"""),
      _code_cell(install),
      _code_cell(config),
      _code_cell("""
# 3. MLflow setup: point tracking and registry at Managed MLflow
import mlflow
from mlflow import MlflowClient

mlflow.set_tracking_uri(TRACKING_URI)
mlflow.set_registry_uri(REGISTRY_URI)

client = MlflowClient()
experiment = mlflow.set_experiment(EXPERIMENT_NAME)
print(f"Experiment '{experiment.name}' -> id={experiment.experiment_id}")
"""),
  ]
  if spark:
    # Literal values (not config variables) so the session cell reads exactly
    # like the Managed Spark docs. The proto field is a string: "4.0", not 4.0.
    environment = (
        f'session_config.runtime_config.version = "{args.runtime_version}"'
    )
    if args.subnetwork:
      environment += (
          "\nsession_config.environment_config.execution_config.subnetwork_uri"
          f' = "{args.subnetwork}"'
      )
    cells.extend(
        _code_cell(text.replace("__SESSION_ENVIRONMENT__", environment))
        for text in _SPARK_CELLS
    )

  return {
      "cells": cells,
      "metadata": {
          "kernelspec": {
              "display_name": args.display_name,
              "language": "python",
              "name": args.kernel_name,
          },
          "language_info": {
              "name": "python",
              "version": args.python_version,
          },
      },
      "nbformat": 4,
      "nbformat_minor": 5,
  }


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  parser.add_argument("--output", required=True, help="Path of the .ipynb.")
  parser.add_argument("--tracking-uri", required=True)
  parser.add_argument("--registry-uri", required=True)
  parser.add_argument("--experiment-name", required=True)
  parser.add_argument(
      "--template", choices=("spark-connect", "basic"), default="spark-connect"
  )
  parser.add_argument("--kernel-name", default="managed-mlflow")
  parser.add_argument("--display-name", default=None)
  parser.add_argument(
      "--python-version",
      default=None,
      help=(
          "Local kernel Python. Defaults to the Python of --runtime-version"
          " (3.13 for 4.0), or 3.12 for --template basic."
      ),
  )
  parser.add_argument("--title", default=None)
  parser.add_argument(
      "--packages",
      nargs="*",
      default=[],
      help="Extra pip requirement specifiers for the install cell.",
  )
  spark_group = parser.add_argument_group("spark-connect template")
  spark_group.add_argument(
      "--spark-region", help="Dataproc region for the Spark Connect session."
  )
  spark_group.add_argument(
      "--spark-project",
      help="Dataproc project. Defaults to the tracking URI's project.",
  )
  spark_group.add_argument(
      "--runtime-version",
      default=_DEFAULT_RUNTIME_VERSION,
      help="Dataproc Serverless runtime. Use 3.0 only if the user asks.",
  )
  spark_group.add_argument(
      "--subnetwork",
      default=None,
      help=(
          'Session subnetwork URI. Defaults to "default" for runtime 4.0'
          " (which requires one) and to none (Dataproc picks) otherwise."
      ),
  )
  spark_group.add_argument("--registered-model-name", default=None)
  spark_group.add_argument(
      "--session-id",
      default=None,
      help=(
          "Managed Spark session ID (4-63 chars of a-z, 0-9, '-'). Defaults to"
          " one derived from --experiment-name."
      ),
  )
  parser.add_argument(
      "--force", action="store_true", help="Overwrite an existing notebook."
  )
  args = parser.parse_args()
  if args.python_version is None:
    args.python_version = (
        _SPARK_RUNTIME_PYTHON.get(args.runtime_version, "3.12")
        if args.template == "spark-connect"
        else "3.12"
    )
  if args.subnetwork is None:
    args.subnetwork = (
        _DEFAULT_SUBNETWORK
        if args.runtime_version == _DEFAULT_RUNTIME_VERSION
        else ""
    )
  if args.display_name is None:
    args.display_name = f"Python {args.python_version} ({args.kernel_name})"

  if args.template == "spark-connect":
    if (
        args.runtime_version in _RUNTIMES_REQUIRING_SUBNETWORK
        and not args.subnetwork
    ):
      sys.exit(
          f"ERROR: Dataproc runtime {args.runtime_version} requires a"
          " subnetwork. Omit --subnetwork to use \"default\" or pass an"
          " IPv4-only subnetwork."
      )
    if not args.spark_region:
      sys.exit("ERROR: --spark-region is required for --template spark-connect.")
    expected = _SPARK_RUNTIME_PYTHON.get(args.runtime_version)
    if expected and expected != args.python_version:
      sys.exit(
          f"ERROR: Dataproc runtime {args.runtime_version} executors run Python"
          f" {expected}, but --python-version is {args.python_version}."
          " @pandas_udf fails when they differ."
      )
    if args.registered_model_name is None:
      args.registered_model_name = f"{args.experiment_name}-model"
    if args.session_id is None:
      args.session_id = _default_session_id(args.experiment_name)
    if not _SESSION_ID_RE.match(args.session_id):
      sys.exit(
          f"ERROR: --session-id {args.session_id!r} must be 4-63 characters of"
          " lowercase letters, digits and '-', start with a letter and not end"
          " with '-'."
      )

  output = os.path.abspath(os.path.expanduser(args.output))
  if not output.endswith(".ipynb"):
    sys.exit("ERROR: --output must end with .ipynb")
  if os.path.exists(output) and not args.force:
    sys.exit(f"ERROR: {output} exists. Pass --force to overwrite.")

  notebook = build_notebook(args)
  os.makedirs(os.path.dirname(output), exist_ok=True)
  with open(output, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
    f.write("\n")
  print(f"Wrote {output} ({len(notebook['cells'])} cells).")


if __name__ == "__main__":
  main()
