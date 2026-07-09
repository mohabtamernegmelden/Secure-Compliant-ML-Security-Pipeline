# Official Machine Learning Model Assets

Please place the official trained machine learning model artifacts inside this directory.

## Required Files:
1. **`best_model.pkl`**: Serialized classifier model binary object (using `joblib`).
2. **`scaler.pkl`**: (Optional) Serialized scaling transformation object (e.g. `StandardScaler` or `MinMaxScaler`).
3. **`encoder.pkl`**: (Optional) Serialized categorical one-hot/ordinal encoding object.
4. **`feature_columns.json`**: Model feature ordering and categorization config schema.

*Note*: If no model is configured in this directory, the backend will fail-safe and return a `503 Service Unavailable` error on all prediction endpoints. Refer to `ML_MODEL_INTEGRATION_GUIDE.md` for complete step-by-step instructions.
