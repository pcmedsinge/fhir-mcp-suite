"""Tool: fhir_search — search a FHIR resource type with optional parameters."""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from fhir_mcp_shared.langfuse import span

from mcp_fhir.settings import settings

log = structlog.get_logger(__name__)

# Allowlist for FHIR resource type names (CapWords, 1-40 chars)
_RESOURCE_TYPE_RE = re.compile(r"^[A-Z][a-zA-Z]{1,39}$")
# Allowlist for parameter names (FHIR search param names: alnum, hyphens, underscores, dots)
_PARAM_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.\-:]{0,63}$")


def _validate_search_params(params: dict[str, str]) -> dict[str, str]:
    """Reject any parameter name that doesn't match the FHIR search-param grammar.

    Values are passed through as strings; the server will reject invalid values.
    We do not validate values here to avoid over-restricting (values can be
    dates, URLs, codeable concepts, etc.).
    """
    safe: dict[str, str] = {}
    for k, v in params.items():
        if not _PARAM_NAME_RE.match(k):
            log.warning("fhir_search_invalid_param", key=k)
            continue
        safe[k] = str(v)
    return safe


async def fhir_search(
    resource_type: str,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Search a FHIR resource type.

    Args:
        resource_type: FHIR resource type (e.g. ``Patient``, ``Observation``).
        params:        FHIR search parameters, e.g. ``{"family": "Smith"}``.
                       ``_count`` defaults to the configured max.

    Returns:
        A FHIR Bundle (type = searchset) as a JSON-serialisable dict.
    """
    resource_type = resource_type.strip()
    if not _RESOURCE_TYPE_RE.match(resource_type):
        raise ValueError(f"Invalid FHIR resource type: {resource_type!r}")

    safe_params = _validate_search_params(params or {})
    safe_params.setdefault("_count", str(settings.fhir_max_results))

    url = f"{settings.fhir_base_url.rstrip('/')}/{resource_type}"

    with span("fhir_search", resource_type=resource_type, params=safe_params):
        log.info("fhir_search", url=url, params=safe_params)
        async with httpx.AsyncClient(timeout=settings.fhir_timeout_s) as client:
            response = await client.get(
                url,
                params=safe_params,
                headers={"Accept": "application/fhir+json"},
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
