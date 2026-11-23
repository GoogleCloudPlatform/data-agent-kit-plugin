---
name: managed-mlflow-notebook
license: Apache-2.0
metadata:
  version: v1
  publisher: google
description: >-
  Sets up a local Python virtual environment (.venv) and Jupyter kernel for
  Google Cloud Managed MLflow notebooks. For a fresh folder, generates a Spark
  Connect notebook that logs to a user-supplied Managed MLflow tracking URI and
  registry URI through the google-cloud-managed-mlflow plugin; for a folder
  that already has an MLflow notebook, sets up the environment for that
  notebook without generating a new one. Use when creating, scaffolding, or
  running a Managed MLflow notebook, when setting up or fixing its .venv or
  kernel, or when %pip fails with "No module named pip". Do NOT use for
  open-source MLflow servers, Databricks MLflow, or MLflow server-side
  implementation changes.
---

# Managed MLflow Notebook

Build a working local notebook environment for Google Cloud Managed MLflow and,
for fresh folders, generate a Spark Connect notebook wired to the user's own
tracking and registry URIs. Bundled scripts perform the deterministic steps:

-   [scripts/inspect_folder.py](scripts/inspect_folder.py): inspects
    `<PROJECT_DIR>` to pick the workflow mode and reports each notebook's
    kernel, Python version, and packages.
-   [scripts/setup_venv.sh](scripts/setup_venv.sh): creates `.venv`, installs
    `pip`, `ipykernel`, `google-cloud-managed-mlflow`, and extra packages, and
    registers a Jupyter kernel.
-   [scripts/new_notebook.py](scripts/new_notebook.py): generates a valid
    `nbformat` 4 `.ipynb` notebook (install cell, config cell with the URIs,
    MLflow setup cell, and Managed Spark Connect workload cells).

