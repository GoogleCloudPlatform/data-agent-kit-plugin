# PySpark Anti-Patterns & Optimization Catalog

This catalog details common Apache Spark and PySpark anti-patterns, their root
causes, and recommended high-performance remediations.

--------------------------------------------------------------------------------

## 1. Iterative Action Amplification

### Anti-Pattern

Invoking terminal actions (`.collect()`, `.count()`, `.take()`, `.first()`,
`.head()`, `.show()`) inside Python loops (`for`, `while`) or list
comprehensions.

```python
# BAD: Triggers a separate physical Spark job for every loop iteration
results = []
for category_id in categories:
  filtered_df = df.filter(df.category == category_id)
  total = filtered_df.count()  # Terminal action inside loop
  results.append((category_id, total))
```

### Why It Fails

-   Breaks Spark's lazy evaluation and Catalyst query optimizer.
-   Submits $N$ sequential Spark jobs over the network, incurring severe cluster
    coordination and scheduling latency.
-   Bogs down the driver and worker JVMs with repeated context switches.

### Optimized Alternative

Vectorize using native grouping or window functions to execute a single,
globally optimized DAG:

```python
# GOOD: Single optimized Catalyst execution plan
import pyspark.sql.functions as F

counts_df = (
    df.filter(F.col("category").isin(categories))
    .groupBy("category")
    .agg(F.count("*").alias("total"))
)
# Write or inspect once
counts_df.write.mode("overwrite").parquet("gs://bucket/counts")
```

--------------------------------------------------------------------------------

## 2. Iterative Lineage Explosion

### Anti-Pattern

Sequentially chaining transformations such as `.union()`, `.unionByName()`, or
`.withColumn()` within a loop.

```python
# BAD: Deep Catalyst AST lineage explosion
df = initial_df
for file_path in file_list:
  next_df = spark.read.parquet(file_path)
  df = df.union(next_df)  # Exponentially deep plan tree
```

### Why It Fails

-   Each iteration wraps the DataFrame in a new Catalyst logical plan node.
-   Chaining dozens or hundreds of transformations creates an extremely deep AST
    lineage tree.
-   When an action is finally executed, the Catalyst optimizer throws
    `java.lang.StackOverflowError` during query planning before any tasks run on
    executors.

### Optimized Alternative

Accumulate DataFrame references in a standard Python collection and apply a
single pass reduction:

```python
# GOOD: Flat union or wildcards
from functools import reduce
from pyspark.sql import DataFrame

# Option A: Read all paths simultaneously
combined_df = spark.read.parquet(*file_list)

# Option B: Reduce with unionByName in a flat reduction
dfs = [spark.read.parquet(p) for p in file_list]
combined_df = reduce(DataFrame.unionByName, dfs)
```

For iterating column transformations, use a single dictionary unpacking or list
comprehension with `.withColumns()` (Spark 3.3+) or `.select()`:

```python
# GOOD: Single pass column projection
columns_to_transform = {
    col: F.col(col).cast("double") for col in numeric_columns
}
df = df.withColumns(columns_to_transform)
```

--------------------------------------------------------------------------------

## 3. Unbounded Driver Operations

### Anti-Pattern

Pulling unbounded, full datasets into the driver node process using
`.toPandas()`, `.collect()`, or list conversions.

```python
# BAD: Pulls all cluster rows to the driver memory
pdf = df.toPandas()
df_rows = df.collect()
```

### Why It Fails

-   The Spark driver operates as a central coordinator with constrained heap
    memory (often 2GB to 8GB).
-   Serializing millions of rows across workers and sending them to the driver
    causes Java OutOfMemory (`java.lang.OutOfMemoryError: Java heap space`) or
    OS container OOM kills (Exit Code 137).

### Optimized Alternative

Always bound data inspection or write distributedly from executors:

```python
# GOOD: Explicitly bound rows if local inspection is required
pdf = df.limit(100).toPandas()

# GOOD: Distributed write directly to GCS or BigLake from executors
df.write.format("bigquery").option(
    "table", "project.dataset.table"
).mode("overwrite").save()
```

--------------------------------------------------------------------------------

## 4. Standard Python UDFs vs. Native / Vectorized Arrow UDFs

### Anti-Pattern

Using row-by-row Python `@udf` decorators or `pyspark.sql.functions.udf` for
operations that can be performed natively or with vectorized Arrow UDFs.

```python
# BAD: Row-by-row JVM <-> Python SerDe serialization bottleneck
from pyspark.sql.functions import udf
from pyspark.sql.types import DoubleType


@udf(returnType=DoubleType())
def convert_currency(amount, rate):
  return amount * rate if amount else None


df = df.withColumn("converted", convert_currency("amount", "rate"))
```

### Why It Fails

