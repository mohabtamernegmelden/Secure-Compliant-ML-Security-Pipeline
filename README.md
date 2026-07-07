# Secure-Compliant-ML-Security-Pipeline
This repository implements a secure and compliant machine learning pipeline for regulated domains such as finance and healthcare. The project now includes hardened preprocessing, model-serving safeguards, and an audit-oriented API layer that is closer to production readiness.

## Recent security enhancements
- Hardened the prediction service to use environment-based configuration for secrets, origins, and audit logging.
- Removed the unsafe default API-key fallback from production paths and made the service fail fast when production secrets are missing.
- Fixed the feature-construction path used by inference so it aligns with the trained model contract.
- Added a regression test for the inference feature vector.

## Current milestone status
- Milestone 1: Completed and strengthened.
- Milestone 2: Completed with model training and evaluation artifacts.
- Milestone 3: In progress; deployment hardening is in place, with Azure Key Vault integration remaining as the next major step.
- Milestone 4: In progress; audit and monitoring hooks are in place and should be expanded for immutable logging.
- Milestone 5: Planned; final presentation and compliance artifacts should be finalized next.
