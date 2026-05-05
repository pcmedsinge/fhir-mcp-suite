"""Unit tests for mcp-fhir tools (no external services required)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

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
async def test_fhir_read_live() -> None:
    """Reads a Patient from the public HAPI demo server."""
    from mcp_fhir.tools.fhir_search import fhir_search

    bundle = await fhir_search("Patient", {"_count": "1"})
    assert bundle.get("resourceType") == "Bundle"
    entries = bundle.get("entry", [])
    assert len(entries) >= 1
