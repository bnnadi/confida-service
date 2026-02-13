"""
Encryption service for sensitive data at rest (INT-31).

Uses AES-256-GCM for authenticated encryption with per-user key derivation via PBKDF2.
Provides data integrity verification via GCM authentication tag.
"""
import base64
import json
import os
from typing import Any, Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# AES-GCM constants
IV_LENGTH = 12  # 96 bits recommended for GCM
TAG_LENGTH = 16  # 128 bits
KEY_LENGTH = 32  # 256 bits
PBKDF2_ITERATIONS = 100_000
SALT_LENGTH = 32


class EncryptionService:
    """Service for encrypting and decrypting sensitive data with per-user keys."""

    def __init__(self):
        self.settings = get_settings()
        self._master_key: Optional[bytes] = None

    def _get_master_key(self) -> bytes:
        """Get or derive master key from config."""
        if self._master_key is not None:
            return self._master_key
        key_str = self.settings.ENCRYPTION_MASTER_KEY
        if not key_str:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY must be set when ENCRYPTION_ENABLED is true. "
                "Use base64-encoded 32 bytes."
            )
        try:
            self._master_key = base64.b64decode(key_str)
        except Exception:
            self._master_key = key_str.encode("utf-8")[:KEY_LENGTH].ljust(KEY_LENGTH, b"\0")
        if len(self._master_key) != KEY_LENGTH:
            raise ValueError(
                f"ENCRYPTION_MASTER_KEY must be {KEY_LENGTH} bytes (base64 or raw). "
                f"Got {len(self._master_key)} bytes."
            )
        return self._master_key

    def _derive_user_key(self, user_id: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Derive per-user encryption key using PBKDF2.
        Returns (key, salt). If salt is None, generates a new one.
        """
        user_id_bytes = str(user_id).encode("utf-8")
        if salt is None:
            salt = os.urandom(SALT_LENGTH)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )
        master = self._get_master_key()
        key = kdf.derive(master + user_id_bytes)
        return key, salt

    def is_enabled(self) -> bool:
        """Check if encryption is enabled and configured."""
        if not self.settings.ENCRYPTION_ENABLED:
            return False
        if not self.settings.ENCRYPTION_MASTER_KEY:
            return False
        return True

    def encrypt(
        self,
        plaintext: Union[str, bytes, dict, list, None],
        user_id: str,
    ) -> Optional[str]:
        """
        Encrypt plaintext for a user. Returns base64(salt + iv + ciphertext) or None for empty.
        Salt is stored in ciphertext for self-contained decryption.
        """
        if not self.is_enabled():
            if plaintext is None:
                return None
            return plaintext if isinstance(plaintext, str) else json.dumps(plaintext)

        if plaintext is None or plaintext == "" or plaintext == {} or plaintext == []:
            return None

        if isinstance(plaintext, (dict, list)):
            plaintext = json.dumps(plaintext)
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        salt = os.urandom(SALT_LENGTH)
        key, _ = self._derive_user_key(user_id, salt)
        iv = os.urandom(IV_LENGTH)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(iv, plaintext, None)

        combined = salt + iv + ciphertext
        return base64.b64encode(combined).decode("ascii")

    def decrypt(
        self,
        ciphertext_b64: Optional[str],
        user_id: str,
        *,
        try_plaintext_fallback: bool = True,
    ) -> Optional[Union[str, dict, list]]:
        """
        Decrypt ciphertext for a user. Returns plaintext string, dict, or list.
        If try_plaintext_fallback and decryption fails, returns as plaintext (legacy data).
        """
        if not ciphertext_b64:
            return None

        if not self.is_enabled():
            return self._parse_decrypted(ciphertext_b64)

        try:
            combined = base64.b64decode(ciphertext_b64)
        except Exception:
            if try_plaintext_fallback:
                return self._parse_decrypted(ciphertext_b64)
            raise

        if len(combined) < SALT_LENGTH + IV_LENGTH + TAG_LENGTH:
            if try_plaintext_fallback:
                return self._parse_decrypted(ciphertext_b64)
            raise ValueError("Ciphertext too short")

        salt = combined[:SALT_LENGTH]
        iv = combined[SALT_LENGTH : SALT_LENGTH + IV_LENGTH]
        ciphertext = combined[SALT_LENGTH + IV_LENGTH :]

        try:
            key, _ = self._derive_user_key(user_id, salt)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, ciphertext, None)
            return self._parse_decrypted(plaintext.decode("utf-8"))
        except Exception as e:
            if try_plaintext_fallback:
                logger.warning(f"Decryption failed, treating as plaintext: {e}")
                return self._parse_decrypted(ciphertext_b64)
            raise

    def _parse_decrypted(self, value: Union[str, bytes]) -> Union[str, dict, list]:
        """Parse decrypted value as JSON if possible, else return string."""
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


# Module-level singleton for convenience
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service singleton."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
