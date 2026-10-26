# Declarative Data Pipeline YAML Format (MVP, pinned)

This file pins the `pipeline.yaml` shape for the MVP of declarative data
pipelines on the orchestration service. Write ONLY the keys listed here.
`scripts/validate_pipeline_yaml.py` enforces this file.

> [!WARNING]
> This format is a pre-release design and can change. The service API does not
> yet accept every key listed here (for example `triggers`, `execution_mode`,
> and `parameters`), and API field names can differ from these YAML keys (for
> example `name`, `dbt.source`, `sdp.source`). Treat this file as the source of
> truth for authoring until the service ships a validator.

## File location and naming

-   path: `pipelines/<pipeline_name>.pipeline.yaml`, relative to the repository
    root (the directory that contains `deployment.yaml`).
-   pipeline_name: `lower_snake_case`, for example `customer_orders`.
-   relative paths inside the file (`dbt.source`, `sdp.source`): resolved from
    the repository root, NOT from the `pipelines/` directory.

## Top-level keys

### intent

-   type: mapping
-   required: yes
-   allowed_children: `goal`

### intent.goal

-   type: string (use a YAML folded block `>-` for multi-line text)
-   required: yes, non-empty
-   meaning: the refined business goal the user approved, in natural language.
-   service_behavior: stored and returned unchanged. The service never reads or
    executes it. Triggers, data models, and code are the plan.
-   content: sources, target, cross-source precedence and cutover dates, dedup
    keys, schedule or deadline, and any lifecycle rule (for example "drop the
    ERP branch after migration"). See `references/intent-refinement.md`.

### execution_mode

-   type: enum string
-   required: yes
-   allowed_values: `TRIGGERED`
-   note: `CONTINUOUS` is out of scope for the MVP.

### triggers

-   type: list
-   required: yes for scheduled pipelines; MAY be omitted when the pipeline is
    only started manually or from an orchestration pipeline.
-   item_shape: `inline_trigger.schedule`

### triggers[].inline_trigger.schedule.interval

-   type: string
-   required: yes
-   format: 5-field cron (`minute hour day-of-month month day-of-week`), for
    example `"0 6 * * *"` for daily at 06:00.

### triggers[].inline_trigger.schedule.time_zone

-   type: string (IANA time zone)
-   required: yes
-   default_to_write: `"UTC"`, unless the user states another time zone.

### parameters

-   type: list
-   required: no (proposed field)
-   item_keys: `name` (`lower_snake_case`), `type` (`STRING`, `INT64`,
    `FLOAT64`, or `BOOL`), `default` (scalar or a `{{ variable }}` reference).

### data_models

-   type: list
-   required: yes, at least one item
-   item_keys: `name` plus exactly one of `dbt` or `sdp`

### data_models[].name

-   type: string, `lower_snake_case`, unique within the file
-   convention: suffix with the engine, for example `customer_orders_dbt`.

### data_models[].dbt

-   source: path to the directory that contains `dbt_project.yml`, for example
    `./dbt_customer_orders`. Required.
-   select: list of dbt node selectors, for example `["tag:customer_orders"]`
    or `["+fct_customer_orders"]`. Optional; omit to run the whole project.

### data_models[].sdp

-   source: path to the Spark Declarative Pipelines project directory that
    contains `spark-pipeline.yml` (or `spark-pipeline.yaml`), for example
    `./spark_sdp`. Required.

## Variables from deployment.yaml

-   syntax: `{{ variable_name }}` inside string values.
-   resolution: substituted per environment from
    `environments.<env>.variables` in the repository-root `deployment.yaml`.
    `project` and `region` from the environment are also available.
-   rule: every referenced variable MUST exist in every environment in
    `deployment.yaml`. Do NOT hardcode project IDs or dataset names that differ
    per environment.
-   note: some design text writes `${var}`. Use `{{ var }}`; it matches the
    design examples and `deployment.yaml` usage.

## Out of scope for the MVP (MUST NOT write)

-   `outcomes`, `quality_gates`
-   `continuous` block, `execution_mode: CONTINUOUS`
-   `data_models[].ingest`, `data_models[].bigquery_sql`
-   event triggers (only `schedule` triggers)
-   `intent.authoring`, `intent.prompt`, or any other `intent` child

Record freshness, quality, and lifecycle requirements in `intent.goal` text
instead, and implement checks as dbt tests or SDP expectations in the code.

## Minimal valid example

```yaml
intent:
  goal: >-
    Build the daily Gold table customer_orders from ERP orders_raw.
execution_mode: TRIGGERED
triggers:
  - inline_trigger:
      schedule:
        interval: "0 6 * * *"
        time_zone: "UTC"
data_models:
  - name: customer_orders_dbt
    dbt:
      source: ./dbt_customer_orders
      select: ["tag:customer_orders"]
```

A full example is in `references/example_customer_orders.pipeline.yaml`.
