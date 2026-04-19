from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime


@dataclass
class OAuthUserInfo:
    email: str
    display_name: str
    provider_id: str


class OAuthClient(ABC):
    """Abstract base for OAuth 2.0 provider clients."""

    @abstractmethod
    async def get_authorization_url(self, state: str, code_verifier: str) -> str:
        """Return the provider's authorization URL for user redirect."""

    @abstractmethod
    async def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        """Exchange an authorization code for access + refresh tokens."""

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Obtain a new access token using the refresh token."""

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch the authenticated user's profile information."""
