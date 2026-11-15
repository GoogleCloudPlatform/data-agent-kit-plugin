# PySpark Compatibility Analysis Guide

PySpark-specific checks: the Python runtime, Python language changes, Python
dependencies, Conda and Pixi, and build checks. Use it with
`spark_migration_reference.md`, which covers what every job type shares (version
mapping, component versions, the Java runtime, connectors, GPU/RAPIDS, and the
Spark migration notes, including PySpark's).

## Procedure

1. Take the target's Python version and preinstalled Python libraries from its component page ("Component Versions" in `spark_migration_reference.md`).
2.  Scan every `.py` file and configuration script as sections 1–3 below
    describe, and check the Spark migration notes, PySpark's included, as "Spark
    Migration Notes" in `spark_migration_reference.md` describes. If the job
    executes inline SQL (`spark.sql(...)`, `sqlContext.sql(...)`,
    `selectExpr(...)`, `expr(...)`), sets `spark.sql.*` properties, or loads
    `.sql` files, also check those queries and properties with
    `spark_sql_analysis.md` (sections 1–2) and run its Catalyst parser check
    (`spark_sql_analysis.md`, section 4.1) alongside the Python build checks in
    section 4.
3. Check the dependencies (sections 2 and 3) and run the build checks (section 4).
4. Record each finding with its `file:line`, why it breaks on the target, and the fix. The report format is in SKILL.md Step 3.

---

## 1. Python Runtime & Language Changes

Don't infer the target Python version from the track number: the same track can
ship different Python versions (cluster image 2.2 ships Python 3.11, Serverless
runtime 2.2 ships Python 3.12, and Serverless runtime 2.3 ships Python 3.11).
For sanity-checking version pins, use the Python versions that the source and
target Spark versions support and the target PySpark's minimum pandas, NumPy,
and PyArrow versions: the index that `fetch_migration_notes.py` prints lists
them ("Spark Migration Notes" in `spark_migration_reference.md`, which also says
where to find any that it marks as unavailable). Also check that
`requirements.txt` or `setup.py` doesn't force an incompatible Python version.

If the Python version changes, check the code against the language and
standard-library changes between the source and target Python versions (removed
syntax, modules, functions, and methods). This guide doesn't list them; the
build checks find most of them:

-   L1 (section 4.1) compiles the code with the target Python, which finds
    removed syntax.
-   L3 (section 4.3) imports the job's standard-library modules with the target
    Python, which finds removed modules and names. If L3 doesn't run, the scan
    must check the job's standard-library imports instead.
-   A removed function or method fails only when the code calls it, so the scan
    must find those.

## 2. Pandas, PyArrow, and NumPy Interoperability

PySpark relies on pandas and PyArrow for vectorized UDFs (`pandas_udf`),
`toPandas()`, and `createDataFrame()` from pandas. Compare the job's pins with
the versions preinstalled on the target (its component page) and the target
PySpark's minimum versions (section 1).

-   If pandas, NumPy, or PyArrow changes version between the source and target,
    check each call that the job makes into that library for APIs removed or
    changed in between. The L3 import check (section 4.3) loads the target
    versions when it pins them, but only running the code exercises the calls.
- Don't turn on Arrow-based conversion (`spark.sql.execution.arrow.pyspark.enabled`) as part of the upgrade unless the source already used it: it changes how types are converted.

## 3. Conda Channels and Pixi

- The Anaconda `defaults` channel has been unavailable on Managed Spark images since May 2024.
-   Images no longer come with preconfigured Conda channels (such as
    `conda-forge`): cluster images `1.3.96+`, `1.4.81+`, `1.5.92+`, `2.0.161+`,
    `2.1.119+`, `2.2.87+`, and `2.3.36+` (older cluster images that still have
    them are no longer allowed), and Serverless runtimes `1.2.89+`, `2.2.89+`,
    and `2.3.42+`. The affected versions changed over several releases, so check
    the [release notes](https://cloud.google.com/dataproc/docs/release-notes)
    for the target version.
-   Without preconfigured channels, the `dataproc:conda.packages` property and a
    plain `conda install <package>` fail. Declare the channel explicitly:
    -   in `dataproc:conda.packages`, write each package as
        `<channel>::<package>==<version>` (e.g. `conda-forge::pip==24.0`);
    -   in `conda` commands in scripts and initialization actions, pass
        `-c conda-forge`;
    -   in `environment.yml`, replace `defaults` with `channels: [conda-forge]`
        (or an explicit mirror channel).
-   If Conda is configured through cluster properties, the code can't fix it:
    report the change needed when the target cluster is created.
-   **Image 3.0 uses Pixi:** cluster image 3.0 (and Serverless runtime 3.0)
    manages Python with Pixi instead of Conda, with `conda-forge` preconfigured
    via `prefix.dev`. On cluster image 3.0, `dataproc:conda.packages` (run via
    `pixi add`; pass `<package>==<version>` without `<channel>::` prefixes) and
    `dataproc:pip.packages` remain supported, whereas
    `dataproc:conda.env.config.uri` (`environment.yml`) and `conda install` in
    initialization actions do not work—migrate those to
    `dataproc:conda.packages`, `dataproc:pip.packages`, or `pixi add`, and
    report the cluster change needed.

## 4. Build Checks Against the Target Version

Build checks show whether the code and its dependencies load on the target version. Run them twice in Step 1: on the original code during the analysis (each failure is a finding), and on the changed code after the upgrade (all checks must pass). Take `<TARGET_PYTHON>` (e.g. `3.11`) and `<TARGET_SPARK>` (e.g. `3.5.3`) from the target's component page.

- Copy the sources to `build_<app_id>_temp/` and run the checks there, so that compiler output (`__pycache__/`) never lands in the user's source directories. Delete the directory after recording the results.
- If a check can't run (tool missing, no network access), don't install toolchains to force it: record it as "not run" with the reason.

### 4.1. L1: Syntax (always)
Compile every retrieved Python file (main file, `--py-files` modules, and the contents of `.zip`/`.egg` archives) with the target Python:

```bash
uv run --no-project --python=<TARGET_PYTHON> -- python -m compileall -q build_<app_id>_temp/
```
If `uv` is unavailable, run `python3 -m compileall -q build_<app_id>_temp/` and note the local Python version in the report if it differs from `<TARGET_PYTHON>`.

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

### 4.3. L3: Import Check (only if `uv` is available)

This check requires `uv` because `uv run --with` provides a clean way to inject
a specific version of `pyspark` into the execution environment without a full
installation. This check downloads the `pyspark` package (several hundred MB).
Execute the job's own import statements for the standard library, `pyspark`,
pandas, NumPy, and PyArrow with the target Python and PySpark, with the
`[sql,ml]` extras that install NumPy, pandas, and PyArrow across Spark 2.4–4.1
(add `connect` on Spark 3.4+ or `pipelines` on Spark 4.1+ only when the job
imports `pyspark.sql.connect` or `pyspark.pipelines`):

```bash
uv run --no-project --python=<TARGET_PYTHON> --with='pyspark[sql,ml]==<TARGET_SPARK>' -- python -I -c '
import sys
stmts = [<each reconstructed stdlib, pyspark, pandas, numpy, and pyarrow import as a string>]
failed = False
for s in stmts:
    try:
        exec(s, {})
    except ImportError as exc:
        print(f"{s}: {exc}", file=sys.stderr)
        failed = True
sys.exit(1 if failed else 0)
'
```

If the target's component page lists NumPy, pandas, and PyArrow versions, pin
them as well (use `==<major>.<minor>.*` when the page omits a patch version,
e.g. `--with='numpy==2.4.*'`, and `==<x.y.z>` when a full patch version is
given). An import error
(`cannot import name '<name>' from '<module>'` or `No module named '<module>'`)
is a finding when it names a `pyspark` module or name, which the target PySpark
removed or renamed; a standard-library one, which the target Python removed; or,
when the check pins the target's versions, a pandas, NumPy, or PyArrow one,
which that version removed. Without pins, check such a name by hand (section 2).
An error about any other module means the check's environment is incomplete, not
that the code is incompatible: the dependency resolution (section 4.2) covers
the job's other packages. The check doesn't start a Spark session, so it can't
detect behavior changes. If `uv` fails during package resolution (for example,
if `<TARGET_SPARK>` is an unreleased version or a GCP patch string not available
on PyPI), record the check as "not run (package resolution failure)" rather than
reporting it as a code compatibility finding. Without `uv`, record the check as
"not run".
