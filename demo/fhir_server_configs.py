"""
fhir-mcp-suite — FHIR server configuration examples
Shows how to point mcp-fhir at different FHIR endpoints:
  1. Public HAPI R4 demo server     (no auth — good for dev/testing)
  2. SMART Health IT open sandbox   (no auth — richer synthetic data)
  3. Epic SMART sandbox             (client_credentials, auto-discovery)
  4. Cerner Ignite sandbox          (client_credentials, explicit token URL)
  5. Any generic FHIR + SMART server
  6. Local HAPI via Docker Compose  (full stack, no external deps)

Usage:
    # Pick the config you want, then run:
    uv run python demo/fhir_server_configs.py --server epic

    # Or import a config into your own agent code:
    from demo.fhir_server_configs import EPIC_SANDBOX, make_session
"""

from __future__ import annotations

import argparse
import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ── 1. Public HAPI R4 — no auth required ────────────────────────────────────
# Great for local dev and demos. Rate-limited; shared test data.
PUBLIC_HAPI = StdioServerParameters(
    command="uv",
    args=["run", "--package", "mcp-fhir", "mcp-fhir"],
    env={
        **os.environ,
        "FHIR_BASE_URL":  "https://hapi.fhir.org/baseR4",
        "SMART_ENABLED":  "false",
        "LOG_FORMAT":     "console",
    },
)

# ── 2. SMART Health IT open sandbox — no auth required ──────────────────────
# Synthea-generated synthetic patients. Richer clinical data than public HAPI.
SMART_HEALTH_IT = StdioServerParameters(
    command="uv",
    args=["run", "--package", "mcp-fhir", "mcp-fhir"],
    env={
        **os.environ,
        "FHIR_BASE_URL":  "https://r4.smarthealthit.org",
        "SMART_ENABLED":  "false",
        "LOG_FORMAT":     "console",
    },
)

# ── 3. Epic SMART Sandbox ────────────────────────────────────────────────────
# Prerequisites:
#   a. Create a free developer account at https://fhir.epic.com/
#   b. Register a "Backend System" app (non-production)
#   c. Copy the Client ID and generate/download the client secret (or JWK)
#   d. Request scopes: system/Patient.read system/Observation.read etc.
#
# Epic supports SMART auto-discovery — leave SMART_TOKEN_URL empty and the
# server will fetch it from:
#   https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/.well-known/smart-configuration
#
# Replace the placeholder values below with your actual app credentials.
EPIC_SANDBOX = StdioServerParameters(
    command="uv",
    args=["run", "--package", "mcp-fhir", "mcp-fhir"],
    env={
        **os.environ,
        "FHIR_BASE_URL":        "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
        "SMART_ENABLED":        "true",
        "SMART_CLIENT_ID":      os.environ.get("EPIC_CLIENT_ID", "YOUR_EPIC_CLIENT_ID"),
        "SMART_CLIENT_SECRET":  os.environ.get("EPIC_CLIENT_SECRET", "YOUR_EPIC_CLIENT_SECRET"),
        # Leave SMART_TOKEN_URL blank → auto-discovered from /.well-known/smart-configuration
        "SMART_TOKEN_URL":      os.environ.get("EPIC_TOKEN_URL", ""),
        "SMART_SCOPES":         "system/Patient.read system/Observation.read system/Condition.read",
        "SMART_GRANT_TYPE":     "client_credentials",
        "LOG_FORMAT":           "console",
    },
)

# ── 4. Cerner Ignite FHIR Sandbox ───────────────────────────────────────────
# Prerequisites:
#   a. Create an account at https://code.cerner.com/
#   b. Register a "System Account" app in the Cerner Developer Console
#   c. Get the Client ID and Client Secret
#   d. Cerner exposes token URL explicitly — set it below.
#
# Replace CERNER_ACCOUNT_ID and credentials with your actual values.
CERNER_SANDBOX = StdioServerParameters(
    command="uv",
    args=["run", "--package", "mcp-fhir", "mcp-fhir"],
    env={
        **os.environ,
        # Replace <account-id> with your Cerner account ID (e.g. "ec2458f2-1e24-41c8-b71b-0e701af7583d")
        "FHIR_BASE_URL":        f"https://fhir-myrecord.cerner.com/r4/{os.environ.get('CERNER_ACCOUNT_ID', 'YOUR_ACCOUNT_ID')}",
        "SMART_ENABLED":        "true",
        "SMART_CLIENT_ID":      os.environ.get("CERNER_CLIENT_ID", "YOUR_CERNER_CLIENT_ID"),
        "SMART_CLIENT_SECRET":  os.environ.get("CERNER_CLIENT_SECRET", "YOUR_CERNER_CLIENT_SECRET"),
        # Cerner requires explicit token URL (no auto-discovery for system apps)
        "SMART_TOKEN_URL":      "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/protocols/oauth2/profiles/smart-v1/token",
        "SMART_SCOPES":         "system/Patient.read system/Observation.read",
        "SMART_GRANT_TYPE":     "client_credentials",
        "LOG_FORMAT":           "console",
    },
)

