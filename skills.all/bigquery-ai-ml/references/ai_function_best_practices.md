# BigQuery ML (BQML) & AI Functions

Rules and syntax standards for BigQuery AI and Machine Learning functions.

## 1. Global Constraints

*   **Connection ID**: Use `'DEFAULT'` for the `connection` argument in remote
    `CREATE MODEL` statements.
*   **Dataset Creation**: Use `CREATE SCHEMA IF NOT EXISTS
    <project>.<dataset>;`.
*   **SQL Only**: You MUST use native BigQuery SQL (via `%%bqsql` magics) for
    all BQML operations (model training, evaluation, prediction). Do NOT use
    BigFrames (`bigframes.ml`) or the BigQuery Python client.

## 3. Mandatory Syntax Checks

*   **Table-Valued Functions (TVFs)**: Table-Valued Functions (including,
    but not limited to, `AI.GENERATE_TABLE`, `AI.FORECAST`, `AI.EVALUATE`,
    and `AI.GENERATE_EMBEDDING`) MUST be placed in the `FROM` clause.
*   **Named Arguments**: `AI.FORECAST` and `AI.EVALUATE` require the `=>`
    operator for optional arguments.
*   **The "Prompt" Alias**: For `AI.GENERATE_TABLE`, the input subquery must
    contain a column aliased as `prompt`.
*   **Schema Quotes**: Ensure the `output_schema` string is enclosed in quotes.

## 4. Model Selection

*   **Time-series**: `AI.FORECAST` uses **TimesFM** endpoints.
*   **Generative**: `AI.GENERATE_TABLE` uses **Gemini** endpoints.
*   **Freshness**: Prefer current models (e.g., `gemini-2.5-flash`) over
    deprecated ones.

## 5. Data Exploration

*   **Mandatory Exploration**: Before training any model or running AI
    functions, you MUST perform data exploration using:
    1.  `ML.DESCRIBE_DATA` to understand the statistics of the dataset.
    2.  A simple `SELECT` query with a `LIMIT` operator (e.g., `LIMIT 5` or
        `LIMIT 10`) to sample the first few rows.

## 6. Model Training and Hyperparameters

*   **Default Parameters**: Always rely on BQML's default parameters and
    hyperparameters unless the prompt explicitly requests specific tuning. Do
    not unnecessarily specify hyperparameters. If one is necessary, justify the
    reasoning.
*   **Data Splitting**: Most BQML models handle data splitting automatically
    (default is `AUTO_SPLIT`). Do not perform manual training/validation/testing
    splits (either via SQL subqueries or Python) unless explicitly instructed.
    *   **TimesFM Exception**: If performing time-series forecasting with
        TimesFM (`AI.FORECAST`), you MUST split your dataset chronologically
        into exactly two parts:
    *   **Historical Data (History)**: Used as history_data in `AI.EVALUATE` and
        `input_data` in `AI.FORECAST`.
    *   **Evaluation Data (Actuals)**: Used as actual_data in `AI.EVALUATE` to
        compare against the forecast.

## 7. Model Evaluation

*   **Use BQML Functions**: Always use native BQML evaluation functions (e.g.,
    `ML.EVALUATE`, `ML.ARIMA_EVALUATE`, `AI.EVALUATE`) to compute metrics.
