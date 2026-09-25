# Spark Optimizations

## Broadcast Joins

When performing a standard join between a large fact table and a tiny dimension
table (lookup table), you MUST use a broadcast hint
`pyspark.sql.functions.broadcast()`. Without it, Spark may perform a heavy
shuffle operation and lead to performance issues or out-of-memory errors.

## Protecting Driver Memory

You MUST NOT call `.toPandas()` or `.collect()` directly on full or
un-aggregated PySpark DataFrames on the driver process. Always perform
cluster-side aggregations (`groupBy().agg()`) or data reduction (`limit()`,
`sample()`) to reduce dataset size before converting to Pandas or using Pyspark
Native libraries for plotting, display, or modeling.

## Iterative Action Amplification

Do not invoke terminal actions (`.collect()`, `.count()`, `.take()`, `.first()`,
`.head()`, `.show()`) inside Python loops (`for`, `while`) or list
comprehensions. Each call breaks lazy evaluation and submits a separate physical
Spark job, incurring $N$ rounds of cluster coordination and scheduling latency.

```python
# BAD: Triggers a separate physical Spark job for every loop iteration
results = []
for category_id in categories:
  filtered_df = df.filter(df.category == category_id)
  total = filtered_df.count()  # Terminal action inside loop
  results.append((category_id, total))

# GOOD: Single optimized Catalyst execution plan
import pyspark.sql.functions as F

counts_df = (
    df.filter(F.col("category").isin(categories))
    .groupBy("category")
    .agg(F.count("*").alias("total"))
)
counts_df.write.mode("overwrite").parquet("gs://bucket/counts")
```

## Iterative Lineage Explosion

Do not sequentially chain `.union()`, `.unionByName()`, or `.withColumn()`
inside a loop. Each iteration wraps the DataFrame in a new Catalyst logical plan
node, and a deep enough AST makes the optimizer raise
`java.lang.StackOverflowError` during planning, before any task reaches an
executor.

```python
# BAD: Deep Catalyst AST lineage explosion
df = initial_df
for file_path in file_list:
  next_df = spark.read.parquet(file_path)
  df = df.union(next_df)  # Exponentially deep plan tree

# GOOD: Read all paths simultaneously
combined_df = spark.read.parquet(*file_list)

# GOOD: Or reduce with unionByName in a single flat reduction
from functools import reduce
from pyspark.sql import DataFrame

dfs = [spark.read.parquet(p) for p in file_list]
combined_df = reduce(DataFrame.unionByName, dfs)
```

For iterating column transformations, use a single pass projection with
`.withColumns()` (Spark 3.3+) or `.select()`:

```python
# GOOD: Single pass column projection
columns_to_transform = {
    col: F.col(col).cast("double") for col in numeric_columns
}
df = df.withColumns(columns_to_transform)
```

## Standard Python UDFs vs. Native / Vectorized Arrow UDFs

Row-by-row Python `@udf` functions break Project Tungsten code generation and
force every row to be serialized from JVM memory into a Python worker subprocess
and back.

```python
# BAD: Row-by-row JVM <-> Python SerDe serialization bottleneck
from pyspark.sql.functions import udf
from pyspark.sql.types import DoubleType


@udf(returnType=DoubleType())
def convert_currency(amount, rate):
  return amount * rate if amount else None


df = df.withColumn("converted", convert_currency("amount", "rate"))
```

1.  **First priority:** use native Spark SQL functions.

    ```python
    # BEST: Native Catalyst expression
    import pyspark.sql.functions as F

    df = df.withColumn("converted", F.col("amount") * F.col("rate"))
    ```

2.  **Second priority (if custom logic is genuinely required):** use a
    vectorized Arrow / Pandas UDF.

    ```python
    # BETTER: Vectorized Apache Arrow batch execution
    import pandas as pd
    from pyspark.sql.functions import pandas_udf

    @pandas_udf("double")
    def vectorized_custom_calc(s: pd.Series) -> pd.Series:
      return s.apply(complex_library_func)

    df = df.withColumn("result", vectorized_custom_calc("features"))
    ```

**RDD-level mapping is the same anti-pattern.** `.rdd.map()`,
`.rdd.mapPartitions()` and `.rdd.flatMap()` drop out of the DataFrame API
entirely, so Catalyst cannot optimize the plan and Tungsten cannot generate code
for it, while Spark still pays the full per-row serialization cost.

```python
# BAD: leaves the optimizer behind
result = df.rdd.map(lambda row: (row.id, row.amount * 1.2)).toDF()

# BETTER: stays in the DataFrame API
result = df.select("id", (F.col("amount") * 1.2).alias("amount"))
```

Registering a Python function through `spark.udf.register("name", fn)` for use
in Spark SQL has the identical cost — prefer a native SQL expression.

## Unbounded Stateful Collections on Skewed Keys

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

## Shuffle Minimization: Coalesce vs. Repartition

Do not use `.repartition(n)` indiscriminately to reduce the number of output
partitions before writing. It forces a full hash partition exchange across all
executors over the network, writing shuffle files to disk. If the goal is simply
to reduce partition count (e.g., to prevent small-file syndrome), that shuffle
is wasted I/O and CPU.

```python
# BAD: Triggers a full cluster-wide network shuffle
df_reduced = df.repartition(10)

# GOOD: Combines existing local partitions without network shuffling
df_reduced = df.coalesce(10)
```

> **When is `repartition()` appropriate?** 1. Increasing partition count (e.g.
> from 2 partitions up to 200 to scale across worker cores). 2. Partitioning by
> specific columns to alleviate data skew (`df.repartition("region_id")`).

## Lingering Exploratory Calls in Production Jobs

Development-time inspection calls (`.show()`, `.count()`, `.printSchema()`,
`display()`) are legitimate while debugging, but each one triggers a separate
physical job that re-executes the upstream plan unless the DataFrame is cached.
The cost is invisible on small interactive data and recurs on every scheduled
production run, so remove them before submission.

```python
# BAD: each call forces an extra Spark job on every production run
df.printSchema()
df.show(10)
print(f"rows: {df.count()}")
df.write.mode("overwrite").parquet("gs://bucket/out")

# GOOD: a single action — the write itself
df.write.mode("overwrite").parquet("gs://bucket/out")
```