# ── 5. Any generic FHIR + SMART server ──────────────────────────────────────
# Template — copy and fill in your own values.
# If your server supports /.well-known/smart-configuration, leave SMART_TOKEN_URL empty.
def make_generic(
    fhir_base_url: str,
    client_id: str,
    client_secret: str,
    token_url: str = "",        # empty = auto-discover
    scopes: str = "system/*.read",
    grant_type: str = "client_credentials",
) -> StdioServerParameters:
    return StdioServerParameters(
        command="uv",
        args=["run", "--package", "mcp-fhir", "mcp-fhir"],
        env={
            **os.environ,
            "FHIR_BASE_URL":        fhir_base_url,
            "SMART_ENABLED":        "true",
            "SMART_CLIENT_ID":      client_id,
            "SMART_CLIENT_SECRET":  client_secret,
            "SMART_TOKEN_URL":      token_url,
            "SMART_SCOPES":         scopes,
            "SMART_GRANT_TYPE":     grant_type,
            "LOG_FORMAT":           "console",
        },
    )

# ── 6. Local Docker Compose full stack ──────────────────────────────────────
# Start with: docker compose up hapi-fhir hapi-validator -d
# Boots a private HAPI FHIR R4 server on :8081 + validator on :8082.
LOCAL_DOCKER = StdioServerParameters(
    command="uv",
    args=["run", "--package", "mcp-fhir", "mcp-fhir"],
    env={
        **os.environ,
        "FHIR_BASE_URL":       "http://localhost:8081/fhir",
        "HAPI_VALIDATOR_URL":  "http://localhost:8082",
        "SMART_ENABLED":       "false",
        "LOG_FORMAT":          "console",
    },
)


# ── Helper: connect and run a quick sanity check ────────────────────────────

async def make_session(params: StdioServerParameters) -> None:
    """Connect to the server, print its capabilities, and run one search."""
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Show available tools
            tools = await session.list_tools()
            print(f"\nConnected — {len(tools.tools)} tools available:")
            for t in tools.tools:
                print(f"  • {t.name}")

            # Capabilities
            cap_result = await session.call_tool("fhir_capabilities", arguments={})
            import json
            caps = json.loads(cap_result.content[0].text)
            print(f"\nFHIR server  : {caps.get('fhir_version', '?')}")
            print(f"Publisher    : {caps.get('publisher', 'n/a')}")
            print(f"Resources    : {caps.get('resource_count', '?')}")

            # One patient search
            search_result = await session.call_tool(
                "fhir_search",
                arguments={"resource_type": "Patient", "params": {"_count": "2"}},
            )
            bundle = json.loads(search_result.content[0].text)
            entries = bundle.get("entry", [])
            print(f"\nPatient search returned {len(entries)} entries")
            for e in entries:
                r = e.get("resource", {})
                print(f"  id={r.get('id')}")


CONFIGS: dict[str, StdioServerParameters] = {
    "hapi":          PUBLIC_HAPI,
    "smart-health":  SMART_HEALTH_IT,
    "epic":          EPIC_SANDBOX,
    "cerner":        CERNER_SANDBOX,
    "local":         LOCAL_DOCKER,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test mcp-fhir against a FHIR server")
    parser.add_argument(
        "--server",
        choices=list(CONFIGS),
        default="hapi",
        help="Which server config to use (default: hapi)",
    )
    args = parser.parse_args()

    cfg = CONFIGS[args.server]
    fhir_url = cfg.env.get("FHIR_BASE_URL", "") if cfg.env else ""
    print(f"\nTarget : {fhir_url}")
    print(f"SMART  : {cfg.env.get('SMART_ENABLED', 'false') if cfg.env else 'false'}")

    asyncio.run(make_session(cfg))
