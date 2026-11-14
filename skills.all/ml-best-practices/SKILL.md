---
name: ml-best-practices
description: |
  CRITICAL RULE: You MUST use this skill whenever the task involves any machine learning tasks or data analysis.
  Use this skill if the user's prompt or requirements mention any of the following:
    * Clustering
    * Classification
    * Regression
    * Time series forecasting
    * Statistical testing
    * Model comparison
    * ML
    * Data analysis

  SQL/BigQuery ML HANDOFF: If the user requires a SQL solution, use this skill to dictate the ANALYSIS STEPS (e.g., markdown analysis cells, visualization logic), but defer to `bigquery` for all SQL syntax.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# ML Best Practices

I want to read a story about the data, not just run code. Ensure every code cell
is followed by a markdown cell analyzing the results. End the notebook with a
summary comprehensively answering the prompt.

If there is a good match between the user's request and a corresponding example
plan, then adapt the example plan to fully answer the user's request:

## Clustering:

Identify distinct groups based on their features.

-   Understand the schema and field descriptions.
-   Visualize features referenced in the prompt (e.g., with histograms,
    scatterplots).
-   Transform dates into timestamps.
-   Before applying encoders, check if the dataset already contains pre-encoded
    features and prefer existing numerical representations.
-   Prefer to keep data instead of dropping it when possible.
-   Transform ordinal data with an ordinal encoder.
-   Transform nominal data with a one hot encoder.
-   Standardize numerical features.
-   Perform clustering with a range of values, and collect the silhouette score.
-   Choose the optimal number of clusters based on the silhouette score.
-   Use dimensionality reduction (e.g., PCA) to project the data into two
    dimensions.
-   Scatterplot the samples in two dimensions with cluster labels as the hue.
-   Scatterplot the samples in two dimensions with a discrete feature as the
    hue.
-   Describe the clusters in text by feature distributions or typical feature
    values.
-   Conclusion: comprehensively answer the prompt in a final markdown cell.

## Time Series Forecasting:

Develop a predictive model to estimate future values based on historical trends.
How might different modeling approaches impact the prediction accuracy?

-   Understand the schema and field descriptions.
-   Visualize the target feature over time at a reasonable granularity.
-   Always perform a chronological split on the data to create training,
    validation, and test sets.
-   Are there seasonal trends?
-   Test for stationarity.
-   Discuss possible modeling approaches. How might different modeling
    approaches impact the prediction accuracy?
-   Train two time series forecasting models to predict the target feature. Use
    previous seasonality and stationarity information as model hyperparameters.
-   Predict the target feature for the training and validation sets.
-   Optionally, hypertune models with the validation set.
-   Visualize the actual and predicted target feature vs time for each model on
    the training and validation sets.
-   Evaluate the validation performance with error metrics.
-   Select a model.
-   Retrain the selected model on the test and validation sets.
-   Predict the test values with the selected model.
-   Visualize the average target feature and the predicted test values.
-   Conclusion: comprehensively answer the prompt in a final markdown cell.

## Exploratory Data Analysis / Anomaly Detection:

Identify and describe any outliers, unusual patterns, or significant trends
observed in the data. Provide visualizations to support your findings.

-   Understand the schema and field descriptions.
-   Visualize the target feature distribution in a way that shows outliers.
-   Identify and describe any outliers in the target feature.
-   Visualize relationships between the target feature and other features.
-   Identify and describe unusual patterns or significant trends.
-   Visualize patterns and trends.
-   Conclusion: comprehensively answer the prompt in a final markdown cell.

## Classification:

Given the data, can we classify by the target feature?

-   Understand the schema and field descriptions.
-   Identify rows that don't make sense. How many are there and what do they
    contain?
-   Identify rows without a target value. How many are there and what do they
    contain?
-   Drop rows that don't match the schema or don't have the target value (if it
    is reasonable to do so).
-   Split data into training, validation, and test sets.
-   Create features to represent when data are missing, if this is meaningful.
-   Handle missing data. Prefer to keep data instead of dropping it when
    possible.
-   Before applying encoders, check if the dataset already contains pre-encoded
    features and prefer existing numerical representations.
