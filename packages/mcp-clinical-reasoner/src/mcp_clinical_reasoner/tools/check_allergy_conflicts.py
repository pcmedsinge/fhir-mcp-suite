"""check_allergy_conflicts — rule-based cross-reactivity check.

No network calls — uses ALLERGEN_CLASSES and DRUG_TO_CLASSES from constants.py.
"""

from __future__ import annotations

import structlog

from mcp_clinical_reasoner.constants import ALLERGEN_CLASSES, DRUG_ALIASES, DRUG_TO_CLASSES
from mcp_clinical_reasoner.validation import validate_allergies_list, validate_drug_name

log = structlog.get_logger(__name__)

_CROSS_REACTIVITY_NOTES = {
    ("penicillin", "cephalosporin"): (
        "Cross-reactivity between penicillins and cephalosporins is estimated at 1–2% "
        "for patients with true penicillin allergy. Side-chain similarity determines risk."
    ),
    ("cephalosporin", "penicillin"): (
        "Cross-reactivity between cephalosporins and penicillins is estimated at 1–2%. "
        "Risk is side-chain dependent; consult allergy specialist if history is unclear."
    ),
    ("nsaid", "nsaid"): (
        "Cross-reactivity within NSAID class is common; aspirin-sensitive patients "
        "may react to other NSAIDs. Consider selective COX-2 inhibitors with caution."
    ),
    ("sulfonamide", "sulfonamide"): (
        "Sulfonamide antibiotics may cross-react; non-antibiotic sulfonamides "
        "(thiazides, furosemide) carry lower risk of true cross-reactivity."
    ),
}


async def check_allergy_conflicts(drug: str, allergies: list[str]) -> dict:
    """Check a target drug for potential conflicts with a patient's known allergies.

    Uses the built-in ALLERGEN_CLASSES cross-reactivity table.
    No external API calls are made.

    Args:
        drug:      Drug name to check (e.g. "ceftriaxone", "ibuprofen").
        allergies: List of known allergen names or class names
                   (e.g. ["penicillin", "amoxicillin", "sulfa"]).

    Returns:
        dict with keys: drug, canonical_drug, allergies_checked, conflicts,
        has_conflicts, disclaimer.
        Each conflict has: allergen, conflict_type, target_class, allergen_class,
        notes.
    """
    drug_name = validate_drug_name(drug)
    validated_allergies = validate_allergies_list(allergies)

    drug_lower = drug_name.lower()
    # Try alias resolution for canonical name
    canonical = DRUG_ALIASES.get(drug_lower, drug_lower)
    # Classes the target drug belongs to
    target_classes = DRUG_TO_CLASSES.get(canonical, [])
    # Also check if the drug name appears directly in any allergen class list
    if not target_classes:
        for cls_name, members in ALLERGEN_CLASSES.items():
            if drug_lower in members:
                target_classes.append(cls_name)

    conflicts: list[dict] = []

    for allergen in validated_allergies:
        allergen_lower = allergen.lower()
        found_conflict = False

        # 1. Direct name match: allergen IS the target drug
        if allergen_lower == drug_lower or allergen_lower == canonical:
            conflicts.append({
                "allergen": allergen,
                "conflict_type": "direct_match",
                "target_class": None,
                "allergen_class": None,
                "notes": f"Patient is allergic to {allergen!r}, which is the same drug as {drug!r}.",
            })
            found_conflict = True

        if found_conflict:
            continue

        # 2. Allergen is a class name, and target drug is in that class
        if allergen_lower in ALLERGEN_CLASSES:
            if canonical in ALLERGEN_CLASSES[allergen_lower] or drug_lower in ALLERGEN_CLASSES[allergen_lower]:
                note = _CROSS_REACTIVITY_NOTES.get((allergen_lower, allergen_lower), "")
                conflicts.append({
                    "allergen": allergen,
                    "conflict_type": "class_membership",
                    "target_class": allergen_lower,
                    "allergen_class": allergen_lower,
                    "notes": note or f"{drug!r} is a member of the {allergen!r} drug class.",
                })
                found_conflict = True

        if found_conflict:
            continue

        # 3. Allergen is a specific drug; check if it shares a class with the target
        allergen_classes = DRUG_TO_CLASSES.get(allergen_lower, [])
        for allergen_cls in allergen_classes:
            if allergen_cls in target_classes:
                note = _CROSS_REACTIVITY_NOTES.get(
                    (allergen_cls, allergen_cls),
                    _CROSS_REACTIVITY_NOTES.get((allergen_cls, allergen_lower), ""),
                )
                conflicts.append({
                    "allergen": allergen,
                    "conflict_type": "cross_reactivity",
                    "target_class": allergen_cls,
                    "allergen_class": allergen_cls,
                    "notes": (
                        note
                        or f"Both {drug!r} and the known allergen {allergen!r} "
                        f"belong to the '{allergen_cls}' drug class."
                    ),
                })
                break  # report once per allergen

    return {
        "drug": drug_name,
        "canonical_drug": canonical,
        "drug_classes": target_classes,
        "allergies_checked": validated_allergies,
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
        "disclaimer": (
            "Rule-based check using built-in cross-reactivity table. "
            "This does NOT replace a clinical allergy assessment. "
            "Always obtain a detailed allergy history and consult a pharmacist or allergist."
        ),
    }
