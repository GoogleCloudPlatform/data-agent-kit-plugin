# PySpark Compatibility Analysis Guide

PySpark-specific checks: the Python runtime, PySpark breaking changes by Spark version, Python dependencies, Conda, and build checks. Use it with `spark_migration_reference.md`, which covers what every job type shares (version mapping, component versions, connectors, GPU/RAPIDS, and Core Spark / SQL breaking changes).

## Official sources

- PySpark migration guide: https://spark.apache.org/docs/latest/api/python/migration_guide/index.html

## Procedure

1. Take the target's Python version and preinstalled Python libraries from its component page ("Component Versions" in `spark_migration_reference.md`).
2. Scan every `.py` file and configuration script for the patterns in sections 1–3 below and in the PySpark migration guide for each intermediate Spark version (e.g. for Spark 2.4 → 3.5, review the changes in 3.0, 3.1, 3.2, 3.3, 3.4, and 3.5).
3. Check the dependencies (sections 2 and 3) and run the build checks (section 4).
4. Record each finding with its `file:line`, why it breaks on the target, and the fix. The report format is in SKILL.md Step 3.

---

## 1. Python Runtime & PySpark Breaking Changes by Spark Version

Take the target Python version from the target's component page, not from the track number: the same track can ship different Python versions (cluster image 2.2 ships Python 3.11, Serverless runtime 2.2 ships Python 3.12, and Serverless runtime 2.3 ships Python 3.11). Minimum Python, pandas, and PyArrow versions enforced by PySpark (`require_minimum_pandas_version()` / `require_minimum_pyarrow_version()`), for sanity-checking version pins:

- **Spark 2.4**: Minimum Python 2.7 / 3.4. Minimum pandas 0.19.2. Minimum PyArrow 0.8.0. Python 2 support deprecated.
- **Spark 3.0**: Minimum Python 2.7 / 3.4. Minimum pandas 0.23.2. Minimum PyArrow 0.12.1. Python 2.7 and < 3.6 support deprecated.
- **Spark 3.1**: Minimum Python 3.6. Minimum pandas 0.23.2. Minimum PyArrow 1.0.0. Python 2.7 and ≤ 3.5 support removed.
- **Spark 3.2**: Minimum Python 3.6. Minimum pandas 0.23.2. Minimum PyArrow 1.0.0. Python 3.6 support deprecated.
- **Spark 3.3**: Minimum Python 3.7. Minimum pandas 1.0.5. Minimum PyArrow 1.0.0. Python 3.6 support removed.
- **Spark 3.4**: Minimum Python 3.7. Minimum pandas 1.0.5. Minimum PyArrow 1.0.0. Python 3.7 support deprecated.
- **Spark 3.5**: Minimum Python 3.8. Minimum pandas 1.0.5. Minimum PyArrow 4.0.0. Python 3.7 support removed.
- **Spark 4.0**: Minimum Python 3.9. Minimum pandas 2.0.0. Minimum PyArrow 11.0.0. Python 3.8 support removed; requires `numpy >= 1.21`.
- **Spark 4.1**: Minimum Python 3.10. Minimum pandas 2.2.0. Minimum PyArrow 15.0.0. Python 3.9 support removed.

Also check that `requirements.txt` or `setup.py` doesn't force an incompatible Python version.

### PySpark breaking changes by Spark version (cumulative)
- **Spark 2.4 → 3.0/3.1 (`Row` field order):** up to Spark 2.4, `Row(**kwargs)` sorted its fields alphabetically; since Spark 3.0 (on Python 3.6+), fields keep the order in which they were passed. Code that relied on alphabetical *positions* (e.g. `row[0]`, or schemas inferred from such Rows) breaks. Fix the code to use field names or explicit schemas (note: the temporary Spark 3.0 `PYSPARK_ROW_FIELD_SORTING_ENABLED` env var was removed in Spark 3.1 and has no effect on Spark 3.1+ runtimes).
- **Spark 3.1 → 3.3 (Pandas API on Spark):** Spark 3.2+ includes the pandas API on Spark (`pyspark.pandas`), which replaces Koalas (`databricks.koalas`).
- **Spark 3.5 → 4.0 (`pyspark.pandas` under ANSI mode):** in Spark 4.0, `pyspark.pandas` raises an exception when `spark.sql.ansi.enabled=true` (the Spark 4.0+ default). Either set `spark.sql.ansi.enabled=false` or set the pandas-on-Spark option `compute.fail_on_ansi_mode=False` (note: Spark 4.1 supports `pyspark.pandas` under ANSI mode by default via `compute.ansi_mode_support=True`).
- **Spark 4.0 → 4.1 (`BinaryType` and safe Arrow conversions):**
  - `BinaryType` maps consistently to Python `bytes` instead of `bytearray` by default (`spark.sql.execution.pyspark.binaryAsBytes=true`). Update code that expects `bytearray`, or set `spark.sql.execution.pyspark.binaryAsBytes=false` as a legacy workaround.
  - `spark.sql.execution.pandas.convertToArrowArraySafely` defaults to `true`, so PyArrow raises errors on unsafe conversions (integer overflow, float truncation, precision loss) in Arrow-enabled UDFs/`pandas_udf` and `createDataFrame`.

### Python language checks
- **Python 2 → 3** (sources on cluster images 1.x):
  - `print` statements → `print()` calls.
  - `dict.iteritems()`, `dict.iterkeys()`, `dict.itervalues()` → `.items()`, `.keys()`, `.values()`.
  - `xrange()` → `range()`.
  - `unicode` vs. `str` handling.
  - `/` returns a float in Python 3; use `//` where the code relied on floor division.