-   Breaks Project Tungsten code generation, memory management, and Catalyst
    optimizations.
-   Requires serializing every single row from JVM memory into a Python worker
    subprocess via Unix pipes, processing one row at a time, and serializing the
    output back to the JVM.

### Optimized Alternative

1.  **First Priority:** Use native Spark SQL functions:

    ```python
    # BEST: Native Catalyst expression
    import pyspark.sql.functions as F

    df = df.withColumn("converted", F.col("amount") * F.col("rate"))
    ```
2.  **Second Priority (if custom logic is required):** Use Vectorized Arrow /
    Pandas UDF (`@pandas_udf`):

    ```python
    # BETTER: Vectorized Apache Arrow batch execution
    import pandas as pd
    from pyspark.sql.functions import pandas_udf

    @pandas_udf("double")
    def vectorized_custom_calc(s: pd.Series) -> pd.Series:
      return s.apply(complex_library_func)

    df = df.withColumn("result", vectorized_custom_calc("features"))
    ```

-   **RDD-level mapping is the same anti-pattern.** `.rdd.map()`,
    `.rdd.mapPartitions()` and `.rdd.flatMap()` drop out of the DataFrame API
    entirely, so Catalyst cannot optimize the plan and Tungsten cannot generate
    code for it. Spark also pays the full JVM↔Python serialization cost per row,
    exactly as with a plain UDF.

    ```python
    # BAD: leaves the optimizer behind
    result = df.rdd.map(lambda row: (row.id, row.amount * 1.2)).toDF()

    # BETTER: stays in the DataFrame API
    result = df.select("id", (F.col("amount") * 1.2).alias("amount"))
    ```

-   Registering a Python function through `spark.udf.register("name", fn)` for
    use in Spark SQL has the identical cost — prefer a native SQL expression.

--------------------------------------------------------------------------------

## 4b. Unbounded Stateful Collections on Skewed Keys

`collect_list()` and `collect_set()` materialize *every* value for a key into a
single in-memory list on one executor. This is not a driver-side problem: it
kills the **worker** holding the hot key. On a skewed key (a default customer
ID, a null placeholder, a sentinel date) one group can hold orders of magnitude
more rows than the median, and the container is OOM-killed.

```python
# BAD: one hot key can hold tens of millions of values
df.groupBy("customer_id").agg(F.collect_list("event"))

# BETTER: aggregate to a bounded result
df.groupBy("customer_id").agg(
    F.count("event").alias("event_count"),
    F.max("event_ts").alias("last_event"),
)

# If the full list is genuinely required, bound it explicitly:
w = Window.partitionBy("customer_id").orderBy(F.col("event_ts").desc())
(
    df.withColumn("rn", F.row_number().over(w))
    .filter(F.col("rn") <= 100)
    .groupBy("customer_id")
    .agg(F.collect_list("event"))
)
```

The same applies to any conversion of distributed data into a local structure —
`.collect()`, `.toPandas()`, `.collectAsList()`, `.toLocalIterator()`, and the
Java-list equivalents in Scala/Java jobs.

--------------------------------------------------------------------------------

## 5. Shuffle Minimization: Coalesce vs. Repartition

### Anti-Pattern

Using `.repartition(n)` indiscriminately to reduce the number of output
partitions before writing.

```python
# BAD: Triggers a full cluster-wide network shuffle
df_reduced = df.repartition(10)
```

### Why It Fails

-   `.repartition()` forces a full hash partition exchange across all executors
    over the network, writing shuffle files to disk.
-   If the goal is simply to reduce partition count (e.g., to prevent small-file
    syndrome), a full shuffle is wasted I/O and CPU overhead.

### Optimized Alternative

Use `.coalesce(n)` when reducing partitions:

```python
# GOOD: Combines existing local partitions without network shuffling
df_reduced = df.coalesce(10)
```

> **When is `repartition()` appropriate?** 1. Increasing partition count (e.g.
> from 2 partitions up to 200 to scale across worker cores). 2. Partitioning by
> specific columns to alleviate data skew (`df.repartition("region_id")`).

--------------------------------------------------------------------------------

## 6. Broadcast Joins

### Anti-Pattern

Performing standard SortMerge joins between a massive fact table (e.g., 500GB)
and a small lookup or dimension table (e.g., 20MB).

```python
# BAD: SortMerge join causes massive network shuffle of both tables
joined_df = fact_df.join(dim_df, on="store_id", how="inner")
```

### Optimized Alternative

Use `broadcast()` hint on the small table:

```python
# GOOD: Broadcasts dimension table to all executors; zero shuffle for fact_df
import pyspark.sql.functions as F

joined_df = fact_df.join(F.broadcast(dim_df), on="store_id", how="inner")
```
