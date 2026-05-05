"""Unit tests for mcp-fhir tools (no external services required)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_fhir_read_invalid_id() -> None:
    from mcp_fhir.tools.fhir_read import fhir_read

    with pytest.raises(ValueError, match="Invalid FHIR resource ID"):
        await fhir_read("Patient", "../../etc/passwd")


@pytest.mark.asyncio
async def test_fhir_read_empty_args() -> None:
    from mcp_fhir.tools.fhir_read import fhir_read

    with pytest.raises(ValueError, match="must not be empty"):
        await fhir_read("", "123")


@pytest.mark.asyncio
async def test_fhir_search_invalid_resource_type() -> None:
    from mcp_fhir.tools.fhir_search import fhir_search

    with pytest.raises(ValueError, match="Invalid FHIR resource type"):
        await fhir_search("../../evil")


@pytest.mark.asyncio
async def test_fhir_search_strips_bad_params() -> None:
    """Parameter names with injection-style characters are silently dropped."""
    from mcp_fhir.tools.fhir_search import _validate_search_params

    result = _validate_search_params(
        {"family": "Smith", "'; DROP TABLE--": "evil", "_count": "10"}
    )
    assert "family" in result
    assert "_count" in result
    assert "'; DROP TABLE--" not in result


@pytest.mark.asyncio
async def test_fhir_search_next_ssrf_guard() -> None:
    """fhir_search_next must reject URLs pointing to a different host."""
    from mcp_fhir.tools.fhir_search import fhir_search_next

    with pytest.raises(ValueError, match="does not match configured"):
        await fhir_search_next("https://evil.example.com/fhir?page=2")


@pytest.mark.asyncio
async def test_fhir_search_next_rejects_non_http() -> None:
    from mcp_fhir.tools.fhir_search import fhir_search_next

    with pytest.raises(ValueError, match="absolute HTTP"):
        await fhir_search_next("file:///etc/passwd")


def test_extract_next_link_present() -> None:
    from mcp_fhir.tools.fhir_search import _extract_next_link

    bundle = {
        "link": [
            {"relation": "self", "url": "https://hapi.fhir.org/baseR4/Patient"},
            {"relation": "next", "url": "https://hapi.fhir.org/baseR4/Patient?_page=2"},
        ]
    }
    assert _extract_next_link(bundle) == "https://hapi.fhir.org/baseR4/Patient?_page=2"


def test_extract_next_link_absent() -> None:
    from mcp_fhir.tools.fhir_search import _extract_next_link

    bundle = {"link": [{"relation": "self", "url": "https://hapi.fhir.org/baseR4/Patient"}]}
    assert _extract_next_link(bundle) is None


def test_extract_next_link_rejects_bad_url() -> None:
    """Malicious server cannot inject a file:// URL via the link array."""
    from mcp_fhir.tools.fhir_search import _extract_next_link

    bundle = {"link": [{"relation": "next", "url": "file:///etc/shadow"}]}
    assert _extract_next_link(bundle) is None


@pytest.mark.asyncio
async def test_validate_against_profile_bad_profile() -> None:
    from mcp_fhir.tools.validate_profile import validate_against_profile

    with pytest.raises(ValueError, match="profile must be a URL"):
        await validate_against_profile(
            resource={"resourceType": "Patient"}, profile="not-a-url-or-alias"
        )


@pytest.mark.asyncio
async def test_validate_against_profile_missing_resource_type() -> None:
    from mcp_fhir.tools.validate_profile import validate_against_profile

    with pytest.raises(ValueError, match="resourceType"):
        await validate_against_profile(resource={"id": "123"})


@pytest.mark.asyncio
async def test_validate_against_profile_alias_resolves() -> None:
    from mcp_fhir.tools.validate_profile import PROFILE_ALIASES, _resolve_profile

    assert _resolve_profile("us-core-patient") == PROFILE_ALIASES["us-core-patient"]
    assert _resolve_profile("https://example.com/profile") == "https://example.com/profile"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fhir_search_live() -> None:
    """Reads a Patient from the public HAPI demo server."""
    from mcp_fhir.tools.fhir_search import fhir_search

    bundle = await fhir_search("Patient", {"_count": "1"})
    assert bundle.get("resourceType") == "Bundle"
    entries = bundle.get("entry", [])
    assert len(entries) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fhir_capabilities_live() -> None:
    """Fetches the CapabilityStatement from the public HAPI demo server."""
    from mcp_fhir.tools.fhir_capabilities import fhir_capabilities

    result = await fhir_capabilities()
    assert result.get("fhir_version") is not None
    assert result.get("resource_count", 0) > 0


# ── SMART integration (requires real sandbox credentials in .env) ─────────────
# Run with:  pytest -m "smart_integration" packages/mcp-fhir/tests/
# Requires .env with SMART_ENABLED=true + SMART_CLIENT_ID + SMART_CLIENT_SECRET
#           + SMART_TOKEN_URL + FHIR_BASE_URL pointing at the sandbox.

@pytest.mark.asyncio
@pytest.mark.smart_integration
async def test_smart_token_acquisition_epic_sandbox() -> None:
    """Acquire a real token from Epic sandbox (requires .env credentials)."""
    import os
    if not os.getenv("SMART_CLIENT_ID"):
        pytest.skip("SMART_CLIENT_ID not configured — set sandbox credentials in .env")

    from mcp_fhir.smart_auth import get_access_token, clear_token_cache
    from mcp_fhir.settings import settings
    clear_token_cache()

    token_url = settings.smart_token_url or ""
    if not token_url:
        from mcp_fhir.smart_auth import discover_token_url
        token_url = await discover_token_url(settings.fhir_base_url)

    token = await get_access_token(
        token_url=token_url,
        client_id=settings.smart_client_id,
        client_secret=settings.smart_client_secret.get_secret_value(),
        scopes=settings.smart_scopes,
    )
    assert token, "Expected non-empty access token"
    assert len(token) > 10


@pytest.mark.asyncio
@pytest.mark.smart_integration
async def test_authenticated_fhir_search_epic_sandbox() -> None:
    """Run fhir_search with real Bearer token against Epic/Cerner sandbox."""
    import os
    if not os.getenv("SMART_ENABLED"):
        pytest.skip("SMART_ENABLED not set — configure sandbox credentials in .env")

    from mcp_fhir.smart_auth import clear_token_cache
    from mcp_fhir.tools.fhir_search import fhir_search
    clear_token_cache()

    bundle = await fhir_search("Patient", {"_count": "1"})
    assert bundle.get("resourceType") == "Bundle"


@pytest.mark.asyncio
@pytest.mark.smart_integration
async def test_authenticated_fhir_read_epic_sandbox() -> None:
    """Read a known synthetic patient from Epic sandbox with Bearer auth."""
    import os
    if not os.getenv("SMART_ENABLED"):
        pytest.skip("SMART_ENABLED not set — configure sandbox credentials in .env")

    from mcp_fhir.smart_auth import clear_token_cache
    from mcp_fhir.tools.fhir_search import fhir_search
    from mcp_fhir.tools.fhir_read import fhir_read
    clear_token_cache()

    # First search to find any patient ID in this sandbox
    bundle = await fhir_search("Patient", {"_count": "1"})
    entries = bundle.get("entry", [])
    if not entries:
        pytest.skip("No patients found in sandbox — check FHIR_BASE_URL")

    patient_id = entries[0]["resource"]["id"]
    resource = await fhir_read("Patient", patient_id)
    assert resource.get("resourceType") == "Patient"
    assert resource.get("id") == patient_id

