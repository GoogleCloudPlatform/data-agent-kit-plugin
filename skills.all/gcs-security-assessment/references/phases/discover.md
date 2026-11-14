# Phase 1: Discover Scope and Telemetry

This phase focuses on defining the scope of the assessment and gathering all
necessary telemetry signals.

## Steps

1.  **Confirm Scope**: Confirm the target scope with the user (project ID,
    location, dataset name, specific buckets, or all buckets). If the user does
    not provide any required fields for the scripts below, **STOP and ASK the
    user to provide any missing required fields for each script below. DO NOT
    attempt to dynamically determine any input like project ID**. If the user
    does not provide a Storage Insights linked dataset name or ID, you MUST list
    available datasets first. **List Dataset**: `python3
    scripts/list_datasets.py --project_id <PROJECT_ID> [--location <LOCATION>]`.
    The script will automatically list all datasets if the user does not specify
    a location. **IMPORTANT** ONLY show the first 10 datasets in the response.
    If there are more than 10 datasets, there should be a note for the user to
    ask to see more datasets or specify a specific location. DO NOT assume
    location unless directly specified by the user. **If more than one dataset
    is returned, you MUST STOP and ask the user to choose one before proceeding
    — never auto-select a dataset or proceed with an assumed one.** When the
    available signals make one dataset a clearly reasonable default, also
    recommend it as a suggested default and give a one-line reason. Reason only
    from the signals `list_datasets.py` returns — the dataset name/ID, its
    location, and its `description` — for example a name/ID indicating a
    production (vs. test/dev) export, broader coverage such as an "all buckets"
    config, or a description or location matching the user's stated intent (e.g.
    "I'd suggest `<name>` — it looks like the prod, all-buckets export"). Only
    recommend when you are genuinely high-confidence; if the datasets are
    ambiguous or look similar, present them neutrally and ask the user to pick
    without steering. The user always makes the final choice. You MUST ONLY use
    Storage Insights to answer questions about buckets.**

    Each dataset entry includes a `scope` field: `projects`, `folders`, or
    `organization`. An entry whose config ingests resources beyond the target
    project — scope `organization` or `folders`, or a project-scoped config
    whose source projects include others or omit the target project entirely —
    also carries a `warning` field. You MUST surface a selected dataset's
    `warning` to the user: relay it along with the note that the telemetry
    scripts automatically restrict bucket and object results to buckets owned by
    the target project. If the user explicitly chose the dataset, do NOT stop to
    ask for re-confirmation — proceed with the assessment and repeat the warning
    as a prominent notice in the final report. When instead you are listing
    datasets for the user to choose from, include the `warning` against the
    affected entries.

2.  **Run Preflight Check**: Validate that the calling identity has the
    prerequisites for the assessment **before** invoking any telemetry script.
    Run:

    `python3 scripts/preflight_permissions.py --project_id <PROJECT_ID>
    --dataset_name <DATASET_NAME>`

    The preflight runs one **required** check and two **recommended** checks:
    (a) `adc` — working application-default credentials (required); (b)
    `storage_insights_enabled` — the Storage Intelligence API is enabled
    (recommended); (c) `bigquery_dataset_access` — the linked dataset is
    queryable (recommended). The BQ check surfaces the "no SI dataset
    configured" or "wrong dataset name" case (as a 404). Storage Intelligence is
    **not** a hard gate: when it is unavailable the assessment degrades to a
    project-level report rather than stopping.

    Parse the JSON output. The `analysis_scope` field tells you which mode to
    run:

    -   **STOP only on a required failure**: If `ready_to_proceed` is `false`
        (i.e. `analysis_scope: "none"` — the `adc` check is `missing`), you
        **MUST IMMEDIATELY STOP** and output your final response. **DO NOT**
        invoke any telemetry-gathering scripts (`fetch_bucket_telemetry.py`,
        `fetch_object_telemetry.py`, or `evaluate_project_security_posture.py`).
        Report the `adc` check's `impact` and `fix` verbatim and wait for the
        user to re-authenticate before re-running preflight.
    -   If `analysis_scope` is `"full"` (SI enabled and dataset queryable),
        proceed with the full assessment: run all telemetry scripts and all
        phases.
    -   If `analysis_scope` is `"project_only"` (a recommended check is
        `missing` — SI not enabled, or no linked dataset), **DO NOT bail out**.
        Run a project-level assessment:
        *   In Step 3 below, run **only**
            `evaluate_project_security_posture.py`. Do **not** run
            `fetch_bucket_telemetry.py` or `fetch_object_telemetry.py`.
        *   Surface the failing recommended check's `fix` once, framed as
            unlocking the full assessment: if `storage_insights_enabled` is
            missing, relay `gcloud services enable
            storageinsights.googleapis.com --project <PROJECT_ID>`; if
            `bigquery_dataset_access` is missing with a 404, relay its `fix` to
            run `list_datasets.py` or create a dataset config.
        *   In later phases, mark bucket- and object-level sections as
            "Unavailable — requires Storage Intelligence" (see the
            **Project-only mode** note in `output.md`).

