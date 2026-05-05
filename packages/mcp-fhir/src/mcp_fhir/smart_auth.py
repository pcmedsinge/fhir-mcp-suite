"""SMART-on-FHIR OAuth 2.0 token management.

Supports:
  - ``client_credentials`` grant — backend services (Epic/Cerner system apps).
    No user interaction; uses client_id + client_secret.
  - ``authorization_code`` grant — EHR launch.  Token acquisition requires a
    browser redirect (outside MCP scope); only token refresh is handled here.

Auto-discovery:
  If ``smart_token_url`` is not configured, this module will attempt to
  auto-discover it via the FHIR server's SMART discovery endpoint:
    GET {fhir_base_url}/.well-known/smart-configuration

Token caching:
  Tokens are cached in-process (asyncio-safe) for their lifetime minus a
  30-second safety buffer.  The cache is keyed on (token_url, client_id) so
  multi-server scenarios are supported.

Usage:
    from mcp_fhir.smart_auth import get_access_token
    token = await get_access_token()   # cached; refreshes automatically
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

log = structlog.get_logger(__name__)

# Grace period before expiry to trigger proactive refresh.
_EXPIRY_BUFFER_S: float = 30.0


class SmartAuthError(RuntimeError):
    """Raised when SMART token acquisition fails."""


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # monotonic time


# Module-level cache: (token_url, client_id) → _CachedToken
_cache: dict[tuple[str, str], _CachedToken] = {}
_cache_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _cache_lock
    if _cache_lock is None:
        _cache_lock = asyncio.Lock()
    return _cache_lock


async def discover_token_url(fhir_base_url: str, timeout_s: float = 10.0) -> str:
    """Fetch the SMART discovery document and return the token endpoint URL.

    Calls ``GET {fhir_base_url}/.well-known/smart-configuration``.
    Falls back to ``{fhir_base_url}/oauth2/token`` if discovery fails.

    Args:
        fhir_base_url: FHIR base URL (no trailing slash).
        timeout_s:     HTTP timeout for the discovery request.

    Returns:
        Token endpoint URL string.
    """
    discovery_url = f"{fhir_base_url.rstrip('/')}/.well-known/smart-configuration"
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(discovery_url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            token_url = data.get("token_endpoint", "")
            if token_url:
                log.info("smart_discovery_ok", token_endpoint=token_url)
                return token_url
    except Exception as exc:
        log.warning("smart_discovery_failed", url=discovery_url, error=str(exc))

    # Fallback — common convention for Epic/Cerner
    fallback = f"{fhir_base_url.rstrip('/')}/oauth2/token"
    log.info("smart_discovery_fallback", token_url=fallback)
    return fallback


async def _acquire_client_credentials(
    token_url: str,
    client_id: str,
    client_secret: str,
    scopes: str,
    timeout_s: float,
) -> _CachedToken:
    """POST client_credentials grant and return a _CachedToken."""
    data = {
        "grant_type": "client_credentials",
        "scope": scopes,
    }
    log.info("smart_token_request", grant="client_credentials",
             token_url=token_url, client_id=client_id)
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(
                token_url,
                data=data,
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        raise SmartAuthError(
            f"SMART token request failed: HTTP {exc.response.status_code} — {body}"
        ) from exc
    except httpx.RequestError as exc:
        raise SmartAuthError(
            f"SMART token request network error: {exc}"
        ) from exc

    payload: dict[str, Any] = response.json()
    access_token = payload.get("access_token", "")
    if not access_token:
        raise SmartAuthError(
            f"SMART token response missing access_token. Got: {list(payload)}"
        )
    expires_in = float(payload.get("expires_in", 300))
    expires_at = time.monotonic() + expires_in - _EXPIRY_BUFFER_S

    log.info("smart_token_acquired",
             expires_in=expires_in, token_type=payload.get("token_type"))
    return _CachedToken(access_token=access_token, expires_at=expires_at)


async def get_access_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    scopes: str = "system/*.read",
    timeout_s: float = 15.0,
) -> str:
    """Return a valid access token, acquiring or refreshing as needed.

    Tokens are cached per ``(token_url, client_id)`` pair.

    Args:
        token_url:     OAuth 2.0 token endpoint URL.
        client_id:     SMART app client ID.
        client_secret: SMART app client secret (client_credentials grant).
        scopes:        Space-separated OAuth scopes.
        timeout_s:     Timeout for the token HTTP request.

    Returns:
        Bearer token string.

    Raises:
        SmartAuthError: If token acquisition fails.
    """
    cache_key = (token_url, client_id)
    async with _get_lock():
        cached = _cache.get(cache_key)
        if cached and time.monotonic() < cached.expires_at:
            log.debug("smart_token_cache_hit", client_id=client_id)
            return cached.access_token

        token = await _acquire_client_credentials(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            timeout_s=timeout_s,
        )
        _cache[cache_key] = token
        return token.access_token


def clear_token_cache() -> None:
    """Evict all cached tokens. Useful in tests."""
    _cache.clear()