Set `SKILL_DIR` to the directory containing this `SKILL.md` (the installed
`managed-mlflow-notebook` skill directory, not the user's project directory).
Treat the bundled scripts as opaque CLI tools: pass `--help` if you need flag
details rather than reading their source code.

## Step 0: Verify Environment and Pick the Mode

Check where your shell runs (`uname -s`: `Darwin` = macOS, `Linux` = Linux
workstation) and inspect the target folder:

```bash
python3 "$SKILL_DIR/scripts/inspect_folder.py" <PROJECT_DIR>
```

Route based on the JSON `mode` field in stdout:

-   **`mode`: `"existing"`** (folder has at least one notebook that uses
    MLflow): follow
    [Mode A: Bring-your-own notebook](#mode-a-bring-your-own-notebook).
-   **`mode`: `"fresh"`** (folder has no MLflow notebook): follow
    [Mode B: Fresh folder](#mode-b-fresh-folder).

If the user explicitly asks for a new notebook inside an `"existing"` folder,
follow Mode B and write to a new file name; you MUST NOT overwrite an existing
notebook.

## Mode A: Bring-your-own notebook

The user's notebook is the source of truth. Make it run; do NOT rewrite it.

-   **MUST NOT generate a new notebook** unless the user asks for one. You may
    offer one at the end, then stop.
-   **MUST NOT ask for the tracking URI or registry URI.** The notebook already
    carries its own MLflow configuration; asking again invites a second,
    conflicting `set_tracking_uri`. Only ask about URIs if `sets_tracking_uri` /
    `sets_registry_uri` is `false` *and* the user asks for help wiring MLflow.
-   **MUST NOT edit the notebook** unless the user asks. If something needs to
    change (for example `installs_managed_mlflow_plugin` is `false`, or a
    package in `imported_packages_not_in_pip_cells` is missing from its `%pip`
    cells), report the finding and propose the edit.

Steps:

1.  From the `inspect_folder.py` JSON output for the target notebook, read
    `kernel_name`, `kernel_display_name`, `python_version`, `pip_packages`, and
    `imported_packages_not_in_pip_cells`. If several MLflow notebooks exist, ask
    the user which one to set up.
2.  Build `.venv` with the **notebook's own kernel name** so VS Code
    auto-selects it, and install the packages the notebook needs:

    ```bash
    bash "$SKILL_DIR/scripts/setup_venv.sh" \
      --project-dir <PROJECT_DIR> \
      --python <PYTHON_VERSION_OR_3.13> \
      --kernel-name <KERNEL_NAME> \
      --display-name "<KERNEL_DISPLAY_NAME>" \
      -- <PIP_PACKAGES...> <IMPORTED_PACKAGES_NOT_IN_PIP_CELLS...>
    ```

    If `kernel_name` is `null`, derive a name from the notebook file name. If
    the notebook uses Spark Connect (`google-cloud-spark-connect` or
    `dataproc-spark-connect`) with `@pandas_udf`, the local Python minor version
    MUST match the runtime set in `session_config.runtime_config.version`
    (runtime `4.0` -> `3.13`, `3.0` -> `3.12`), not the default.
3.  Run [Verify](#verify), then hand off to the user.

## Mode B: Fresh folder

### Step 1: Ask for the URIs and the Spark region

> [!IMPORTANT] You MUST ask the user for both URIs before generating any code.
> Do NOT invent URIs, reuse URIs from examples or other notebooks, or derive one
> from the other: tracking (a namespace) and registry (a registry) are separate
> resources and can live in different projects or locations.

If the user does not have the full URIs yet, ask for `<PROJECT_ID>`,
`<LOCATION>`, `<NAMESPACE_ID>`, and `<REGISTRY_ID>`, construct the URIs using
the format below, and confirm them with the user:

```text
Tracking URI: https://<ENDPOINT>/<API_VERSION>/projects/<PROJECT_ID>/locations/<LOCATION>/namespaces/<NAMESPACE_ID>
Registry URI: https://<ENDPOINT>/<API_VERSION>/projects/<PROJECT_ID>/locations/<LOCATION>/registries/<REGISTRY_ID>
```

`<ENDPOINT>` is the Managed MLflow API host (for example
`mlflow.googleapis.com`), and `<API_VERSION>` matches what that endpoint serves
(for example `v1alpha`).

In the same message, ask for the **Spark region** for the Managed Spark Connect
session (for example `us-central1`) and whether Spark should run in a different
project than the tracking URI's project. The Spark region is independent of the
MLflow location, so MUST NOT copy one into the other.

Do NOT ask about the Spark runtime version: default to **runtime 4.0** (Apache
Spark 4.2, Python 3.13) on the `default` subnetwork unless the user states they
are not using runtime 4.0. Only then switch to their runtime (for example `3.0`
with Python `3.12`) in Steps 2 and 3. If the user specifies a custom subnetwork,
pass it via `--subnetwork`.

Key runtime 4.0 rules (see the
[Managed Service for Apache Spark runtime 4.0 documentation](https://docs.cloud.google.com/managed-spark/docs/concepts/versions/spark-runtime-4.0)):

-   **Subnetwork is mandatory**: every runtime 4.0 session requires an IPv4-only
    subnetwork (dual-stack and IPv6-only subnetworks are unsupported).
    `new_notebook.py` sets `subnetwork_uri = "default"` by default and exits
    non-zero if runtime 4.0 is requested without a subnetwork.
-   **Premium tier & DCU quota**: interactive sessions run in the premium tier
    and consume `DataComputeUnitsPerProjectPerRegion` quota rather than Compute
    Engine CPU/disk quota. Quota errors during session creation indicate
    insufficient DCU quota.
-   **Memory shapes**: drivers and executors use `highmem` (7.75 GiB per vCPU)
    by default. Do NOT set `spark.executor.memory`, `spark.driver.memory`, or
    `spark.memory.offHeap.*`; set `spark.dataproc.executor.memory.shape` if the
    user needs a different shape.
-   **Default catalog**: the Lakehouse runtime catalog is the default Spark
    catalog; the `bigquery` catalog and `spark.read.format("bigquery")` remain
    available.
-   **Pre-installed libraries**: runtime 4.0 includes `xgboost` 3.4 and
    `mlflow`, matching the generated install cell.

**Pass/fail check:** `new_notebook.py` validates both URIs and exits non-zero if
either URI does not match the Managed MLflow resource path format.

### Step 2: Build the .venv and register the kernel

```bash
bash "$SKILL_DIR/scripts/setup_venv.sh" \
  --project-dir <PROJECT_DIR> \
  --python 3.13 \
  --kernel-name <KERNEL_NAME> \
  --display-name "Python 3.13 (<KERNEL_NAME>)" \
  -- "google-cloud-spark-connect[interactive,client]" "xgboost>=3.4.0" "pandas<3" <EXTRA_PACKAGES...>
```

Use `--python 3.12` (and the matching display name) only when targeting runtime
`3.0`. `[client]` installs the JVM-free `pyspark-client`; MUST NOT install
`pyspark` or `dataproc-spark-connect` into the same `.venv`, because they write
to the same `pyspark` namespace and overwrite one another.

### Step 3: Generate the Spark Connect notebook

```bash
python3 "$SKILL_DIR/scripts/new_notebook.py" \
  --output <PROJECT_DIR>/<NOTEBOOK_NAME>.ipynb \
  --tracking-uri "<TRACKING_URI>" \
  --registry-uri "<REGISTRY_URI>" \
  --experiment-name <EXPERIMENT_NAME> \
  --spark-region <SPARK_REGION> \
  [--spark-project <SPARK_PROJECT_ID>] \
  --kernel-name <KERNEL_NAME> \
  --display-name "Python 3.13 (<KERNEL_NAME>)" \
  [--session-id <SESSION_ID>] \
  [--packages <EXTRA_PACKAGES...>]
```

Defaults are `--runtime-version 4.0`, `--python-version 3.13`,
`--subnetwork default`, and a `--session-id` derived from `--experiment-name`.
If the user is not using runtime 4.0, pass
`--runtime-version <RUNTIME> --python-version <MATCHING_PYTHON>` (for example
`3.0` and `3.12`); the subnetwork line is omitted unless `--subnetwork` is
passed. The script exits non-zero on a runtime/Python mismatch, runtime 4.0
without a subnetwork, or an invalid session ID.

Pass the same `--kernel-name` as Step 2. The script refuses to overwrite an
existing file unless `--force` is passed. Use `--template basic` only when the
user explicitly asks for a notebook without Spark.

Generated notebook structure:

1.  Markdown title and prerequisites.
2.  **Install cell**: `%pip install google-cloud-managed-mlflow` first, then
    `%pip install -q -U "google-cloud-spark-connect[interactive,client]"
    "xgboost>=3.4.0" "pandas<3" ...`. Keep this as the first code cell so all
    later imports resolve on a fresh kernel.
3.  **Config cell**: `TRACKING_URI`, `REGISTRY_URI`, `EXPERIMENT_NAME`,
    `REGISTERED_MODEL_NAME`, Spark project/region/session ID, and cluster
    sizing.
4.  **MLflow setup cell**: `set_tracking_uri(TRACKING_URI)`,
    `set_registry_uri(REGISTRY_URI)`, `MlflowClient()`, `set_experiment`.
5.  **Spark Connect cells**: a Managed Spark Connect session
    (`ManagedSparkSession` from `google-cloud-spark-connect`) with barrier-mode
    settings, distributed `SparkXGBClassifier` training, booster logged with
    `mlflow.xgboost.log_model`, registration with an `@champion` alias, local
    and `@pandas_udf` inference from the registry, and session termination. With
    default settings, the session cell configures:

    ```python
    from google.cloud.dataproc_v1 import Session
    from google.cloud.managed_spark_connect import ManagedSparkSession

    session_config = Session()
    session_config.runtime_config.version = "4.0"
    session_config.environment_config.execution_config.subnetwork_uri = "default"
    props = session_config.runtime_config.properties
    ...
    spark = (
        ManagedSparkSession.builder
        .projectId(SPARK_PROJECT_ID)
        .location(SPARK_REGION)
        .sessionId(SPARK_SESSION_ID)
        .sessionConfig(session_config)
        .idleTtlSeconds(1800)
        .getOrCreate()
    )
    ```

### Step 4: Customize the workload (when asked)

Replace the synthetic data cell with the user's dataset (for example a BigQuery
table read via `spark.read.format("bigquery")`) or adjust the model. Follow
these rules whenever editing MLflow or Spark cells:

-   Reference the `TRACKING_URI` and `REGISTRY_URI` variables. MUST NOT paste
    URI literals into later cells or call `set_tracking_uri` /
    `set_registry_uri` a second time.
-   Keep `spark.dynamicAllocation.enabled=false` and
    `spark.sql.adaptive.enabled=false` for `SparkXGBClassifier`: barrier mode
    fails under dynamic allocation or AQE partition coalescing.
-   Log Spark-trained XGBoost models with
    `mlflow.xgboost.log_model(xgb_model=model.get_booster(), ...)`, NOT
    `mlflow.spark.log_model` (the Spark flavor requires a local JVM Hadoop
    filesystem unavailable on Spark Connect clients).
-   Create Spark sessions with `ManagedSparkSession` from
    `google.cloud.managed_spark_connect` (`google-cloud-spark-connect`), not
    `DataprocSparkSession`, and pass the `Session` proto via
    `.sessionConfig(...)`.
-   Named sessions (`.sessionId(SPARK_SESSION_ID)`) reconnect on rerun and
    **ignore `session_config`**. To apply changed Spark properties, run
    `spark.stop(terminate=True)` first or change `SPARK_SESSION_ID`. End the
    notebook with `spark.stop(terminate=True)`; plain `spark.stop()` leaves a
    named session running until its idle TTL.
-   To use extra PyPI packages inside a UDF on the remote session, prefer
    `%dpip install <PACKAGE>` (or `spark.addArtifacts("<PACKAGE>", pypi=True)`);
    also install locally if imported outside Spark.
-   Keep `session_config.runtime_config.version = "4.0"` (string, not float) and
    `subnetwork_uri` unless the user asks for another runtime or subnetwork. If
    the runtime changes, rebuild `.venv` with the matching Python minor version.
-   On runtime 4.0, MUST NOT set `spark.executor.memory`, `spark.driver.memory`,
    their `memoryOverhead`, `spark.memory.offHeap.*`, or removed
    `spark.dataproc.*.compute.tier` / `*.disk.tier` properties: they are
    unsupported and memory settings combined with a memory shape cause session
    rejection. Use memory shapes and `dataproc.tier`.
-   If you add a new package import, add it both to the install cell and to
    `.venv` (`bash "$SKILL_DIR/scripts/setup_venv.sh" ... -- <PACKAGE>`).
-   Keep edited notebooks valid `nbformat` 4 JSON.

## Safeguards Built Into `setup_venv.sh`

Do NOT bypass `setup_venv.sh` by hand; it prevents common local environment
failures:

-   **`uv venv --seed`**: a plain `uv venv` omits `pip`, causing `%pip install`
    to fail with `.venv/bin/python: No module named pip`. The script also
    repairs an existing pip-less `.venv`.
-   **Python 3.13 by default**: matches Managed Spark serverless runtime `4.0`
    executors (`3.12` for runtime `3.0`). `@pandas_udf` fails when local and
    executor Python minor versions differ. `--python-preference managed` ensures
    Linux and macOS download the exact CPython version rather than picking up
    mismatched OS, Homebrew, or Xcode interpreters.
-   **Never `/bin/python3 -m pip install ...`**: system Python on Linux and
    Homebrew Python on macOS are externally managed (PEP 668), and macOS
    `/usr/bin/python3` is the Xcode stub. Always select the `.venv` kernel.
-   **Local project directory**: refuses shared network source mounts (such as
    `/google/src/...` or `/Volumes/google/src/...`) whose top-level folders can
    shadow Python standard-library modules, and `cd`s into `<PROJECT_DIR>`
    before running Python.
-   **macOS `libomp` check for `xgboost`**: macOS `xgboost` wheels link
    `@rpath/libomp.dylib` (`/opt/homebrew/opt/libomp/lib` on Apple Silicon) and
    do not bundle OpenMP. When `xgboost` is installed in `.venv` on macOS,
    `setup_venv.sh` verifies `import xgboost` and runs `brew install libomp` if
    Homebrew is already installed (`/opt/homebrew/bin/brew`,
    `/usr/local/bin/brew`, or on `PATH`). It never installs Homebrew silently.

## macOS vs. Remote Linux Host (SSH / Cloud Workstation)

The skill runs on both macOS and Linux, but `.venv`, the Jupyter kernelspec, and
Application Default Credentials (ADC) exist **only on the machine that created
them**. Before Step 2, check `uname -s` (`Darwin` = macOS, `Linux` = Linux) and
confirm where the user opens the notebook. If your shell runs on a remote Linux
host while the user opens VS Code locally on macOS (or vice versa), tell the
user and run setup on the machine that will execute the kernel.

Platform differences:

-   **Install `uv`**:
    -   Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` (installs to
        `~/.local/bin`)
    -   macOS: `brew install uv` (or the `curl` installer)
-   **Jupyter kernelspec directory**:
    -   Linux: `~/.local/share/jupyter/kernels/`
    -   macOS: `~/Library/Jupyter/kernels/`
-   **Opening the notebook in VS Code**:
    -   Remote Linux `.venv`: connect VS Code via **Remote-SSH** to that Linux
        host; a local macOS VS Code window cannot see remote kernels.
    -   macOS `.venv`: open in local VS Code on the Mac.
-   **ADC login**:
    -   Headless / SSH Linux session without a local browser:
        `gcloud auth application-default login --no-launch-browser`
    -   macOS (or Linux desktop with a browser):
        `gcloud auth application-default login`
-   **`python3` for generator scripts**:
    -   Linux: system Python 3.11+
    -   macOS: `/usr/bin/python3` is 3.9; both Python helper scripts support
        Python 3.9+
-   **OpenMP for `xgboost`**:
    -   Linux: bundled in the wheel
    -   macOS: requires `libomp` (`brew install libomp`); see
        [macOS: missing Homebrew / `libomp` for `xgboost`](#macos-missing-homebrew--libomp-for-xgboost)

Cross-machine rules:

-   **MUST NOT copy or sync `.venv` across machines** (for example via a synced
    cloud drive or `scp -r`): interpreter symlinks and binary wheels are
    platform-specific. `setup_venv.sh` detects a non-runnable `.venv` and
    prompts you to remove and recreate it in place.
-   **Kernels are per machine**: running `setup_venv.sh` on a remote Linux host
    registers the kernel only there; if the user switches to local macOS, rerun
    Step 2 on the Mac.
-   **ADC is per machine**: running `gcloud auth application-default login` on
    macOS does not populate credentials on a remote Linux host, and SSH host
    credentials do not provide Google Cloud ADC. A `DefaultCredentialsError` or
    401/403 from the plugin or Spark Connect usually means ADC was configured on
    the other machine.
-   **Subnetwork `default`**: runtime 4.0 requires an IPv4-only subnetwork in
    `<SPARK_REGION>`. If session creation fails because `default` is missing, is
    dual-stack/IPv6-only, or lacks Private Google Access, ask the user for an
    IPv4-only subnetwork and regenerate with `--subnetwork` (this is a GCP
    project network setting, not a macOS/Linux difference).

## macOS: missing Homebrew / `libomp` for `xgboost`

If `setup_venv.sh` fails on macOS because `xgboost` cannot load `libomp.dylib`
and `brew` was not found, **ask the user before installing Homebrew** and offer
two options:

1.  **Install Homebrew + `libomp` (recommended, system-wide)**:

    -   On Apple Silicon Macs where `/opt/homebrew` is already owned by `$USER`
        (common on managed workstations where `/opt/homebrew/etc` contains
        system-managed files that make Homebrew's `install.sh` prompt for
        `sudo`), initialize Homebrew directly with `git` (no `sudo`) and install
        `libomp`:

        ```bash
        git -C /opt/homebrew init -q && \
          git -C /opt/homebrew config remote.origin.url https://github.com/Homebrew/brew && \
          git -C /opt/homebrew config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*' && \
          git -C /opt/homebrew config core.autocrlf false && \
          git -C /opt/homebrew fetch --force origin && \
          git -C /opt/homebrew fetch --force --tags origin && \
          git -C /opt/homebrew remote set-head origin --auto && \
          git -C /opt/homebrew reset --hard origin/HEAD && \
          /opt/homebrew/bin/brew install libomp
        ```

        Remind the user they can add `eval "$(/opt/homebrew/bin/brew shellenv)"`
        to `~/.zprofile` to put `brew` on `PATH`.
    -   Otherwise, ask the user to install Homebrew (for example from
        https://brew.sh) and run `brew install libomp`.
2.  **Zero-install kernel fallback**: if the user does not want Homebrew and
    `scikit-learn` is in `.venv` (`mlflow` pulls it in, and its macOS wheel
    bundles `libomp.dylib`), add `"env": {"DYLD_LIBRARY_PATH":
    "<PROJECT_DIR>/.venv/lib/python<PYTHON_VERSION>/site-packages/sklearn/.dylibs"}`
    (for example `python3.13`) to the registered `kernel.json` (path printed by
    `setup_venv.sh`). This applies to the Jupyter kernel only, not bare
    `.venv/bin/python`, and rerunning `setup_venv.sh` overwrites `kernel.json`,
    so reapply it afterward.

Then rerun [Verify](#verify).

## Verify

```bash
cd <PROJECT_DIR>
.venv/bin/python -m json.tool <NOTEBOOK_NAME>.ipynb > /dev/null && echo "valid JSON"
.venv/bin/python -c "import mlflow, google.auth, xgboost; print(mlflow.__version__, xgboost.__version__)"  # omit xgboost for --template basic
```

**Pass/fail criteria:** `setup_venv.sh` exits `0` and prints the `pip`,
`ipykernel`, `mlflow`, and (when installed) `xgboost` versions plus the existing
`kernel.json` path; the JSON validation prints `valid JSON`; and the import
check prints version strings without errors. If any check exits non-zero, fix
the reported error and rerun.

Hand off to the user with three steps:

1.  Run `gcloud auth application-default login` once **on the machine that runs
    the kernel** (add `--no-launch-browser` on a remote Linux host without a
    local browser).
2.  Open the notebook in VS Code (via Remote-SSH if `.venv` lives on a remote
    Linux host) and select the kernel by its display name if not auto-selected.
3.  Restart the kernel after running the install cell for the first time.
