"""Unit tests for mcp-terminology tools (no external services required)."""

from __future__ import annotations

import pytest

# ── validation helpers ───────────────────────────────────────────────────────

def test_resolve_system_alias_loinc() -> None:
    from mcp_terminology.validation import resolve_system
    assert resolve_system("loinc") == "http://loinc.org"


def test_resolve_system_alias_snomed() -> None:
    from mcp_terminology.validation import resolve_system
    assert resolve_system("snomed") == "http://snomed.info/sct"
    assert resolve_system("snomed-ct") == "http://snomed.info/sct"


def test_resolve_system_alias_rxnorm() -> None:
    from mcp_terminology.validation import resolve_system
    assert resolve_system("rxnorm") == "http://www.nlm.nih.gov/research/umls/rxnorm"


def test_resolve_system_raw_url() -> None:
    from mcp_terminology.validation import resolve_system
    url = "http://loinc.org"
    assert resolve_system(url) == url


def test_resolve_system_rejects_unknown_alias() -> None:
    from mcp_terminology.validation import resolve_system
    with pytest.raises(ValueError, match="not a known alias"):
        resolve_system("not-a-real-system")


def test_resolve_system_rejects_empty() -> None:
    from mcp_terminology.validation import resolve_system
    with pytest.raises(ValueError, match="must not be empty"):
        resolve_system("")


def test_validate_code_ok() -> None:
    from mcp_terminology.validation import validate_code
    assert validate_code("8302-2") == "8302-2"
    assert validate_code("73211009") == "73211009"
    assert validate_code("E11.9") == "E11.9"


def test_validate_code_strips_whitespace() -> None:
    from mcp_terminology.validation import validate_code
    assert validate_code("  8302-2  ") == "8302-2"


def test_validate_code_rejects_injection() -> None:
    from mcp_terminology.validation import validate_code
    with pytest.raises(ValueError, match="Invalid code"):
        validate_code("'; DROP TABLE--")


def test_validate_code_rejects_empty() -> None:
    from mcp_terminology.validation import validate_code
    with pytest.raises(ValueError, match="must not be empty"):
        validate_code("")


def test_validate_url_ok() -> None:
    from mcp_terminology.validation import validate_url
    url = "http://hl7.org/fhir/ValueSet/administrative-gender"
    assert validate_url(url) == url


def test_validate_url_rejects_file_scheme() -> None:
    from mcp_terminology.validation import validate_url
    with pytest.raises(ValueError, match="absolute HTTP"):
        validate_url("file:///etc/passwd")


def test_sanitise_filter_strips_control_chars() -> None:
    from mcp_terminology.validation import sanitise_filter
    assert sanitise_filter("body\x00height") == "bodyheight"


def test_sanitise_filter_truncates() -> None:
    from mcp_terminology.validation import sanitise_filter
    assert len(sanitise_filter("a" * 300)) == 200


def test_validate_max_results_clamps() -> None:
    from mcp_terminology.validation import validate_max_results
    assert validate_max_results(0) == 1
    assert validate_max_results(200) == 100
    assert validate_max_results(20) == 20


# ── search_codes ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_codes_rejects_unsupported_system() -> None:
    from mcp_terminology.tools.search_codes import search_codes
    with pytest.raises(ValueError, match="not supported"):
        await search_codes(query="heart failure", system="icd-10-cm")


@pytest.mark.asyncio
async def test_search_codes_rejects_empty_query() -> None:
    from mcp_terminology.tools.search_codes import search_codes
    with pytest.raises(ValueError, match="must not be empty"):
        await search_codes(query="", system="loinc")


# ── translate_code ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_translate_code_rejects_bad_source_system() -> None:
    from mcp_terminology.tools.translate_code import translate_code
    with pytest.raises(ValueError, match="not a known alias"):
        await translate_code("12345", source_system="fake-system", target_system="icd-10-cm")


@pytest.mark.asyncio
async def test_translate_code_rejects_bad_target_system() -> None:
    from mcp_terminology.tools.translate_code import translate_code
    with pytest.raises(ValueError, match="not a known alias"):
        await translate_code("73211009", source_system="snomed", target_system="not-real")


# ── expand_valueset ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expand_valueset_rejects_bad_url() -> None:
    from mcp_terminology.tools.expand_valueset import expand_valueset
    with pytest.raises(ValueError, match="absolute HTTP"):
        await expand_valueset(url="not-a-url")


@pytest.mark.asyncio
async def test_expand_valueset_rejects_file_url() -> None:
    from mcp_terminology.tools.expand_valueset import expand_valueset
    with pytest.raises(ValueError, match="absolute HTTP"):
        await expand_valueset(url="file:///etc/passwd")


# ── lookup_code ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lookup_code_rejects_bad_system() -> None:
    from mcp_terminology.tools.lookup_code import lookup_code
    with pytest.raises(ValueError, match="not a known alias"):
        await lookup_code(system="not-real", code="123")


@pytest.mark.asyncio
async def test_lookup_code_rejects_bad_code() -> None:
    from mcp_terminology.tools.lookup_code import lookup_code
    with pytest.raises(ValueError, match="Invalid code"):
        await lookup_code(system="loinc", code="'; DROP TABLE--")


# ── integration (requires tx.fhir.org) ───────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.integration
async def test_lookup_loinc_body_height() -> None:
    from mcp_terminology.tools.lookup_code import lookup_code
    result = await lookup_code(system="loinc", code="8302-2")
    assert result["code"] == "8302-2"
    assert "height" in result["display"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_loinc_body_height() -> None:
    from mcp_terminology.tools.search_codes import search_codes
    result = await search_codes(query="body height", system="loinc", max_results=5)
    assert isinstance(result["results"], list)
    assert len(result["results"]) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_expand_administrative_gender() -> None:
    from mcp_terminology.tools.expand_valueset import expand_valueset
    result = await expand_valueset(
        url="http://hl7.org/fhir/ValueSet/administrative-gender"
    )
    codes = [c["code"] for c in result["codes"]]
    assert "male" in codes
    assert "female" in codes
