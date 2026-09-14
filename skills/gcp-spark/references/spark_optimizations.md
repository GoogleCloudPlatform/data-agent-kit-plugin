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