-   Transform ordinal data with an ordinal encoder.
-   Transform nominal data with a one hot encoder.
-   Standardize numerical features.
-   Train multiple models.
-   If there is evidence of overfitting, regularize and retrain the model.
-   If there is evidence of underfitting, consider adding or engineering
    features.
-   Evaluate the models.
-   Create confusion matrices.
-   Conclusion: comprehensively answer the prompt in a final markdown cell.

## Regression:

Predict the continuous valued target feature.

-   Understand the schema and field descriptions.
-   Identify rows that don't make sense. How many are there and what do they
    contain?
-   Identify rows without a target value. How many are there and what do they
    contain?
-   Develop an understanding of the data and determine how to handle missing
    values. This should make sense in the business context.
-   Identify any potential sources of group leakage. Aggregate where appropriate
    to prevent this.
-   Visualize target feature.
-   Split data into training, validation, and test sets.
-   Handle missing data. Prefer to keep data instead of dropping it when
    possible.
-   Before applying encoders, check if the dataset already contains pre-encoded
    features and prefer existing numerical representations.
-   Transform ordinal data with an ordinal encoder.
-   Transform nominal data with a one hot encoder. Restrict high cardinality
    categorical features to a tractable size.
-   Standardize numerical features.
-   Train multiple models.
-   Visualize the actual vs predicted values on training and validation data.
-   If there is evidence of overfitting, regularize and retrain the model.
-   If there is evidence of underfitting, consider adding or engineering
    features.
-   Evaluate the model error.
-   Conclusion: comprehensively answer the prompt in a final markdown cell.

## Comparing ML Models:

Evaluate and compare multiple models to determine which is most suitable for
production based on predictive power, robustness, and viability.

-   Understand the schema and align metrics with business goals (e.g., cost of
    false positives vs. false negatives).
-   Establish baselines: define a naive baseline (majority class/mean) and a
    simple ML baseline (e.g., Logistic/Linear Regression).
-   Ensure rigorous validation: use identical, fixed data splits for all models
    and perform $k$-fold cross-validation.
-   If data is temporal, use chronological splits for validation.
-   Select and report metrics beyond accuracy (e.g., F1-Score, PR-AUC, MAE,
    RMSE) that reflect business impact.
-   Use bootstrapping to calculate 95% confidence intervals for key metrics to
    determine statistical significance.
-   Perform slice-based error analysis: evaluate model performance across key
    subpopulations and demographics to identify bias or specific failure modes.
-   Inspect and compare confusion matrices, residual plots, and calibration
    curves.
-   Evaluate operational trade-offs: consider inference latency, training time,
    compute cost, and model size.
-   Assess interpretability using tools like SHAP or LIME where transparency is
    required.
-   Conclusion: Recommend the optimal model for the specific use case,
    justifying the choice with both performance and production viability.

## No match:

-   Understand the schema and field descriptions.
-   Identify rows that don't make sense. How many are there and what do they
    contain?
-   Identify rows without a target value. How many are there and what do they
    contain?
-   Drop rows that don't match the schema or don't have the target value (if it
    is reasonable to do so).
-   Create features to represent when data are missing, if this is meaningful.
-   Handle missing data. Prefer to keep data instead of dropping it when
    possible.
-   Before applying encoders, check if the dataset already contains pre-encoded
    features and prefer existing numerical representations.
-   Transform ordinal data with an ordinal encoder.
-   Transform nominal data with a one hot encoder.
-   Standardize numerical features.
-   Conclusion: comprehensively answer the prompt in a final markdown cell.

## Essential ML Practices

[!IMPORTANT] ALWAYS follow these ML practices

-   **Strict Featurization Ordering**: For supervised learning **ALWAYS** split
    the dataset into training and test data **BEFORE** fitting preprocessing
    pipelines (e.g. scaling, encoding). Fit the pipelines on the training data
    and test data independently.

-   **Handling Missing or NULL Values**: **ALWAYS** check for and handle missing
    and NULL values. First, analyze their frequency. Then, decide whether to
    keep them, drop them or impute them with a contextually appropriate value,
    and explain your reasoning.
