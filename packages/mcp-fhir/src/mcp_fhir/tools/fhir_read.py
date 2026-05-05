"""Tool: fhir_read — read a single FHIR resource by type and ID."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from fhir_mcp_shared.langfuse import span

from mcp_fhir.settings import settings

log = structlog.get_logger(__name__)


async def fhir_read(resource_type: str, resource_id: str) -> dict[str, Any]:
    """Retrieve a single FHIR resource.

    Args:
        resource_type: FHIR resource type (e.g. ``Patient``, ``Observation``).
        resource_id:   Server-assigned logical ID.

    Returns:
        The resource as a JSON-serialisable dict.

    Raises:
        ValueError: If the resource type or ID is empty.
        httpx.HTTPStatusError: On non-2xx responses.
    """
    resource_type = resource_type.strip()
    resource_id = resource_id.strip()
    if not resource_type or not resource_id:
        raise ValueError("resource_type and resource_id must not be empty")

    # Basic input sanitization: FHIR logical IDs are alphanum + hyphens, max 64 chars
    if len(resource_id) > 64 or not all(c.isalnum() or c in "-." for c in resource_id):
        raise ValueError(f"Invalid FHIR resource ID: {resource_id!r}")

    url = f"{settings.fhir_base_url.rstrip('/')}/{resource_type}/{resource_id}"

    with span("fhir_read", resource_type=resource_type, resource_id=resource_id):
        log.info("fhir_read", url=url)
        async with httpx.AsyncClient(timeout=settings.fhir_timeout_s) as client:
            response = await client.get(
                url, headers={"Accept": "application/fhir+json"}
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
