# Security Architecture Documentation

## Overview
This document summarizes the security posture of the current fraud-detection project and the controls applied around data handling, model training, and future deployment.

## Data protection controls
- Fernet encryption is used for the identifier fields before the secure export is created.
- The training workflow avoids using direct identifiers as model features.
- The processed dataset is stored separately from the raw source file.

## Threat considerations
| Concern | Current mitigation |
|:---|:---|
| Sensitive identifier exposure | Fernet encryption before export |
| Data leakage into model training | Raw identifiers are removed from the modeling matrix |
| Reproducibility | Trained models and metadata are saved under models |
| Production secret handling | The key should be moved to Azure Key Vault or another managed secret store |

## Deployment direction
The project is structured so that the notebook training workflow can later be exposed through a secure API service. The main security focus for production is to protect the encryption key, control access to the inference endpoint, and keep model artifacts versioned.
