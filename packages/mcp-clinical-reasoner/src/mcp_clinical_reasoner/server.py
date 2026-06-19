"""mcp-clinical-reasoner server entrypoint.

Four MCP tools:
  - lookup_drug              — resolve drug name/RxCUI → structured info (RxNav)
  - check_drug_interactions  — detect DDIs for a set of drug names (OpenFDA)
  - check_dose               — rule-based single/daily dose range check
  - check_allergy_conflicts  — rule-based cross-reactivity check

Transport selected via MCP_TRANSPORT env var (default: stdio).
"""

from __future__ import annotations

import json
import time
import uuid

import anyio
import structlog
from fhir_mcp_shared.langfuse import trace as lf_trace
from fhir_mcp_shared.logging import configure_logging
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_clinical_reasoner.settings import settings
from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts
from mcp_clinical_reasoner.tools.check_dose import check_dose
from mcp_clinical_reasoner.tools.check_drug_interactions import check_drug_interactions
from mcp_clinical_reasoner.tools.lookup_drug import lookup_drug

log = structlog.get_logger(__name__)

_SESSION_ID: str = str(uuid.uuid4())


def _build_server() -> Server:
    server = Server("mcp-clinical-reasoner")

    @server.list_tools()  # type: ignore
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="lookup_drug",
                description=(
                    "Look up a drug by name or RxNorm CUI. "
                    "Returns the canonical RxNorm name, RxCUI, drug class membership, "
                    "dose reference info (if available), and allergen class. "
                    "Use this first to get the RxCUI before calling check_drug_interactions."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name_or_rxcui": {
                            "type": "string",
                            "description": (
                                "Drug name (e.g. 'metformin', 'Advil') "
                                "or RxNorm CUI (e.g. '6809')."
                            ),
                        },
                    },
                    "required": ["name_or_rxcui"],
                },
            ),
            Tool(
                name="check_drug_interactions",
                description=(
                    "Check for drug-drug interactions (DDIs) among 2–10 drugs by name. "
                    "Uses the FDA drug label database (api.fda.gov) — interaction text "
                    "from official FDA-approved labeling. No API key required."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 10,
                            "description": "List of 2–10 drug names (e.g. ['ibuprofen', 'lisinopril', 'metformin']).",
                        },
                    },
                    "required": ["drug_names"],
                },
            ),
            Tool(
                name="check_dose",
                description=(
                    "Check a proposed drug dose against the built-in reference table (~20 common drugs). "
                    "Returns assessment: within_range, exceeds_single_dose, exceeds_daily_dose, "
                    "below_typical, or unknown_drug (if not in table). "
                    "No network calls — uses built-in rules only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug": {
                            "type": "string",
                            "description": "Drug name (e.g. 'ibuprofen', 'acetaminophen', 'Tylenol').",
                        },
                        "dose_mg": {
                            "type": "number",
                            "description": "Proposed single dose in milligrams.",
                        },
                        "frequency": {
                            "type": "string",
                            "description": (
                                "Dosing frequency (e.g. 'bid', 'q8h', 'daily', 'tid'). "
                                "Optional — used to estimate daily dose."
                            ),
                            "default": "",
                        },
                    },
                    "required": ["drug", "dose_mg"],
                },
            ),
            Tool(
                name="check_allergy_conflicts",
                description=(
                    "Check a drug for potential allergy conflicts using a built-in "
                    "cross-reactivity table. Supports drug class allergies (e.g. 'penicillin', "
                    "'nsaid', 'sulfonamide') and specific drug names. "
                    "No network calls — uses built-in rules only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "drug": {
                            "type": "string",
                            "description": "Drug to check (e.g. 'ceftriaxone', 'ibuprofen').",
                        },
                        "allergies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Patient's known allergens — drug names or class names "
                                "(e.g. ['penicillin', 'sulfa', 'aspirin'])."
                            ),
                        },
                    },
                    "required": ["drug", "allergies"],
                },
            ),
        ]

    @server.call_tool()  # type: ignore
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
        call_id = str(uuid.uuid4())
        log.info("tool_call", tool=name, call_id=call_id, session_id=_SESSION_ID)
        t0 = time.perf_counter()

        with lf_trace(
            name=name,
            session_id=_SESSION_ID,
            tags=["mcp-clinical-reasoner", name],
            call_id=call_id,
            server_version="1.0.0",
        ) as tr:
            try:
                if name == "lookup_drug":
                    result = await lookup_drug(name_or_rxcui=arguments["name_or_rxcui"])
                elif name == "check_drug_interactions":
                    result = await check_drug_interactions(drug_names=arguments["drug_names"])
                elif name == "check_dose":
                    result = await check_dose(
                        drug=arguments["drug"],
                        dose_mg=float(arguments["dose_mg"]),
                        frequency=arguments.get("frequency", ""),
                    )
                elif name == "check_allergy_conflicts":
                    result = await check_allergy_conflicts(
                        drug=arguments["drug"],
                        allergies=arguments["allergies"],
                    )
                else:
                    raise ValueError(f"Unknown tool: {name!r}")

                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                payload = json.dumps(result, indent=2)
                if tr:
                    tr.update(output={"response_bytes": len(payload), "latency_ms": latency_ms})
                log.info("tool_ok", tool=name, call_id=call_id,
                         latency_ms=latency_ms, response_bytes=len(payload))
                return [TextContent(type="text", text=payload)]

            except Exception as exc:
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                if tr:
                    tr.update(output={"error": str(exc), "latency_ms": latency_ms})
                log.error("tool_error", tool=name, call_id=call_id,
                          latency_ms=latency_ms, error=str(exc))
                return [TextContent(type="text", text=f"Error: {exc}")]

    return server


async def _run_stdio(server: Server) -> None:
    from mcp.server.lowlevel.server import NotificationOptions
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-clinical-reasoner",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


async def _run_sse(server: Server) -> None:
    try:
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
    except ImportError as exc:
        raise RuntimeError(
            "SSE transport requires 'uvicorn' and 'starlette'. "
            "Install with: pip install uvicorn starlette"
        ) from exc

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):  # type: ignore[no-untyped-def]
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name="mcp-clinical-reasoner",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=None,  # type: ignore[arg-type]
                        experimental_capabilities={},
                    ),
                ),
            )

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )
    config = uvicorn.Config(
        app=starlette_app,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.log_level.lower(),
    )
    await uvicorn.Server(config).serve()


def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    log.info("mcp_clinical_reasoner_starting",
             transport=settings.mcp_transport,
             version="1.0.0",
             session_id=_SESSION_ID)
    server = _build_server()
    if settings.mcp_transport == "sse":
        anyio.run(_run_sse, server)
    else:
        anyio.run(_run_stdio, server)


if __name__ == "__main__":
    main()

