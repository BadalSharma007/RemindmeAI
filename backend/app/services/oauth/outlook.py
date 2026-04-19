"""Outlook OAuth 2.0 client using Microsoft Identity Platform.

Implements the ``OAuthClient`` ABC using PKCE (S256) — no client secret
required for public clients, but we store one for confidential-client flows.
All HTTP calls use ``httpx`` (already a project dependency).

Endpoints
---------
  Authorize : https://login.microsoftonline.com/common/oauth2/v2.0/authorize
  Token     : https://login.microsoftonline.com/common/oauth2/v2.0/token
  User info : https://graph.microsoft.com/v1.0/me

Scopes requested
----------------
  offline_access  — required to receive a refresh_token
  User.Read       — /me profile (email + displayName)
  Mail.Read       — read messages via Graph API
  Calendars.ReadWrite — create/update calendar events (Phase 3)
"""
from __future__ import annotations

import base64
import hashlib
import os
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

from app.services.oauth.base import OAuthClient, OAuthTokens, OAuthUserInfo

_AUTHORITY = "https://login.microsoftonline.com/common/oauth2/v2.0"
_AUTHORIZE_URL = f"{_AUTHORITY}/authorize"
_TOKEN_URL = f"{_AUTHORITY}/token"
_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me"

_SCOPES = [
    "offline_access",
    "User.Read",
    "Mail.Read",
    "Calendars.ReadWrite",
]


def _generate_code_challenge(code_verifier: str) -> str:
    """Derive the S256 PKCE code challenge from *code_verifier*."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OutlookOAuthClient(OAuthClient):
    """Microsoft Identity Platform OAuth 2.0 client (PKCE, S256).

    Instantiated once at application startup and reused across requests.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    # ------------------------------------------------------------------
    # OAuthClient interface
    # ------------------------------------------------------------------

    async def get_authorization_url(self, state: str, code_verifier: str) -> str:
        """Return the Microsoft Identity authorization URL.

        The ``code_challenge`` is derived from *code_verifier* using S256.
        The caller is responsible for persisting *code_verifier* (e.g. in
        Redis) keyed by *state* so it can be retrieved during token exchange.
        """
        code_challenge = _generate_code_challenge(code_verifier)
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "response_mode": "query",
            "scope": " ".join(_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        """Exchange an authorization code for access + refresh tokens."""
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            "scope": " ".join(_SCOPES),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(_TOKEN_URL, data=data)
        resp.raise_for_status()
        return _parse_token_response(resp.json())

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Obtain a new access token using *refresh_token*."""
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(_SCOPES),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(_TOKEN_URL, data=data)
        resp.raise_for_status()
        return _parse_token_response(resp.json())

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch the authenticated user's profile from Microsoft Graph."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                _GRAPH_ME_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
        resp.raise_for_status()
        data = resp.json()
        email = (
            data.get("mail")
            or data.get("userPrincipalName")
            or ""
        )
        display_name = data.get("displayName") or email
        provider_id = data.get("id") or email
        return OAuthUserInfo(
            email=email,
            display_name=display_name,
            provider_id=provider_id,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_token_response(payload: dict) -> OAuthTokens:
    """Convert a Microsoft token response dict to ``OAuthTokens``."""
    expires_in: int = int(payload.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    return OAuthTokens(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token", ""),
        expires_at=expires_at,
    )


# ---------------------------------------------------------------------------
# Module-level singleton (mirrors the gmail pattern)
# ---------------------------------------------------------------------------

def _build_outlook_client() -> OutlookOAuthClient | None:
    """Build the client from environment / settings.  Returns None if not configured."""
    try:
        from app.config import settings
        if not settings.outlook_client_id:
            return None
        return OutlookOAuthClient(
            client_id=settings.outlook_client_id,
            client_secret=settings.outlook_client_secret,
            redirect_uri=settings.outlook_redirect_uri,
        )
    except Exception:
        return None


outlook_oauth_client: OutlookOAuthClient | None = _build_outlook_client()
