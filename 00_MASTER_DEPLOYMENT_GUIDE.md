# 🚀 MASTER DEPLOYMENT GUIDE - Complete Step-by-Step

**Start here. Follow each step in order. This is the definitive deployment guide.**

---

## ⏱️ Time Estimates

- **Prerequisites Setup**: 15 minutes
- **Local Testing**: 10 minutes  
- **Azure Deployment**: 30 minutes
- **Verification**: 10 minutes
- **Total**: ~65 minutes for first deployment

---

## 📋 Phase 1: Prerequisites (15 min)

### 1.1 Verify Required Tools

```powershell
# PowerShell as Administrator

# Check Docker
docker --version  # Should be 24.0+

# Check Azure CLI
az --version  # Should be 2.50+

# Check Git
git --version  # Should be 2.40+

# Verify Azure login
az account show
# If fails, run: az login
```

**If any tool is missing:**
- Docker: https://www.docker.com/products/docker-desktop
- Azure CLI: https://learn.microsoft.com/cli/azure/install-azure-cli-windows

### 1.2 Navigate to Project

```powershell
cd "C:\Users\TUF F16\Desktop\New folder (2)\New folder\Secure-Compliant-ML-Security-Pipeline"
```

### 1.3 Generate 3 Strong Secrets

```powershell
# Run this 3 times and save the output

$secret = -join ((1..64) | ForEach-Object { '{0:X}' -f (Get-Random -Maximum 16) })
Write-Host "Secret: $secret"

# You'll have:
# 1. JWT_SECRET_KEY = SECRET_1
# 2. API_KEY = SECRET_2  
# 3. ENCRYPTION_KEY = SECRET_3
```

**Save these somewhere safe!** You'll need them in the next phase.

### 1.4 Create GitHub Actions Secrets (Skip if no CI/CD)

Go to your GitHub repository:
1. Settings → Secrets and variables → Actions
2. Create these 6 secrets:

```
AZURE_SUBSCRIPTION_ID      = YOUR_SUBSCRIPTION_ID
AZURE_CLIENT_ID            = YOUR_CLIENT_ID
AZURE_TENANT_ID            = YOUR_TENANT_ID
JWT_SECRET_KEY             = SECRET_1 (from above)
API_KEY                    = SECRET_2 (from above)
ENCRYPTION_KEY             = SECRET_3 (from above)
```

