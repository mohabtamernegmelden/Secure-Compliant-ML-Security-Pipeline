# Security Preprocessing Documentation

## Overview
This document describes the data protection steps applied to the current fraud dataset in data/raw/AIML Dataset.csv. The notebook encrypts sensitive identifiers, saves a privacy-preserving export, and uses engineered numeric features for training.

## Dataset profile
- Source: data/raw/AIML Dataset.csv
- Shape: 6,362,620 rows and 11 columns
- Target column: isFraud
- Fraud class count: 8,213 positive rows and 6,354,407 negative rows
- Sensitive columns: nameOrig and nameDest

## Privacy controls applied
### 1. Fernet encryption
The notebook encrypts the identifier fields nameOrig and nameDest with Fernet before exporting the secure dataset. The encryption key is stored in data/processed/fernet_key.key.

### 2. Secure export
A privacy-preserving export is written to data/processed/secure_dataset.csv. The export contains the encrypted identifier fields and synthetic profiles used for experimentation.

### 3. Feature preparation for training
The modeling matrix excludes raw identifiers and uses engineered numeric factors such as:
- transaction type encoding
- balance ratios
- balance deltas
- log-transformed amount values

## Recommended production hardening
- Store the Fernet key in Azure Key Vault or another managed secret store.
- Keep the training dataset and the encrypted export separate from the raw source.
- Version the model artifacts and metadata used for inference.
