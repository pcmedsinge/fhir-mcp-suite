"""Input validation for mcp-clinical-reasoner tools."""

from __future__ import annotations

import re

# RxCUI: 1-8 decimal digits (NLM RxNorm concept IDs are typically 3-7 digits).
_RXCUI_RE = re.compile(r"^\d{1,8}$")

# Drug/allergen names: letters, digits, hyphens, spaces, periods, parentheses, slashes.
# Blocks HTML/script injection characters.
_DRUG_NAME_RE = re.compile(r"^[a-zA-Z0-9\-\. ()/]{1,200}$")


def validate_rxcui(rxcui: str) -> str:
    """Return stripped RxCUI, raising ValueError if invalid."""
    v = rxcui.strip()
    if not v:
        raise ValueError("rxcui must not be empty")
    if not _RXCUI_RE.match(v):
        raise ValueError(f"Invalid RxCUI {v!r}. Must be 1-8 decimal digits (e.g. '6809').")
    return v


def validate_drug_name(name: str) -> str:
    """Return stripped drug name, raising ValueError if invalid."""
    v = name.strip()
    if not v:
        raise ValueError("drug name must not be empty")
    if not _DRUG_NAME_RE.match(v):
        raise ValueError(
            f"Invalid drug name {v!r}. Use only letters, digits, hyphens, spaces, '.', '()', '/'."
        )
    return v


def validate_rxcuis_list(rxcuis: list[str], min_len: int = 2, max_len: int = 10) -> list[str]:
    """Validate a list of RxCUI strings for the interaction check tool."""
    if len(rxcuis) < min_len:
        raise ValueError(
            f"At least {min_len} RxCUIs required for interaction check; got {len(rxcuis)}."
        )
    if len(rxcuis) > max_len:
        raise ValueError(f"At most {max_len} RxCUIs allowed; got {len(rxcuis)}.")
    return [validate_rxcui(r) for r in rxcuis]


def validate_dose(dose_mg: float) -> float:
    """Return dose_mg, raising ValueError if out of bounds."""
    if dose_mg <= 0:
        raise ValueError(f"dose_mg must be positive; got {dose_mg}.")
    if dose_mg > 100_000:
        raise ValueError(
            f"dose_mg={dose_mg} exceeds maximum allowed value (100 000 mg). "
            "Check units — dose should be in milligrams."
        )
    return dose_mg


def validate_allergies_list(allergies: list[str], max_len: int = 50) -> list[str]:
    """Validate a list of allergen names."""
    if len(allergies) > max_len:
        raise ValueError(f"Allergen list too long ({len(allergies)}); max {max_len}.")
    return [validate_drug_name(a) for a in allergies]


def is_rxcui(value: str) -> bool:
    """Return True if value looks like a numeric RxCUI."""
    return bool(_RXCUI_RE.match(value.strip()))
