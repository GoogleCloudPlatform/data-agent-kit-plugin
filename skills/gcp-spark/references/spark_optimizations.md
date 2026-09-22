# Spark Optimizations

All Spark-based data processing jobs (including PySpark, Spark SQL, and Spark
Scala/Java applications) on Dataproc Serverless and Dataproc clusters must be
optimized for execution scalability, partition efficiency, and memory safety.

This reference defines the mandatory optimization directives. See also:

-   `references/pyspark_anti_patterns.md` — detailed anti-pattern catalog with
    root causes and recommended rewrites.
-   `references/spark_refactoring_guide.md` — the pre-submission verification
    checklist and user confirmation protocol.

--------------------------------------------------------------------------------

## Core Execution Directives

### 1. No Iterative Action Amplification

Never execute terminal actions (such as `.collect()`, `.count()`, `.take()`,
`.first()`, `.head()`, or `.show()`) inside a loop or iterative flow.
Consolidate operations to perform compute transformations and run a single,
vectorized aggregation action on the driver.

*   **Rationale:** Triggering terminal actions inside loops breaks execution
    lazy-evaluation. It forces the engine to run distinct, unoptimized physical
    jobs per iteration, causing CPU-congestive JVM fallbacks and cluster network
    overhead.
*   **Reference:** See
    `references/pyspark_anti_patterns.md#1-iterative-action-amplification`.

### 2. No Iterative Lineage Explosion

Never repeatedly chain transformations (such as `.union()`, `.unionByName()`, or
`.withColumn()`) inside iterative structures. Collect DataFrame references into
collections and apply flat reduction operations in a single query-planning pass
(e.g., `functools.reduce(DataFrame.unionByName, dfs)`).

*   **Rationale:** Linear or exponential scaling of transformations inside loops
    creates an extremely deep AST lineage tree, throwing
    `java.lang.StackOverflowError` in the Catalyst Query Planner before
    execution even starts.
*   **Reference:** See
    `references/pyspark_anti_patterns.md#2-iterative-lineage-explosion`.

### 3. Prioritize Native Functions

Prioritize native engine expressions and SQL functions (`pyspark.sql.functions`)
over custom UDFs (user-defined functions) or RDD-level mapping. If custom logic
is unavoidable and cannot be expressed natively, check if it can be rewritten
using vectorized, arrow-optimized UDFs (such as `@pandas_udf`) to minimize
serialization fallbacks.

*   **Rationale:** Custom runtime UDFs break compiler vectorization and Tungsten
    engine optimization, requiring severe network serialization overhead between
    the JVM host and the worker Python process. Vectorized Arrow/Pandas UDFs
    batch transfers in columnar format to mitigate serialization penalties.
*   **Reference:** See
    `references/pyspark_anti_patterns.md#4-standard-python-udfs-vs-native--vectorized-arrow-udfs`.

### 4. Bounded Driver Operations

Never pull unbounded datasets into the driver node process (e.g., full collected
memory states or conversions to local structures like `.toPandas()` or
`.collect()`). Enforce row bounds (`.limit(n)`) or use distributed writing
handlers directly on executor workers to GCS or BigQuery.

*   **Rationale:** Extracting unbounded datasets to the driver process triggers
    Java OutOfMemory (`java.lang.OutOfMemoryError`) or container termination
    (Exit Code 137). Unbounded stateful collections on skewed keys similarly
    crash worker nodes.
*   **Reference:** See
    `references/pyspark_anti_patterns.md#3-unbounded-driver-operations`.

### 5. Minimized Data Shuffling & Partition Optimization

When reducing partition counts of target datasets, combine adjacent partitions
locally on executors using `.coalesce(n)` without triggering a global network
shuffle. Avoid hash-based layout `.repartition(n)` unless explicitly needed to
increase partitions or balance severe data skew. Use `broadcast()` hints for
joins between large tables and small lookup tables.

*   **Rationale:** Repartitioning forces complete cluster-wide data shuffles,
    creating heavy disk spill and I/O bottlenecks. Local partition coalescence
    achieves target density without shuffling network workloads.
*   **Reference:** See
    `references/pyspark_anti_patterns.md#5-shuffle-minimization-coalesce-vs-repartition`
    and `references/pyspark_anti_patterns.md#6-broadcast-joins`.

--------------------------------------------------------------------------------

## Pre-Submission User Confirmation for Refactoring

**Mandatory Trigger:** When the user requests to submit a job, run a batch,
export code, or deploy to production, the agent MUST perform this verification
step before calling any Spark job/batch submission command (such as `gcloud
dataproc jobs submit pyspark` or Dataproc batch create).

1.  **Interactive vs. Production:** Intermediate checks (e.g., `.show()`,
    `.count()`, `.printSchema()`, `display()`) are permitted during
    development/debugging, but **MUST** be removed or commented out for
    production to avoid redundant computation stages.
2.  **Anti-Pattern Review:** Read the candidate file and check it against every
    item in `references/pyspark_anti_patterns.md`. Do not skim: open the file,
    walk the checklist in `references/spark_refactoring_guide.md`, and note the
    specific line numbers for each finding so the user can act on them.

    Pay particular attention to patterns that are easy to miss by eye:

    -   Driver-pulling actions (`.collect()`, `.toPandas()`) without a preceding
        `.limit()` or `.sample()` — and especially any of these **inside a loop
        or comprehension**, where the cost is multiplied per iteration.
    -   Row-at-a-time Python UDFs (`@udf`, `spark.udf.register`, `.rdd.map`)
        where a native `pyspark.sql.functions` expression or an Arrow-based
        `@pandas_udf` would avoid serialization overhead.
    -   `.repartition()` used to *reduce* partition count where `.coalesce()`
        avoids a full shuffle.
    -   Unbounded stateful aggregations (`collect_list`, `collect_set`) on
        potentially skewed keys.
    -   Lingering exploratory calls (`.show()`, `.count()`, `.printSchema()`,
        `display()`) that each force an extra job.

    > **Scope:** this review applies equally to PySpark, Spark SQL, and
    > Scala/Java jobs. There is no automated checker, so a job you did not read
    > is a job you did not verify — never report a clean result for code you
    > have not actually inspected.
3.  **Action on Optimization/Refactoring:** If any refactoring or optimization
    is identified (e.g., removing intermediate checks, optimizing shuffles,
    addressing UDFs, or mitigating OOM risks):

    *   **DO NOT submit the job immediately.**
    *   Halt execution and list the concrete refactoring action items.
    *   Request confirmation at the end of your response using the following
        template:

> **Proposed Refactoring Action Items:** - [List specific refactoring
> requirements, e.g., removing intermediate checks, optimizing physical layout,
> converting UDFs]
>
> **Action Item Confirmation:** Before submitting this job, would you like me to
> apply the refactoring action items listed above to optimize performance?

4.  **Only proceed with submission in a subsequent turn after explicit user
    approval.**
