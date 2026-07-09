import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Application Settings
    ENVIRONMENT: str = Field(default="development", validation_alias="ENVIRONMENT")
    PORT: int = Field(default=8000, validation_alias="PORT")
    HOST: str = Field(default="0.0.0.0", validation_alias="HOST")
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Security and JWT
    JWT_SECRET_KEY: str = Field(default="e83d8e578a101b44d715dfeb6e6761fa63bc87e9cf19920d3f23a492fdfbc30b", validation_alias="JWT_SECRET_KEY")
    REFRESH_JWT_SECRET_KEY: str = Field(default="9aefb20c6a8bb1cf5bcf7a61d157ebce60da3bb2e805560b299e525fd408f62c", validation_alias="REFRESH_JWT_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    API_KEY: str = Field(default="local-dev-api-key-replace-in-production", validation_alias="API_KEY")

    # Encryption secrets
    ENCRYPTION_KEY: Optional[str] = Field(default=None, validation_alias="ENCRYPTION_KEY")
    ENCRYPTION_SALT: Optional[str] = Field(default="ml_security_default_salt_change_in_prod", validation_alias="ENCRYPTION_SALT")

    # Redis configuration
    REDIS_URL: Optional[str] = Field(default=None, validation_alias="REDIS_URL")

    # Azure Key Vault (optional for local deployment)
    AZURE_KEYVAULT_URL: Optional[str] = Field(default=None, validation_alias="AZURE_KEYVAULT_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()

# Post-processing to fetch secrets from Azure Key Vault if configured
def load_azure_secrets():
    # Allow local and test environments to run without Azure Key Vault.
    # In production, Key Vault is optional unless the deployment explicitly wants centralized secret storage.
    if settings.ENVIRONMENT == "production" and not settings.AZURE_KEYVAULT_URL:
        print("Warning: AZURE_KEYVAULT_URL is not configured; using local environment values.")

    if settings.AZURE_KEYVAULT_URL:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            print(f"Connecting to Azure Key Vault: {settings.AZURE_KEYVAULT_URL}")
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=settings.AZURE_KEYVAULT_URL, credential=credential)
            
            # Helper to safely retrieve secrets
            def get_secret(secret_name: str, default_val: str) -> str:
                kv_name = secret_name.replace("_", "-")
                try:
                    return client.get_secret(kv_name).value
                except Exception as e:
                    if settings.ENVIRONMENT == "production":
                        raise RuntimeError(f"Failed to load critical secret {secret_name} from Key Vault in production: {e}")
                    print(f"Warning: Failed to fetch secret '{secret_name}' from Key Vault: {e}. Using local/default value.")
                    return default_val

            settings.JWT_SECRET_KEY = get_secret("JWT-SECRET-KEY", settings.JWT_SECRET_KEY)
            settings.REFRESH_JWT_SECRET_KEY = get_secret("REFRESH-JWT-SECRET-KEY", settings.REFRESH_JWT_SECRET_KEY)
            settings.API_KEY = get_secret("API-KEY", settings.API_KEY)
            settings.ENCRYPTION_KEY = get_secret("ENCRYPTION-KEY", settings.ENCRYPTION_KEY or "")
            settings.REDIS_URL = get_secret("REDIS-URL", settings.REDIS_URL or "")
            
        except Exception as e:
            if settings.ENVIRONMENT == "production":
                raise RuntimeError(f"Azure Key Vault connection failed in production: {e}") from e
            print(f"Failed to load secrets from Azure Key Vault: {e}. Running with local configuration.")

# Load secrets if Key Vault is set
load_azure_secrets()
