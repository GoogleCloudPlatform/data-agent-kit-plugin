# Compute Capacity Planning (Editions Migration & Rightsizing)

Guidelines for Org Admins and billing owners on evaluating On-Demand to Edition
migrations, as well as rightsizing active Edition reservations and commitments.

## Table of Contents

-   [Framing & Guardrails](#framing-guardrails) (Lines 24-42)
-   [1. Unified Slot Estimator Engine](#1-unified-slot-estimator-engine) (Lines
    44-62)
-   [2. On-Demand to Editions Migration](#2-on-demand-to-editions-migration)
    (Lines 64-101)
    -   [Slot Estimator Migration Deep Links](#slot-estimator-migration-deep-links)
        (Lines 70-84)
    -   [Navigation & Workload Profiling](#navigation-workload-profiling) (Lines
        86-101)
-   [3. Existing Edition Capacity Rightsizing](#3-existing-edition-capacity-rightsizing)
    (Lines 103-145)
    -   [Slot Estimator Rightsizing Deep Links](#slot-estimator-rightsizing-deep-links)
        (Lines 109-121)
    -   [Edition-Level Rightsizing Decision Playbook](#edition-level-rightsizing-decision-playbook)
        (Lines 123-145)

## Framing & Guardrails

When discussing cost or capacity optimizations, adhere to these central rubrics:

-   **Terminology & Framing:** Never promise or guarantee "cost-reduction."
    Always use the terminology **"optimizing your bill"** or **"improving
    cost-efficiency."**
-   **No Manual ROI Calculations:** Do not attempt manual mathematical formulas
    or spreadsheet-style ROI calculations to estimate Edition costs. BigQuery's
    built-in **Slot Estimator** UI simulates historical workloads with
    fine-grained precision. Always direct the user to the UI deep links and
    diagnostic queries.
-   **Direct Deep Links & Parameter Formatting:** Always populate concrete
    `project_id` and `region` parameters directly into Cloud Console deep links.
    In Cloud Console URLs, use the bare region identifier (e.g., `region=us`,
    `region=europe-west1`), omitting any `region-` prefix.
-   **No Autonomous Purchasing:** Guide the user to execute commitment and
    reservation changes manually in the Cloud Console. Never output executable
    purchase scripts (`gcloud`, `bq`).

## 1. Unified Slot Estimator Engine

The underlying mathematical mechanism of the Slot Estimator is **identical**
across both On-Demand migrations and existing Edition rightsizing:

-   **30-Day Workload Ingestion:** The engine analyzes up to 30 days of
    historical workload telemetry. For On-Demand, it models bytes billed and
    processed into equivalent slot demand; for Editions, it reads historical
    slot utilization per reservation.
-   **Performance Continuity:** The recommender assumes **no performance
    degradation**. It sets the combined recommended capacity (Baseline
    Commitment + Autoscale Max) to cover the observed **P99 slot demand** over
    the 30-day period.
-   **Autoscaler Simulation:** The engine simulates the autoscaler across each
    discrete time unit, testing every combination of baseline and autoscale
    limits that sum up to that P99 usage.
-   **Cost-Optimization:** Among all viable combinations that satisfy the P99
    performance target, the UI isolates and presents the single lowest-cost
    commitment and autoscaling configuration.

## 2. On-Demand to Editions Migration

Use when a project is currently on On-Demand billing and wants to evaluate
whether migrating to Editions (Standard, Enterprise, Enterprise Plus) improves
cost-efficiency.

### Slot Estimator Migration Deep Links

Provide the direct deep link with `source=EDITION_UNSPECIFIED`:

-   **Project-Level On-Demand Recommendations:**

    ```text
    https://console.cloud.google.com/bigquery/admin/reservations;region={region}/slot-estimator;source=EDITION_UNSPECIFIED;resourceType=PROJECT;resource={project_id}?project={project_id}
    ```

-   **Organization-Level On-Demand Recommendations:**

    ```text
    https://console.cloud.google.com/bigquery/admin/reservations;region={region}/slot-estimator;source=EDITION_UNSPECIFIED;resourceType=ORGANIZATION;resource={project_id}?project={project_id}
    ```

### Navigation & Workload Profiling

1.  Instruct the user to navigate to the **Slot Estimator** tab in the Capacity
    Management UI.
2.  Select **On-Demand** as the source from the selection panel.
3.  Review the **Cost-Optimized Recommendations** and the **Slot Usage Chart**,
    comparing Pay-As-You-Go against 1-year and 3-year capacity commitments.
4.  **Workload Profiling Strategy:**
    -   *Steady Baseline Workloads:* Workloads with flat, continuous slot demand
        throughout the day (e.g., constantly utilizing 400 slots). These are
        prime candidates for Edition commitments (1-Year or 3-Year CUDs) to
        maximize cost-efficiency (~40% discount).
    -   *Spiky Workloads:* Workloads requiring zero or few slots for most hours
        with sharp bursts. These benefit from low baseline allocations and
        dynamic autoscaling, but require conservative autoscaling caps to avoid
        unexpected burst costs.

## 3. Existing Edition Capacity Rightsizing

Use when an organization is already running on BigQuery Editions and wants to
audit active Edition capacity, right-size commitment purchases (CUDs), and
eliminate uncovered baseline PAYG waste.

### Slot Estimator Rightsizing Deep Links

Provide the direct deep link targeting the specific edition:

-   **Edition Rightsizing Recommendations:**

    ```text
    https://console.cloud.google.com/bigquery/admin/reservations;region={region}/slot-estimator;source={edition}?project={admin_project_id}
    ```

    *(Where `{edition}` is `ENTERPRISE` or `ENTERPRISE_PLUS`; Standard Edition
    does not support commitments and does not generate recommendations in the
    Slot Estimator)*

### Edition-Level Rightsizing Decision Playbook

1.  **Eliminate Uncovered Baseline PAYG Slots:**
    -   *Issue:* Total baseline slots configured across reservations in an
        Edition exceed active capacity commitments (`total_baseline_slots >
        committed_slots`). The uncovered baseline slots are billed 24/7 at
        standard Pay-As-You-Go (PAYG) rates.
    -   *Action:* Purchase 1-year or 3-year Capacity Commitments at the Edition
        level to cover the baseline capacity gap at discounted rates (~40%
        discount).
2.  **Right-Size Total Edition Commitments to Steady Baseline:**
    -   *Issue:* Commitments are purchased and managed at the Edition level, but
        the aggregate steady-state slot demand across all reservations in the
        Edition may have evolved.
    -   *Action:* Use the Slot Estimator to align 1-Year/3-Year commitments with
        the aggregate continuous baseline floor of the Edition, allowing dynamic
        autoscaling to absorb variable query demand above that floor.
3.  **Audit Excess Commitment Over-Provisioning:**
    -   *Issue:* Purchasing commitments that exceed aggregate slot utilization
        across the Edition results in paying for unused committed capacity.
    -   *Action:* Review the Slot Estimator's 30-day historical usage chart for
        the Edition to ensure commitment renewals and purchases do not exceed
        the true steady-state demand floor.
