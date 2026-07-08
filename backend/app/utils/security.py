import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings
from app.services.logging_service import security_logger

class SymmetricCipher:
    """
    Symmetric cipher service for encrypting and decrypting sensitive data fields.
    Useful in healthcare (PHI) or finance (PII) auditing scenarios.
    """
    def __init__(self):
        try:
            # Separate encryption secret and salt from auth secrets
            enc_secret = settings.ENCRYPTION_KEY or settings.JWT_SECRET_KEY
            enc_salt = settings.ENCRYPTION_SALT.encode("utf-8") if settings.ENCRYPTION_SALT else b"ml_security_default_salt"
            
            # Setup PBKDF2 key derivation (SHA256, 100,000 iterations)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=enc_salt,
                iterations=100000,
            )
            derived_key = kdf.derive(enc_secret.encode("utf-8"))
            self.key = base64.urlsafe_b64encode(derived_key)
            self.cipher = Fernet(self.key)
        except Exception as e:
            security_logger.error(f"Failed to initialize SymmetricCipher with KDF: {e}. Generating ephemeral key.")
            self.key = Fernet.generate_key()
            self.cipher = Fernet(self.key)

    def encrypt(self, plain_text: str) -> str:
        """
        Encrypt a string value. Returns a base64 string.
        """
        if not plain_text:
            return ""
        try:
            encrypted_bytes = self.cipher.encrypt(plain_text.encode("utf-8"))
            return encrypted_bytes.decode("utf-8")
        except Exception as e:
            security_logger.error(f"Encryption failed: {e}")
            return ""

    def decrypt(self, cipher_text: str) -> str:
        """
        Decrypt a base64 string. Returns plain text.
        """
        if not cipher_text:
            return ""
        try:
            decrypted_bytes = self.cipher.decrypt(cipher_text.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            security_logger.error(f"Decryption failed: {e}")
            return ""

# Export initialized cipher instance
symmetric_cipher = SymmetricCipher()
