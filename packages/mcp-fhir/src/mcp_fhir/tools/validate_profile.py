"""Tool: validate_against_profile — validate a FHIR resource against a profile URL."""

from __future__ import annotations

from typing import Any

import structlog
from fhir_mcp_shared.langfuse import span
from fhir_mcp_shared.models.validation import ValidationReport

from mcp_fhir.hapi.client import validate_resource

log = structlog.get_logger(__name__)

# Supported profile shorthand aliases → canonical URL
PROFILE_ALIASES: dict[str, str] = {
    "us-core-patient": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient",
    "us-core-observation": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-clinical-result",
    "us-core-condition": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns",
    "us-core-medication-request": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationrequest",
    "us-core-encounter": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter",
    "ips-patient": "http://hl7.org/fhir/uv/ips/StructureDefinition/Patient-uv-ips",
}


def _resolve_profile(profile: str) -> str:
    """Resolve a profile shorthand or return the URL as-is."""
    if not profile:
        return ""
    resolved = PROFILE_ALIASES.get(profile.lower(), profile)
    # Reject obviously non-URL values that aren't known aliases
    if not resolved.startswith(("http://", "https://")):
        raise ValueError(f"profile must be a URL or one of: {', '.join(PROFILE_ALIASES)}")
    return resolved


async def validate_against_profile(
    resource: dict[str, Any],
    profile: str = "",
    fhir_version: str = "4.0.1",
) -> dict[str, Any]:
    """Validate a FHIR resource against an optional profile.

    Args:
        resource:     A FHIR resource as a dict (must contain ``resourceType``).
        profile:      Profile URL or shorthand alias (e.g. ``us-core-patient``).
                      Empty string = base FHIR R4 spec validation only.
        fhir_version: FHIR version string for the HAPI validator.

    Returns:
        A dict representation of :class:`ValidationReport` with
        ``is_conformant``, ``error_count``, ``warning_count``, and ``issues``.
    """
    resource_type = resource.get("resourceType")
    if not resource_type or not isinstance(resource_type, str):
        raise ValueError("resource must contain a string 'resourceType' field")

    resolved_profile = _resolve_profile(profile)

    with span(
        "validate_against_profile",
        resource_type=resource_type,
        profile=resolved_profile or "base",
    ):
        report: ValidationReport = await validate_resource(
            resource=resource,
            profile=resolved_profile,
            fhir_version=fhir_version,
        )

    log.info(
        "validate_against_profile_done",
        resource_type=resource_type,
        profile=resolved_profile or "base",
        is_conformant=report.is_conformant,
        error_count=report.error_count,
        warning_count=report.warning_count,
    )
    return report.model_dump()
