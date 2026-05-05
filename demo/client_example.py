"""
fhir-mcp-suite — programmatic client example
Shows how to call mcp-fhir tools from any Python application,
exactly as an LLM agent (LangChain, LangGraph, etc.) would.

Usage:
    uv run python demo/client_example.py

Requirements:
    uv sync --all-packages -q
    # For validate_against_profile: docker compose up hapi-validator -d
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ── Server launch parameters ────────────────────────────────────────────────
# This is all an MCP host (Claude Desktop, LangGraph, etc.) needs to start
# your server. Swap the env vars to point at your own FHIR endpoint.
SERVER = StdioServerParameters(
    command="uv",
    args=["run", "--package", "mcp-fhir", "mcp-fhir"],
    env={
        **os.environ,                                 # inherit PATH, HOME, etc.
        "FHIR_BASE_URL":      "https://hapi.fhir.org/baseR4",
        "HAPI_VALIDATOR_URL": "http://localhost:8082",
        "SMART_ENABLED":      "false",
        "LOG_FORMAT":         "console",
    },
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _text(result: Any) -> str:
    """Extract the text payload from a CallToolResult."""
    if hasattr(result, "content"):
        for block in result.content:
            if hasattr(block, "text"):
                return block.text
    return str(result)


def _json(result: Any) -> Any:
    return json.loads(_text(result))


def _print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ── Example calls ────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"\nConnected to mcp-fhir — {len(tools.tools)} tools available:")
            for t in tools.tools:
                print(f"  • {t.name}: {t.description[:70]}...")

            # ── 1. fhir_capabilities ────────────────────────────────────────
            _print_section("1 / 5 — fhir_capabilities")
            result = await session.call_tool("fhir_capabilities", arguments={})
            caps = _json(result)
            print(f"  FHIR version : {caps.get('fhir_version')}")
            print(f"  Publisher    : {caps.get('publisher', 'n/a')}")
            print(f"  Resource count: {caps.get('resource_count')}")

            # ── 2. fhir_search ──────────────────────────────────────────────
            _print_section("2 / 5 — fhir_search  (Patient, _count=3)")
            result = await session.call_tool(
                "fhir_search",
                arguments={
                    "resource_type": "Patient",
                    "params": {"_count": "3", "_sort": "-_lastUpdated"},
                },
            )
            bundle = _json(result)
            entries = bundle.get("entry", [])
            print(f"  Total  : {bundle.get('total', '?')}")
            print(f"  Returned: {len(entries)} entries")
            first_id: str | None = None
            for i, e in enumerate(entries[:3]):
                r = e.get("resource", {})
                name = ""
                if r.get("name"):
                    n = r["name"][0]
                    name = " ".join(n.get("given", []) + [n.get("family", "")]).strip()
                print(f"    [{i+1}] id={r.get('id')}  name={name or 'n/a'}")
                if i == 0:
                    first_id = r.get("id")

            # ── 3. fhir_search_next (pagination) ───────────────────────────
            _print_section("3 / 5 — fhir_search_next  (Observation pagination)")
            obs_result = await session.call_tool(
                "fhir_search",
                arguments={
                    "resource_type": "Observation",
                    "params": {"subject": first_id or "", "_count": "5"},
                },
            )
            obs_bundle = _json(obs_result)
            next_url = obs_bundle.get("_next_url")
            print(f"  Observations page 1: {len(obs_bundle.get('entry', []))} entries")
            if next_url:
                page2 = await session.call_tool(
                    "fhir_search_next",
                    arguments={"next_url": next_url},
                )
                page2_bundle = _json(page2)
                print(f"  Observations page 2: {len(page2_bundle.get('entry', []))} entries")
            else:
                print(f"  Only 1 page (total={obs_bundle.get('total', '?')})")

            # ── 4. fhir_read ────────────────────────────────────────────────
            _print_section("4 / 5 — fhir_read  (Patient)")
            read_id = first_id or "example"
            result = await session.call_tool(
                "fhir_read",
                arguments={"resource_type": "Patient", "resource_id": read_id},
            )
            patient = _json(result)
            print(f"  resourceType : {patient.get('resourceType')}")
            print(f"  id           : {patient.get('id')}")
            print(f"  gender       : {patient.get('gender', 'n/a')}")
            print(f"  birthDate    : {patient.get('birthDate', 'n/a')}")

            # ── 5. validate_against_profile ─────────────────────────────────
            _print_section("5 / 5 — validate_against_profile")

            # Step A: broken resource — missing US Core required fields
            print("\n  [A] Patient missing identifier + name + gender (should FAIL):")
            broken = await session.call_tool(
                "validate_against_profile",
                arguments={
                    "resource": {
                        "resourceType": "Patient",
                        "id": "demo-patient-bad",
                        "birthDate": "1985-04-12",
                    },
                    "profile": "us-core-patient",
                },
            )
            report_a = _json(broken)
            errors_a = [i for i in report_a.get("issues", []) if i.get("severity") in ("error", "fatal")]
            print(f"  valid={report_a.get('valid')}  errors={len(errors_a)}")
            for e in errors_a[:3]:
                print(f"    ✗  {e.get('message', '')}")

            # Step B: fixed resource — all required fields present
            print("\n  [B] Patient with identifier + name + gender (should PASS):")
            fixed = await session.call_tool(
                "validate_against_profile",
                arguments={
                    "resource": {
                        "resourceType": "Patient",
                        "id": "demo-patient-good",
                        "identifier": [{"system": "urn:oid:2.16.840.1.113883.4.6", "value": "1234567890"}],
                        "name": [{"family": "Rivera", "given": ["Maria"]}],
                        "gender": "female",
                        "birthDate": "1985-04-12",
                    },
                    "profile": "us-core-patient",
                },
            )
            report_b = _json(fixed)
            errors_b = [i for i in report_b.get("issues", []) if i.get("severity") in ("error", "fatal")]
            print(f"  valid={report_b.get('valid')}  errors={len(errors_b)}")

            print(f"\n{'═' * 60}")
            print("  All 5 tools called successfully via MCP client.")
            print(f"{'═' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
