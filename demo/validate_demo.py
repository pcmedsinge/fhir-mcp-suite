"""
Post #1 demo: profile validation in mcp-fhir
Story: missing US Core required fields → validator catches it → fix → passes.

Usage:
    # 1. Start HAPI validator:  docker-compose up hapi-validator
    # 2. Wait ~60s for validator to boot, then:
    uv run python demo/validate_demo.py
"""

from __future__ import annotations

import asyncio
import os

BROKEN_PATIENT = {
    "resourceType": "Patient",
    "id": "demo-patient-bad",
    # US Core requires: identifier + name.family + gender
    # This one has none of those → should fail
    "birthDate": "1985-04-12",
}

FIXED_PATIENT = {
    "resourceType": "Patient",
    "id": "demo-patient-good",
    "identifier": [{"system": "urn:oid:2.16.840.1.113883.4.6", "value": "1234567890"}],
    "name": [{"family": "Rivera", "given": ["Maria"]}],
    "gender": "female",
    "birthDate": "1985-04-12",
}


def _sep(title: str) -> None:
    print(f"\n{'─' * 56}")
    print(f"  {title}")
    print(f"{'─' * 56}")


async def main() -> None:
    os.environ.setdefault("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")
    os.environ.setdefault("HAPI_VALIDATOR_URL", "http://localhost:8082")
    os.environ.setdefault("SMART_ENABLED", "false")
    os.environ.setdefault("LOG_FORMAT", "console")

    from mcp_fhir.tools.validate_profile import validate_against_profile

    print("\nmcp-fhir — US Core profile validation demo")
    print("Differentiator: built-in HAPI profile validation")

    # ── Step 1: broken resource ──────────────────────────────────────────
    _sep("STEP 1 — Validate a Patient missing required US Core fields")
    print("  Sending resource with no identifier, no name, no gender …")
    result = await validate_against_profile(
        resource=BROKEN_PATIENT, profile="us-core-patient"
    )
    valid = result.get("valid")
    issues = result.get("issues", [])
    errors = [i for i in issues if i.get("severity") in ("error", "fatal")]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    print(f"\n  valid    : {valid}")
    print(f"  errors   : {len(errors)}")
    print(f"  warnings : {len(warnings)}")
    if errors:
        print("\n  Error details:")
        for e in errors[:5]:
            print(f"    ✗  {e.get('message', '')}")

    # ── Step 2: fixed resource ───────────────────────────────────────────
    _sep("STEP 2 — Fix the resource (add identifier + name + gender)")
    print("  Sending corrected Patient resource …")
    result2 = await validate_against_profile(
        resource=FIXED_PATIENT, profile="us-core-patient"
    )
    valid2 = result2.get("valid")
    issues2 = result2.get("issues", [])
    errors2 = [i for i in issues2 if i.get("severity") in ("error", "fatal")]
    warnings2 = [i for i in issues2 if i.get("severity") == "warning"]
    print(f"\n  valid    : {valid2}")
    print(f"  errors   : {len(errors2)}")
    print(f"  warnings : {len(warnings2)}")
    if valid2:
        print("\n  ✓  Resource conforms to US Core Patient profile")

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'═' * 56}")
    print("  Why this matters for clinical AI safety:")
    print("  An LLM that generates FHIR resources can silently")
    print("  produce non-conformant data. mcp-fhir catches it")
    print("  before it reaches production EHR systems.")
    print(f"{'═' * 56}\n")


if __name__ == "__main__":
    asyncio.run(main())
