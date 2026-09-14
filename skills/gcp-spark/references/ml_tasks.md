# ML on Dataproc

**Verified patterns** for ML training:
- **XGBoost**: Use `SparkXGBClassifier`
- **Native Spark ML**: `GBTClassifier`, `RandomForestClassifier`,
  `LogisticRegression`

## LightGBM on Dataproc

> [!WARNING]
> **LightGBM has dependency conflicts on Dataproc Serverless.** The SynapseML
> LightGBM wrapper conflicts with Dataproc's internal libraries.

**Alternatives:**
1. **Use XGBoost** — Similar performance, native Spark support.
2. **Use Native Spark ML** — `GBTClassifier` provides similar gradient boosting
3. **Use Vertex AI** — Train LightGBM on Vertex, export model, load in Spark
   for inference
4. **Use Dataproc Cluster** (not Serverless) — More control over dependencies

**If you must use LightGBM**, consider:
- Training on a dedicated Dataproc cluster created with LightGBM spark packages
  set in the cluster properties:
  `spark:spark.jars.packages=com.microsoft.azure:synapseml_2.12:1.1.3`
- **MUST** disable Dataproc Autoscaling on the cluster
- Using ONNX model export for inference

---

## XGBoost Parameter Restrictions

> [!WARNING]
> **`SparkXGBClassifier` does NOT allow setting custom `objective` parameter.**
> The objective is automatically inferred from the classifier type:
> - `SparkXGBClassifier` → `binary:logistic` (inferred)
> - `SparkXGBRegressor` → `reg:squarederror` (inferred)

> [!WARNING]
> **`SparkXGBClassifier`** requires `dynamicAllocation=false`

**Prohibited** (causes `ValueError`):
```python
# ❌ DO NOT do this
xgb = SparkXGBClassifier(objective="binary:logistic", ...)
```

**Correct**:
```python
# ✅ Do this - objective is automatically set
xgb = SparkXGBClassifier(
    features_col="features",
    label_col="label",
    numRound=100,
    maxDepth=6,
)
```

See [XGBoost PySpark documentation]
(https://xgboost.readthedocs.io/en/stable/python/python_api.html#module-xgboost.spark)
for allowed parameters.

--------------------------------------------------------------------------------

## PySpark ML Vector Probability Slicing Syntax

> [!IMPORTANT] **Vector to Array Conversion Required**: `SparkXGBClassifier`,
> `RandomForestClassifier`, and Spark ML models output a `Vector` column named
> `probability`. You **CANNOT** index a Vector directly (`col("probability")[1]`
> causes a runtime crash). You MUST use `vector_to_array` from
> `pyspark.ml.functions` before filtering or slicing probabilities:

```python
from pyspark.ml.functions import vector_to_array
from pyspark.sql.functions import col

# ✅ CORRECT: Convert Vector column to Array before indexing
df_with_array = df.withColumn("prob_array", vector_to_array("probability"))
fraudulent_df = df_with_array.filter(col("prob_array")[1] >= 0.70)
```

--------------------------------------------------------------------------------

## PySpark Feature Assembly & Null/Unseen Label Handling

> [!IMPORTANT] **Null & Unseen Label Protection**: Always set
> `handleInvalid="keep"` or `handleInvalid="skip"` when initializing
> `VectorAssembler` and `StringIndexer` to prevent pipeline crashes when
> processing missing values or unseen categories.