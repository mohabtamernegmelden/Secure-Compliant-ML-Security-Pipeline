# Remaining Work Checklist

This document lists the items that are still needed to take the project from a functional prototype to a production-ready deployment.

## 1. Production secrets and configuration
- Replace default JWT secrets with strong generated values in [app/config.py](../app/config.py) and [app/services/auth_service.py](../app/services/auth_service.py).
- Replace the default API key in [app/config.py](../app/config.py) and [app/services/auth_service.py](../app/services/auth_service.py).
- Move sensitive values out of the repository and into environment variables or Azure Key Vault by updating [app/config.py](../app/config.py) and [.env.production.example](../.env.production.example).
- Rotate any demo credentials still embedded in [app/services/auth_service.py](../app/services/auth_service.py).

## 2. Official model integration
- Confirm that the files in the models directory are the official production model artifacts in [models](../models).
- If a different model will be used, replace the files in [models/best_model.pkl](../models/best_model.pkl), [models/scaler.pkl](../models/scaler.pkl), [models/encoder.pkl](../models/encoder.pkl), and [models/feature_columns.json](../models/feature_columns.json).
- Validate that the feature order and categories still match the model training contract by updating [models/feature_columns.json](../models/feature_columns.json) if needed.

## 3. Authentication hardening
- Replace the current hardcoded user store in [app/services/auth_service.py](../app/services/auth_service.py) with a real identity provider.
- Prefer Azure Entra ID, a database-backed auth service, or another enterprise-grade authentication system and update [app/dependencies.py](../app/dependencies.py) and [app/routers/auth.py](../app/routers/auth.py) accordingly.
- Add password rotation, MFA, and role management for production use by extending [app/services/auth_service.py](../app/services/auth_service.py) and the auth-related schemas in [app/schemas/auth.py](../app/schemas/auth.py).

## 4. Azure infrastructure
- Provision an Azure Container Registry and update the deployment steps in [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Provision an Azure App Service or Azure Container Apps environment and align the runtime settings in [Dockerfile](../Dockerfile), [docker-compose.yml](../docker-compose.yml), and [scripts/run_production.sh](../scripts/run_production.sh).
- Provision Azure Key Vault for secret storage and update [app/config.py](../app/config.py).
- Configure monitoring and logging resources such as Application Insights and Log Analytics by adding deployment and configuration updates in [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Set up networking, DNS, and HTTPS if required by your environment.

## 5. CI/CD and deployment automation
- Add a GitHub Actions or Azure DevOps pipeline in a new workflow file under [.github](../.github) or the repository root.
- Automate build, test, and deployment steps by extending [Dockerfile](../Dockerfile) and the deployment guidance in [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Add rollback and release-versioning procedures in [README.md](../README.md) and [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Configure deployment approvals for production environments.

## 6. Observability and operations
- Add centralized logging and alerting by updating [app/services/logging_service.py](../app/services/logging_service.py) and [app/middleware/logging.py](../app/middleware/logging.py).
- Monitor prediction failures, auth failures, and service health through [app/routers/health.py](../app/routers/health.py) and [app/routers/predict.py](../app/routers/predict.py).
- Add dashboards for API usage, latency, and model performance in the Azure monitoring configuration referenced by [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Define incident response and support procedures in [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).

## 7. Security hardening
- Review and tighten CORS settings for your real frontend domains in [app/middleware/cors.py](../app/middleware/cors.py).
- Restrict allowed headers and methods if needed in [app/main.py](../app/main.py).
- Enforce HTTPS-only traffic in production by updating [app/main.py](../app/main.py) and the deployment guidance in [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Review dependency versions and apply regular security updates in [requirements.txt](../requirements.txt).

## 8. Documentation and handoff
- Document the production environment variables and secrets required in [.env.production.example](../.env.production.example) and [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Document the model update process for future releases in [ML_MODEL_INTEGRATION_GUIDE.md](../ML_MODEL_INTEGRATION_GUIDE.md) and [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).
- Preserve a deployment runbook for the operations team in [docs/production_usage_and_azure_deployment.md](../docs/production_usage_and_azure_deployment.md).

## Priority order
1. Replace secrets and demo credentials.
2. Confirm or replace the production model artifacts.
3. Provision Azure infrastructure.
4. Set up CI/CD and monitoring.
5. Replace in-memory auth with a real identity system.

## Current status
The project is functional and test-passing, but it is not yet fully production-ready until the items above are completed.
