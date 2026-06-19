"""Unit tests for mcp-clinical-reasoner (no network required)."""

from __future__ import annotations

import pytest

# ── validation ───────────────────────────────────────────────────────────────


def test_validate_rxcui_valid() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcui

    assert validate_rxcui("6809") == "6809"
    assert validate_rxcui("  29046  ") == "29046"


def test_validate_rxcui_rejects_empty() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcui

    with pytest.raises(ValueError, match="must not be empty"):
        validate_rxcui("")


def test_validate_rxcui_rejects_alpha() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcui

    with pytest.raises(ValueError, match="Invalid RxCUI"):
        validate_rxcui("abc")


def test_validate_rxcui_rejects_too_long() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcui

    with pytest.raises(ValueError, match="Invalid RxCUI"):
        validate_rxcui("123456789")  # 9 digits


def test_validate_drug_name_valid() -> None:
    from mcp_clinical_reasoner.validation import validate_drug_name

    assert validate_drug_name("metformin") == "metformin"
    assert validate_drug_name("  amoxicillin-clavulanate  ") == "amoxicillin-clavulanate"


def test_validate_drug_name_rejects_injection() -> None:
    from mcp_clinical_reasoner.validation import validate_drug_name

    with pytest.raises(ValueError, match="Invalid drug name"):
        validate_drug_name("<script>alert(1)</script>")


def test_validate_drug_name_rejects_empty() -> None:
    from mcp_clinical_reasoner.validation import validate_drug_name

    with pytest.raises(ValueError, match="must not be empty"):
        validate_drug_name("")


def test_validate_rxcuis_list_ok() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcuis_list

    result = validate_rxcuis_list(["6809", "29046"])
    assert result == ["6809", "29046"]


def test_validate_rxcuis_list_too_few() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcuis_list

    with pytest.raises(ValueError, match="At least 2"):
        validate_rxcuis_list(["6809"])


def test_validate_rxcuis_list_too_many() -> None:
    from mcp_clinical_reasoner.validation import validate_rxcuis_list

    with pytest.raises(ValueError, match="At most 10"):
        validate_rxcuis_list([str(i) for i in range(1, 13)])


def test_validate_dose_valid() -> None:
    from mcp_clinical_reasoner.validation import validate_dose

    assert validate_dose(500.0) == 500.0


def test_validate_dose_rejects_zero() -> None:
    from mcp_clinical_reasoner.validation import validate_dose

    with pytest.raises(ValueError, match="must be positive"):
        validate_dose(0.0)


def test_validate_dose_rejects_negative() -> None:
    from mcp_clinical_reasoner.validation import validate_dose

    with pytest.raises(ValueError, match="must be positive"):
        validate_dose(-10.0)


def test_validate_dose_rejects_absurd() -> None:
    from mcp_clinical_reasoner.validation import validate_dose

    with pytest.raises(ValueError, match="exceeds maximum"):
        validate_dose(200_000.0)


def test_is_rxcui() -> None:
    from mcp_clinical_reasoner.validation import is_rxcui

    assert is_rxcui("6809") is True
    assert is_rxcui("metformin") is False
    assert is_rxcui("12345678") is True
    assert is_rxcui("123456789") is False  # 9 digits


# ── check_dose ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_dose_within_range() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    result = await check_dose("ibuprofen", 400.0, "tid")
    assert result["assessment"] == "within_range"
    assert result["found_in_table"] is True
    assert result["canonical_name"] == "ibuprofen"
    assert result["estimated_daily_dose_mg"] == 1200.0


@pytest.mark.asyncio
async def test_check_dose_exceeds_single() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    result = await check_dose("ibuprofen", 1200.0)
    assert result["assessment"] == "exceeds_single_dose"


@pytest.mark.asyncio
async def test_check_dose_exceeds_daily() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    # 800 mg qid = 3200 mg/day, max is 3200 — so exactly at limit = within_range
    # Use 600 mg x6 = 3600 > 3200
    result = await check_dose("ibuprofen", 600.0, "q4h")
    assert result["assessment"] == "exceeds_daily_dose"
    assert result["estimated_daily_dose_mg"] == 3600.0


@pytest.mark.asyncio
async def test_check_dose_brand_alias() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    # "tylenol" is an alias for acetaminophen
    result = await check_dose("tylenol", 500.0)
    assert result["found_in_table"] is True
    assert result["canonical_name"] == "acetaminophen"


@pytest.mark.asyncio
async def test_check_dose_unknown_drug() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    result = await check_dose("imaginarydrug", 100.0)
    assert result["assessment"] == "unknown_drug"
    assert result["found_in_table"] is False


@pytest.mark.asyncio
async def test_check_dose_rejects_bad_name() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    with pytest.raises(ValueError, match="Invalid drug name"):
        await check_dose("<script>", 100.0)


@pytest.mark.asyncio
async def test_check_dose_rejects_zero_dose() -> None:
    from mcp_clinical_reasoner.tools.check_dose import check_dose

    with pytest.raises(ValueError, match="must be positive"):
        await check_dose("ibuprofen", 0.0)


