from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    decrypt_token,
    encrypt_token,
    get_current_user_id,
)
from app.database import get_db
from app.models.email_connection import EmailConnection
from app.models.user import User
from app.schemas.auth import ConnectResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Phase 2: Redis-backed PKCE store with in-memory dict as fallback.
# Redis provides TTL (pkce_ttl_seconds) and survives process restarts /
# multi-worker deployments.  The fallback keeps Phase 1 dev behaviour intact.
# ---------------------------------------------------------------------------
_PKCE_FALLBACK: dict[str, str] = {}


def _pkce_set(state: str, code_verifier: str) -> None:
    try:
        import redis as _redis  # noqa: PLC0415

        from app.config import settings as _s  # noqa: PLC0415

        r = _redis.from_url(_s.redis_url, socket_connect_timeout=1)
        r.setex(f"pkce:{state}", _s.pkce_ttl_seconds, code_verifier)
    except Exception:  # noqa: BLE001
        _PKCE_FALLBACK[state] = code_verifier


def _pkce_pop(state: str) -> str | None:
    try:
        import redis as _redis  # noqa: PLC0415

        from app.config import settings as _s  # noqa: PLC0415

        r = _redis.from_url(_s.redis_url, socket_connect_timeout=1)
        key = f"pkce:{state}"
        raw = r.get(key)
        if raw:
            r.delete(key)
            return raw.decode()
        return None
    except Exception:  # noqa: BLE001
        return _PKCE_FALLBACK.pop(state, None)


@router.get("/start/{provider}")
async def start_oauth_redirect(provider: str):
    """Browser-friendly GET endpoint — redirects straight to Google/Outlook login."""
    from fastapi.responses import RedirectResponse as _RR  # noqa: PLC0415
    if provider == "gmail":
        from app.services.oauth.gmail import generate_pkce_pair, gmail_oauth_client  # noqa: PLC0415
        state = secrets.token_urlsafe(32)
        code_verifier, _ = generate_pkce_pair()
        _pkce_set(state, code_verifier)
        url = await gmail_oauth_client.get_authorization_url(state, code_verifier)
        return _RR(url)
    raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")


@router.post("/connect/{provider}", response_model=ConnectResponse)
async def initiate_oauth(
    provider: str,
) -> ConnectResponse:
    """
    Start the OAuth 2.0 PKCE flow for a given provider.
    Returns a redirect URL for the frontend to navigate to.
    """
    if provider == "gmail":
        from app.services.oauth.gmail import generate_pkce_pair, gmail_oauth_client  # noqa: PLC0415
        state = secrets.token_urlsafe(32)
        code_verifier, _ = generate_pkce_pair()
        _pkce_set(state, code_verifier)
        redirect_url = await gmail_oauth_client.get_authorization_url(state, code_verifier)
    elif provider == "outlook":
        from app.services.oauth.outlook import outlook_oauth_client  # noqa: PLC0415
        if outlook_oauth_client is None:
            raise HTTPException(status_code=503, detail="Outlook OAuth not configured")
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        _pkce_set(state, code_verifier)
        redirect_url = await outlook_oauth_client.get_authorization_url(state, code_verifier)
    else:
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")

    return ConnectResponse(redirect_url=redirect_url, state=state)


@router.get("/callback/{provider}", response_model=TokenResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    OAuth 2.0 callback endpoint. Exchanges the authorization code for tokens,
    creates or updates the user + email connection, and returns a JWT.
    """
    if provider not in ("gmail", "outlook"):
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' not supported")

    code_verifier = _pkce_pop(state)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    if provider == "gmail":
        from app.services.oauth.gmail import gmail_oauth_client  # noqa: PLC0415
        oauth_client = gmail_oauth_client
    else:
        from app.services.oauth.outlook import outlook_oauth_client  # noqa: PLC0415
        if outlook_oauth_client is None:
            raise HTTPException(status_code=503, detail="Outlook OAuth not configured")
        oauth_client = outlook_oauth_client

    try:
        tokens = await oauth_client.exchange_code(code, code_verifier)
        user_info = await oauth_client.get_user_info(tokens.access_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}") from exc

    # Upsert user
    result = await db.execute(select(User).where(User.email == user_info.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            email=user_info.email,
            display_name=user_info.display_name,
        )
        db.add(user)
        await db.flush()

    # Upsert email connection
    conn_result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.user_id == user.id,
            EmailConnection.provider == "gmail",
            EmailConnection.provider_email == user_info.email,
        )
    )
    connection = conn_result.scalar_one_or_none()
    if connection is None:
        connection = EmailConnection(
            user_id=user.id,
            provider="gmail",
            provider_email=user_info.email,
            access_token_enc=encrypt_token(tokens.access_token),
            refresh_token_enc=encrypt_token(tokens.refresh_token),
            token_expiry=tokens.expires_at,
            is_active=True,
        )
        db.add(connection)
    else:
        connection.access_token_enc = encrypt_token(tokens.access_token)
        connection.refresh_token_enc = encrypt_token(tokens.refresh_token)
        connection.token_expiry = tokens.expires_at
        connection.is_active = True

    await db.commit()

    # Trigger immediate poll (don't wait for Beat schedule)
    try:
        if provider == "gmail":
            from app.services.ingestion.gmail_poller import poll_all_gmail_connections  # noqa: PLC0415
            poll_all_gmail_connections.apply_async()
        else:
            from app.services.ingestion.outlook_poller import poll_all_outlook_connections  # noqa: PLC0415
            poll_all_outlook_connections.apply_async()
    except Exception:
        pass  # Non-critical; Beat will pick it up in 5min

    jwt_token = create_access_token(subject=str(user.id))

    # Redirect to frontend with token in URL so the UI can pick it up automatically
    from fastapi.responses import RedirectResponse  # noqa: PLC0415
    from app.config import settings as cfg  # noqa: PLC0415
    frontend = cfg.frontend_url.rstrip("/")
    return RedirectResponse(
        url=f"{frontend}/auth/callback?token={jwt_token}&email={user_info.email}",
        status_code=302,
    )


@router.delete("/disconnect/{provider}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def disconnect_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> None:
    """Revoke OAuth tokens and deactivate the email connection."""
    result = await db.execute(
        select(EmailConnection).where(
            EmailConnection.user_id == uuid.UUID(current_user_id),
            EmailConnection.provider == provider,
            EmailConnection.is_active == True,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Revoke token at provider (best-effort for all providers)
    if provider == "gmail":
        try:
            from app.services.oauth.gmail import gmail_oauth_client  # noqa: PLC0415
            access_token = decrypt_token(connection.access_token_enc)
            await gmail_oauth_client.revoke_token(access_token)
        except Exception:
            pass
    # Outlook tokens expire naturally; no dedicated revocation endpoint needed

    connection.is_active = False
    await db.commit()


@router.get("/me")
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return the current authenticated user's profile."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "timezone": user.timezone,
    }
