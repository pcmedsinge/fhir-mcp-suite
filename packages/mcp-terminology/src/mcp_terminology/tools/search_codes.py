"""Tool: search_codes — free-text search within a terminology system.

Uses the FHIR $expand operation on the system's implicit ValueSet:
    GET {base}/ValueSet/$expand?url={valueset_url}&filter={query}&count={n}
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from fhir_mcp_shared.langfuse import span

from mcp_terminology.constants import SYSTEM_DISPLAY, SYSTEM_VALUESET
from mcp_terminology.settings import settings
from mcp_terminology.validation import (
    resolve_system,
    sanitise_filter,
    validate_max_results,
)

log = structlog.get_logger(__name__)


def _parse_expansion(valueset: dict[str, Any]) -> list[dict[str, str]]:
    """Extract code entries from a ValueSet expansion."""
    contains = (valueset.get("expansion") or {}).get("contains") or []
    results: list[dict[str, str]] = []
    for entry in contains:
        results.append(
            {
                "system": entry.get("system", ""),
                "system_name": SYSTEM_DISPLAY.get(entry.get("system", ""), ""),
                "code": entry.get("code", ""),
                "display": entry.get("display", ""),
                "abstract": str(entry.get("abstract", False)).lower(),
                "inactive": str(entry.get("inactive", False)).lower(),
            }
        )
    return results


async def search_codes(
    query: str,
    system: str,
    max_results: int = 0,
) -> dict[str, Any]:
    """Search for codes by free text within a terminology system.

    Calls ``ValueSet/$expand`` with a ``filter`` parameter on the implicit
    ValueSet for the given system. Systems with broad ValueSets (LOINC,
    SNOMED CT, RxNorm) are fully supported. ICD-10 and other systems without
    an implicit ValueSet on ``tx.fhir.org`` will return a ``not_supported``
    error with guidance.

    Args:
        query:       Free-text search string (e.g. ``"body height"``, ``"diabetes"``).
        system:      System alias or URI (e.g. ``"loinc"``, ``"snomed"``, ``"rxnorm"``).
        max_results: Maximum codes to return (1-100). 0 = use server default.

    Returns:
        Dict with ``system_url``, ``query``, ``total`` (expansion total if
        reported), and ``results`` (list of ``{system, code, display}``).
    """
    system_url = resolve_system(system)
    safe_query = sanitise_filter(query)
    if not safe_query:
        raise ValueError("query must not be empty")

    valueset_url = SYSTEM_VALUESET.get(system_url)
    if not valueset_url:
        supported = [k for k, v in {a: resolve_system(a) for a in
                     ["loinc", "snomed", "rxnorm"]} .items()]
        raise ValueError(
            f"Free-text search is not supported for system {system_url!r} "
            f"on tx.fhir.org. Supported systems: {', '.join(supported)}. "
            "Use lookup_code for exact code lookup instead."
        )

    n = validate_max_results(max_results or settings.terminology_max_results)
    params: dict[str, str | int] = {
        "url": valueset_url,
        "filter": safe_query,
        "count": n,
    }

    url = f"{settings.terminology_base_url.rstrip('/')}/ValueSet/$expand"

    with span("search_codes", system=system_url, query=safe_query, max_results=n):
        log.info("search_codes", url=url, system=system_url, query=safe_query)
        async with httpx.AsyncClient(timeout=settings.terminology_timeout_s) as client:
            response = await client.get(
                url,
                params={k: str(v) for k, v in params.items()},
                headers={"Accept": "application/fhir+json"},
            )
            response.raise_for_status()
            valueset: dict[str, Any] = response.json()

    results = _parse_expansion(valueset)
    total = (valueset.get("expansion") or {}).get("total")

    return {
        "system_url": system_url,
        "system_name": SYSTEM_DISPLAY.get(system_url, system_url),
        "query": safe_query,
        "total": total,
        "results": results,
    }
