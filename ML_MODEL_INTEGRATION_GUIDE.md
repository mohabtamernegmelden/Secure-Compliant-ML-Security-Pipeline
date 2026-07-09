# Machine Learning Model Integration Guide
### Developer Documentation for the Secure & Compliant ML Security Pipeline

This document guides the Machine Learning team or the next developer on how to integrate the official trained ML model into the FastAPI backend. 

---

## 1. Overview
The backend architecture is **fully model-agnostic**. It decouples endpoint routing, authentication, audit logging, rate limiting, and system security from the specific variables, shapes, and types of your machine learning models. 

At boot time, the backend dynamically loads column configurations, scaling assets, and encoding assets to prepare the feature vector on-demand. By design, the backend is currently loaded with placeholder assets and is waiting for the official ML artifacts. You can swap in a new model by replacing the binary files and updating a single JSON configuration.

---

## 2. Required ML Artifacts
The backend loads all ML assets from the `models/` directory. When integrating the official model, place the following files in `/home/am73/Downloads/fastapi/models/`:

```text
models/
├── best_model.pkl           # [REQUIRED] The serialized classifier model object
├── scaler.pkl               # [OPTIONAL] Fittet scikit-learn scaler object
├── encoder.pkl              # [OPTIONAL] Fittet scikit-learn encoder object
└── feature_columns.json     # [REQUIRED] Features ordering and categorization configuration
```

### Artifact Purpose & Specifications:
* **`best_model.pkl`**: A serialized Python object containing your trained classifier. It must be serialized using `joblib`.
* **`scaler.pkl`**: A serialized scaler (e.g. `StandardScaler`, `RobustScaler`, or `MinMaxScaler`) used to normalize numeric columns. This is optional; if your model does not require scaling (like a tree-based model), omit this file.
* **`encoder.pkl`**: A serialized categorical encoder (e.g. `OneHotEncoder` or `OrdinalEncoder`) used to encode string columns. This is optional; if your model contains no categorical features, omit this file.
* **`feature_columns.json`**: A JSON configuration declaring the exact numerical and categorical features in the order they were supplied during model training.

---

## 3. Model Requirements
The trained model object loaded from `best_model.pkl` must conform to the standard Python estimator interface:
1. **`predict(X)`**: Must accept a 2D NumPy array of shape `(n_samples, n_features)` and return an array of prediction class labels.
2. **`predict_proba(X)`**: Highly recommended. Must accept a 2D NumPy array and return a 2D array of class probabilities of shape `(n_samples, n_classes)`.
   * *Note*: If the model does not support `predict_proba` (e.g. SVM or regression models), the backend automatically falls back to generating a pseudo-probability mapping, but a true probability output is preferred.

### Classification Target Output:
* The current API contract expects a binary integer target classification: `0` (low risk/legitimate) and `1` (high risk/fraud).
* If your official model is a multi-class classifier or outputs string categories directly, you must update the prediction response schema (`PredictionResponse.prediction` to `str`) and adjust the prediction routers to handle it.

---

## 4. Feature Requirements
The order, type, and count of features passed to the model must match training parameters exactly.

### Configuration Format (`feature_columns.json`):
Your JSON configuration file must use the following schema structure:
```json
{
    "numerical_features": [
        "feature_name_1",
        "feature_name_2"
    ],
    "categorical_features": [
        "feature_name_3"
    ],
    "categories": {
        "feature_name_3": [
            "category_value_a",
            "category_value_b"
        ]
    }
}
```

The preprocessing service builds the feature vector by first extracting and scaling the list of `numerical_features` in the specified order, followed by the list of encoded `categorical_features`.

---

