"""lookup_drug — resolve a drug name or RxNorm CUI to structured drug info."""

from __future__ import annotations

import httpx
import structlog

from mcp_clinical_reasoner.constants import ALLERGEN_CLASSES, DOSE_TABLE, DRUG_ALIASES, DRUG_TO_CLASSES
from mcp_clinical_reasoner.settings import settings
from mcp_clinical_reasoner.validation import is_rxcui, validate_drug_name, validate_rxcui

log = structlog.get_logger(__name__)


async def lookup_drug(name_or_rxcui: str) -> dict:
    """Look up a drug by name or RxNorm CUI.

    Returns structured info: RxCUI, canonical name, drug classes, dose rules
    (if the drug is in the built-in dose table), and allergen class membership.

    Args:
        name_or_rxcui: Drug name (e.g. "metformin") or RxNorm CUI (e.g. "6809").

    Returns:
        dict with keys: rxcui, name, tty, found, dose_info, allergen_classes,
        source, disclaimer.
    """
    raw = name_or_rxcui.strip()

    if is_rxcui(raw):
        rxcui = validate_rxcui(raw)
        props = await _fetch_properties(rxcui)
    else:
        name = validate_drug_name(raw)
        rxcui, props = await _resolve_name(name)

    if rxcui is None:
        return {
            "found": False,
            "input": raw,
            "message": f"Drug {raw!r} not found in RxNorm. Check spelling or try the RxNorm CUI.",
        }

    canonical = props.get("name", raw).lower()

    # Dose info from built-in table (canonical name or alias lookup)
    dose_info: dict | None = None
    table_key = DRUG_ALIASES.get(canonical)
    if table_key:
        entry = DOSE_TABLE[table_key]
        dose_info = {
            "max_single_dose_mg": entry["max_single_dose_mg"],
            "max_daily_dose_mg": entry["max_daily_dose_mg"],
            "typical_adult_dose_mg": entry["typical_adult_dose_mg"],
            "routes": entry["routes"],
            "notes": entry["notes"],
        }

    # Allergen class membership
    allergen_classes = DRUG_TO_CLASSES.get(canonical, [])

    return {
        "found": True,
        "rxcui": rxcui,
        "name": props.get("name", raw),
        "tty": props.get("tty", ""),
        "language": props.get("language", "ENG"),
        "dose_info": dose_info,
        "allergen_classes": allergen_classes,
        "source": "RxNorm / NLM RxNav",
        "disclaimer": (
            "Dose ranges are general adult references only. "
            "Always verify dosing with a licensed prescriber or pharmacist."
        ),
    }


async def _fetch_properties(rxcui: str) -> dict:
    """Fetch RxCUI properties from RxNav."""
    url = f"{settings.rxnav_base_url}/rxcui/{rxcui}/properties.json"
    async with httpx.AsyncClient(timeout=settings.rxnav_timeout_s) as client:
        r = await client.get(url)
        r.raise_for_status()
    data = r.json()
    props = data.get("properties") or {}
    return props


async def _resolve_name(name: str) -> tuple[str | None, dict]:
    """Resolve a drug name to RxCUI + properties via RxNav /rxcui.json."""
    url = f"{settings.rxnav_base_url}/rxcui.json"
    async with httpx.AsyncClient(timeout=settings.rxnav_timeout_s) as client:
        r = await client.get(url, params={"name": name, "search": "1"})
        r.raise_for_status()
    data = r.json()

    rxnorm_ids: list[str] = data.get("idGroup", {}).get("rxnormId") or []
    if not rxnorm_ids:
        return None, {}

    rxcui = rxnorm_ids[0]
    props = await _fetch_properties(rxcui)
    return rxcui, props
