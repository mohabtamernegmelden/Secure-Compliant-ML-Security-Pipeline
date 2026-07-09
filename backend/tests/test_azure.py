import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the project directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from azure.core.exceptions import (
    ServiceRequestError,
    ClientAuthenticationError,
    ResourceNotFoundError,
    ServiceResponseError
)

def test_azure_keyvault_unavailable_dev_mode():
    """
    Test that in development mode, when Azure Key Vault is unavailable,
    the application falls back gracefully and does not raise an exception.
    """
    with patch("azure.keyvault.secrets.SecretClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = ServiceRequestError("Vault connection failed")
        mock_client_cls.return_value = mock_client
        
        with patch("app.config.settings.ENVIRONMENT", "development"), \
             patch("app.config.settings.AZURE_KEYVAULT_URL", "https://mockvault.vault.azure.net"):
            from app.config import load_azure_secrets
            # Call should not raise an error
            load_azure_secrets()

def test_azure_keyvault_unavailable_prod_mode():
    """
    Test that in production mode, when Azure Key Vault is unavailable,
    the application fails immediately with a RuntimeError.
    """
    with patch("azure.keyvault.secrets.SecretClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = ServiceRequestError("Vault unavailable")
        mock_client_cls.return_value = mock_client
        
        with patch("app.config.settings.ENVIRONMENT", "production"), \
             patch("app.config.settings.AZURE_KEYVAULT_URL", "https://mockvault.vault.azure.net"):
            from app.config import load_azure_secrets
            with pytest.raises(RuntimeError) as exc_info:
                load_azure_secrets()
            assert "Azure Key Vault connection failed in production" in str(exc_info.value)

def test_azure_invalid_credentials_prod_mode():
    """
    Test that in production mode, when credentials are invalid,
    the application fails immediately with a RuntimeError.
    """
    with patch("azure.keyvault.secrets.SecretClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = ClientAuthenticationError("Authentication failed")
        mock_client_cls.return_value = mock_client
        
        with patch("app.config.settings.ENVIRONMENT", "production"), \
             patch("app.config.settings.AZURE_KEYVAULT_URL", "https://mockvault.vault.azure.net"):
            from app.config import load_azure_secrets
            with pytest.raises(RuntimeError) as exc_info:
                load_azure_secrets()
            assert "Azure Key Vault connection failed in production" in str(exc_info.value)

def test_azure_connection_timeout_prod_mode():
    """
    Test that in production mode, when a connection timeout occurs,
    the application fails immediately with a RuntimeError.
    """
    with patch("azure.keyvault.secrets.SecretClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = ServiceResponseError("Connection timeout")
        mock_client_cls.return_value = mock_client
        
        with patch("app.config.settings.ENVIRONMENT", "production"), \
             patch("app.config.settings.AZURE_KEYVAULT_URL", "https://mockvault.vault.azure.net"):
            from app.config import load_azure_secrets
            with pytest.raises(RuntimeError) as exc_info:
                load_azure_secrets()
            assert "Azure Key Vault connection failed in production" in str(exc_info.value)

def test_azure_secret_not_found_prod_mode():
    """
    Test that in production mode, if a required secret is missing,
    the application fails immediately with a RuntimeError.
    """
    with patch("azure.keyvault.secrets.SecretClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")
        mock_client_cls.return_value = mock_client
        
        with patch("app.config.settings.ENVIRONMENT", "production"), \
             patch("app.config.settings.AZURE_KEYVAULT_URL", "https://mockvault.vault.azure.net"):
            from app.config import load_azure_secrets
            with pytest.raises(RuntimeError) as exc_info:
                load_azure_secrets()
            assert "Failed to load critical secret" in str(exc_info.value)
