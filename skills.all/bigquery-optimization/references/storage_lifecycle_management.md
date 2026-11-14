# Storage Lifecycle Management (Retention & TTL Optimization)

Decision matrix and parameters for at-rest storage right-sizing.

## 1. Optimization Decision Matrix

<!-- mdformat off -->
| Target Area | Trigger / Condition | Action / Parameter | Expected Impact |
| :--- | :--- | :--- | :--- |
| **Partition TTL** | Staging dataset or rolling logs | Set `default_partition_expiration_days` or `partition_expiration_days` | Automatically drops expired partitions after window |
| **Time Travel Tuning** | Ephemeral tables on `PHYSICAL` storage | Set `max_time_travel_hours = 48` (2-day min) | Drops `time_travel_physical_bytes` by ~5/7 (~71%) |
| **Unpartitioned Table** | Mature table (>90d) with active-only spend | Partition table by date or timestamp | Unlocks 50% Long-Term discount on historical rows |
| **Dev/Test Replication** | Full CTAS staging table copies | Replace with `CREATE TABLE CLONE` | Billed only for delta blocks added/modified |
| **Disaster Recovery** | Point-in-time table backups | Replace with `CREATE SNAPSHOT TABLE` | Billed only for modified/deleted base rows |
| **Cold Compliance** | Data accessed <1 time/year | Export to GCS Archive + query via BigLake | ~8x cheaper than BigQuery long-term logical rate |
<!-- mdformat on -->

## 2. Savings Formulas & Calculation

```text
# Time Travel Reduction Savings (Physical billing only):
estimated_tt_savings = (
                         current_time_travel_gib
                         * (1 - (new_window_hours / current_window_hours))
                       ) * price_active_physical
```

## 3. Gotchas & Constraints

-   **DML Clock Reset:** Unpartitioned `UPDATE`/`MERGE` touches all partitions,
    resetting their 90-day long-term timer back to 0. Always filter `WHERE
    _PARTITIONDATE >= ...`.
-   **Fail-Safe Invariant:** Fail-Safe window is fixed at 7 days
    non-configurable; continues to accrue active physical storage charges after
    Time Travel ends.
-   **Logical Billing Applicability:** Time Travel and Fail-Safe bytes are free
    under `LOGICAL` billing; tuning `max_time_travel_hours` yields \$0 storage
    savings on Logical datasets.
-   **TTL Permanent Drop:** Data dropped via partition expiration cannot be
    recovered once Time Travel + Fail-Safe windows elapse.
