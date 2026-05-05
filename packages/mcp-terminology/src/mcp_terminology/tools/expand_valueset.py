"""Tool: expand_valueset — expand a FHIR ValueSet, optionally filtered by text.

Uses the FHIR $expand operation:
    GET {base}/ValueSet/$expand?url={url}&filter={filter}&count={n}
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from fhir_mcp_shared.langfuse import span

from mcp_terminology.constants import SYSTEM_DISPLAY
from mcp_terminology.settings import settings
from mcp_terminology.validation import sanitise_filter, validate_max_results, validate_url

log = structlog.get_logger(__name__)


async def expand_valueset(
    url: str,
    filter: str = "",
    max_results: int = 0,
) -> dict[str, Any]:
    """Expand a FHIR ValueSet and return its codes, optionally filtered.

    Calls ``ValueSet/$expand`` on the terminology server. Works with any
    ValueSet that ``tx.fhir.org`` hosts, including US Core, SNOMED,
    LOINC, and FHIR-defined ValueSets.

    Args:
        url:         Canonical ValueSet URL
                     (e.g. ``"http://hl7.org/fhir/ValueSet/administrative-gender"``).
        filter:      Optional free-text filter to narrow results.
        max_results: Maximum codes to return (1-100). 0 = server default.

    Returns:
        Dict with ``url``, ``title``, ``total``, and ``codes`` list of
        ``{system, system_name, code, display}``.
    """
    safe_url = validate_url(url, "url")
    safe_filter = sanitise_filter(filter) if filter else ""
    n = validate_max_results(max_results or settings.terminology_max_results)

    params: dict[str, str] = {"url": safe_url, "count": str(n)}
    if safe_filter:
        params["filter"] = safe_filter

    endpoint = f"{settings.terminology_base_url.rstrip('/')}/ValueSet/$expand"

    with span("expand_valueset", valueset_url=safe_url, filter=safe_filter, max_results=n):
        log.info("expand_valueset", endpoint=endpoint, valueset_url=safe_url)
        async with httpx.AsyncClient(timeout=settings.terminology_timeout_s) as client:
            response = await client.get(
                endpoint,
                params=params,
                headers={"Accept": "application/fhir+json"},
            )
            response.raise_for_status()
            valueset: dict[str, Any] = response.json()

    expansion = valueset.get("expansion") or {}
    contains = expansion.get("contains") or []

    codes: list[dict[str, str]] = [
        {
            "system": entry.get("system", ""),
            "system_name": SYSTEM_DISPLAY.get(entry.get("system", ""), ""),
            "code": entry.get("code", ""),
            "display": entry.get("display", ""),
        }
        for entry in contains
    ]

    return {
        "url": safe_url,
        "title": valueset.get("title") or valueset.get("name") or "",
        "total": expansion.get("total"),
        "returned": len(codes),
        "codes": codes,
    }
