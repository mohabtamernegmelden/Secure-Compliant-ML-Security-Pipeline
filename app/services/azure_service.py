from typing import Optional
from app.config import settings
from app.services.logging_service import app_logger

class AzureKeyVaultService:
    """
    Service to interact with Azure Key Vault dynamically.
    Falls back to settings/environment variables if Azure Key Vault is not configured.
    """
    def __init__(self):
        self.vault_url = settings.AZURE_KEYVAULT_URL
        self.client = None
        
        if self.vault_url:
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient
                
                credential = DefaultAzureCredential()
                self.client = SecretClient(vault_url=self.vault_url, credential=credential)
                app_logger.info(f"Azure Key Vault service initialized for URL: {self.vault_url}")
            except Exception as e:
                app_logger.error(f"Failed to initialize Azure Key Vault client: {e}")

    def get_secret(self, secret_name: str, fallback_value: str) -> str:
        """
        Retrieve a secret from Key Vault by name. Falls back if not found or client not initialized.
        """
        if not self.client:
            return fallback_value
            
        try:
            # Azure Key Vault names must match: ^[0-9a-zA-Z-]+$
            kv_name = secret_name.replace("_", "-")
            secret = self.client.get_secret(kv_name)
            return secret.value
        except Exception as e:
            app_logger.warning(f"Failed to retrieve secret {secret_name} (as {kv_name}) from Key Vault: {e}. Using fallback.")
            return fallback_value

azure_keyvault_service = AzureKeyVaultService()
