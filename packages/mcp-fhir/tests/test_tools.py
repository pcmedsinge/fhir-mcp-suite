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