## 5. Preprocessing Requirements
The [preprocessing_service.py](file:///home/am73/Downloads/fastapi/app/services/preprocessing_service.py) automatically coordinates scaling and encoding based on the contents of the config file.

* **Numerical Scaling**: If `"numerical_features"` contains one or more elements, the service loads `models/scaler.pkl` and transforms inputs. If it is empty `[]`, no scaler is loaded or run.
* **Categorical Encoding**: If `"categorical_features"` contains one or more elements, the service loads `models/encoder.pkl` and transforms input strings. If it is empty `[]`, no encoder is loaded or run.

### Disabling Preprocessing Internally:
If your model already encapsulates the complete preprocessing pipeline internally (e.g., an XGBoost model using built-in categorical support, or a pipeline object like `sklearn.pipeline.Pipeline` serialized directly in `best_model.pkl`), disable external preprocessing by:
1. Setting both `"numerical_features"` and `"categorical_features"` to empty lists `[]` in `feature_columns.json`.
2. Setting the raw inputs to pass directly through the service.

---

## 6. Backend Integration Steps

Follow these five steps to plug in your model:

### Step 1: Copy ML Artifacts
Copy the new trained artifacts directly into `/home/am73/Downloads/fastapi/models/`, overwriting the existing files:
```bash
cp /path/to/your/official_model.pkl models/best_model.pkl
cp /path/to/your/official_scaler.pkl models/scaler.pkl
cp /path/to/your/official_encoder.pkl models/encoder.pkl
```

### Step 2: Update feature_columns.json
Modify `models/feature_columns.json` to declare the feature lists matching your training feature ordering.

### Step 3: Update PredictionInput Schema
Open [app/schemas/prediction.py](file:///home/am73/Downloads/fastapi/app/schemas/prediction.py) and update `PredictionInput` to declare all fields required by your model. Use appropriate Pydantic Types and range constraints (e.g. `ge` or `le`):
```python
class PredictionInput(BaseModel):
    # Example fields for Credit Card Fraud model
    time: float = Field(..., ge=0.0, description="Seconds elapsed elapsed between this transaction and the first transaction")
    amount: float = Field(..., ge=0.0, description="Transaction amount")
    v1: float = Field(..., description="PCA anonymized feature V1")
    v2: float = Field(..., description="PCA anonymized feature V2")
    # ... Add all remaining features
```

### Step 4: Run Tests
Execute the pytest suite from the project root to verify the service loads and functions correctly:
```bash
pytest -v
```

### Step 5: Verify Predictions
Verify that the output predictions are identical. Use the built-in comparison test `test_compare_model_vs_api` or run a smoke test locally:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 7. Files That May Need Updates
If the official model fits the default binary classifier paradigm, you only need to modify **one file**:
* **`app/schemas/prediction.py`**: Update `PredictionInput` to declare your model's input features.

### Advanced Customizations:
* **Custom Preprocessing Logic**: If your pipeline requires custom column transformations (e.g., custom date conversions or mathematical log transforms) instead of standard scikit-learn scaling, edit the `preprocess_batch` method in [app/services/preprocessing_service.py](file:///home/am73/Downloads/fastapi/app/services/preprocessing_service.py).
* **Direct Model Properties**: If you need to custom-tune the model parameters (e.g. manually overriding a classification probability threshold), edit the `predict` method in [app/services/model_service.py](file:///home/am73/Downloads/fastapi/app/services/model_service.py).

---

## 8. Validation Checklist
Verify the following checks are complete before declaring integration successful:
- [ ] **Model Loaded**: The API boots up and the log shows `Model version 1.0.0 loaded successfully.`
- [ ] **Endpoint Responding**: `POST /predict` returns a `200 OK` status code.
- [ ] **No Feature Mismatch**: No `ValueError` regarding input shape is raised during inference.
- [ ] **Correct Label Format**: Prediction returns the target index matching the training classes.
- [ ] **Probability Output**: Probability matches the soft confidence probability of class 1.
- [ ] **Health Endpoint Green**: `GET /health` returns `status: "healthy"` and `model_loaded: true`.
- [ ] **All Tests Pass**: Pytest reports 22/22 tests passing.

---

## 9. Troubleshooting

### 1. `ValueError: X has 10 features, but StandardScaler is expecting 4`
* **Cause**: The list of features declared under `"numerical_features"` in `feature_columns.json` does not match the features used to fit the scaler in `scaler.pkl`.
* **Fix**: Ensure the columns list and order matches the scaler's training parameters.

### 2. `AttributeError: 'NoneType' object has no attribute 'transform'`
* **Cause**: Numerical features are declared in `feature_columns.json`, but `scaler.pkl` was not copied or is missing.
* **Fix**: Ensure the scaler file exists or set `"numerical_features": []` in the config if no scaling is required.

### 3. `ModuleNotFoundError: No module named 'xgboost'` (or similar)
* **Cause**: Your model object belongs to a library not listed in the default environment.
* **Fix**: Add the library to `requirements.txt` and run `pip install -r requirements.txt`.

### 4. `KeyError: 'some_feature_name'`
* **Cause**: The Pydantic schema in `prediction.py` or the client request payload did not provide a feature name declared in the configuration.
* **Fix**: Ensure the request payload and Pydantic schema contain all keys declared in `feature_columns.json`.

---

## 10. Example Integration Scenarios

Below are instructions for integrating different model types:

### Scenario A: XGBoost Model
1. Place the trained `xgb_model.pkl` as `best_model.pkl` in `models/`.
2. XGBoost accepts categorical features natively if configured during training. If you trained the model using native categorical features:
   * Keep `"categorical_features": []` and `"numerical_features": []` in `feature_columns.json` to bypass standard scikit-learn preprocessing.
3. Install dependencies by adding `xgboost` to `requirements.txt` and rebuild the container.

### Scenario B: LightGBM Model
1. Save the model via `joblib.dump(lgb_model, "models/best_model.pkl")` or copy the binary.
2. If your model uses raw pandas DataFrames with categorical categories, you will need to adjust the `PreprocessingService` or `ModelService` to construct a DataFrame instead of a raw NumPy array:
   * Edit `model_service.py` `predict` method:
     ```python
     import pandas as pd
     # ... inside predict()
     df_features = pd.DataFrame(features, columns=self.xgb_features)
     predictions = self.model.predict(df_features)
     ```
3. Add `lightgbm` to `requirements.txt`.

### Scenario C: Random Forest Model
1. Save your Random Forest model, MinMaxScaler, and OneHotEncoder as `best_model.pkl`, `scaler.pkl`, and `encoder.pkl`.
2. Configure `feature_columns.json` listing the numerical and categorical columns.
3. Random Forest requires no extra libraries; the standard `scikit-learn` in `requirements.txt` is fully sufficient.

---

## 11. Future Compatibility
The modular service layer uses clean, standard interfaces:
* All communications between the routers and services are done using plain Python dictionaries and NumPy matrices.
* This means you can replace the model with entirely new paradigms (such as PyTorch models, deep neural networks, or ensemble models) in the future. As long as the inputs are formatted to a NumPy matrix and predictions return an array, the API endpoints and security components will work without modification.
