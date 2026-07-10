# Production Usage and Azure Deployment Guide

This document summarizes what was completed in the project, how to run it locally, and how to deploy it to Azure.

## What was completed

The backend is now aligned with the ML integration guide and is ready for production-style use with the current fraud-detection model assets.

### Implemented changes

- Integrated the model-loading path so the app resolves ML artifacts from the repository’s models directory reliably.
- Aligned the feature metadata in models/feature_columns.json with the active fraud model contract.
- Updated the prediction request schema to validate the expected input fields and constraints.
- Added production-oriented environment configuration and a production startup script.
- Kept the FastAPI app ready for containerized deployment with Docker and Azure-friendly settings.

### Current ML contract

The API expects these input fields:

- age
- income
- transaction_amount
- risk_score
- department
- user_role

The preprocessing workflow uses the configured numerical and categorical feature lists from models/feature_columns.json.

---

## Local usage

### 1. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and adjust values if needed:

```powershell
Copy-Item .env.example .env
```

For production-style local testing, you can also use:

```powershell
Copy-Item .env.production.example .env
```

### 4. Run tests

```powershell
pytest -q
```

### 5. Start the application

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or use the production startup script:

```powershell
bash .\scripts\run_production.sh
```

### 6. Check health

```powershell
curl http://127.0.0.1:8000/health
```

### 7. Authenticate and call the prediction endpoint

Login:

```powershell
curl -X POST http://127.0.0.1:8000/login `
  -H "Content-Type: application/json" `
  -d '{"username":"analyst","password":"AnalystPass123!"}'
```

Example prediction request:

```powershell
curl -X POST http://127.0.0.1:8000/predict `
  -H "Content-Type: application/json" `
  -H "X-API-Key: local-dev-api-key-replace-in-production" `
  -d '{"age":35,"income":75000.0,"transaction_amount":120.5,"risk_score":0.23,"department":"finance","user_role":"user"}'
```

---

## Docker usage

Build and run the application locally in a container:

```powershell
docker build -t secure-ml-backend .
docker run -p 8000:8000 --env-file .env secure-ml-backend
```

You can also use Docker Compose:

```powershell
docker-compose up --build
```

---

## Azure deployment

The project is already structured for Azure deployment using Docker and environment variables.

### Recommended Azure target

Use Azure App Service for a simple production deployment with a container image.

### 1. Create a resource group

```powershell
az group create --name rg-secure-ml --location eastus
```

### 2. Create an Azure Container Registry

```powershell
az acr create --resource-group rg-secure-ml --name <acrname> --sku Premium --admin-enabled true
```

> Note: Some Azure regions do not support the Basic or Standard ACR tiers. Use `Premium` if the lower tiers are not available.

### 3. Build and push the container image

```powershell
az acr login --name <acrname>
docker build -t <acrname>.azurecr.io/secure-ml-backend:latest .
docker push <acrname>.azurecr.io/secure-ml-backend:latest
```

### 4. Create an App Service plan

```powershell
az appservice plan create --name plan-secure-ml --resource-group rg-secure-ml --sku B1 --is-linux
```

### 5. Create the web app

```powershell
az webapp create --resource-group rg-secure-ml --plan plan-secure-ml --name <app-name> --deployment-container-image-name <acrname>.azurecr.io/secure-ml-backend:latest
```

### 6. Configure container image and app settings

```powershell
az webapp config container set --name <app-name> --resource-group rg-secure-ml --docker-custom-image-name <acrname>.azurecr.io/secure-ml-backend:latest --docker-registry-server-url https://<acrname>.azurecr.io

az webapp config appsettings set --name <app-name> --resource-group rg-secure-ml --settings \
  ENVIRONMENT=production \
  PORT=8000 \
  HOST=0.0.0.0 \
  API_KEY=<strong-api-key> \
  JWT_SECRET_KEY=<strong-jwt-secret> \
  REFRESH_JWT_SECRET_KEY=<strong-refresh-secret>
```

### 7. Optional: connect to Azure Key Vault

If you want to store secrets centrally, set:

```powershell
az webapp config appsettings set --name <app-name> --resource-group rg-secure-ml --settings AZURE_KEYVAULT_URL=https://<your-keyvault-name>.vault.azure.net/
```

Then grant the App Service managed identity access to the Key Vault secrets.

### 8. Restart and test the app

```powershell
az webapp restart --name <app-name> --resource-group rg-secure-ml
```

Open the deployed URL in your browser and test the health endpoint:

```powershell
https://<app-name>.azurewebsites.net/health
```

---

## Production checklist

Before going live, confirm the following:

- Replace default secrets with strong values.
- Set the API key to a production-safe value.
- Ensure the model artifacts in models/ are the official ones you intend to use.
- Configure Azure Key Vault or secure application settings if required.
- Enable monitoring and log retention for the deployed app.

---

## Notes

- The API documentation is available at /docs in non-production environments.
- In production, the app is intended to run behind HTTPS and with strong secret management.
- If you later replace the model with a different artifact set, keep the feature contract consistent with models/feature_columns.json.
