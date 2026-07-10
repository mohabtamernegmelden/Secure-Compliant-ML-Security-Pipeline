param(
    [string]$ResourceGroup = "Ahmed",
    [string]$AcrName = "frauddetection",
    [string]$LoginServer = "frauddetection-b6grf4h2dne2fnc4.azurecr.io",
    [string]$AppName = "fraud-detection",
    [string]$PlanName = "plan-fraud-detection",
    [string]$Location = "francecentral",
    [string]$ImageName = "secure-ml-backend",
    [string]$ImageTag = "latest",
    [string]$ApiKey = "replace-with-strong-api-key",
    [string]$JwtSecret = "replace-with-strong-jwt-secret",
    [string]$RefreshJwtSecret = "replace-with-strong-refresh-secret",
    [string]$KeyVaultUrl = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$fullImage = "$LoginServer/$ImageName`:$ImageTag"

Write-Host "Checking Azure CLI authentication..."
az account show --output none

Write-Host "Creating resource group if needed..."
az group create --name $ResourceGroup --location $Location | Out-Null

Write-Host "Logging in to Azure Container Registry..."
az acr login --name $AcrName

Write-Host "Building Docker image..."
docker build -t $fullImage .

Write-Host "Pushing Docker image..."
docker push $fullImage

Write-Host "Ensuring App Service plan exists..."
$planExists = $null
try {
    $planExists = az appservice plan show --name $PlanName --resource-group $ResourceGroup --query name -o tsv 2>$null
} catch {
    $planExists = $null
}

if ([string]::IsNullOrWhiteSpace($planExists)) {
    Write-Host "App Service plan '$PlanName' not found. Creating plan..."
    az appservice plan create --name $PlanName --resource-group $ResourceGroup --sku B1 --is-linux --location $Location | Out-Null
}

Write-Host "Ensuring web app exists..."
$appExists = $null
try {
    $appExists = az webapp show --name $AppName --resource-group $ResourceGroup --query name -o tsv 2>$null
} catch {
    $appExists = $null
}

if ([string]::IsNullOrWhiteSpace($appExists)) {
    Write-Host "Web App '$AppName' not found. Creating web app..."
    az webapp create --resource-group $ResourceGroup --plan $PlanName --name $AppName --deployment-container-image-name $fullImage | Out-Null
}

$acrPassword = az acr credential show --name $AcrName --query passwords[0].value -o tsv

Write-Host "Configuring container image..."
az webapp config container set `
    --name $AppName `
    --resource-group $ResourceGroup `
    --docker-custom-image-name $fullImage `
    --docker-registry-server-url "https://$LoginServer" `
    --docker-registry-server-user $AcrName `
    --docker-registry-server-password $acrPassword | Out-Null

Write-Host "Setting app settings..."
$settings = @(
    "WEBSITES_PORT=8000",
    "ENVIRONMENT=production",
    "API_KEY=$ApiKey",
    "JWT_SECRET_KEY=$JwtSecret",
    "REFRESH_JWT_SECRET_KEY=$RefreshJwtSecret"
)

if ($KeyVaultUrl -and $KeyVaultUrl.Trim() -ne "") {
    $settings += "AZURE_KEYVAULT_URL=$KeyVaultUrl"
}

az webapp config appsettings set --name $AppName --resource-group $ResourceGroup --settings $settings | Out-Null

Write-Host "Restarting web app..."
az webapp restart --name $AppName --resource-group $ResourceGroup | Out-Null

$siteUrl = "https://$AppName.azurewebsites.net"
Write-Host "Deployment complete."
Write-Host "Health check: $siteUrl/health"
Write-Host "App URL: $siteUrl"
