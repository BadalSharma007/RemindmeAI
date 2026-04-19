"""Unit tests for app.services.oauth.outlook — no network calls."""
from __future__ import annotations

import hashlib
import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.oauth.outlook import (
    OutlookOAuthClient,
    _generate_code_challenge,
    _parse_token_response,
)


_CLIENT = OutlookOAuthClient(
    client_id="test-client-id",
    client_secret="test-secret",
    redirect_uri="http://localhost:8000/auth/callback/outlook",
)


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

def test_code_challenge_is_s256():
    """S256 = base64url(sha256(verifier)) without padding."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
    assert _generate_code_challenge(verifier) == expected


def test_code_challenge_no_padding():
    challenge = _generate_code_challenge("any_verifier_string")
    assert "=" not in challenge


# ---------------------------------------------------------------------------
# Authorization URL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_authorization_url_contains_required_params():
    url = await _CLIENT.get_authorization_url(state="abc123", code_verifier="verifier_xyz")
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "code_challenge_method=S256" in url
    assert "state=abc123" in url
    assert "offline_access" in url


# ---------------------------------------------------------------------------
# Token parsing
# ---------------------------------------------------------------------------

def test_parse_token_response_basic():
    payload = {
        "access_token": "acc_tok",
        "refresh_token": "ref_tok",
        "expires_in": 3600,
    }
    tokens = _parse_token_response(payload)
    assert tokens.access_token == "acc_tok"
    assert tokens.refresh_token == "ref_tok"
    assert tokens.expires_at > datetime.now(timezone.utc)


def test_parse_token_response_missing_refresh():
    """refresh_token is optional on silent token refreshes."""
    payload = {"access_token": "acc", "expires_in": 1800}
    tokens = _parse_token_response(payload)
    assert tokens.refresh_token == ""


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exchange_code_returns_tokens(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_in": 3600,
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.oauth.outlook.httpx.AsyncClient", return_value=mock_client):
        tokens = await _CLIENT.exchange_code("auth_code_xyz", "code_verifier_123")

    assert tokens.access_token == "new_access"
    assert tokens.refresh_token == "new_refresh"
