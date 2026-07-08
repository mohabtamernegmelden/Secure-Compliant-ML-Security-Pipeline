# Risk and Compliance Report

## Project focus
This report summarizes the current fraud-detection workflow implemented around the dataset in data/raw/AIML Dataset.csv.

## Data security approach
The notebook applies a privacy-preserving preprocessing step before model training. Sensitive identifier fields are encrypted with Fernet and exported to data/processed/secure_dataset.csv so the modeling workflow does not rely on raw customer identifiers.

## Modeling workflow
The current pipeline uses a notebook-based training flow that:
- loads the raw fraud dataset
- encrypts identifier columns
- creates engineered numeric features
- performs EDA for imbalance, distributions, and feature relationships
- trains XGBoost, LightGBM, and CatBoost models
- saves the trained artifacts under models

## Risk and compliance notes
- Encryption is applied to direct identifier fields before the secure export is written.
- The training matrix uses engineered features rather than raw identifiers.
- The workflow is designed for reproducibility through saved model artifacts and metadata.
- Production hardening should include managed secret storage, versioned model deployment, and monitoring.
