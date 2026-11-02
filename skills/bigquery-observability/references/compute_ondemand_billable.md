# Billable On-Demand Compute (Bytes Billed)

## Table of Contents

-   [CORE RULE: The Golden Base CTE (bytes_billed_cte)](#core-rule-the-golden-base-cte-bytes_billed_cte)
    (Lines 10-112)
-   [Modifying the Output (Agent Instructions)](#modifying-the-output-agent-instructions)
    (Lines 113-121)

## CORE RULE: The Golden Base CTE (bytes_billed_cte)

Whenever you are asked to analyze, sum, filter, or group on-demand compute
costs, you MUST NOT query `INFORMATION_SCHEMA.JOBS` directly. You must ALWAYS
use the following Common Table Expression (CTE) as your absolute foundation.
This handles the extreme complexities of BigQuery billing, including
parent/child script double-counting, BQML 50x multipliers, and PST timezone
partitioning.

```googlesql
CREATE TEMP FUNCTION isBillable(error_result ANY TYPE)
AS (
  error_result IS NULL OR error_result.reason = 'stopped'
);

-- BigQuery hides the number of bytes billed on queries against tables with row-level security.
CREATE TEMP FUNCTION isMaybeUsingRowLevelSecurity(
  job_type STRING, tib_billed FLOAT64, error_result ANY TYPE)
AS (
  job_type = 'QUERY'
  AND tib_billed IS NULL
  AND isBillable(error_result)
);

WITH
  bytes_billed_cte AS (
    SELECT
      project_id,
      job_id,
      user_email,
      -- A hash grouping similar queries that only differ by literal values
      query_info.query_hashes.normalized_literals AS query_hash,
      total_bytes_billed,
      total_bytes_processed,
      referenced_tables,
      error_result,
      job_type,
      -- Jobs are billed by end_time in PST8PDT timezone, regardless of where the job ran
      EXTRACT(DATE FROM end_time AT TIME ZONE 'PST8PDT') AS billing_date,
      TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) AS duration_ms,

      -- Multiply CREATE_MODEL by 50x. NOTE: I_S.JOBS does not track the specific model type.
      -- BQML pricing varies, so this conservatively assumes all models are the highest-billed (50x) types.
      (total_bytes_billed / 1024 / 1024 / 1024 / 1024)
        * CASE statement_type
          WHEN 'CREATE_MODEL' THEN 50
          ELSE 1
          END AS total_tb_billed,

      -- Flags queries where billed bytes were hidden/NULL due to Row-Level Security
      isMaybeUsingRowLevelSecurity(
        job_type,
        total_bytes_billed / 1024 / 1024 / 1024 / 1024,
        error_result) AS is_maybe_using_rls
    FROM
      -- JOBS and JOBS_BY_PROJECT are synonyms for project-scoped job history
      `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE
      -- Partition pruning: Pad creation_time by -2/+1 days to cover the target PST end_time billing window
      DATE(creation_time)
        BETWEEN DATE_SUB('{start_date}', INTERVAL 2 DAY)
        AND DATE_ADD('{end_date}', INTERVAL 1 DAY)
      AND EXTRACT(DATE FROM end_time AT TIME ZONE 'PST8PDT')
        BETWEEN '{start_date}'
        AND '{end_date}'
      AND job_type = 'QUERY'
      AND reservation_id IS NULL
      -- Scripts do not incur cost; their child queries do. Exclude to avoid double counting.
      AND (statement_type <> 'SCRIPT' OR statement_type IS NULL)
      AND isBillable(error_result)
  )
-- Default executable query: Daily spend & RLS masked query audit
SELECT
  '{region}' AS region,
  billing_date,
  ROUND(SUM(total_tb_billed), 4) AS total_tb_billed,
  COUNTIF(is_maybe_using_rls) AS jobs_using_row_level_security
FROM
  bytes_billed_cte
GROUP BY
  region,
  billing_date
ORDER BY
  billing_date;

-- Alternative troubleshooting aggregations:
-- 1. Top users by spend:
-- SELECT user_email, SUM(total_tb_billed) AS total_tb_billed FROM bytes_billed_cte GROUP BY 1 ORDER BY 2 DESC;
--
-- 2. Top queries by spend & processed bytes (job-level attribution, no multi-table fan-out):
-- SELECT query_hash, COUNT(1) AS query_count, SUM(total_tb_billed) AS total_tb_billed, SUM(total_bytes_processed) AS total_bytes_processed, ANY_VALUE(referenced_tables) AS sample_referenced_tables FROM bytes_billed_cte GROUP BY 1 ORDER BY 3 DESC LIMIT 10;
--
-- 3. Candidate tables referenced by high-scan queries (IMPORTANT: NEVER use SUM(total_bytes_billed) or SUM(total_bytes_processed) with UNNEST(referenced_tables), because job-level bytes repeat for every joined table; use COUNT(DISTINCT job_id), MAX(total_bytes_processed), and join TABLE_STORAGE for actual table size):
-- SELECT ref.project_id AS table_project_id, ref.dataset_id, ref.table_id, COUNT(DISTINCT c.job_id) AS referencing_job_count, MAX(c.total_bytes_processed) AS max_job_bytes_processed, MAX(s.total_logical_bytes) AS table_logical_bytes FROM bytes_billed_cte AS c, UNNEST(c.referenced_tables) AS ref LEFT JOIN `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.TABLE_STORAGE AS s ON ref.project_id = s.project_id AND ref.dataset_id = s.table_schema AND ref.table_id = s.table_name GROUP BY 1, 2, 3 ORDER BY table_logical_bytes DESC, max_job_bytes_processed DESC LIMIT 20;
```

> **⚠️ BQML Multiplier Caveat:** BigQuery ML pricing for on-demand queries
> depends on the specific type of model being created. Because
> `INFORMATION_SCHEMA.JOBS` does not track which type of model was created, the
> `total_tb_billed` calculation conservatively assumes all `CREATE_MODEL`
> statements were creating the higher-billed (50x multiplier) model types. Keep
> this in mind when diagnosing massive BQML spikes.

## Modifying the Output (Agent Instructions)

-   **Placeholders**: Replace `{project_id}` with the target Google Cloud
    project ID, `{region}` with the dataset or job execution region (e.g. `us`,
    `europe-west1`), `{start_date}` with the start date (`YYYY-MM-DD`), and
    `{end_date}` with the end date (`YYYY-MM-DD`).
-   **Custom Aggregations**: To answer specific user questions, take the Golden
    CTE above and append your specific aggregation logic to the bottom of the
    script.
