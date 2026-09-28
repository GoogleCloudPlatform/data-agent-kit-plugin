---
name: bigquery-bigframes
metadata:
  version: v3
description: >-
  Generates Python code using BigQuery DataFrames (BigFrames). Use by default for any Python data task involving BigQuery, including data processing, analysis, and machine learning. Don't use for SQL-first workflows or the google-cloud-bigquery client library — use bigquery-basics.

---

# BigFrames (BigQuery DataFrame) basics
BigFrames is a Python library that lets you take advantage of BigQuery
data processing by using familiar Python APIs.

## Generic Coding Guidelines

*   **Avoid `.to_pandas()`**: You MUST NOT use `.to_pandas()` to download the
    entire dataset into memory. There are some exceptions:
    *   An error message explicitly requests you to use `to_pandas()`
    *   You are going to visualize the data, **and** the visualization library
        does not accept BigFrames Dataframe/Series instances. In this case,
        reduce the amount of data you are going to download before calling
        `.to_pandas()`
*   **Avoid `read_gbq()` for SQL**: Do not write SQL queries and execute them
    with `read_gbq()`. Use BigFrames Dataframe/Series methods instead.
*   **Use BigFrames ML package for Machine Learning Tasks**: Do not use
    Scikit-learn or other ML libraries with BigFrames dataframes. Import your
    tools/classes from `bigframes.ml`.
*   **Stay in the Cloud**: Perform data cleaning, transformation, and analysis
    via BigFrames methods to leverage BigQuery's scale.
*   **Accessors over UDFs/Lambdas**:
    *   Prefer built-in accessors (e.g., `df.col.str.*`, `df.col.dt.*`) over
        remote UDFs.
    *   **Do not use lambdas** with `Series.map()` or `DataFrame.apply()`.
*   **Schema Verification**: Do not assume schema of intermediate outputs.
    Check `.dtypes` after loading, and use `display()` with `.head()` or
    `.peek()`.
*   **Visualization**: BigFrames Dataframe mostly works directly with
    Matplotlib, Seaborn, and other plotting libraries. If your attempt didn't
    work, try using the "plot" accessor. If that didn't work either, you MUST
    sample or aggregate your data to make it small enough before calling
    "to_pandas()".

## Model Development

*   **Unlike Scikit-learn**: BigFrames' `predict()` method always returns a
    **DataFrame** containing both predictions and features (not just a series
    of predictions).
*   **No `random_state`**: Do not pass a `random_state` argument when
    instantiating BigFrames ML models.
*   **Automatic Scaling**: Do not use `OneHotEncoder` or `StandardScaler`
    unless explicitly requested (handled automatically).
*   **Hyperparameter Tuning**: You must write custom loops (BigFrames lacks
    `GridSearchCV` or `RandomizedSearchCV`).
*   **ARIMA Plus** (Forecasting):
    -   Import from `bigframes.ml.forecasting`.
    -   Sort data chronologically and split around a timepoint before training.
    -   Prediction horizon must be less than or equal to training horizon.
*   **PCA**: BigFrames' PCA class lacks simple `transform()` method. Use
    `predict()` instead.
*   **Model Persistence**: To persist a model, use `model.to_gbq()`. To load a
    persisted model, use `bpd.read_gbq_model()`.
