---
name: bigquery-ai-ml
license: Apache-2.0
metadata:
  version: v3
  publisher: google
description: >-
  Leverages BigQuery's built-in machine learning and GenAI capabilities
  for advanced data analytics. Use when you need to write SQL queries
  that perform time-series forecasting, predict values, detect outliers or anomalies, find key drivers,
  perform semantic search or vector search, classify text, calculate similarity,
  summarize content, translate language, evaluate models, filter by semantic conditions,
  measure the causal effect of an intervention, compute correlations between columns,
  generate descriptive statistics and table distribution profiles,
  detect change points or structural breaks, extract trend or seasonality components,
  or leverage generative AI capabilities in BigQuery. Do not use for general
  BigQuery dataset, table, or job management requests.
---

# BigQuery AI & ML

BigQuery integrates with Vertex AI to provide powerful machine learning and
generative AI capabilities directly within SQL queries using built-in functions
like `AI.FORECAST`, `AI.KEY_DRIVERS`, `AI.DETECT_ANOMALIES`, and `AI.GENERATE`.

> [!IMPORTANT]
> You MUST read and follow the global constraints and mandatory function routing rules in
> [ai_function_best_practices.md](references/ai_function_best_practices.md) before writing any BQML AI/ML SQL query.

## Reference Directory

- **Best Practices**: [ai_function_best_practices.md](references/ai_function_best_practices.md) - Global constraints, connection settings, and mandatory syntax checks for BQML queries in notebooks.

### Functions Reference

- **AI.AGG** ([ai_agg.md](references/ai_agg.md))
  - **SQL Shape:** Aggregate
  - **Requires CREATE MODEL:** No
  - **Usage:** Multi-row semantic aggregation with `GROUP BY`; synthesizes 1 summary string across many rows (unlike per-row `AI.GENERATE`).
- **AI.CAUSAL_EFFECT** ([ai_causal_effect.md](references/ai_causal_effect.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Quantifies counterfactual post-intervention impact on a time series after a specific treatment timestamp.
- **AI.CLASSIFY** ([ai_classify.md](references/ai_classify.md))
  - **SQL Shape:** Scalar
  - **Requires CREATE MODEL:** No
  - **Usage:** Semantic classification of text or multimodal unstructured data into predefined category labels.
- **AI.DETECT_ANOMALIES** ([ai_detect_anomalies.md](references/ai_detect_anomalies.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Zero-shot **TimesFM** detector for isolated time-series point anomalies/outliers (use `ML.DETECT_CHANGE_POINTS` for sustained regime shifts).
- **AI.EVALUATE** ([ai_evaluate.md](references/ai_evaluate.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Zero-shot **TimesFM** time-series forecast evaluation/backtesting against a historical holdout split.
- **AI.FORECAST** ([ai_forecast.md](references/ai_forecast.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Zero-shot **TimesFM** time-series forecasting without training a custom model.
- **AI.GENERATE** ([ai_generate.md](references/ai_generate.md))
  - **SQL Shape:** Scalar
  - **Requires CREATE MODEL:** No
  - **Usage:** Default for per-row LLM text or multimodal structured extraction (`output_schema`); returns `STRUCT`. Prefer over `AI.GENERATE_TABLE`.
- **AI.GENERATE_EMBEDDING** ([ai_generate_embedding.md](references/ai_generate_embedding.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** Yes
  - **Usage:** Batch generates `ARRAY<FLOAT64>` vector embeddings for text or visual content using a remote embedding model.
- **AI.GENERATE_TABLE** ([ai_generate_table.md](references/ai_generate_table.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** Yes
  - **Usage:** Table-valued structured extraction (`FROM` clause); only use instead of `AI.GENERATE` when a remote model + TVF is explicitly needed.
- **AI.IF** ([ai_if.md](references/ai_if.md))
  - **SQL Shape:** Scalar
  - **Requires CREATE MODEL:** No
  - **Usage:** Evaluates boolean semantic conditions (`BOOL`) on text or multimodal data for `WHERE`/`CASE`/`JOIN` filtering (do not use `AI.GENERATE_TABLE`).
- **AI.KEY_DRIVERS** ([ai_key_drivers.md](references/ai_key_drivers.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Default one-step attribution of dimensional segments driving metric changes (`interest_label_col` `TRUE` vs. `FALSE`). Prefer over `CONTRIBUTION_ANALYSIS`.
- **AI.PREDICT** ([ai_predict.md](references/ai_predict.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Zero-shot **TabFM** foundation model for tabular classification or regression without training and managing custom models.
- **AI.SCORE** ([ai_score.md](references/ai_score.md))
  - **SQL Shape:** Scalar
  - **Requires CREATE MODEL:** No
  - **Usage:** Assigns a continuous `FLOAT64` semantic score to text or multimodal data for ranking or sorting (`ORDER BY`).
- **AI.SEARCH** ([ai_search.md](references/ai_search.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Simplified semantic search using a raw string query on tables with autonomous background embeddings (`AI.EMBED` generated column).
- **AI.SIMILARITY** ([ai_similarity.md](references/ai_similarity.md))
  - **SQL Shape:** Scalar
  - **Requires CREATE MODEL:** No
  - **Usage:** Computes an on-the-fly semantic similarity score (`FLOAT64`) between two text or multimodal inputs without stored embeddings.
- **Remote Models** ([remote_models.md](references/remote_models.md))
  - **SQL Shape:** CREATE MODEL
  - **Requires CREATE MODEL:** Yes
  - **Usage:** Creates a Vertex AI `REMOTE WITH CONNECTION DEFAULT` model entity for functions that require one (`AI.GENERATE_TABLE`, `AI.GENERATE_EMBEDDING`, `VECTOR_SEARCH`).
- **CONTRIBUTION_ANALYSIS** ([ml_contribution_analysis.md](references/ml_contribution_analysis.md))
  - **SQL Shape:** CREATE MODEL
  - **Requires CREATE MODEL:** Yes
  - **Usage:** Model-based driver analysis (`CREATE MODEL ... OPTIONS(MODEL_TYPE='CONTRIBUTION_ANALYSIS')` + `ML.GET_INSIGHTS`). Use `AI.KEY_DRIVERS` unless a `MODEL` entity is required.
- **ML.CORRELATION** ([ml_correlation.md](references/ml_correlation.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Calculates statistical correlation coefficients between numeric columns, optionally sliced by dimensions.
- **ML.DESCRIBE_DATA** ([ml_describe_data.md](references/ml_describe_data.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Generates descriptive statistics (e.g., count, mean, median, min, max, stddev, quantiles, nulls, top values) for columns in a table or subquery.
- **ML.DETECT_CHANGE_POINTS** ([ml_detect_change_points.md](references/ml_detect_change_points.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Detects structural breaks or sustained regime shifts (`[begin_timestamp, end_timestamp]` intervals) in a time series.
- **ML.SEASONALITY** ([ml_seasonality.md](references/ml_seasonality.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Extracts recurring periodic/seasonal components from a historical time series.
- **ML.TREND** ([ml_trend.md](references/ml_trend.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** No
  - **Usage:** Extracts the smoothed long-term trend component from a historical time series.
- **VECTOR_SEARCH** ([vector_search.md](references/vector_search.md))
  - **SQL Shape:** TVF
  - **Requires CREATE MODEL:** Yes
  - **Usage:** Searches pre-computed `ARRAY<FLOAT64>` embedding columns between a base table and query table (paired with `AI.GENERATE_EMBEDDING`, unlike `AI.SEARCH`).
