# Spark Pre-Submission Refactoring Guide & Protocol

This guide defines the mandatory pre-submission verification protocol to follow
before executing Spark jobs, Dataproc batches, or exporting production code.

--------------------------------------------------------------------------------

## 1. When This Protocol Applies

When the user requests to submit a job, run a batch on Dataproc, export code, or
deploy a pipeline to production, the agent **MUST** perform static verification
before calling any submission tool (such as `gcloud dataproc jobs submit
pyspark` or Dataproc batch create).

This applies equally to PySpark, Spark SQL, and Scala/Java jobs.

--------------------------------------------------------------------------------

## 2. How to Apply the Review

There is no automated checker. Work through the code by reading it:

1.  Open the script or notebook and read it end to end. For notebooks, review
    every code cell — an anti-pattern in cell 3 still costs you even if cell 12
    looks fine.
2.  Check the code against every section of `spark_optimizations.md`, and record
    the **file and line number** of each match so the finding is actionable
    rather than abstract.
3.  Look especially at control flow. The same `.collect()` is cheap once and
    ruinous inside a `for` loop or a list comprehension, so note the nesting
    context, not just the call.

> A job you did not read is a job you did not verify — never report a clean
> result for code you have not actually inspected.

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

--------------------------------------------------------------------------------

## 4. Reference

-   `spark_optimizations.md` — the catalog of Spark anti-patterns: what to look
    for, why it is slow or unsafe, and how to rewrite it.
