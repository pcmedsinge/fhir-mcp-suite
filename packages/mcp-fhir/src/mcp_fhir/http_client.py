"""Auth-aware HTTP helpers for mcp-fhir.

Provides ``get_fhir_headers()`` — returns the standard FHIR Accept header plus
an ``Authorization: Bearer <token>`` header when SMART auth is enabled.

All tools call this function instead of hardcoding the Accept header directly,
so auth is a single transparent layer that requires no other tool changes.

Auto-discovery:
    If ``SMART_ENABLED=true`` but ``SMART_TOKEN_URL`` is empty, the token URL
    is auto-discovered once from the FHIR server's
    ``/.well-known/smart-configuration`` endpoint and cached for the process
    lifetime.
"""

from __future__ import annotations

import asyncio

import structlog

from mcp_fhir.settings import settings

log = structlog.get_logger(__name__)

# Cache the discovered token URL so we only call discovery once per process.
_discovered_token_url: str | None = None
_discovery_lock: asyncio.Lock | None = None


def _get_discovery_lock() -> asyncio.Lock:
    global _discovery_lock
    if _discovery_lock is None:
        _discovery_lock = asyncio.Lock()
    return _discovery_lock


async def _resolve_token_url() -> str:
    """Return the configured or auto-discovered token URL."""
    global _discovered_token_url
    if settings.smart_token_url:
        return settings.smart_token_url

    async with _get_discovery_lock():
        # Double-check inside lock
        if _discovered_token_url:
            return _discovered_token_url
        from mcp_fhir.smart_auth import discover_token_url
        url = await discover_token_url(settings.fhir_base_url)
        _discovered_token_url = url
        return url


async def get_fhir_headers() -> dict[str, str]:
    """Return HTTP headers for a FHIR request.

    Always includes ``Accept: application/fhir+json``.
    Adds ``Authorization: Bearer <token>`` when ``SMART_ENABLED=true``.

    Returns:
        Headers dict ready to pass to an httpx request.

    Raises:
        SmartAuthError: If SMART is enabled but token acquisition fails.
    """
    headers: dict[str, str] = {"Accept": "application/fhir+json"}

    if not settings.smart_enabled:
        return headers

    token_url = await _resolve_token_url()
    from mcp_fhir.smart_auth import get_access_token
    token = await get_access_token(
        token_url=token_url,
        client_id=settings.smart_client_id,
        client_secret=settings.smart_client_secret.get_secret_value(),
        scopes=settings.smart_scopes,
        timeout_s=settings.smart_token_timeout_s,
    )
    headers["Authorization"] = f"Bearer {token}"
    log.debug("fhir_request_auth", smart_enabled=True, client_id=settings.smart_client_id)
    return headers


def reset_discovery_cache() -> None:
    """Clear the cached discovered token URL. Useful in tests."""
    global _discovered_token_url
    _discovered_token_url = None
