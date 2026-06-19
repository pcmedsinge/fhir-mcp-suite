"""mcp-fhir server entrypoint.

Registers five MCP tools:
  - fhir_capabilities        — CapabilityStatement summary (what the server supports)
  - fhir_read                — read a single FHIR resource
  - fhir_search              — search a FHIR resource type
  - fhir_search_next         — follow a Bundle pagination link
  - validate_against_profile — validate a resource against a HAPI-backed profile

Transport is selected via the MCP_TRANSPORT env var (default: stdio).
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
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

from mcp_fhir.settings import settings
from mcp_fhir.tools.fhir_capabilities import fhir_capabilities
from mcp_fhir.tools.fhir_read import fhir_read
from mcp_fhir.tools.fhir_search import fhir_search, fhir_search_next
from mcp_fhir.tools.validate_profile import validate_against_profile

# Stable session ID for the lifetime of this server process.
# Groups all tool calls from one MCP session in LangFuse.
_SESSION_ID: str = str(uuid.uuid4())

log = structlog.get_logger(__name__)


def _build_server() -> Server:
    server = Server("mcp-fhir")

    @server.list_tools()  # type: ignore
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="fhir_capabilities",
                description=(
                    "Retrieve a summary of the FHIR server's CapabilityStatement: "
                    "FHIR version, software, supported resource types, and available "
                    "search parameters. Call this first to understand what the server supports."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="fhir_read",
                description=(
                    "Read a single FHIR R4 resource by type and logical ID. "
                    "Returns the full resource JSON."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_type": {
                            "type": "string",
                            "description": "FHIR resource type, e.g. 'Patient', 'Observation'.",
                        },
                        "resource_id": {
                            "type": "string",
                            "description": "Server-assigned logical ID.",
                        },
                    },
                    "required": ["resource_type", "resource_id"],
                },
            ),
            Tool(
                name="fhir_search",
                description=(
                    "Search a FHIR R4 resource type. "
                    "Returns a FHIR Bundle (searchset) with matching entries."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource_type": {
                            "type": "string",
                            "description": "FHIR resource type to search.",
                        },
                        "params": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": (
                                "FHIR search parameters as key-value pairs, "
                                "e.g. {'family': 'Smith', 'gender': 'female'}."
                            ),
                        },
                    },
                    "required": ["resource_type"],
                },
            ),
            Tool(
                name="validate_against_profile",
                description=(
                    "Validate a FHIR R4 resource against a StructureDefinition profile "
                    "using the HAPI validator. Supports US Core and IPS profiles as well "
                    "as base FHIR R4 conformance. "
                    "Returns conformance status, error count, and issue details."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource": {
                            "description": "A FHIR resource as a JSON object (or a JSON string that will be parsed).",
                        },
                        "profile": {
                            "type": "string",
                            "description": (
                                "Profile URL or alias (e.g. 'us-core-patient', "
                                "'http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient'). "
                                "Empty string = base R4 validation only."
                            ),
                            "default": "",
                        },
                        "fhir_version": {
                            "type": "string",
                            "description": "FHIR version (default '4.0.1').",
                            "default": "4.0.1",
                        },
                    },
                    "required": ["resource"],
                },
            ),
            Tool(
                name="fhir_search_next",
                description=(
                    "Follow a Bundle pagination link returned by fhir_search. "
                    "Pass the '_next_url' value from the previous search result. "
                    "Returns the next page as a FHIR Bundle, again with '_next_url' "
                    "if more pages exist."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "next_url": {
                            "type": "string",
                            "description": "The '_next_url' from a previous fhir_search Bundle.",
                        }
                    },
                    "required": ["next_url"],
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
            tags=["mcp-fhir", name],
            call_id=call_id,
            server_version="1.0.0",
        ) as tr:
            try:
                if name == "fhir_capabilities":
                    result = await fhir_capabilities()
                elif name == "fhir_read":
                    result = await fhir_read(
                        resource_type=arguments["resource_type"],
                        resource_id=arguments["resource_id"],
                    )
                elif name == "fhir_search":
                    result = await fhir_search(
                        resource_type=arguments["resource_type"],
                        params=arguments.get("params"),
                    )
                elif name == "validate_against_profile":
                    _res = arguments["resource"]
                    if isinstance(_res, str):
                        import json as _json

                        _res = _json.loads(_res)
                    result = await validate_against_profile(
                        resource=_res,
                        profile=arguments.get("profile", ""),
                        fhir_version=arguments.get("fhir_version", "4.0.1"),
                    )
                elif name == "fhir_search_next":
                    result = await fhir_search_next(next_url=arguments["next_url"])
                else:
                    raise ValueError(f"Unknown tool: {name!r}")

                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                payload = json.dumps(result, indent=2)
                if tr:
                    tr.update(output={"response_bytes": len(payload), "latency_ms": latency_ms})
                log.info(
                    "tool_ok",
                    tool=name,
                    call_id=call_id,
                    latency_ms=latency_ms,
                    response_bytes=len(payload),
                )
                return [TextContent(type="text", text=payload)]

            except Exception as exc:
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                if tr:
                    tr.update(output={"error": str(exc), "latency_ms": latency_ms})
                log.error(
                    "tool_error", tool=name, call_id=call_id, latency_ms=latency_ms, error=str(exc)
                )
                return [TextContent(type="text", text=f"Error: {exc}")]

    return server


async def _run_stdio(server: Server) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-fhir",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


async def _run_sse(server: Server) -> None:
    """Run the server in SSE mode (HTTP + Server-Sent Events)."""
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
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name="mcp-fhir",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
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
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()


def main() -> None:
    """Entry point for ``mcp-fhir`` CLI."""
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    log.info(
        "mcp_fhir_starting",
        transport=settings.mcp_transport,
        version="1.0.0",
        session_id=_SESSION_ID,
    )
    server = _build_server()

    if settings.mcp_transport == "sse":
        anyio.run(_run_sse, server)
    else:
        anyio.run(_run_stdio, server)


if __name__ == "__main__":
    main()
