# What to Provide to Finish the Project

Use this file as a checklist of the information and assets needed to complete the remaining production work.

## 1. Azure deployment details
Provide the following if you want deployment to Azure:
- Azure subscription ID
- Azure resource group name
- Preferred Azure region
- Container registry name
- App Service or Container Apps name

## 2. Production secrets
Provide secure values for:
- JWT secret key
- Refresh JWT secret key
- API key
- Optional Azure Key Vault URL

## 3. Official model artifacts
If the current model files are not the final production model, provide:
- best_model.pkl
- scaler.pkl
- encoder.pkl
- feature_columns.json

## 4. Deployment preference
Choose one:
- Azure App Service
- Azure Container Apps
- GitHub Actions pipeline
- Azure DevOps pipeline

## 5. Extra requirements
If needed, also provide:
- Custom domain name
- Database connection details
- Monitoring or alerting preferences
- Authentication provider choice

## 6. Optional extras
If you want the project fully production-ready, you can also provide:
- a frontend URL for CORS configuration
- a Redis connection string
- a preferred logging destination

Once these items are provided, the project can be finished and deployed with the correct configuration.
