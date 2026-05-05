"""Tool: fhir_search — search a FHIR resource type with optional parameters.

Also exposes fhir_search_next for following Bundle pagination links.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

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
        The bundle will include a ``_next_url`` key when more pages exist;
        pass that value to ``fhir_search_next`` to retrieve the next page.
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
            bundle: dict[str, Any] = response.json()

    # Attach pagination helper key so the LLM knows there are more pages.
    next_url = _extract_next_link(bundle)
    if next_url:
        bundle["_next_url"] = next_url
    return bundle


def _extract_next_link(bundle: dict[str, Any]) -> str | None:
    """Return the ``next`` relation URL from a FHIR Bundle link array, or None."""
    for link in bundle.get("link") or []:
        if link.get("relation") == "next":
            raw = link.get("url", "")
            # Validate it is actually an HTTP(S) URL before surfacing it.
            parsed = urlparse(raw)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return raw
    return None


async def fhir_search_next(next_url: str) -> dict[str, Any]:
    """Follow a pagination link from a previous ``fhir_search`` Bundle.

    Args:
        next_url: The ``_next_url`` value returned by a previous search.
                  Must be an absolute HTTP(S) URL from the same FHIR server.

    Returns:
        The next Bundle page, also with ``_next_url`` if further pages exist.

    Raises:
        ValueError: If ``next_url`` is not a valid absolute HTTP(S) URL or
                    points to a different host than the configured FHIR server.
    """
    parsed = urlparse(next_url)
    configured = urlparse(settings.fhir_base_url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("next_url must be an absolute HTTP(S) URL")

    # SSRF guard: next_url host must match the configured FHIR server host.
    if parsed.netloc != configured.netloc:
        raise ValueError(
            f"next_url host {parsed.netloc!r} does not match configured "
            f"FHIR server {configured.netloc!r}"
        )

    with span("fhir_search_next", url=next_url):
        log.info("fhir_search_next", url=next_url)
        async with httpx.AsyncClient(timeout=settings.fhir_timeout_s) as client:
            response = await client.get(
                next_url, headers={"Accept": "application/fhir+json"}
            )
            response.raise_for_status()
            bundle: dict[str, Any] = response.json()

    next2 = _extract_next_link(bundle)
    if next2:
        bundle["_next_url"] = next2
    return bundle