3.  **Gather Telemetry**: Run the telemetry scripts that match your
    `analysis_scope` (from Step 2). Use your shell execution tool (e.g.,
    `run_shell_command` or equivalent) to execute them. The scripts are split
    into two groups — which you run is gated on `analysis_scope`:

    ```
    # ALWAYS RUN -- both `full` and `project_only` modes:
    *   **Project Telemetry**: `python3
        scripts/evaluate_project_security_posture.py
        --project_id <PROJECT_ID>`

    # FULL MODE ONLY -- run these two ONLY when `analysis_scope` is `full`.
    # If `analysis_scope` is `project_only`, SKIP both: they query Storage
    # Insights and will fail or return empty without it. Running them is a
    # constraint violation, not a fallback.
    *   **Bucket Telemetry**: `python3 scripts/fetch_bucket_telemetry.py
        --project_id <PROJECT_ID> --dataset_name <DATASET_NAME>
        [--bucket_names <BUCKET1,BUCKET2>]`
    *   **Object Telemetry**: `python3 scripts/fetch_object_telemetry.py
        --project_id <PROJECT_ID> --dataset_name <DATASET_NAME>
        [--bucket_names <BUCKET1,BUCKET2>]`

    *   **Data Consumption**: Capture the standard output from these
        scripts, which is a JSON array. Parse the JSON to extract security
        signals. For example, map `ubla_enabled` to the UBLA check, and
        `public_objects` count to public access checks for Phase 2
        (Classification) and Phase 3 (Baseline Security Eval). - See
        `references/telemetry_signals.md` for the complete list of signals
        and their sources.
    ```

4.  **Handle Gaps and Errors**: If the script execution fails or any signal
    cannot be gathered, handle it explicitly:

    ```
    -   **Authentication Errors**: If the error indicates missing
        credentials, instruct the user to log in using
        `gcloud auth application-default login` and `gcloud auth login`.
    -   **API Not Enabled**: If BigQuery is not enabled, instruct the user
        to enable it by providing the exact command: `gcloud services enable
        bigquery.googleapis.com --project <PROJECT_ID>`.
    -   **Permission Errors**: If a `PermissionDenied` error occurs (e.g.,
        lacking BigQuery Viewer/Data Viewer roles), explain the missing
        permissions to the user and gracefully fall back to alternative
        signaling if available or note the gap.
    -   **Missing Dataset**: If the BigQuery dataset doesn't exist, inform
        the user that Storage Insights export needs to be configured for
        the target dataset.
    -   Do NOT assume a value. Log the gap explicitly.
    ```

> [!CAUTION]
> You MUST have telemetry before proceeding. Do not guess at
> configurations. If a critical signal is unavailable, inform the user and
> explain what it would have told you.
