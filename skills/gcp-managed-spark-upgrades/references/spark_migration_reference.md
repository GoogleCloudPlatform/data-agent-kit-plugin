# Common Spark Migration Reference

Use this reference to identify compatibility issues based on Dataproc Image version upgrades (and their corresponding Spark versions).

> [!NOTE]
> **Upgrades are cumulative.** If you are upgrading across multiple versions (e.g., Dataproc 1.5 directly to Dataproc 3.0), you must account for **all** the breaking changes listed in every intermediate section below (2.0+, 2.1, 2.2, and 3.0).

## Dataproc 1.4 / 1.5 (Spark 2.4) to Dataproc 2.0+ (Spark 3.1+)

### Core Spark / SQL (Applies to PySpark, Scala, Java, SQL)
*   **Calendar System**: Changed to Proleptic Gregorian in Spark 3.0. Date/timestamp parsing/formatting might behave differently.
*   **SQLContext/HiveContext**: Deprecated. Use `SparkSession.builder` to initialize.
*   **unionAll**: Deprecated. Use `union` instead.
*   **spark.mllib**: Mostly deprecated in favor of `spark.ml` (DataFrame-based machine learning).
*   **date_add/date_sub**: Second argument must be an integer (no floats or non-literal strings).

### PySpark Specific
*   **Row Construction**: `Row` keyword arguments are sorted alphabetically in Spark 3.0+. Ensure code does not rely on insertion order.
*   **Pandas/Arrow**: Requires Pandas >= 0.23.2 and PyArrow >= 0.12.1 for optimized conversions.

## Dataproc 2.0 (Spark 3.1) to Dataproc 2.1 (Spark 3.3)

### PySpark Specific
*   **Pandas API on Spark**: Spark 3.2+ introduced the pandas API on Spark (`pyspark.pandas`), replacing Koalas.

## Dataproc 2.1 (Spark 3.3) to Dataproc 2.2 / 2.3 (Spark 3.5)

### Core Spark / SQL
*   **YARN Configs**: YARN-specific executor configs deprecated in favor of general spark executor configs (e.g., `spark.yarn.executor.failuresValidityInterval` -> `spark.executor.failuresValidityInterval`).

### PySpark Specific
*   **SQL/DataFrame Interoperability**: In Spark 3.4+, DataFrames can be passed directly to `spark.sql` using string interpolation: `spark.sql("SELECT * FROM {df}", df=df)`.

## Dataproc 2.x (Spark 3.x) to Dataproc 3.0 (Spark 4.0)

### Core Spark / SQL
*   **ANSI SQL Default**: `spark.sql.ansi.enabled` is now `true` by default in Spark 4.0. This enforces stricter SQL semantics (e.g., division by zero or invalid type casts will throw runtime exceptions instead of returning `NULL`). Set `spark.sql.ansi.enabled` to `false` to revert to legacy behavior.
*   **Table Provider**: `CREATE TABLE` without a `USING` clause now defaults to the value defined in `spark.sql.sources.default` instead of Hive.

### PySpark Specific
*   **Python Requirement**: Minimum Python version required is 3.9 in Spark 4.0. Support for older Python versions is dropped.
