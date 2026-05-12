"""check_drug_interactions — detect DDIs via FDA drug label API (OpenFDA).

NLM RxNav's /interaction endpoint was removed in May 2026 (API v3.1.353).
This implementation uses the FDA drug label database (api.fda.gov), which
contains structured drug interaction sections from FDA-approved labeling.
No API key required. Rate limit: 240 requests/minute.
"""

from __future__ import annotations

import re

import httpx
import structlog

log = structlog.get_logger(__name__)

_OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

# Map specific drug names to pharmacological class terms that appear in FDA labels.
# FDA labeling often uses class names ("ACE-inhibitors", "NSAIDs") rather than
# individual drug names, so we check both the drug name and its class aliases.
_CLASS_ALIASES: dict[str, list[str]] = {
    # ACE inhibitors
    "lisinopril":   ["lisinopril", "ACE", "ACE-inhibitor", "ACE inhibitor", "angiotensin-converting enzyme"],
    "enalapril":    ["enalapril", "ACE", "ACE-inhibitor", "angiotensin-converting enzyme"],
    "ramipril":     ["ramipril", "ACE", "ACE-inhibitor", "angiotensin-converting enzyme"],
    "captopril":    ["captopril", "ACE", "ACE-inhibitor", "angiotensin-converting enzyme"],
    # NSAIDs
    "ibuprofen":    ["ibuprofen", "NSAID", "NSAIDs", "non-steroidal anti-inflammatory", "nonsteroidal"],
    "naproxen":     ["naproxen", "NSAID", "NSAIDs", "non-steroidal anti-inflammatory"],
    "celecoxib":    ["celecoxib", "NSAID", "NSAIDs", "COX-2"],
    "diclofenac":   ["diclofenac", "NSAID", "NSAIDs", "non-steroidal anti-inflammatory"],
    "indomethacin": ["indomethacin", "NSAID", "NSAIDs"],
    # Anticoagulants / antiplatelets
    "warfarin":     ["warfarin", "coumarin", "anticoagulant"],
    "aspirin":      ["aspirin", "salicylate", "antiplatelet"],
    "clopidogrel":  ["clopidogrel", "antiplatelet"],
    # Statins
    "atorvastatin": ["atorvastatin", "statin", "HMG-CoA"],
    "simvastatin":  ["simvastatin", "statin", "HMG-CoA"],
    # Biguanides
    "metformin":    ["metformin", "biguanide"],
    # ARBs
    "losartan":     ["losartan", "ARB", "angiotensin II", "angiotensin receptor"],
    "valsartan":    ["valsartan", "ARB", "angiotensin II", "angiotensin receptor"],
    # SSRIs
    "fluoxetine":   ["fluoxetine", "SSRI", "serotonin reuptake"],
    "sertraline":   ["sertraline", "SSRI", "serotonin reuptake"],
    # Opioids
    "morphine":     ["morphine", "opioid"],
    "oxycodone":    ["oxycodone", "opioid"],
}


def _aliases(drug_name: str) -> list[str]:
    """Return search terms for a drug (name + pharmacological class aliases)."""
    canonical = drug_name.strip().lower()
    for key, terms in _CLASS_ALIASES.items():
        if key == canonical:
            return terms
    return [drug_name]


async def check_drug_interactions(drug_names: list[str]) -> dict:
    """Check for drug-drug interactions using FDA drug label data.

    Fetches each drug's FDA label and searches the drug_interactions section
    for mentions of the other drugs (by name or pharmacological class).

    Args:
        drug_names: List of 2–10 drug names (e.g. ["ibuprofen", "lisinopril"]).

    Returns:
        dict with keys: drugs, interaction_count, interactions, has_interactions,
        source, disclaimer.
    """
    if len(drug_names) < 2:
        raise ValueError("At least 2 drug names required.")
    if len(drug_names) > 10:
        raise ValueError("Maximum 10 drug names allowed.")

    interactions: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for primary_drug in drug_names:
            label_text, brand = await _fetch_interaction_text(client, primary_drug)
            if label_text is None:
                continue
            for other_drug in drug_names:
                if other_drug == primary_drug:
                    continue
                pair_key = tuple(sorted([primary_drug.lower(), other_drug.lower()]))
                if pair_key in seen_pairs:
                    continue
                excerpt = _find_mention(label_text, other_drug)
                if excerpt:
                    seen_pairs.add(pair_key)
                    interactions.append({
                        "drug_a": primary_drug,
                        "drug_b": other_drug,
                        "brand_name": brand or primary_drug,
                        "interaction_text": excerpt,
                        "source_label": "FDA approved labeling",
                    })

    return {
        "drugs": drug_names,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "has_interactions": len(interactions) > 0,
        "source": "FDA drug label database (api.fda.gov/drug/label)",
        "disclaimer": (
            "Interaction data sourced from FDA-approved drug labeling. "
            "Clinical significance depends on patient context. "
            "Always consult a pharmacist or prescriber."
        ),
    }


async def _fetch_interaction_text(
    client: httpx.AsyncClient, drug_name: str
) -> tuple[str | None, str | None]:
    """Fetch a drug's interaction section text from FDA label database."""
    params = {"search": f"openfda.generic_name:{drug_name}", "limit": 3}
    try:
        r = await client.get(_OPENFDA_BASE, params=params)
        if r.status_code == 404:
            return None, None
        r.raise_for_status()
        data = r.json()
        for result in data.get("results", []):
            di_sections = result.get("drug_interactions", [])
            if di_sections:
                text = " ".join(di_sections)
                brand_list = result.get("openfda", {}).get("brand_name", [])
                brand = brand_list[0] if brand_list else None
                return text, brand
        return None, None
    except httpx.HTTPStatusError as exc:
        log.warning("openfda_label_fetch_failed", drug=drug_name, status=exc.response.status_code)
        return None, None


def _find_mention(label_text: str, other_drug: str) -> str | None:
    """Return a relevant excerpt if other_drug (or its class) is mentioned in label_text."""
    for term in _aliases(other_drug):
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        m = pattern.search(label_text)
        if m:
            # Return ~300 chars of context around the match
            start = max(0, m.start() - 80)
            end = min(len(label_text), m.end() + 300)
            return label_text[start:end].strip()
    return None

