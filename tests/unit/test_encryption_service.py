"""
Unit tests for EncryptionService (INT-31).
"""
import base64
import os
import pytest

from app.services.encryption_service import EncryptionService, get_encryption_service, KEY_LENGTH


@pytest.fixture
def encryption_service(monkeypatch):
    """Create EncryptionService with test master key."""
    key = os.urandom(KEY_LENGTH)
    key_b64 = base64.b64encode(key).decode("ascii")
    mock_settings = type("Settings", (), {
        "ENCRYPTION_MASTER_KEY": key_b64,
        "ENCRYPTION_ENABLED": True,
    })()
    monkeypatch.setattr("app.services.encryption_service.get_settings", lambda: mock_settings)
    # Reset singleton so we get fresh instance with mocked settings
    import app.services.encryption_service as enc_mod
    enc_mod._encryption_service = None
    return get_encryption_service()


@pytest.fixture
def encryption_service_disabled(monkeypatch):
    """Create EncryptionService with encryption disabled."""
    mock_settings = type("Settings", (), {
        "ENCRYPTION_MASTER_KEY": "",
        "ENCRYPTION_ENABLED": False,
    })()
    monkeypatch.setattr("app.services.encryption_service.get_settings", lambda: mock_settings)
    import app.services.encryption_service as enc_mod
    enc_mod._encryption_service = None
    return get_encryption_service()


class TestEncryptionService:
    """Tests for EncryptionService."""

    def test_encrypt_decrypt_string(self, encryption_service):
        """Encrypt and decrypt a string round-trips correctly."""
        plain = "Hello, world!"
        enc = encryption_service.encrypt(plain, "user-123")
        assert enc is not None
        assert enc != plain
        dec = encryption_service.decrypt(enc, "user-123")
        assert dec == plain

    def test_encrypt_decrypt_dict(self, encryption_service):
        """Encrypt and decrypt a dict round-trips correctly."""
        plain = {"score": 85, "clarity": 0.9}
        enc = encryption_service.encrypt(plain, "user-456")
        assert enc is not None
        dec = encryption_service.decrypt(enc, "user-456")
        assert dec == plain

    def test_encrypt_decrypt_list(self, encryption_service):
        """Encrypt and decrypt a list round-trips correctly."""
        plain = [1, 2, "three"]
        enc = encryption_service.encrypt(plain, "user-789")
        assert enc is not None
        dec = encryption_service.decrypt(enc, "user-789")
        assert dec == plain

    def test_wrong_user_key_fails(self, encryption_service):
        """Decrypting with wrong user_id fails."""
        plain = "secret"
        enc = encryption_service.encrypt(plain, "user-A")
        assert enc is not None
        with pytest.raises(Exception):
            encryption_service.decrypt(enc, "user-B", try_plaintext_fallback=False)

    def test_none_empty_return_none(self, encryption_service):
        """encrypt returns None for None, empty string, empty dict, empty list."""
        assert encryption_service.encrypt(None, "user") is None
        assert encryption_service.encrypt("", "user") is None
        assert encryption_service.encrypt({}, "user") is None
        assert encryption_service.encrypt([], "user") is None

    def test_decrypt_none_returns_none(self, encryption_service):
        """decrypt returns None for None input."""
        assert encryption_service.decrypt(None, "user") is None

    def test_disabled_passthrough(self, encryption_service_disabled):
        """When disabled, encrypt returns plaintext and decrypt returns as-is."""
        plain = "no encryption"
        enc = encryption_service_disabled.encrypt(plain, "user")
        assert enc == plain
        dec = encryption_service_disabled.decrypt(plain, "user")
        assert dec == plain

    def test_is_enabled(self, encryption_service, encryption_service_disabled):
        """is_enabled reflects configuration."""
        assert encryption_service.is_enabled() is True
        assert encryption_service_disabled.is_enabled() is False
