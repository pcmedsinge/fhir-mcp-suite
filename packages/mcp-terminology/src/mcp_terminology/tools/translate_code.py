"""Tool: translate_code — translate a code from one system to another.

Uses the FHIR $translate operation:
    GET {base}/ConceptMap/$translate?code={code}&system={src}&target={tgt}
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from fhir_mcp_shared.langfuse import span

from mcp_terminology.constants import SYSTEM_DISPLAY
from mcp_terminology.settings import settings
from mcp_terminology.validation import resolve_system, validate_code

log = structlog.get_logger(__name__)


def _parse_translate_parameters(params: dict[str, Any]) -> dict[str, Any]:
    """Parse Parameters resource returned by $translate."""
    result_bool = False
    matches: list[dict[str, str]] = []

    for p in params.get("parameter") or []:
        name = p.get("name", "")
        if name == "result":
            result_bool = bool(p.get("valueBoolean", False))
        elif name == "match":
            match: dict[str, str] = {}
            for part in p.get("part") or []:
                pn = part.get("name", "")
                if pn == "equivalence":
                    match["equivalence"] = part.get("valueCode", "")
                elif pn == "concept":
                    coding = part.get("valueCoding") or {}
                    match["code"] = coding.get("code", "")
                    match["system"] = coding.get("system", "")
                    match["display"] = coding.get("display", "")
                    match["system_name"] = SYSTEM_DISPLAY.get(
                        coding.get("system", ""), coding.get("system", "")
                    )
                elif pn == "source":
                    match["source_map"] = part.get("valueUri", "")
            if match:
                matches.append(match)

    return {"result": result_bool, "matches": matches}


async def translate_code(
    code: str,
    source_system: str,
    target_system: str,
) -> dict[str, Any]:
    """Translate a code from one terminology system to another.

    Uses the FHIR ``ConceptMap/$translate`` operation on ``tx.fhir.org``.
    Well-supported mappings include SNOMED ↔ ICD-10, LOINC ↔ SNOMED, and
    RxNorm ↔ NDC (where official ConceptMaps exist on the server).

    Args:
        code:           The source code (e.g. ``"73211009"`` for SNOMED diabetes).
        source_system:  Source system alias or URI (e.g. ``"snomed"``).
        target_system:  Target system alias or URI (e.g. ``"icd-10-cm"``).

    Returns:
        Dict with ``result`` (bool), ``source_code``, ``source_system``,
        ``target_system``, and ``matches`` (list of translated codes with
        ``code``, ``display``, ``equivalence``).
    """
    source_url = resolve_system(source_system)
    target_url = resolve_system(target_system)
    safe_code = validate_code(code)

    params: dict[str, str] = {
        "code": safe_code,
        "system": source_url,
        "target": target_url,
    }

    url = f"{settings.terminology_base_url.rstrip('/')}/ConceptMap/$translate"

    with span(
        "translate_code",
        source_system=source_url,
        target_system=target_url,
        code=safe_code,
    ):
        log.info("translate_code", url=url, source=source_url, target=target_url)
        async with httpx.AsyncClient(timeout=settings.terminology_timeout_s) as client:
            response = await client.get(
                url, params=params, headers={"Accept": "application/fhir+json"}
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

    parsed = _parse_translate_parameters(data)

    return {
        "result": parsed["result"],
        "source_code": safe_code,
        "source_system": source_url,
        "source_system_name": SYSTEM_DISPLAY.get(source_url, source_url),
        "target_system": target_url,
        "target_system_name": SYSTEM_DISPLAY.get(target_url, target_url),
        "matches": parsed["matches"],
    }
