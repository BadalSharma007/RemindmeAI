from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.services.oauth.base import OAuthClient, OAuthTokens, OAuthUserInfo

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate a PKCE code_verifier and code_challenge pair.
    Returns (code_verifier, code_challenge).
    """
    code_verifier = secrets.token_urlsafe(96)[:128]
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


class GmailOAuthClient(OAuthClient):
    """Gmail OAuth 2.0 client using Authorization Code + PKCE flow."""

    def __init__(self) -> None:
        self._client_id = settings.gmail_client_id
        self._client_secret = settings.gmail_client_secret
        self._redirect_uri = settings.gmail_redirect_uri
        self._scopes = settings.gmail_scopes

    async def get_authorization_url(self, state: str, code_verifier: str) -> str:
        """Build the Google authorization URL with PKCE."""
        _, code_challenge = _derive_challenge(code_verifier)
        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                    "code": code,
                    "code_verifier": code_verifier,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return _parse_token_response(data)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Get a new access token using the refresh token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        tokens = _parse_token_response(data)
        # Google doesn't always return a new refresh token on refresh
        if not tokens.refresh_token:
            tokens.refresh_token = refresh_token
        return tokens

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user profile from Google."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        return OAuthUserInfo(
            email=data["email"],
            display_name=data.get("name", data["email"]),
            provider_id=data["sub"],
        )

    async def revoke_token(self, token: str) -> None:
        """Revoke an OAuth token at Google."""
        async with httpx.AsyncClient() as client:
            await client.post(REVOKE_URL, params={"token": token})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive_challenge(code_verifier: str) -> tuple[str, str]:
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def _parse_token_response(data: dict) -> OAuthTokens:
    expires_in = data.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    return OAuthTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token", ""),
        expires_at=expires_at,
    )


# Singleton
gmail_oauth_client = GmailOAuthClient()
