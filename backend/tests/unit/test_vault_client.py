"""Unit tests for app.services.vault.client — no real Vault required."""
from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_encrypt_response(ciphertext: str = "vault:v1:abc123"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": {"ciphertext": ciphertext}}
    resp.raise_for_status = MagicMock()
    return resp


def _make_decrypt_response(plaintext_b64: str):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": {"plaintext": plaintext_b64}}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# VaultTransitClient unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_encrypt_calls_correct_url():
    from app.services.vault.client import VaultTransitClient

    client = VaultTransitClient(
        vault_addr="http://vault:8200",
        vault_token="token",
        key_name="mykey",
        mount="transit",
    )
    resp = _make_encrypt_response("vault:v1:encrypted")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=resp)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client.encrypt("hello")

    assert result == "vault:v1:encrypted"
    called_url = mock_http.post.call_args[0][0]
    assert called_url == "http://vault:8200/v1/transit/encrypt/mykey"


@pytest.mark.asyncio
async def test_encrypt_base64_encodes_plaintext():
    from app.services.vault.client import VaultTransitClient

    client = VaultTransitClient("http://vault:8200", "token")
    resp = _make_encrypt_response("vault:v1:x")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=resp)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await client.encrypt("secret-oauth-token")

    sent_json = mock_http.post.call_args[1]["json"]
    decoded = base64.b64decode(sent_json["plaintext"]).decode()
    assert decoded == "secret-oauth-token"


@pytest.mark.asyncio
async def test_decrypt_returns_plaintext():
    from app.services.vault.client import VaultTransitClient

    client = VaultTransitClient("http://vault:8200", "token")
    b64_value = base64.b64encode(b"my-secret").decode()
    resp = _make_decrypt_response(b64_value)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=resp)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client.decrypt("vault:v1:abc")

    assert result == "my-secret"


@pytest.mark.asyncio
async def test_health_check_true_on_200():
    from app.services.vault.client import VaultTransitClient

    client = VaultTransitClient("http://vault:8200", "token")
    resp = MagicMock()
    resp.status_code = 200

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=resp)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client.health_check()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_false_on_exception():
    from app.services.vault.client import VaultTransitClient

    client = VaultTransitClient("http://vault:8200", "token")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=ConnectionError("refused"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client.health_check()

    assert result is False


# ---------------------------------------------------------------------------
# vault_encrypt / vault_decrypt module-level helpers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vault_encrypt_falls_back_to_fernet_when_no_vault(monkeypatch):
    """When vault_addr is empty, vault_encrypt() should use Fernet."""
    from app.config import settings
    monkeypatch.setattr(settings, "vault_addr", "")
    monkeypatch.setattr(settings, "vault_token", "")

    from app.services.vault.client import vault_encrypt
    result = await vault_encrypt("plain-text-token")

    # Fernet ciphertext starts with gAAAAA (base64 URL safe)
    assert isinstance(result, str)
    assert not result.startswith("vault:")


@pytest.mark.asyncio
async def test_vault_decrypt_routes_fernet_ciphertext(monkeypatch):
    """Non-vault: ciphertext should be decrypted by Fernet."""
    from app.config import settings
    monkeypatch.setattr(settings, "vault_addr", "")
    monkeypatch.setattr(settings, "vault_token", "")

    from app.services.vault.client import vault_encrypt, vault_decrypt
    ciphertext = await vault_encrypt("roundtrip-value")
    plaintext = await vault_decrypt(ciphertext)

    assert plaintext == "roundtrip-value"


@pytest.mark.asyncio
async def test_vault_decrypt_raises_on_vault_prefix_without_client(monkeypatch):
    """A vault: prefixed ciphertext without a configured client should raise."""
    from app.config import settings
    monkeypatch.setattr(settings, "vault_addr", "")
    monkeypatch.setattr(settings, "vault_token", "")

    from app.services.vault.client import vault_decrypt
    with pytest.raises(ValueError, match="not configured"):
        await vault_decrypt("vault:v1:some-ciphertext")
