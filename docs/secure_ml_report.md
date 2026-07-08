# Secure ML Report

## Executive summary
This project now uses a notebook-driven fraud-detection pipeline that loads the dataset from data/raw/AIML Dataset.csv, encrypts sensitive customer identifiers, performs EDA, and trains three modern boosting models: XGBoost, LightGBM, and CatBoost.

## Current compliance approach
The notebook applies a privacy-focused preprocessing flow before model training:
- The identifier columns nameOrig and nameDest are encrypted with Fernet using a generated key stored in data/processed/fernet_key.key.
- The encrypted export is saved as data/processed/secure_dataset.csv.
- Raw identifiers are removed from the modeling matrix so the model learns from engineered numeric features rather than directly from PII.

## Data protection controls
- Encryption: Fernet is used for the direct identifier fields.
- Privacy-preserving export: synthetic profiles are added to support experimentation while limiting direct exposure of customer identities.
- Feature hygiene: the training set uses engineered features such as transaction-type encoding, balance ratios, balance deltas, and log-transformed amounts.

## Model training workflow
The updated notebook trains three separate boosting models:
1. XGBoost classifier
2. LightGBM classifier
3. CatBoost classifier

Each model is evaluated with the same hold-out validation strategy, and the trained artifacts are saved in models.

## Operational notes
- The notebook produces EDA plots for class distribution, transaction-type behavior, outlier ranges, and correlation structure.
- Model performance metrics are calculated inside the notebook and saved in metadata for reproducibility.
- The service in src/app.py is expected to use the same engineered feature shape as the notebook.

## Recommended next step
For production use, keep the encryption key in a managed secret store such as Azure Key Vault and add a deployment pipeline that version-controls the trained models and metadata artifacts.
