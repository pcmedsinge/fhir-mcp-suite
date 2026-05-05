"""
fhir-mcp-suite — end-to-end demo script
Runs all five mcp-fhir tools against the public HAPI R4 demo server.
No credentials required.

Usage:
    uv run python demo/run_demo.py
    uv run python demo/run_demo.py --fhir-url https://r4.smarthealthit.org
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import textwrap
from typing import Any


def _banner(title: str) -> None:
    width = 60
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def _pretty(data: Any, indent: int = 2) -> str:
    return json.dumps(data, indent=indent)


def _truncate(text: str, max_lines: int = 12) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + f"\n  ... ({len(lines) - max_lines} more lines)"


async def demo_capabilities() -> dict[str, Any]:
    from mcp_fhir.tools.fhir_capabilities import fhir_capabilities

    _banner("1 / 5 — fhir_capabilities")
    result = await fhir_capabilities()
    print(f"  FHIR version : {result.get('fhir_version')}")
    print(f"  Resources    : {result.get('resource_count')}")
    print(f"  Publisher    : {result.get('publisher', 'n/a')}")
    return result


async def demo_search() -> str | None:
    from mcp_fhir.tools.fhir_search import fhir_search

    _banner("2 / 5 — fhir_search  (Patient, _count=3)")
    bundle = await fhir_search("Patient", {"_count": "3", "_sort": "-_lastUpdated"})
    entries = bundle.get("entry", [])
    print(f"  Total found  : {bundle.get('total', '?')}")
    print(f"  Returned     : {len(entries)} entries")
    patient_id: str | None = None
    for i, e in enumerate(entries):
        res = e.get("resource", {})
        name_parts = []
        if res.get("name"):
            n = res["name"][0]
            name_parts = n.get("given", []) + [n.get("family", "")]
        print(f"    [{i+1}] id={res.get('id')}  name={' '.join(name_parts).strip() or 'n/a'}")
        if i == 0:
            patient_id = res.get("id")
    next_url = bundle.get("_next_url")
    if next_url:
        print(f"  Pagination   : next page available")
    return patient_id


async def demo_search_next(patient_id: str | None) -> None:
    from mcp_fhir.tools.fhir_search import fhir_search, fhir_search_next

    _banner("3 / 5 — fhir_search_next  (pagination)")
    bundle = await fhir_search("Observation", {"_count": "5", "subject": patient_id or ""})
    next_url = bundle.get("_next_url")
    if next_url:
        print(f"  Following next link …")
        page2 = await fhir_search_next(next_url)
        print(f"  Page 2 entries: {len(page2.get('entry', []))}")
    else:
        total = bundle.get("total", 0)
        print(f"  Only 1 page of Observations for this patient (total={total}) — no next link needed")


async def demo_read(patient_id: str | None) -> dict[str, Any] | None:
    from mcp_fhir.tools.fhir_read import fhir_read

    _banner("4 / 5 — fhir_read  (Patient/{id})")
    if not patient_id:
        print("  Skipped — no patient ID from search step")
        return None
    resource = await fhir_read("Patient", patient_id)
    rt = resource.get("resourceType", "?")
    rid = resource.get("id", "?")
    gender = resource.get("gender", "unknown")
    dob = resource.get("birthDate", "unknown")
    print(f"  resourceType : {rt}")
    print(f"  id           : {rid}")
    print(f"  gender       : {gender}")
    print(f"  birthDate    : {dob}")
    return resource


async def demo_validate(resource: dict[str, Any] | None) -> None:
    from mcp_fhir.tools.validate_profile import validate_against_profile

    _banner("5 / 5 — validate_against_profile  (us-core-patient)")
    if not resource:
        print("  Skipped — no resource from read step")
        return

    hapi_url = os.getenv("HAPI_VALIDATOR_URL", "")
    if not hapi_url or hapi_url == "http://localhost:8080":
        # Quick reachability check
        import httpx
        try:
            r = httpx.get(f"{hapi_url or 'http://localhost:8082'}/fhir/metadata", timeout=3)
            r.raise_for_status()
        except Exception:
            print("  HAPI validator sidecar not running — skipping.")
            print("  Start it with:  docker-compose up hapi-validator")
            return

    result = await validate_against_profile(resource=resource, profile="us-core-patient")
    valid = result.get("valid")
    issues = result.get("issues", [])
    errors = [i for i in issues if i.get("severity") in ("error", "fatal")]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    print(f"  Valid        : {valid}")
    print(f"  Errors       : {len(errors)}")
    print(f"  Warnings     : {len(warnings)}")
    if errors:
        for e in errors[:3]:
            print(f"    ✗ {e.get('message', '')}")


async def main(fhir_url: str) -> None:
    os.environ.setdefault("FHIR_BASE_URL", fhir_url)
    # SMART auth OFF for the public demo (no credentials needed)
    os.environ.setdefault("SMART_ENABLED", "false")
    os.environ.setdefault("LOG_FORMAT", "console")

    print(f"\nfhir-mcp-suite demo")
    print(f"FHIR server : {fhir_url}")
    print(f"SMART auth  : {os.environ.get('SMART_ENABLED', 'false')}")

    await demo_capabilities()
    patient_id = await demo_search()
    await demo_search_next(patient_id)
    resource = await demo_read(patient_id)
    await demo_validate(resource)

    print(f"\n{'═' * 60}")
    print("  Demo complete — all 5 tools exercised.")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fhir-mcp-suite end-to-end demo")
    parser.add_argument(
        "--fhir-url",
        default="https://hapi.fhir.org/baseR4",
        help="FHIR R4 base URL (default: public HAPI demo server)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.fhir_url))
