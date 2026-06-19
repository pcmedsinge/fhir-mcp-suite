"""Unit tests for SMART-on-FHIR auth (no real credentials — httpx mocked via respx)."""

from __future__ import annotations

import time

import httpx
import pytest
import respx

# ── smart_auth unit tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acquire_token_success() -> None:
    """client_credentials grant returns and caches an access token."""
    from mcp_fhir.smart_auth import clear_token_cache, get_access_token

    clear_token_cache()

    with respx.mock:
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "tok-abc", "expires_in": 300, "token_type": "Bearer"},
            )
        )
        token = await get_access_token(
            token_url="https://auth.example.com/token",
            client_id="myclient",
            client_secret="mysecret",
            scopes="system/*.read",
        )
    assert token == "tok-abc"


@pytest.mark.asyncio
async def test_acquire_token_cached() -> None:
    """Second call reuses cached token without hitting the network."""
    from mcp_fhir.smart_auth import clear_token_cache, get_access_token

    clear_token_cache()

    call_count = 0
    with respx.mock:

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                200,
                json={"access_token": "tok-xyz", "expires_in": 600, "token_type": "Bearer"},
            )

        respx.post("https://auth.example.com/token").mock(side_effect=handler)

        await get_access_token(
            token_url="https://auth.example.com/token",
            client_id="c1",
            client_secret="s1",
        )
        await get_access_token(
            token_url="https://auth.example.com/token",
            client_id="c1",
            client_secret="s1",
        )

    assert call_count == 1, "Token should have been served from cache on second call"


@pytest.mark.asyncio
async def test_acquire_token_refreshes_on_expiry() -> None:
    """Expired token triggers a new token request."""
    from mcp_fhir import smart_auth
    from mcp_fhir.smart_auth import _CachedToken, clear_token_cache

    clear_token_cache()

    # Pre-populate cache with an already-expired token
    cache_key = ("https://auth.example.com/token", "c2")
    smart_auth._cache[cache_key] = _CachedToken(
        access_token="old-token",
        expires_at=time.monotonic() - 1.0,  # expired 1 second ago
    )

    with respx.mock:
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(
                200,
                json={"access_token": "new-token", "expires_in": 300, "token_type": "Bearer"},
            )
        )
        token = await smart_auth.get_access_token(
            token_url="https://auth.example.com/token",
            client_id="c2",
            client_secret="s2",
        )

    assert token == "new-token"


@pytest.mark.asyncio
async def test_acquire_token_http_error() -> None:
    """HTTP 401 from token endpoint raises SmartAuthError."""
    from mcp_fhir.smart_auth import SmartAuthError, clear_token_cache, get_access_token

    clear_token_cache()

    with respx.mock:
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )
        with pytest.raises(SmartAuthError, match="401"):
            await get_access_token(
                token_url="https://auth.example.com/token",
                client_id="bad",
                client_secret="bad",
            )


@pytest.mark.asyncio
async def test_acquire_token_missing_access_token() -> None:
    """Response missing access_token field raises SmartAuthError."""
    from mcp_fhir.smart_auth import SmartAuthError, clear_token_cache, get_access_token

    clear_token_cache()

    with respx.mock:
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(200, json={"token_type": "Bearer"})
        )
        with pytest.raises(SmartAuthError, match="missing access_token"):
            await get_access_token(
                token_url="https://auth.example.com/token",
                client_id="c3",
                client_secret="s3",
            )


@pytest.mark.asyncio
async def test_discover_token_url_success() -> None:
    """SMART discovery extracts token_endpoint from .well-known/smart-configuration."""
    from mcp_fhir.smart_auth import discover_token_url

    with respx.mock:
        respx.get("https://fhir.example.com/.well-known/smart-configuration").mock(
            return_value=httpx.Response(
                200,
                json={"token_endpoint": "https://fhir.example.com/oauth2/token"},
            )
        )
        url = await discover_token_url("https://fhir.example.com")

    assert url == "https://fhir.example.com/oauth2/token"


@pytest.mark.asyncio
async def test_discover_token_url_fallback() -> None:
    """Discovery 404 falls back to {base}/oauth2/token."""
    from mcp_fhir.smart_auth import discover_token_url

    with respx.mock:
        respx.get("https://fhir.example.com/.well-known/smart-configuration").mock(
            return_value=httpx.Response(404)
        )
        url = await discover_token_url("https://fhir.example.com")

    assert url == "https://fhir.example.com/oauth2/token"


# ── http_client unit tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_fhir_headers_no_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """With SMART disabled, headers only contain Accept."""
    monkeypatch.setenv("SMART_ENABLED", "false")
    from importlib import reload

    import mcp_fhir.settings as s_mod

    reload(s_mod)
    import mcp_fhir.http_client as hc_mod

    reload(hc_mod)

    headers = await hc_mod.get_fhir_headers()
    assert headers == {"Accept": "application/fhir+json"}
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_get_fhir_headers_with_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """With SMART enabled, Bearer token appears in headers."""
    from mcp_fhir.smart_auth import clear_token_cache

    clear_token_cache()

    monkeypatch.setenv("SMART_ENABLED", "true")
    monkeypatch.setenv("SMART_CLIENT_ID", "client123")
    monkeypatch.setenv("SMART_CLIENT_SECRET", "secret456")
    monkeypatch.setenv("SMART_TOKEN_URL", "https://auth.example.com/token")

    from importlib import reload

    import mcp_fhir.settings as s_mod

    reload(s_mod)
    import mcp_fhir.http_client as hc_mod

    reload(hc_mod)
    hc_mod.reset_discovery_cache()

    with respx.mock:
        respx.post("https://auth.example.com/token").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "bearer-token-789",
                    "expires_in": 300,
                    "token_type": "Bearer",
                },
            )
        )
        headers = await hc_mod.get_fhir_headers()

    assert headers["Accept"] == "application/fhir+json"
    assert headers["Authorization"] == "Bearer bearer-token-789"
