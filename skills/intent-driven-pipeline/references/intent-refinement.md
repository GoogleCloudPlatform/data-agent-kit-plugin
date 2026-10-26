# Intent Refinement: from a vague request to an approved `intent.goal`

Most pipeline defects come from an under-specified goal, not from code. Turn the
user's request into a precise `intent.goal` before you write any code.

## Rules

-   You MUST sample the source data before you ask questions. Ask only what the
    data and metadata cannot answer.
-   You MUST ask exactly ONE question per turn. Offer a recommended answer that
    is grounded in the sampled data (for example "I see 312 storefront rows with
    an `erp_ref` that also exists in `orders_raw`; dedup on `erp_ref`?").
-   After each answer, update the draft goal and show it as a `diff` block.
-   You MUST NOT generate dbt or SDP code until the user approves the final
    goal text.
-   If the user says "just build it", fill every open slot with the recommended
    default, list each default as an assumption, and ask for ONE approval of the
    whole goal.
-   Keep the user's raw request verbatim in your notes; it is NOT written to the
    YAML in the MVP format.

## Slots a precise goal fills

Fill every slot that applies. A slot that does not apply is skipped, not
invented.

### sources

-   what: fully qualified source tables or paths, and what each one holds.
-   evidence: `@skill:discovering-gcp-data-assets` search, schema, row sample.
-   example: `erp.orders_raw` (legacy ERP orders), `storefront.shop_orders`.

### target

-   what: target table name, grain (one row per what), and dataset variable.
-   example: Gold table `customer_orders`, one row per order, in
    `{{ gold_dataset }}`.

### join_or_match_keys

-   what: how records in different sources refer to the same entity.
-   evidence: value overlap measured on a sample, not column-name similarity.
-   example: `shop_orders.erp_ref = orders_raw.ord_id`.

### precedence

-   what: which source wins when both have the same entity.
-   example: Storefront wins.

### cutover_dates

-   what: dates when precedence or logic changes.
-   example: before 2026-07-01 ERP is the source of truth; from 2026-07-01
    Storefront is.

### dedup_rule

-   what: key and tie-breaker for duplicates within or across sources.
-   example: dedup on `erp_ref`; keep the Storefront row.

### filters_and_exclusions

-   what: rows to drop (test accounts, cancelled orders, null keys).

### schedule_and_deadline

-   what: when data must be fresh, in which time zone. This becomes the cron
    in `triggers`; the goal keeps the business deadline.
-   example: refresh daily at 06:00 UTC.

### lifecycle_rules

-   what: planned future changes the pipeline must support.
-   example: drop the ERP branch once the ERP migration is complete.

## Question order

Ask in this order and skip any slot the data already answers:

1.  sources and target (confirm what you discovered)
2.  join_or_match_keys
3.  precedence and cutover_dates
4.  dedup_rule
5.  filters_and_exclusions (only if the sample shows candidates)
6.  schedule_and_deadline
7.  lifecycle_rules (only if the user mentioned a migration or end date)

## Goal text style

-   Plain language, 2 to 6 sentences, present tense.
-   Name tables and key columns exactly as they exist.
-   State dates as `YYYY-MM-DD` and times with a time zone.
-   Contains rules that are true of the pipeline, not of a single table
    (for example source precedence). Column meanings belong in the code docs.
-   No SQL, no engine names, no cron strings.

## Worked example

### Raw request

Populate the gold order table from ERP and storefront orders. Storefront would
be source of truth from July.

### Approved goal

Union ERP orders (erp.orders_raw) and Storefront orders (storefront.shop_orders)
into the Gold table customer_orders, one row per order. Before 2026-07-01 ERP is
the source of truth. From 2026-07-01 Storefront is the source of truth: when
both sources have the same order, keep the Storefront row and deduplicate on
shop_orders.erp_ref = orders_raw.ord_id. Storefront orders with no erp_ref are
kept. Refresh daily at 06:00 UTC. Drop the ERP branch once the ERP migration is
complete.

### Questions that produced it (one per turn)

1.  "I found `erp.orders_raw` and `storefront.shop_orders`. Target Gold table
    `customer_orders` in `{{ gold_dataset }}`, one row per order?"
2.  "`shop_orders.erp_ref` matches `orders_raw.ord_id` for 97% of sampled
    rows. Use it to match orders across sources?"
3.  "'From July' means from 2026-07-01, with Storefront winning on overlap?"
4.  "Storefront orders with no `erp_ref` (3% of the sample): keep them?"
5.  "Refresh daily at 06:00 UTC?"

## Day-2 intent changes

When the user changes a rule ("the ERP migration is complete", "move the refresh
to 04:00"), you MUST:

1.  Edit `intent.goal` first and show the `diff`.
2.  Get approval of the new goal.
3.  Only then change the code and `triggers` that the new goal affects.
