"""HAPI FHIR validator sidecar client.

Wraps the markiantorno/validator-wrapper REST API.  Sends a resource JSON
to ``POST /validate`` and returns a normalised :class:`ValidationReport`.

If the validator is unreachable (e.g. sidecar not running) the method
returns a report with a single FATAL issue rather than raising — the MCP
tool surfaces this as a structured error to the client.

Ported and adapted from P1 (fhir-mapping-agent/tools/validator.py).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog
from fhir_mcp_shared.models.validation import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)

from mcp_fhir.settings import settings

log = structlog.get_logger(__name__)

_SEVERITY_MAP: dict[str, ValidationSeverity] = {
    "fatal": ValidationSeverity.FATAL,
    "error": ValidationSeverity.ERROR,
    "warning": ValidationSeverity.WARNING,
    "information": ValidationSeverity.INFORMATION,
    "informational": ValidationSeverity.INFORMATION,
}

# Profile URL prefix → pinned IG package (matches what validator-wrapper pre-caches)
_PROFILE_IG_MAP: dict[str, str] = {
    "http://hl7.org/fhir/us/core/": "hl7.fhir.us.core#8.0.0",
    "http://hl7.org/fhir/uv/ips/": "hl7.fhir.uv.ips#2.0.0",
    "http://hl7.org/fhir/uv/sdc/": "hl7.fhir.uv.sdc#3.0.0",
}


def _igs_for_profile(profile: str) -> list[str]:
    """Return the IG package(s) needed to resolve *profile*."""
    for prefix, ig in _PROFILE_IG_MAP.items():
        if profile.startswith(prefix):
            return [ig]
    return []


def _build_request(resource: dict[str, Any], profile: str, fhir_version: str) -> dict[str, Any]:
    igs = _igs_for_profile(profile) if profile else []
    ctx: dict[str, Any] = {
        "sv": fhir_version,
        "profiles": [profile] if profile else [],
        "locale": "en",
    }
    if igs:
        ctx["igs"] = igs
    return {
        "cliContext": ctx,
        "filesToValidate": [
            {
                "fileName": "resource.json",
                "fileContent": json.dumps(resource),
                "fileType": "json",
            }
        ],
    }


def _location_of(issue: dict[str, Any]) -> str | None:
    for key in ("expression", "location"):
        loc = issue.get(key)
        if isinstance(loc, list) and loc:
            return str(loc[0])
    return None


def _parse_outcome(outcome: dict[str, Any], profile: str, resource_type: str) -> ValidationReport:
    issues: list[ValidationIssue] = []
    for raw in outcome.get("issues", []) or []:
        sev_str = (raw.get("level") or raw.get("severity") or "information").lower()
        sev = _SEVERITY_MAP.get(sev_str, ValidationSeverity.INFORMATION)
        message = (
            raw.get("message")
            or (raw.get("details") or {}).get("text")
            or raw.get("diagnostics")
            or raw.get("code")
            or "(no message)"
        )
        issues.append(
            ValidationIssue(
                severity=sev,
                code=raw.get("code") or "unknown",
                location=_location_of(raw),
                message=str(message),
            )
        )
    is_conformant = not any(
        i.severity in (ValidationSeverity.ERROR, ValidationSeverity.FATAL) for i in issues
    )
    return ValidationReport(
        profile=profile, resource_type=resource_type, is_conformant=is_conformant, issues=issues
    )


async def validate_resource(
    resource: dict[str, Any],
    profile: str = "",
    fhir_version: str = "4.0.1",
) -> ValidationReport:
    """Validate *resource* against *profile* using the HAPI validator sidecar.

    Args:
        resource:     A FHIR resource as a plain dict.
        profile:      Profile URL to validate against, e.g.
                      ``http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient``.
                      Empty string means base-spec validation only.
        fhir_version: FHIR version string for the HAPI CLI context.

    Returns:
        :class:`ValidationReport` with ``is_conformant`` and any issues.
    """
    resource_type = resource.get("resourceType", "Unknown")
    body = _build_request(resource, profile, fhir_version)
    url = f"{settings.hapi_validator_url.rstrip('/')}/validate"

    try:
        async with httpx.AsyncClient(timeout=settings.hapi_validator_timeout_s) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.TimeoutException) as exc:
        err_type = (
            "timeout"
            if isinstance(exc, (httpx.ReadTimeout, httpx.TimeoutException))
            else "connection-error"
        )
        log.warning("hapi_validator_unreachable", url=url, error=str(exc))
        return ValidationReport(
            profile=profile,
            resource_type=resource_type,
            is_conformant=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.FATAL,
                    code=err_type,
                    message=f"HAPI validator unreachable at {url}: {exc}",
                )
            ],
        )
    except httpx.HTTPStatusError as exc:
        log.warning("hapi_validator_http_error", status=exc.response.status_code)
        return ValidationReport(
            profile=profile,
            resource_type=resource_type,
            is_conformant=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.FATAL,
                    code="http-error",
                    message=f"Validator returned HTTP {exc.response.status_code}",
                )
            ],
        )

    # The validator-wrapper envelope: {"outcomes": [...], "sessionId": ..., "validationTimes": ...}
    # Fall back to treating data as a bare list/dict for compatibility.
    if isinstance(data, dict) and "outcomes" in data:
        outcomes = data["outcomes"]
    elif isinstance(data, list):
        outcomes = data
    else:
        outcomes = [data]
    all_issues: list[ValidationIssue] = []
    for outcome in outcomes:
        report = _parse_outcome(outcome, profile, resource_type)
        all_issues.extend(report.issues)

    is_conformant = not any(
        i.severity in (ValidationSeverity.ERROR, ValidationSeverity.FATAL) for i in all_issues
    )
    return ValidationReport(
        profile=profile,
        resource_type=resource_type,
        is_conformant=is_conformant,
        issues=all_issues,
    )