- **Python 3.7/3.8 → 3.10+:**
  - `from collections import Mapping, Sequence, Iterable` → import them from `collections.abc` (the aliases were removed in Python 3.10).
  - `asyncio` event-loop changes.
  - Python 3.12 removed `distutils`, `imp`, `asynchat`, `asyncore`, and `smtpd`. Compiling the code (section 4.1) doesn't catch this, so the scan must.
  - Older `numpy`, `pandas`, `scipy`, and `pyarrow` releases may not support Python 3.10+ or 3.11+ (section 4.2 checks this).

## 2. Pandas, PyArrow, and NumPy Interoperability

PySpark relies on pandas and PyArrow for vectorized UDFs (`pandas_udf`), `toPandas()`, and `createDataFrame()` from pandas. Compare the job's pins with the versions preinstalled on the target (its component page) and the minimum versions in section 1.

- **pandas 2.0+ (and `pyspark.pandas` in Spark 4.0+):** `DataFrame.append()` / `Series.append()` were removed (use `concat()`), and `DataFrame.iteritems()` / `Series.iteritems()` were removed (use `.items()`).
- **NumPy 1.24+:** the aliases `np.int`, `np.float`, `np.bool`, `np.object`, and `np.str` (deprecated in 1.20) were removed. Use the built-ins `int`, `float`, `bool`, `object`, `str`, or specific types such as `np.int64` and `np.float64`.
- Don't turn on Arrow-based conversion (`spark.sql.execution.arrow.pyspark.enabled`) as part of the upgrade unless the source already used it: it changes how types are converted.

## 3. Conda Channels (clusters)

- The Anaconda `defaults` channel has been unavailable on Managed Spark images since May 2024.
- Preconfigured channels, including `conda-forge`, were removed starting with the June 22, 2026 sub-minor versions (`2.2.82`, `2.3.31`, and `3.0.4`); the removal extends to all images after August 24, 2026 (note: `2.2.84`, `2.3.33`, and `3.0.6` were subsequently rolled back).
- So declare channels explicitly: replace `defaults`, and set `channels: [conda-forge]` (or an explicit mirror channel) in `environment.yml`, or pass `-c conda-forge` to `conda` commands in scripts and initialization actions.
- If Conda is configured through cluster properties, the code can't fix it: report the change needed when the target cluster is created (see the [June 22, 2026 release notes](https://cloud.google.com/dataproc/docs/release-notes#June_22_2026)).

## 4. Build Checks Against the Target Version

Build checks show whether the code and its dependencies load on the target version. Run them twice in Step 1: on the original code during the analysis (each failure is a finding), and on the changed code after the upgrade (all checks must pass). Take `<TARGET_PYTHON>` (e.g. `3.11`) and `<TARGET_SPARK>` (e.g. `3.5.3`) from the target's component page.

- Copy the sources to `build_<app_id>_temp/` and run the checks there, so that compiler output (`__pycache__/`) never lands in the user's source directories. Delete the directory after recording the results.
- If a check can't run (tool missing, no network access), don't install toolchains to force it: record it as "not run" with the reason.

### 4.1. L1: Syntax (always)
Compile every retrieved Python file (main file, `--py-files` modules, and the contents of `.zip`/`.egg` archives) with the target Python:
```bash
uv run --no-project --python=<TARGET_PYTHON> -- python -m compileall -q build_<app_id>_temp/
```
If `uv` is unavailable, run `python3 -m compileall -q build_<app_id>_temp/` and note the local Python version in the report if it differs from `<TARGET_PYTHON>`. Compilation doesn't detect removed standard-library modules (section 1).

### 4.2. L2: Dependency Resolution (when the job declares dependencies)
Resolve the job's Python dependencies for the target Python on Linux x86_64 without installing them:
```bash
uv pip compile <REQUIREMENTS_FILE> --python-version=<TARGET_PYTHON> --python-platform=x86_64-manylinux_2_28 --output-file=build_<app_id>_temp/requirements_resolved.txt
```
If `uv` is unavailable:
```bash
python3 -m pip install --dry-run --ignore-installed --only-binary=:all: --python-version=<TARGET_PYTHON> --platform=manylinux2014_x86_64 -r <REQUIREMENTS_FILE>
```
- Include dependencies declared outside the manifest: the `dataproc:pip.packages` and `dataproc:conda.packages` cluster properties and packages installed by initialization actions (clusters), or packages baked into a custom container (Serverless).
- `--only-binary=:all:` fails for packages that publish no wheels. Check those packages manually; the failure alone doesn't prove an incompatibility.
- Compare the resolved versions with the packages preinstalled on the target. Flag pins that conflict with them, and flag any `pyspark` pin that differs from `<TARGET_SPARK>`: the platform provides PySpark, and an installed copy can shadow it.
- For Conda environment files, resolve with `conda` or `mamba` only if one is already installed; otherwise review the channels and pins manually (section 3). Never fetch PyPI (`pypi.org`) or Anaconda (`anaconda.org`) web pages to look up unpinned package names—only explicit version pins and the target image's preinstalled component table need comparison.
- Archives that contain compiled extensions (`.so` files) were built for the source Python. Flag them for a rebuild against `<TARGET_PYTHON>`.

### 4.3. L3: PySpark Import Check (only if `uv` is available)
This check requires `uv` because `uv run --with` provides a clean way to inject a specific version of `pyspark` into the execution environment without a full installation. This check downloads the `pyspark` package (several hundred MB). Execute the job's own `pyspark` import statements against the target PySpark:
```bash
uv run --no-project --python=<TARGET_PYTHON> --with=pyspark==<TARGET_SPARK> -- python -c "<the job's pyspark import statements, separated by semicolons>"
```
An `ImportError` confirms a removed or renamed API. The check doesn't start a Spark session, so it can't detect behavior changes. Without `uv`, record the check as "not run".