# ── check_allergy_conflicts ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allergy_direct_match() -> None:
    from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts

    result = await check_allergy_conflicts("ibuprofen", ["ibuprofen"])
    assert result["has_conflicts"] is True
    assert result["conflicts"][0]["conflict_type"] == "direct_match"


@pytest.mark.asyncio
async def test_allergy_class_membership() -> None:
    from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts

    # ceftriaxone is a cephalosporin; allergen = "cephalosporin" (class name)
    result = await check_allergy_conflicts("ceftriaxone", ["cephalosporin"])
    assert result["has_conflicts"] is True
    assert result["conflicts"][0]["conflict_type"] == "class_membership"


@pytest.mark.asyncio
async def test_allergy_cross_reactivity() -> None:
    from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts

    # naproxen is in the nsaid class; known allergen is ibuprofen (also nsaid)
    result = await check_allergy_conflicts("naproxen", ["ibuprofen"])
    assert result["has_conflicts"] is True
    assert result["conflicts"][0]["conflict_type"] == "cross_reactivity"


@pytest.mark.asyncio
async def test_allergy_no_conflict() -> None:
    from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts

    result = await check_allergy_conflicts("metformin", ["penicillin"])
    assert result["has_conflicts"] is False
    assert result["conflicts"] == []


@pytest.mark.asyncio
async def test_allergy_empty_list_no_conflict() -> None:
    from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts

    result = await check_allergy_conflicts("ibuprofen", [])
    assert result["has_conflicts"] is False


@pytest.mark.asyncio
async def test_allergy_rejects_bad_drug_name() -> None:
    from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts

    with pytest.raises(ValueError, match="Invalid drug name"):
        await check_allergy_conflicts("; rm -rf /", ["penicillin"])


# ── check_drug_interactions (validation only, no network) ────────────────────


@pytest.mark.asyncio
async def test_interactions_rejects_single_rxcui() -> None:
    from mcp_clinical_reasoner.tools.check_drug_interactions import check_drug_interactions

    with pytest.raises(ValueError, match="At least 2"):
        await check_drug_interactions(["6809"])


@pytest.mark.asyncio
async def test_interactions_rejects_too_many() -> None:
    from mcp_clinical_reasoner.tools.check_drug_interactions import check_drug_interactions

    with pytest.raises(ValueError, match="Maximum 10"):
        await check_drug_interactions([str(i) for i in range(1, 13)])


# ── lookup_drug (validation only, no network) ────────────────────────────────


@pytest.mark.asyncio
async def test_lookup_drug_rejects_empty() -> None:
    from mcp_clinical_reasoner.tools.lookup_drug import lookup_drug

    with pytest.raises(ValueError, match="must not be empty"):
        await lookup_drug("")


@pytest.mark.asyncio
async def test_lookup_drug_rejects_injection() -> None:
    from mcp_clinical_reasoner.tools.lookup_drug import lookup_drug

    with pytest.raises(ValueError, match="Invalid drug name"):
        await lookup_drug("<script>alert()</script>")


# ── constants sanity ─────────────────────────────────────────────────────────


def test_all_dose_table_entries_have_required_fields() -> None:
    from mcp_clinical_reasoner.constants import DOSE_TABLE

    required = {"rxcui", "max_single_dose_mg", "max_daily_dose_mg", "routes", "notes"}
    for name, entry in DOSE_TABLE.items():
        missing = required - entry.keys()
        assert not missing, f"{name!r} is missing fields: {missing}"


def test_drug_aliases_coverage() -> None:
    from mcp_clinical_reasoner.constants import DOSE_TABLE, DRUG_ALIASES

    for name in DOSE_TABLE:
        assert name in DRUG_ALIASES, f"canonical name {name!r} not in DRUG_ALIASES"


def test_allergen_classes_nonempty() -> None:
    from mcp_clinical_reasoner.constants import ALLERGEN_CLASSES

    for cls, members in ALLERGEN_CLASSES.items():
        assert len(members) >= 2, f"Class {cls!r} has fewer than 2 members"


# ── integration (requires network → rxnav.nlm.nih.gov) ───────────────────────


@pytest.mark.asyncio
@pytest.mark.integration
async def test_lookup_metformin_by_name() -> None:
    from mcp_clinical_reasoner.tools.lookup_drug import lookup_drug

    result = await lookup_drug("metformin")
    assert result["found"] is True
    assert result["rxcui"] == "6809"
    assert "metformin" in result["name"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_lookup_metformin_by_rxcui() -> None:
    from mcp_clinical_reasoner.tools.lookup_drug import lookup_drug

    result = await lookup_drug("6809")
    assert result["found"] is True
    assert "metformin" in result["name"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_interactions_simvastatin_fluconazole() -> None:
    # simvastatin=36567, fluconazole=4450 — known high-severity DDI
    from mcp_clinical_reasoner.tools.check_drug_interactions import check_drug_interactions

    result = await check_drug_interactions(["36567", "4450"])
    assert result["interaction_count"] >= 1
    assert result["has_high_severity"] is True
