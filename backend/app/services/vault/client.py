"""HashiCorp Vault transit secret engine client.

Provides the same ``encrypt_token`` / ``decrypt_token`` interface as the
Fernet-based ``app.core.security`` module.  When Vault is configured and
reachable the transit backend is used for AES-256-GCM encryption.
When Vault is unavailable (not configured, unreachable, or returns an error)
it automatically falls back to Fernet — ensuring zero downtime during Vault
migrations.

Environment variables consumed via ``app.config.Settings``:
  VAULT_ADDR     — e.g. https://vault.internal:8200
  VAULT_TOKEN    — root / app-role / k8s service-account token
  VAULT_TRANSIT_KEY — key name in transit secrets engine (default: "remindmeai")
  VAULT_TRANSIT_MOUNT — mount path (default: "transit")

Usage::

    from app.services.vault.client import vault_encrypt, vault_decrypt

    ciphertext = await vault_encrypt("plaintext-token")
    plaintext  = await vault_decrypt(ciphertext)
"""
from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Prefix used to distinguish Vault ciphertext from Fernet ciphertext.
# Vault transit always produces "vault:v1:..." so we can reliably detect.
_VAULT_PREFIX = "vault:"


def _is_vault_ciphertext(value: str) -> bool:
    return value.startswith(_VAULT_PREFIX)


class VaultTransitClient:
    """Async wrapper around the Vault transit secrets engine HTTP API.

    Parameters
    ----------
    vault_addr:     Base URL of the Vault server.
    vault_token:    Authentication token.
    key_name:       Transit key name (must already exist in Vault).
    mount:          Transit secrets engine mount path.
    timeout:        HTTP timeout in seconds.
    """

    def __init__(
        self,
        vault_addr: str,
        vault_token: str,
        key_name: str = "remindmeai",
        mount: str = "transit",
        timeout: float = 5.0,
    ) -> None:
        self._base = vault_addr.rstrip("/")
        self._token = vault_token
        self._key = key_name
        self._mount = mount
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-Vault-Token": self._token,
            "Content-Type": "application/json",
        }

    async def encrypt(self, plaintext: str) -> str:
        """Encrypt *plaintext* using the Vault transit backend.

        Returns the Vault ciphertext string (``vault:v1:...``).
        """
        b64_plain = base64.b64encode(plaintext.encode()).decode()
        url = f"{self._base}/v1/{self._mount}/encrypt/{self._key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json={"plaintext": b64_plain},
            )
        resp.raise_for_status()
        return resp.json()["data"]["ciphertext"]

    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt a Vault transit ciphertext, returning the plaintext string."""
        url = f"{self._base}/v1/{self._mount}/decrypt/{self._key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                url,
                headers=self._headers,
                json={"ciphertext": ciphertext},
            )
        resp.raise_for_status()
        b64_plain = resp.json()["data"]["plaintext"]
        return base64.b64decode(b64_plain).decode()

    async def rotate_key(self) -> None:
        """Rotate the transit key (new version; old versions still decrypt)."""
        url = f"{self._base}/v1/{self._mount}/keys/{self._key}/rotate"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=self._headers)
        resp.raise_for_status()
        logger.info("Vault transit key '%s' rotated successfully", self._key)

    async def health_check(self) -> bool:
        """Return True if Vault is initialized, unsealed, and reachable."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._base}/v1/sys/health")
            # 200 = active, 429 = standby — both mean the cluster is healthy
            return resp.status_code in (200, 429)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Module-level helpers with Fernet fallback
# ---------------------------------------------------------------------------

def _get_vault_client() -> Optional[VaultTransitClient]:
    """Return a configured ``VaultTransitClient`` or ``None`` if not set up."""
    try:
        from app.config import settings
        if not settings.vault_addr or not settings.vault_token:
            return None
        return VaultTransitClient(
            vault_addr=settings.vault_addr,
            vault_token=settings.vault_token,
            key_name=settings.vault_transit_key,
            mount=settings.vault_transit_mount,
        )
    except Exception:
        return None


async def vault_encrypt(plaintext: str) -> str:
    """Encrypt using Vault transit; fall back to Fernet on any error."""
    client = _get_vault_client()
    if client is not None:
        try:
            return await client.encrypt(plaintext)
        except Exception as exc:
            logger.warning(
                "Vault encrypt failed (%s), falling back to Fernet", exc
            )
    # Fernet fallback
    from app.core.security import encrypt_token
    return encrypt_token(plaintext)


async def vault_decrypt(ciphertext: str) -> str:
    """Decrypt: route to Vault for vault: prefix, else use Fernet."""
    if _is_vault_ciphertext(ciphertext):
        client = _get_vault_client()
        if client is not None:
            try:
                return await client.decrypt(ciphertext)
            except Exception as exc:
                logger.error("Vault decrypt failed: %s", exc)
                raise ValueError(f"Vault decryption error: {exc}") from exc
        raise ValueError("Vault ciphertext present but Vault client not configured")

    # Not a Vault ciphertext → Fernet
    from app.core.security import decrypt_token
    return decrypt_token(ciphertext)
