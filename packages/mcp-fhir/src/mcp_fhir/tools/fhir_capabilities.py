"""Tool: fhir_capabilities — retrieve the FHIR server's CapabilityStatement."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from fhir_mcp_shared.langfuse import span

from mcp_fhir.http_client import get_fhir_headers
from mcp_fhir.settings import settings

log = structlog.get_logger(__name__)


async def fhir_capabilities() -> dict[str, Any]:
    """Retrieve the CapabilityStatement (metadata) from the FHIR server.

    Returns a summary dict — full CapabilityStatement JSON can be large,
    so we extract the fields most useful to an LLM:
    - fhirVersion
    - software name + version
    - supported resource types + interactions
    - supported search parameters per resource (first 10 per resource)

    Returns:
        Dict with ``fhir_version``, ``software``, ``resources`` (summary list).
    """
    url = f"{settings.fhir_base_url.rstrip('/')}/metadata"

    with span("fhir_capabilities"):
        log.info("fhir_capabilities", url=url)
        headers = await get_fhir_headers()
        async with httpx.AsyncClient(timeout=settings.fhir_timeout_s) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            cap: dict[str, Any] = response.json()

    # Summarize to avoid overwhelming the LLM context window.
    software = cap.get("software") or {}
    resources_raw = (cap.get("rest") or [{}])[0].get("resource") or []

    resources: list[dict[str, Any]] = []
    for r in resources_raw:
        interactions = [i.get("code") for i in (r.get("interaction") or []) if i.get("code")]
        search_params = [
            sp.get("name") for sp in (r.get("searchParam") or [])[:10] if sp.get("name")
        ]
        resources.append(
            {
                "type": r.get("type"),
                "interactions": interactions,
                "searchParams": search_params,
            }
        )

    return {
        "fhir_version": cap.get("fhirVersion"),
        "software": {
            "name": software.get("name"),
            "version": software.get("version"),
        },
        "resource_count": len(resources),
        "resources": resources,
    }
