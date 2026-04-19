"""Unit tests for app.core.security — no external I/O."""
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

# Generate a test key pair
_TEST_FERNET_KEY = Fernet.generate_key().decode()
_TEST_SECRET_KEY = "test-secret-key-for-unit-tests-32chars!!"


def _make_settings():
    """Patch settings with test values."""
    return {
        "app.core.security.settings.secret_key": _TEST_SECRET_KEY,
        "app.core.security.settings.fernet_key": _TEST_FERNET_KEY,
        "app.core.security.settings.access_token_expire_minutes": 60,
    }


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "secret_key", _TEST_SECRET_KEY)
    monkeypatch.setattr(settings, "fernet_key", _TEST_FERNET_KEY)
    monkeypatch.setattr(settings, "access_token_expire_minutes", 60)
    # Reset the cached Fernet instance
    import app.core.security as sec
    sec._fernet = None


def test_create_and_decode_token_roundtrip():
    from app.core.security import create_access_token, decode_access_token
    token = create_access_token(subject="user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"


def test_expired_token_raises():
    from app.core.security import create_access_token, decode_access_token
    token = create_access_token(subject="user-456", expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_tampered_token_raises():
    from app.core.security import create_access_token, decode_access_token
    token = create_access_token(subject="user-789")
    # Flip a character in the payload segment
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1][:-2] + "XX" + "." + parts[2]
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_encrypt_decrypt_roundtrip():
    from app.core.security import encrypt_token, decrypt_token
    plaintext = "ya29.very_long_google_oauth_token_here"
    ciphertext = encrypt_token(plaintext)
    assert ciphertext != plaintext
    assert decrypt_token(ciphertext) == plaintext


def test_different_fernet_key_fails_decryption(monkeypatch):
    from app.core.security import encrypt_token
    import app.core.security as sec

    # Encrypt with the test key
    plaintext = "some-oauth-token"
    ciphertext = encrypt_token(plaintext)

    # Switch to a different key
    new_key = Fernet.generate_key().decode()
    from app.config import settings
    monkeypatch.setattr(settings, "fernet_key", new_key)
    sec._fernet = None  # reset cached instance

    from app.core.security import decrypt_token
    with pytest.raises(ValueError):
        decrypt_token(ciphertext)
