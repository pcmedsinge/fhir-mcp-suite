"""Tool: lookup_code — look up a single code in a terminology system.

Calls the FHIR $lookup operation:
    GET {base}/CodeSystem/$lookup?system={system}&code={code}
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fhir_mcp_shared.langfuse import span

from mcp_terminology.settings import settings
from mcp_terminology.validation import resolve_system, validate_code

log = structlog.get_logger(__name__)


def _parse_parameters(params: dict[str, Any]) -> dict[str, Any]:
    """Extract named values from a FHIR Parameters resource."""
    result: dict[str, Any] = {}
    designations: list[dict[str, str]] = []
    for p in params.get("parameter") or []:
        name = p.get("name", "")
        if name == "designation":
            # designation is a group of sub-parameters
            sub: dict[str, str] = {}
            for sp in p.get("part") or []:
                sn = sp.get("name", "")
                sv = sp.get("valueString") or sp.get("valueCoding", {}).get("display", "")
                if sv:
                    sub[sn] = str(sv)
            if sub:
                designations.append(sub)
        else:
            val = (
                p.get("valueString")
                or p.get("valueBoolean")
                or p.get("valueCode")
                or p.get("valueUri")
                or (p.get("valueCoding") or {}).get("display")
            )
            if val is not None:
                result[name] = val
    if designations:
        result["designations"] = designations
    return result


async def lookup_code(
    system: str,
    code: str,
    version: str = "",
) -> dict[str, Any]:
    """Look up a single code in a terminology system using FHIR $lookup.

    Args:
        system:  System alias (e.g. ``"loinc"``, ``"snomed"``) or canonical URI.
        code:    The code to look up (e.g. ``"8302-2"``, ``"73211009"``).
        version: Optional terminology version string.

    Returns:
        Dict with ``system_url``, ``system_name``, ``code``, ``display``,
        ``definition`` (if available), and ``designations`` (if available).

    Raises:
        ValueError: On invalid inputs.
        httpx.HTTPStatusError: If the terminology server returns 4xx/5xx.
    """
    system_url = resolve_system(system)
    safe_code = validate_code(code)

    params: dict[str, str] = {"system": system_url, "code": safe_code}
    if version:
        params["version"] = version[:50]

    url = f"{settings.terminology_base_url.rstrip('/')}/CodeSystem/$lookup"

    with span("lookup_code", system=system_url, code=safe_code):
        log.info("lookup_code", url=url, system=system_url, code=safe_code)
        async with httpx.AsyncClient(timeout=settings.terminology_timeout_s) as client:
            response = await client.get(
                url, params=params, headers={"Accept": "application/fhir+json"}
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

    parsed = _parse_parameters(data)

    from mcp_terminology.constants import SYSTEM_DISPLAY
    return {
        "system_url": system_url,
        "system_name": SYSTEM_DISPLAY.get(system_url, system_url),
        "code": safe_code,
        "display": parsed.get("display", ""),
        "definition": parsed.get("definition", ""),
        "designations": parsed.get("designations", []),
        "version": parsed.get("version", ""),
    }
