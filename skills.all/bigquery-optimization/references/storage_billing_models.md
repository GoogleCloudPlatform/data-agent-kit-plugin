# Storage Billing Models: Logical vs. Physical Optimization

Guidance for evaluating whether a BigQuery dataset achieves better
cost-efficiency under `LOGICAL` or `PHYSICAL` storage billing.

## Table of Contents

-   [1. Evaluation Workflow](#1-evaluation-workflow) (Lines 23-87)
    -   [Step 1: Gather Target Metrics](#step-1-gather-target-metrics) (Lines
        28-40)
    -   [Step 2: Calculate Cost Comparison](#step-2-calculate-cost-comparison)
        (Lines 42-67)
    -   [Step 3: Evaluate Decision Rules & Trade-offs](#step-3-evaluate-decision-rules-trade-offs)
        (Lines 69-87)
-   [2. Actionable Recommendations](#2-actionable-recommendations) (Lines
    89-113)
    -   [If Currently on Logical Billing:](#if-currently-on-logical-billing)
        (Lines 94-103)
    -   [If Currently on Physical Billing:](#if-currently-on-physical-billing)
        (Lines 105-113)
-   [3. Critical Footguns](#3-critical-footguns) (Lines 115-135)

## 1. Evaluation Workflow

Follow this step-by-step workflow when a user inquires about switching storage
billing models:

### Step 1: Gather Target Metrics

Retrieve storage metrics from the regional `INFORMATION_SCHEMA.TABLE_STORAGE`
view for the target dataset.

-   **Scope:** Query ``
    `{project_id}`.`region-{location}`.INFORMATION_SCHEMA.TABLE_STORAGE``
    filtered by `table_schema = '{dataset_id}'`, `table_type = 'BASE TABLE'`,
    and non-zero storage (`total_physical_bytes + fail_safe_physical_bytes > 0`)
    to isolate billable native base tables.
-   **Inputs Required:** `active_logical_bytes`, `long_term_logical_bytes`,
    `active_physical_bytes`, `long_term_physical_bytes`,
    `time_travel_physical_bytes`, and `fail_safe_physical_bytes`.

### Step 2: Calculate Cost Comparison

Calculate the forecasted monthly costs for both models using regional or
contract unit rates:

```text
logical_cost  = (active_logical_gib * price_active_logical)
              + (long_term_logical_gib * price_long_term_logical)

physical_cost = (
                  (active_physical_gib + fail_safe_physical_gib)
                  * price_active_physical
                )
              + (long_term_physical_gib * price_long_term_physical)

forecast_total_cost_difference = logical_cost - physical_cost
```

*(Note: In `TABLE_STORAGE`, `active_physical_bytes` already includes baseline
active data and `time_travel_physical_bytes`. Adding `fail_safe_physical_bytes`
completes the active physical storage footprint).*

-   **Positive Delta (`> 0`):** Physical billing is forecasted to have lower
    total cost.
-   **Negative Delta (`< 0`):** Logical billing is cheaper; transitioning to
    Physical billing would increase costs.

### Step 3: Evaluate Decision Rules & Trade-offs

1.  **Break-Even Compression Threshold:**
    -   *Baseline Ratio:* Physical rates (\$0.04/GiB active, \$0.02/GiB
        long-term in US) are roughly **2x** Logical rates (\$0.02/GiB active,
        \$0.01/GiB long-term). In standard US regions, data must compress
        **better than 2:1 (>2x)** (`logical_volume / physical_volume > 2`)
        before accounting for overhead.
    -   *Regional & Contract Adjustments:* For non-US regions or enterprise
        contracts, calculate the specific `price_physical / price_logical` ratio
        dynamically using current rates from
        [BigQuery Storage Pricing](https://cloud.google.com/bigquery/pricing#storage-pricing).
2.  **Time Travel & Fail-Safe Overhead:**
    -   Under **Logical** billing, Time Travel and Fail-Safe bytes are **free**.
    -   Under **Physical** billing, Time Travel and Fail-Safe bytes are **billed
        at the physical active rate**.
    -   High-churn workloads (frequent `UPDATE`/`DELETE` or daily full-table
        overwrites) inflate physical storage and require higher break-even
        compression (often 2.5x–3x+).

## 2. Actionable Recommendations

Determine the dataset's current storage billing model (via metadata or
`INFORMATION_SCHEMA.TABLE_STORAGE`):

### If Currently on Logical Billing:

-   **Physical is More Cost-Effective (`forecast_total_cost_difference > 0` &
    Low Churn):** Recommend updating the dataset storage billing model to
    `PHYSICAL` in dataset settings.
-   **High Churn but Strong Compression:** Recommend reducing the dataset Time
    Travel window (e.g., from 7 days down to 2 days) *before* transitioning to
    Physical billing to minimize overhead.
-   **Logical is More Cost-Effective (`forecast_total_cost_difference < 0`):**
    Recommend remaining on `LOGICAL` billing.

### If Currently on Physical Billing:

-   **Logical is More Cost-Effective (`forecast_total_cost_difference < 0`):**
    Recommend transitioning the dataset back to `LOGICAL` billing in dataset
    settings (verifying the 14-day lock-in cooldown has elapsed).
-   **Physical is Favorable but Inflated by Time Travel:** Recommend reducing
    the dataset Time Travel window to lower billable physical active bytes
    without changing the billing model.
-   **Physical is Optimal:** Recommend maintaining `PHYSICAL` billing.

## 3. Critical Footguns

-   **14-Day Cooldown (Hard Lock-in):** Once a dataset's storage billing model
    is updated, it **cannot be changed again for 14 days**. Verify compression
    and historical churn across a full cycle before advising a change.
-   **24-Hour Propagation Delay:** After updating the storage billing model on a
    dataset, it takes up to **24 hours** for the change to take effect and be
    reflected in storage billing calculations.
-   **Time Travel & Fail-Safe Incur Active Physical Rates:** Under Physical
    billing, both Time Travel (1–7 days) and Fail-Safe (7-day non-configurable
    disaster recovery) storage are billed at the **active physical rate**. In
    contrast, Time Travel and Fail-Safe bytes are completely free under Logical
    billing. For high-churn datasets, Time Travel + Fail-Safe overhead can
    outweigh compression savings.
-   **Free Tier Proration & Scope:** The 10 GiB monthly free tier is pooled
    across the Cloud Billing account and prorated per second (e.g., 100 GiB
    stored for 1 day is ~3.3 GiB-months, fitting within the free tier).
-   **Deletion Footgun on Physical Storage:** Deleting a table stops billing
    immediately under Logical storage, but continues accruing active physical
    charges for 9–14 days (Time Travel + 7-day Fail-Safe) under Physical
    storage.
