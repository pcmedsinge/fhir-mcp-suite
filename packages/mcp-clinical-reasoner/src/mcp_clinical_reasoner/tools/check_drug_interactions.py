"""check_drug_interactions — detect DDIs via NLM RxNav interaction API."""

from __future__ import annotations

import httpx
import structlog

from mcp_clinical_reasoner.settings import settings
from mcp_clinical_reasoner.validation import validate_rxcuis_list

log = structlog.get_logger(__name__)

_SEVERITY_RANK = {"high": 0, "moderate": 1, "low": 2, "unknown": 3}


async def check_drug_interactions(rxcuis: list[str]) -> dict:
    """Check drug-drug interactions for a set of RxNorm CUIs.

    Uses the NLM RxNav interaction API
    (https://rxnav.nlm.nih.gov/InteractionAPIs.html).

    Args:
        rxcuis: List of 2–10 RxNorm CUI strings (e.g. ["6809", "29046"]).

    Returns:
        dict with keys: rxcuis, drugs, interaction_count, interactions,
        has_high_severity, has_moderate_severity, sources, disclaimer.
    """
    validated = validate_rxcuis_list(rxcuis)

    url = f"{settings.rxnav_base_url}/interaction/list.json"
    params = {"rxcuis": " ".join(validated)}

    async with httpx.AsyncClient(timeout=settings.rxnav_timeout_s) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()

    data = r.json()
    interactions, sources = _parse_interactions(data)

    has_high = any(i["severity"].lower() == "high" for i in interactions)
    has_moderate = any(i["severity"].lower() == "moderate" for i in interactions)

    # Sort by severity (high first)
    interactions.sort(key=lambda x: _SEVERITY_RANK.get(x["severity"].lower(), 3))

    return {
        "rxcuis": validated,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "has_high_severity": has_high,
        "has_moderate_severity": has_moderate,
        "sources": sources,
        "disclaimer": (
            "Interaction data sourced from NLM RxNav (DrugBank, ONCHigh, etc.). "
            "Clinical significance depends on patient context. "
            "Always consult a pharmacist or prescriber."
        ),
    }


def _parse_interactions(data: dict) -> tuple[list[dict], list[str]]:
    """Parse the fullInteractionTypeGroup response from RxNav."""
    interactions: list[dict] = []
    sources: list[str] = []

    for group in data.get("fullInteractionTypeGroup") or []:
        source_name = group.get("sourceName", "Unknown")
        if source_name not in sources:
            sources.append(source_name)

        for full_type in group.get("fullInteractionType") or []:
            # Extract the two drug concepts involved
            min_concepts = full_type.get("minConcept") or []
            drug_names = [c.get("name", "") for c in min_concepts]
            drug_rxcuis = [c.get("rxcui", "") for c in min_concepts]

            for pair in full_type.get("interactionPair") or []:
                severity = pair.get("severity", "unknown")
                description = pair.get("description", "")

                interactions.append({
                    "drug_1": drug_names[0] if len(drug_names) > 0 else "",
                    "drug_2": drug_names[1] if len(drug_names) > 1 else "",
                    "rxcui_1": drug_rxcuis[0] if len(drug_rxcuis) > 0 else "",
                    "rxcui_2": drug_rxcuis[1] if len(drug_rxcuis) > 1 else "",
                    "severity": severity,
                    "description": description,
                    "source": source_name,
                })

    return interactions, sources