*(Skip if you'll deploy manually)*

---

## ✅ Phase 2: Local Testing (10 min)

**Test that everything works locally before Azure deployment.**

### 2.1 Build Docker Images

```powershell
# Build backend
docker build -t secure-ml-backend:latest .

# Build frontend
docker build -f frontend/Dockerfile -t secure-ml-frontend:latest ./frontend

# Verify builds
docker images | Select-String "secure-ml"
```

Expected output:
```
REPOSITORY                     TAG       IMAGE ID
secure-ml-backend              latest    abc123...
secure-ml-frontend             latest    def456...
```

### 2.2 Test with Docker Compose

```powershell
# Start services
docker-compose up --build

# Wait for output showing both services running
# Look for: "ml_security_backend" and "ml_security_frontend"
```

### 2.3 Verify Local Access

Open browser:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Test Login:**
```
Username: analyst
Password: analyst123
```

### 2.4 Stop Services

```powershell
# Press Ctrl+C in terminal, or in another terminal:
docker-compose down
```

✅ **If everything loaded and you could login, you're ready for Azure!**

---

## 🔧 Phase 3: Azure Setup (30 min)

### 3.1 Login to Azure

```powershell
az login

# Verify you're logged in to the correct subscription
az account show

# If not, set subscription:
az account set --subscription "87553ff2-c58e-428a-ac47-e92e15d852ef"
```

### 3.2 Get Your Subscription ID

```powershell
$SUBSCRIPTION_ID = az account show --query id --output tsv
Write-Host "Your Subscription ID: $SUBSCRIPTION_ID"
# Save this! You'll use it multiple times
```

### 3.3 Create or reuse an Azure Resource Group

If you already have an existing resource group, set the same name here and skip the `az group create` command.

```powershell
$RESOURCE_GROUP = "Mohab"
$LOCATION = "France Central"

# If the resource group already exists, skip the next command.
az group create `
  --name $RESOURCE_GROUP `
  --location $LOCATION

Write-Host "Resource group created: $RESOURCE_GROUP"
```

### 3.4 Create Azure Container Registry

```powershell
$ACR_NAME = "frauddetection"
$RESOURCE_GROUP = "Ahmed"

az acr create `
  --resource-group $RESOURCE_GROUP `
  --name $ACR_NAME `
  --sku Premium `
  --admin-enabled false

# Get the login server
$ACR_LOGIN_SERVER = az acr show `
  --name $ACR_NAME `
  --query loginServer `
  --output tsv

Write-Host "ACR Login Server: $ACR_LOGIN_SERVER"
Write-Host "Example: $ACR_LOGIN_SERVER/image:latest"
```

> Note: Some regions do not support Basic or Standard ACR tiers. If `Basic` fails, use `Premium`.

### 3.5 Login to ACR

```powershell
az acr login --name $ACR_NAME

# Verify
docker ps  # Should show ACR login context
```

### 3.6 Build & Push Docker Images to ACR

```powershell
$ACR_LOGIN_SERVER = "frauddetection-b6grf4h2dne2fnc4.azurecr.io"

# ===== BACKEND IMAGE =====
docker build -t secure-ml-backend:latest .
docker tag secure-ml-backend:latest "$ACR_LOGIN_SERVER/secure-ml-backend:latest"
docker push "$ACR_LOGIN_SERVER/secure-ml-backend:latest"

Write-Host "✓ Backend image pushed to ACR"

# ===== FRONTEND IMAGE =====
docker build -f frontend/Dockerfile -t secure-ml-frontend:latest ./frontend
docker tag secure-ml-frontend:latest "$ACR_LOGIN_SERVER/secure-ml-frontend:latest"
docker push "$ACR_LOGIN_SERVER/secure-ml-frontend:latest"

Write-Host "✓ Frontend image pushed to ACR"

# Verify images in ACR
az acr repository list --name frauddetection
```

Expected output:
```
secure-ml-backend
secure-ml-frontend
```

### 3.7 Deploy Azure Infrastructure (Bicep)

```powershell
$ENVIRONMENT = "prod"
$RESOURCE_GROUP = "Ahmed"
$LOCATION = "France Central"
$ACR_NAME = "frauddetection"

Write-Host "Deploying infrastructure (this takes 5-10 minutes)..."

az deployment group create `
  --resource-group $RESOURCE_GROUP `
  --template-file iac/main.bicep `
  --parameters `
    environmentName=$ENVIRONMENT `
    resourceGroupName=$RESOURCE_GROUP `
    location=$LOCATION `
    containerRegistryName=$ACR_NAME `
    containerAppsEnvironmentName="cae-fraud-detection-$ENVIRONMENT" `
    backendAppName="app-backend-$ENVIRONMENT" `
    frontendAppName="app-frontend-$ENVIRONMENT" `
    keyVaultName="Fraud-detection" `
    logAnalyticsName="law-fraud-detection-$ENVIRONMENT" `
    appInsightsName="ai-fraud-detection-$ENVIRONMENT"

Write-Host "✓ Infrastructure deployed successfully!"
```

### 3.8 Get Deployment Outputs

```powershell
$RESOURCE_GROUP = "Ahmed"

$outputs = az deployment group show `
  --resource-group $RESOURCE_GROUP `
  --name main `
  --query properties.outputs `
  | ConvertFrom-Json

$BACKEND_FQDN = $outputs.backendAppFqdn.value
$FRONTEND_FQDN = $outputs.frontendAppFqdn.value
$KV_URI = $outputs.keyVaultUri.value
$WEB_APP_NAME = "Fraud-detection"
$DEFAULT_DOMAIN = "fraud-detection-bpf8e4c7dsb5d6h7.francecentral-01.azurewebsites.net"

Write-Host "Backend FQDN: $BACKEND_FQDN"
Write-Host "Frontend FQDN: $FRONTEND_FQDN"
Write-Host "Key Vault: $KV_URI"
Write-Host "Web App Name: $WEB_APP_NAME"
Write-Host "Default Domain: https://$DEFAULT_DOMAIN"

# Save these! You'll need them next
```

### 3.9 Add Secrets to Azure Key Vault

```powershell
$KV_NAME = "fraud-detection"
$JWT_SECRET = "CEA34B9AA69AC3F303AA179BC10E0444902993485E3D99E0120218F423582DAF"       # From Phase 1
$API_KEY = "E6D4325E1FE515FEB171958F06714C5088D9D6063A6380C10B4B341D64163C8B"          # From Phase 1
$ENCRYPTION_KEY = "04B7FEF96CD391A402DE96F8DE1B57E19C847C608BBF34448EC15EE85A9650ED"   # From Phase 1

# Add secrets
az keyvault secret set `
  --vault-name $KV_NAME `
  --name "JWT-SECRET-KEY" `
  --value $JWT_SECRET

az keyvault secret set `
  --vault-name $KV_NAME `
  --name "API-KEY" `
  --value $API_KEY

az keyvault secret set `
  --vault-name $KV_NAME `
  --name "ENCRYPTION-KEY" `
  --value $ENCRYPTION_KEY

Write-Host "✓ Secrets added to Key Vault"

# Verify
az keyvault secret list --vault-name $KV_NAME
```

### 3.10 Update Container Apps with Images

```powershell
$BACKEND_APP = "app-backend-prod"
$FRONTEND_APP = "app-frontend-prod"
$RESOURCE_GROUP = "Ahmed"
$ACR_LOGIN_SERVER = "frauddetection-b6grf4h2dne2fnc4.azurecr.io"

# Update backend
az containerapp update `
  --name $BACKEND_APP `
  --resource-group $RESOURCE_GROUP `
  --image "$ACR_LOGIN_SERVER/secure-ml-backend:latest"

# Update frontend
az containerapp update `
  --name $FRONTEND_APP `
  --resource-group $RESOURCE_GROUP `
  --image "$ACR_LOGIN_SERVER/secure-ml-frontend:latest"

Write-Host "✓ Container apps updated with images"
```

### 3.11 Configure Environment Variables

```powershell
$BACKEND_APP = "app-backend-prod"
$FRONTEND_APP = "app-frontend-prod"
$RESOURCE_GROUP = "Ahmed"
$KV_URL = "https://fraud-detection.vault.azure.net/"
$BACKEND_FQDN = "app-backend-prod.azurecontainerapps.io"  # From Phase 3.8

# Backend environment variables
az containerapp update `
  --name $BACKEND_APP `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars `
    ENVIRONMENT=production `
    AZURE_KEYVAULT_URL=$KV_URL

# Frontend environment variables
az containerapp update `
  --name $FRONTEND_APP `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars `
    REACT_APP_API_URL="https://$BACKEND_FQDN" `
    REACT_APP_ENVIRONMENT=production

Write-Host "✓ Environment variables configured"
```

---

## 🔍 Phase 4: Verification (10 min)

### 4.1 Get Application URLs

```powershell
$RESOURCE_GROUP = "Ahmed"

# Backend URL
$BACKEND_FQDN = az containerapp show `
  --name app-backend-prod `
  --resource-group $RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn `
  --output tsv

# Frontend URL
$FRONTEND_FQDN = az containerapp show `
  --name app-frontend-prod `
  --resource-group $RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn `
  --output tsv

Write-Host "======================================"
Write-Host "Frontend: https://$FRONTEND_FQDN"
Write-Host "Backend:  https://$BACKEND_FQDN"
Write-Host "API Docs: https://$BACKEND_FQDN/docs"
Write-Host "Web App: Fraud-detection"
Write-Host "Default Domain: https://fraud-detection-bpf8e4c7dsb5d6h7.francecentral-01.azurewebsites.net"
Write-Host "======================================"
```

### 4.2 Test Backend Health Check

```powershell
$API_KEY = "YOUR_API_KEY_HERE"
$BACKEND_FQDN = "app-backend-prod.azurecontainerapps.io"

$response = Invoke-WebRequest `
  -Uri "https://$BACKEND_FQDN/health" `
  -Headers @{"X-API-Key" = $API_KEY} `
  -SkipHttpErrorCheck

Write-Host "Status Code: $($response.StatusCode)"
Write-Host "Response: $($response.Content)"

# Expected: 200 with {"status": "healthy", ...}
```

### 4.3 Open Frontend in Browser

```powershell
# Replace FRONTEND_FQDN with actual value from 4.1
Start-Process "https://FRONTEND_FQDN"
```

**You should see:**
- Login page loads
- Demo credentials visible
- No HTTPS certificate warnings

### 4.4 Test Login

```
Username: analyst
Password: analyst123
```

**After successful login, you should see:**
- Dashboard with system status
- "Model Loaded" indicator
- Fraud prediction form

### 4.5 Test Prediction

Fill in form with sample data:
```
Age: 35
Income: 75000
Transaction Amount: 120.5
Risk Score: 0.23
Department: finance
User Role: user
```

Click "Analyze for Fraud"

**You should see:**
- Prediction result card
- Fraud probability percentage
- Risk level (Low/Medium/High)

✅ **If all tests pass, your deployment is successful!**

---

## 📊 Phase 5: Post-Deployment (Optional)

### 5.1 Monitor with Application Insights

```powershell
# Get Azure Portal link
Write-Host "https://portal.azure.com"

# Navigate to:
# Resource Groups → Ahmed → ai-fraud-detection-prod
# View: Requests, Performance, Failures, Availability
```

### 5.2 View Real-time Logs

```powershell
az containerapp logs show `
  --name app-backend-prod `
  --resource-group Ahmed `
  --follow
```

### 5.3 Test Scale-up (Generate Load)

```powershell
# Open PowerShell in a loop to generate requests
$BACKEND_FQDN = "app-backend-prod.azurecontainerapps.io"
$API_KEY = "YOUR_API_KEY"

for ($i = 0; $i -lt 100; $i++) {
    Invoke-WebRequest `
      -Uri "https://$BACKEND_FQDN/health" `
      -Headers @{"X-API-Key" = $API_KEY} `
      -SkipHttpErrorCheck | Out-Null
    Write-Host "Request $i sent"
}

# Check in Azure Portal to see replicas scaling up
```

### 5.4 Setup Alerting (Optional)

```powershell
# In Azure Portal:
# 1. Go to Application Insights
# 2. Alerts → Create Alert Rule
# 3. Set conditions for high error rate or slow response
# 4. Add action group to send email notifications
```

---

## 🎯 Troubleshooting Quick Reference

### Container App won't start

```powershell
# Check logs
az containerapp logs show `
  --name app-backend-prod `
  --resource-group Ahmed

# Look for:
# - Image not found → Verify image in ACR
# - KeyVault access denied → Check managed identity
# - Port already in use → Check health probes
```

### Frontend shows blank page

```powershell
# Check frontend logs
az containerapp logs show `
  --name app-frontend-prod `
  --resource-group Ahmed

# Check browser console (F12) for:
# - API_URL incorrect
# - CORS errors
# - Network timeouts
```

### Can't login

```powershell
# Verify JWT secret is correct in Key Vault
az keyvault secret show `
  --vault-name fraud-detection `
  --name "JWT-SECRET-KEY"

# Check backend logs for auth errors
az containerapp logs show `
  --name app-backend-prod `
  --resource-group Ahmed
```

### 429 Too Many Requests

```powershell
# Rate limiting is active
# Wait 60 seconds or adjust limit in app/utils/limiter.py
```

---

## ✅ Final Checklist

After deployment, verify:

```
FRONTEND
☐ Loads at https://FRONTEND_FQDN
☐ Login page displays correctly
☐ Demo credentials work
☐ Dashboard displays after login
☐ System status shows "healthy"
☐ No HTTPS certificate warnings

BACKEND
☐ Health check returns 200
☐ /docs endpoint accessible
☐ Can make predictions
☐ Returns fraud probability

INFRASTRUCTURE  
☐ All resources in resource group
☐ Container images in ACR
☐ Secrets in Key Vault
☐ Logs in Application Insights

MONITORING
☐ Can see requests in Application Insights
☐ No errors in logs
☐ Containers auto-restart on crash
☐ Replicas scale when needed
```

---

## 📚 Additional Resources

- **Docker commands**: [DOCKER_AND_AZURE_DEPLOYMENT.md](docs/DOCKER_AND_AZURE_DEPLOYMENT.md)
- **Full runbook**: [AZURE_DEPLOYMENT_RUNBOOK.md](docs/AZURE_DEPLOYMENT_RUNBOOK.md)
- **Environment vars**: [ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md)
- **File summary**: [DEPLOYMENT_FILES_SUMMARY.md](DEPLOYMENT_FILES_SUMMARY.md)
- **Quick reference**: [QUICK_START_DEPLOYMENT.md](QUICK_START_DEPLOYMENT.md)

---

## 🎉 You're Done!

Your **Secure & Compliant ML Fraud Detection Pipeline** is now deployed to Azure!

**What you have:**
- ✅ Frontend React app running in Container Apps
- ✅ Backend API with ML inference in Container Apps
- ✅ Secrets securely managed in Key Vault
- ✅ Monitoring via Application Insights
- ✅ Auto-scaling enabled
- ✅ HTTPS with managed certificates
- ✅ Production-ready infrastructure

**Next steps:**
1. Configure CI/CD (GitHub Actions will auto-deploy on code push)
2. Set up custom domain (optional)
3. Configure backups (optional)
4. Review security policies (recommended)

---

**Status**: ✅ Production Ready  
**Deployment Time**: ~65 minutes  
**Last Updated**: 2026-07-10

