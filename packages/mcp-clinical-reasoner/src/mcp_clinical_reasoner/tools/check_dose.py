"""check_dose — rule-based dose range check against built-in table.

No network calls — uses the DOSE_TABLE in constants.py.
"""

from __future__ import annotations

from typing import Any

import structlog

from mcp_clinical_reasoner.constants import DOSE_TABLE, DRUG_ALIASES
from mcp_clinical_reasoner.validation import validate_dose, validate_drug_name

log = structlog.get_logger(__name__)

# Approximate times-per-day mapping for common frequency strings.
_FREQUENCY_MAP: dict[str, float] = {
    "qd": 1.0, "daily": 1.0, "once": 1.0, "once daily": 1.0, "od": 1.0,
    "bid": 2.0, "twice daily": 2.0, "q12h": 2.0, "q12": 2.0,
    "tid": 3.0, "three times daily": 3.0, "q8h": 3.0, "q8": 3.0,
    "qid": 4.0, "four times daily": 4.0, "q6h": 4.0, "q6": 4.0,
    "q4h": 6.0, "q4": 6.0, "six times daily": 6.0,
    "prn": 4.0,  # assume max 4x/day for PRN without other context
}


def _parse_frequency(freq: str) -> float | None:
    """Return doses-per-day for a frequency string, or None if unrecognised."""
    f = freq.strip().lower()
    return _FREQUENCY_MAP.get(f)


async def check_dose(drug: str, dose_mg: float, frequency: str = "") -> dict[str, Any]:
    """Check a proposed dose against the built-in dose reference table.

    Args:
        drug:      Drug name (e.g. "ibuprofen") or a brand alias (e.g. "Advil").
        dose_mg:   Proposed single dose in milligrams.
        frequency: Dosing frequency (e.g. "bid", "q8h", "daily"). Optional.

    Returns:
        dict with keys: drug, canonical_name, rxcui, proposed_dose_mg,
        max_single_dose_mg, max_daily_dose_mg, estimated_daily_dose_mg,
        assessment, frequency_recognised, notes, source, disclaimer.
        assessment ∈ {within_range, exceeds_single_dose, exceeds_daily_dose,
                      below_typical, unknown_drug}.
    """
    name = validate_drug_name(drug)
    dose = validate_dose(dose_mg)

    canonical = DRUG_ALIASES.get(name.lower())
    if canonical is None:
        return {
            "drug": name,
            "canonical_name": None,
            "found_in_table": False,
            "assessment": "unknown_drug",
            "proposed_dose_mg": dose,
            "message": (
                f"Drug {name!r} is not in the built-in dose table (~20 common drugs). "
                "Use lookup_drug to verify the RxNorm name, then consult a "
                "clinical reference or pharmacist."
            ),
            "source": "rule-based (mcp-clinical-reasoner built-in table)",
            "disclaimer": "Built-in table covers ~20 common drugs only.",
        }

    entry = DOSE_TABLE[canonical]
    max_single = entry["max_single_dose_mg"]
    max_daily = entry["max_daily_dose_mg"]
    typical = entry["typical_adult_dose_mg"]

    # Estimate daily dose if frequency given
    freq_lower = frequency.strip().lower()
    times_per_day = _parse_frequency(freq_lower) if freq_lower else None
    estimated_daily: float | None = dose * times_per_day if times_per_day else None

    # Determine assessment
    if dose > max_single:
        assessment = "exceeds_single_dose"
    elif estimated_daily is not None and estimated_daily > max_daily:
        assessment = "exceeds_daily_dose"
    elif dose < typical * 0.25:
        assessment = "below_typical"
    else:
        assessment = "within_range"

    return {
        "drug": name,
        "canonical_name": canonical,
        "rxcui": entry["rxcui"],
        "found_in_table": True,
        "proposed_dose_mg": dose,
        "frequency": frequency or None,
        "frequency_recognised": times_per_day is not None if freq_lower else None,
        "estimated_daily_dose_mg": round(estimated_daily, 2) if estimated_daily else None,
        "max_single_dose_mg": max_single,
        "max_daily_dose_mg": max_daily,
        "typical_adult_dose_mg": typical,
        "routes": entry["routes"],
        "assessment": assessment,
        "notes": entry["notes"],
        "source": "rule-based (mcp-clinical-reasoner built-in table)",
        "disclaimer": (
            "Reference values are general adult doses from standard references. "
            "Dose must be individualised; always verify with a prescriber or pharmacist."
        ),
    }
