"""mcp-terminology server entrypoint.

Registers four MCP tools:
  - lookup_code      — look up a single code (LOINC, SNOMED, RxNorm, ICD-10, …)
  - search_codes     — free-text search within a terminology system
  - translate_code   — translate a code across systems via ConceptMap/$translate
  - expand_valueset  — expand any FHIR ValueSet, optionally filtered

Transport is selected via the MCP_TRANSPORT env var (default: stdio).
"""

from __future__ import annotations

import json
import time
import uuid

import anyio
import structlog
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from fhir_mcp_shared.langfuse import trace as lf_trace
from fhir_mcp_shared.logging import configure_logging

from mcp_terminology.settings import settings
from mcp_terminology.tools.expand_valueset import expand_valueset
from mcp_terminology.tools.lookup_code import lookup_code
from mcp_terminology.tools.search_codes import search_codes
from mcp_terminology.tools.translate_code import translate_code

log = structlog.get_logger(__name__)

_SESSION_ID: str = str(uuid.uuid4())


def _build_server() -> Server:
    server = Server("mcp-terminology")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="lookup_code",
                description=(
                    "Look up a single code in a medical terminology system using FHIR $lookup. "
                    "Returns display name, definition, and alternate designations. "
                    "Supports LOINC, SNOMED CT, RxNorm, ICD-10, ICD-10-CM, CVX, UCUM, NDC, CPT."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "system": {
                            "type": "string",
                            "description": (
                                "System alias (e.g. 'loinc', 'snomed', 'rxnorm', 'icd-10-cm') "
                                "or canonical URI (e.g. 'http://loinc.org')."
                            ),
                        },
                        "code": {
                            "type": "string",
                            "description": "The code to look up (e.g. '8302-2', '73211009').",
                        },
                        "version": {
                            "type": "string",
                            "description": "Optional terminology version string.",
                            "default": "",
                        },
                    },
                    "required": ["system", "code"],
                },
            ),
            Tool(
                name="search_codes",
                description=(
                    "Search for codes by free text within a terminology system. "
                    "Uses FHIR ValueSet/$expand. "
                    "Supported systems: loinc, snomed, rxnorm. "
                    "For exact code lookup use lookup_code instead."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Free-text search (e.g. 'body height', 'diabetes mellitus').",
                        },
                        "system": {
                            "type": "string",
                            "description": "System alias: 'loinc', 'snomed', or 'rxnorm'.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum codes to return (1-100). Default: 20.",
                            "default": 20,
                        },
                    },
                    "required": ["query", "system"],
                },
            ),
            Tool(
                name="translate_code",
                description=(
                    "Translate a code from one terminology system to another "
                    "using FHIR ConceptMap/$translate. "
                    "Common supported mappings: SNOMED ↔ ICD-10-CM, LOINC ↔ SNOMED, RxNorm ↔ NDC."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The code to translate.",
                        },
                        "source_system": {
                            "type": "string",
                            "description": "Source system alias or URI.",
                        },
                        "target_system": {
                            "type": "string",
                            "description": "Target system alias or URI.",
                        },
                    },
                    "required": ["code", "source_system", "target_system"],
                },
            ),
            Tool(
                name="expand_valueset",
                description=(
                    "Expand a FHIR ValueSet to retrieve all (or filtered) codes it contains. "
                    "Accepts any canonical ValueSet URL hosted on tx.fhir.org. "
                    "Useful for exploring allowed values for coded FHIR elements."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": (
                                "Canonical ValueSet URL "
                                "(e.g. 'http://hl7.org/fhir/ValueSet/administrative-gender')."
                            ),
                        },
                        "filter": {
                            "type": "string",
                            "description": "Optional free-text filter to narrow results.",
                            "default": "",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum codes to return (1-100). Default: 20.",
                            "default": 20,
                        },
                    },
                    "required": ["url"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
        call_id = str(uuid.uuid4())
        log.info("tool_call", tool=name, call_id=call_id, session_id=_SESSION_ID)
        t0 = time.perf_counter()

        with lf_trace(
            name=name,
            session_id=_SESSION_ID,
            tags=["mcp-terminology", name],
            call_id=call_id,
            server_version="1.0.0",
        ) as tr:
            try:
                if name == "lookup_code":
                    result = await lookup_code(
                        system=arguments["system"],
                        code=arguments["code"],
                        version=arguments.get("version", ""),
                    )
                elif name == "search_codes":
                    result = await search_codes(
                        query=arguments["query"],
                        system=arguments["system"],
                        max_results=int(arguments.get("max_results", 0)),
                    )
                elif name == "translate_code":
                    result = await translate_code(
                        code=arguments["code"],
                        source_system=arguments["source_system"],
                        target_system=arguments["target_system"],
                    )
                elif name == "expand_valueset":
                    result = await expand_valueset(
                        url=arguments["url"],
                        filter=arguments.get("filter", ""),
                        max_results=int(arguments.get("max_results", 0)),
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
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-terminology",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,  # type: ignore[arg-type]
                    experimental_capabilities={},
                ),
            ),
        )


async def _run_sse(server: Server) -> None:
    """Run the server in SSE mode (HTTP + Server-Sent Events)."""
    try:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        import uvicorn
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
                    server_name="mcp-terminology",
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
    log.info("mcp_terminology_starting",
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

