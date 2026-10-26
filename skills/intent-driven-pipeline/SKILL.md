---
name: intent-driven-pipeline
description: >-
  Turns a natural-language data pipeline request into a declarative data
  pipeline for the Orchestration service: a refined, user-approved
  `intent.goal`, dbt or Spark Declarative Pipelines (SDP) code, and a
  `pipelines/PIPELINE_NAME.pipeline.yaml` (`execution_mode: TRIGGERED`, cron
  `triggers`, `data_models`). Use when the user describes a pipeline outcome in
  business terms (for example "populate the gold orders table from ERP and
  storefront; storefront is the source of truth from July"), asks to create or
  edit a `.pipeline.yaml`, changes a declarative pipeline's intent or schedule,
  or needs a declarative pipeline fixed after a `dbt` failure or source schema
  drift. Refines intent one question at a time, delegates code generation, and
  validates the YAML and `dbt compile`. Does not deploy. Do NOT use for Cloud
  Composer / Airflow orchestration pipelines or for creating `deployment.yaml`,
  and do NOT use for standalone dbt model edits that have no pipeline YAML.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Intent-Driven Declarative Data Pipelines

Build and maintain a declarative data pipeline from what the user wants, not
from how to build it. Every pipeline has three parts that you keep in sync:

-   intent: `intent.goal` in the pipeline YAML. The business rules, in plain
    language, approved by the user.
-   plan: `triggers` and `data_models` in the pipeline YAML.
-   code: the dbt project or SDP project that `data_models` points to.

The intent is the contract. Code and schedule follow from it. When a rule
changes, change the intent first.

## Reference Routing

You MUST read the reference before the step that needs it. Do NOT guess file
names.

-   `references/pipeline-yaml-format.md`: the pinned YAML keys and values.
    Read before Step 4.
-   `references/intent-refinement.md`: slots, question order, and goal style.
    Read before Step 2.
-   `references/example_customer_orders.pipeline.yaml`: a complete example.
    Read before Step 4.
-   `scripts/validate_pipeline_yaml.py`: deterministic YAML validator. Run it
    with `--help` to learn its interface. Do NOT read its source.

## Hard Rules

-   You MUST get user approval of the `intent.goal` text BEFORE generating any
    code.
-   You MUST ask exactly ONE question per turn during refinement.
-   You MUST delegate dbt code to `@skill:dbt-bigquery` and SDP / PySpark code
    to `@skill:gcp-spark`, and follow their conventions. Do NOT hand-write SQL
    outside those conventions.
-   You MUST NOT create `deployment.yaml`. If it is missing, hand off to
    `@skill:gcp-pipeline-orchestration` (Step 0).
-   You MUST NOT write keys that are out of scope in
    `references/pipeline-yaml-format.md` (`outcomes`, `quality_gates`,
    `continuous`, `ingest`, `bigquery_sql`).
-   You MUST NOT deploy the pipeline to the orchestration service, and MUST NOT run
    `dbt run`, `dbt build`, or any job that writes to tables without explicit
    user confirmation.
-   You MUST NOT drop, truncate, or delete tables or datasets.
-   Show every file change as an inline `diff` block.

> [!IMPORTANT]
> Priority over other skills: this skill owns the pipeline YAML and the
> `intent.goal`. `@skill:dbt-bigquery` and `@skill:gcp-spark` own the code.
> `@skill:gcp-pipeline-orchestration` owns `deployment.yaml` and Airflow
> orchestration pipeline files. Do NOT write Airflow orchestration YAML for a
> declarative data pipeline.

## Workflow

Route the request first:

-   new pipeline: Steps 0 to 6.
-   change to an existing pipeline (new rule, new schedule, new source):
    Step 0, then "Day-2 Changes".
-   failing pipeline or schema drift: Step 0, then "Failure and Self-Heal".

### Step 0: Environment Check

Run these checks and report the results in one short list. Do NOT ask the user
for values you can discover.

1.  Project and region: `gcloud config get-value project`; region from
    `deployment.yaml` if present. Pass: project ID is non-empty.
2.  Repository root: the directory that holds `deployment.yaml`, otherwise the
    current working directory.
3.  `deployment.yaml` at the repository root. Record the environment names and
    every key under `environments.<env>.variables`.
4.  Existing code: directories that contain `dbt_project.yml` (dbt) or
    `spark-pipeline.yml` / `spark-pipeline.yaml` (SDP).
5.  Existing pipeline files: `pipelines/*.pipeline.yaml`.
6.  Tools: `dbt --version` (when dbt is used) and `python3 -c "import yaml"`.
    If a tool is missing, follow `@skill:dbt-bigquery` setup guidance.

Decision:

```
if deployment.yaml is missing:
    tell the user: "This repository has no deployment.yaml. Declarative
      pipelines reference per-environment variables from it."
    hand off to @skill:gcp-pipeline-orchestration to initialize it
      (that skill runs its own init command and asks for names).
    You MAY continue Steps 1-3 (discovery, intent, code) meanwhile, but
      MUST NOT write {{ variable }} references until deployment.yaml exists.
    STOP before Step 4 until deployment.yaml exists.
else:
    continue.
```

### Step 1: Discover Sources and Target

1.  Use `@skill:discovering-gcp-data-assets` to find the source tables the
    request mentions and the target dataset. Prefer names and datasets from
    `deployment.yaml` variables.
2.  For each source: get the schema, row count, and a sample of at most 20
    rows (`LIMIT 20`, selected columns only).
3.  Measure what the questions in Step 2 need: candidate match-key overlap
    between sources, null rates of keys, duplicate counts, min/max dates.

Pass: every source in the request resolves to one table with a known schema.
If a source is ambiguous, ask the user to pick (one question).

### Step 2: Refine the Intent

Follow `references/intent-refinement.md`.

1.  Draft the goal from the request and the Step 1 evidence.
2.  Ask ONE question per turn, in the reference's order, each with a
    recommended answer grounded in the sampled data.
3.  After each answer, show the updated goal as a `diff`.
4.  Show the final goal and ask: "Approve this goal?"

Pass: the user explicitly approves the goal text. Do NOT continue without it.

### Step 3: Generate Code

Ask the user which engine to use only when it is not already determined:

-   existing dbt project, BigQuery-only sources, SQL transformations: dbt.
-   existing SDP project, files in Cloud Storage, or streaming-style logic:
    SDP.

Then:

-   dbt: delegate to `@skill:dbt-bigquery`. Pass it the approved goal and the
    Step 1 schemas. Require: a tag that matches the `select` you will write
    (for example `tag:customer_orders`), dbt tests for the goal's keys and
    dedup rule (`unique`, `not_null`), and model `description`s that cite the
    goal's rules. Target dataset comes from a `deployment.yaml` variable via
    dbt `vars` or profiles, never hardcoded per environment.
-   SDP: delegate to `@skill:gcp-spark`. The project MUST contain
    `spark-pipeline.yml` at its root.
-   Reuse the existing project when one exists. Add models; do NOT restructure
    unrelated models.

Pass: the code implements every rule in the approved goal. List each rule
with the file that implements it.

### Step 4: Write the Pipeline YAML

Read `references/pipeline-yaml-format.md` and
`references/example_customer_orders.pipeline.yaml`.

1.  Path: `pipelines/<pipeline_name>.pipeline.yaml` at the repository root.
2.  `intent.goal`: the approved text, verbatim.
3.  `execution_mode: TRIGGERED`.
4.  `triggers`: one `inline_trigger.schedule` whose cron meets the goal's
    deadline, `time_zone: "UTC"` unless the goal states another zone.
5.  `parameters`: only values the code reads (for example a cutover date);
    environment-specific defaults reference `deployment.yaml` variables, for
    example `default: "{{ gold_dataset }}"`.
6.  `data_models`: one entry per dbt or SDP project; `source` paths are
    relative to the repository root; dbt `select` matches the tags from
    Step 3.
7.  If `deployment.yaml` does not list the new file under
    `environments.<env>.pipelines`, show the user the `diff` that adds
    `- source: pipelines/<pipeline_name>.pipeline.yaml` and apply it only after
    approval.

### Step 5: Validate

Run all checks. Fix and re-run until every check passes, at most 3 attempts,
then report the remaining failure to the user.

1.  YAML format: `python3 <skill_dir>/scripts/validate_pipeline_yaml.py
    pipelines/<pipeline_name>.pipeline.yaml`. Pass: JSON `status` is `PASS`.
2.  dbt compile: `dbt compile --select <select>` from the dbt project
    directory. Pass: exit code 0.
3.  Dry run: run the compiled SQL of each new model with
    `bq query --dry_run --use_legacy_sql=false`. Pass: no error. If you lack
    permission, say so and continue.
4.  SDP: run the SDP dry run per `@skill:gcp-spark` when available. If not
    available, state that SDP was not validated.

### Step 6: Review and Hand-Off

Show:

1.  The approved goal.
2.  A list of created or changed files, each with an inline `diff`.
3.  Validation results from Step 5, one line per check.
4.  Assumptions you made.
5.  Next steps: the user reviews and commits; deployment to the Orchestration
    service is NOT available from this skill yet.

Ask for approval of the change set. Do NOT run `dbt run` or deploy.

## Day-2 Changes

Use when the user changes a business rule, a source, or a schedule, for
example "the ERP migration is complete" or "move the refresh to 04:00 UTC".

1.  Read the current `intent.goal` and the files `data_models` points to.
2.  Edit `intent.goal` FIRST. Show the `diff` and ask for approval.
3.  After approval, list what the new goal changes:
    -   code (for example drop the ERP branch and its source),
    -   `triggers` (new cron),
    -   `parameters`.
4.  Apply only those changes via the owning skill (Step 3), update the YAML
    (Step 4), and re-run Step 5.
5.  Finish with Step 6.

Schedule-only change: update the goal's deadline sentence and the cron. Do NOT
touch code.

## Failure and Self-Heal

Use when `dbt compile`, `dbt run`, a dry run, or a test fails, or when a source
schema changed (renamed, dropped, or retyped column).

1.  Collect evidence. Do NOT guess:
    -   the exact error text,
    -   the current schema of every source the failing model reads
        (`@skill:discovering-gcp-data-assets`),
    -   the column names and types the code expects.
2.  Diagnose: state the root cause in one or two sentences, citing the error
    and the schema difference.
3.  If the fix changes which column or source is canonical (for example
    `erp_ref` renamed to `erp_order_ref`, or a source dropped), ask the user to
    confirm the canonical source or column (one question).
4.  Propose a remediation plan: root cause, files to change, whether
    `intent.goal` changes, and how you will validate. Wait for approval.
5.  Patch the code via the owning skill. Update `intent.goal` only if a
    business rule changed; a pure rename does not change the goal unless the
    goal names the column.
6.  Re-run Step 5. Pass: every check passes.
7.  Finish with Step 6, including the root cause.

> [!CAUTION]
> Never fix a failure by dropping data, deleting rows, relaxing a test the goal
> requires, or removing a dedup rule. If the only fix needs one of these, stop
> and ask the user.
