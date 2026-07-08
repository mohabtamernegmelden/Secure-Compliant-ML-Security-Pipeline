# Secure & Compliant ML Security Pipeline

## Project purpose
This project uses the fraud dataset in data/raw/AIML Dataset.csv to build a notebook-based workflow that combines privacy-preserving preprocessing, exploratory data analysis, and trained fraud-detection models.

## Current workflow
1. Load the raw transactional dataset.
2. Encrypt sensitive identifiers such as nameOrig and nameDest using Fernet.
3. Save a privacy-preserving export to data/processed/secure_dataset.csv.
4. Engineer features such as transaction type encoding, balance ratios, balance deltas, and log-transformed amounts.
5. Run EDA for class imbalance, transaction-type behavior, outlier analysis, and correlation structure.
6. Train XGBoost, LightGBM, and CatBoost models and save the trained artifacts under models.

## Security and compliance focus
- Sensitive identifiers are encrypted before the dataset is exported.
- The trained model uses engineered numeric features instead of raw identifiers.
- The notebook saves metadata so the training run is reproducible.
- The service in src/app.py is intended to use the same feature contract as the notebook.

## Key files
- notebooks/Fraud Detection.ipynb: full EDA, encryption, training, and model-saving workflow
- data/processed/secure_dataset.csv: privacy-preserving export used for modeling
- models: trained model files and metadata
- src/app.py: inference service and feature handling
- tests/test_app.py: regression checks for the service helpers

## Expected outcome
The project now supports a realistic fraud-detection pipeline that is privacy-aware and model-focused, with saved model artifacts ready for deployment or API integration.
