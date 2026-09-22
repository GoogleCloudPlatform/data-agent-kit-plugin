# Spark Pre-Submission Refactoring Guide & Protocol

This guide outlines the mandatory pre-submission verification protocol to follow
before executing Spark jobs, Dataproc batches, or exporting production code.

--------------------------------------------------------------------------------

## 1. Pre-Submission Refactoring Protocol

When the user requests to submit a job, run a batch on Dataproc, export code, or
deploy a pipeline to production, the agent **MUST** perform static verification
before calling any submission tool.

### Verification Checklist

-   [ ] **No Action Amplification:** Check for terminal actions (`.collect()`,
    `.count()`, `.take()`, `.first()`, `.show()`) inside loops.
-   [ ] **No Lineage Explosion:** Check for iterative transformation chaining
    (`.union()`, `.withColumn()`) inside loops.
-   [ ] **No Unbounded Driver Transfers:** Check for unbounded `.toPandas()` or
    `.collect()` without `.limit(n)` or `.sample()`.
-   [ ] **No Inefficient UDFs:** Check for Python row-by-row standard `@udf`
    where native `pyspark.sql.functions` or `@pandas_udf` could be used.
-   [ ] **Optimal Partition Layout:** Check for `.repartition()` reducing
    partitions where `.coalesce()` should be used.
-   [ ] **Prune Exploratory Calls:** Remove or comment out debugging statements
    (`.show()`, `.printSchema()`, `.count()`, `display()`) that generate
    unnecessary stages.

--------------------------------------------------------------------------------

## 2. How to Apply the Checklist

There is no automated checker for this skill. Work through the checklist by
reading the code:

1.  Open the script or notebook and read it end to end. For notebooks, review
    every code cell — an anti-pattern in cell 3 still costs you even if cell 12
    looks fine.
2.  For each checklist item above, record the **file and line number** of any
    match, so the finding is actionable rather than abstract.
3.  Look especially at control flow. The same `.collect()` is cheap once and
    ruinous inside a `for` loop or a list comprehension, so note the nesting
    context, not just the call.
4.  See `pyspark_anti_patterns.md` for the detailed rationale and the
    recommended rewrite for each pattern.

--------------------------------------------------------------------------------

## 3. Mandatory User Confirmation Protocol

If any refactoring or optimization is identified:

1.  **DO NOT submit the job immediately.**
2.  Halt execution and list the concrete refactoring action items.
3.  Request confirmation from the user using the following template:

```markdown
> **Proposed Refactoring Action Items:**
> - [List specific refactoring requirements, e.g., removing intermediate checks, converting UDF to native expression, replacing repartition with coalesce]
>
> **Action Item Confirmation:** Before submitting this job, would you like me to apply the refactoring action items listed above to optimize performance?
```

4.  Only proceed with modifying the code and submitting the job in a subsequent
    turn after explicit user approval.
