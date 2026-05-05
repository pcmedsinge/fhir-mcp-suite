# mcp-fhir

> FHIR R4 MCP server with built-in HAPI profile validation.
> Part of the [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite) monorepo.

[![PyPI](https://img.shields.io/pypi/v/mcp-fhir)](https://pypi.org/project/mcp-fhir/)
[![CI](https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../../LICENSE)

## What it does

`mcp-fhir` exposes three MCP tools that let any MCP-compatible AI (Claude, GPT-4o, etc.) interact
with any FHIR R4 server **and** validate resources against US Core and IPS profiles in one shot —
something no other public FHIR MCP server does today (May 2026).

| Tool | Description |
|------|-------------|
| `fhir_read` | Read a single FHIR resource by type + ID |
| `fhir_search` | Search a resource type with FHIR query params |
| `validate_against_profile` | Validate a resource against a profile URL via HAPI validator |

## Quick start

```bash
# requires Python 3.12+
uvx mcp-fhir           # stdio transport (Claude Desktop)

# or SSE transport (HTTP)
MCP_TRANSPORT=sse uvx mcp-fhir
```

### Claude Desktop config (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "fhir": {
      "command": "uvx",
      "args": ["mcp-fhir"],
      "env": {
        "FHIR_BASE_URL": "https://hapi.fhir.org/baseR4"
      }
    }
  }
}
```

## Configuration

All settings via environment variables (see [`.env.example`](../../.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `FHIR_BASE_URL` | `https://hapi.fhir.org/baseR4` | FHIR server base URL |
| `HAPI_VALIDATOR_URL` | `http://localhost:8080` | HAPI validator sidecar |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `MCP_PORT` | `8000` | Port for SSE transport |
| `LOG_FORMAT` | `json` | `json` or `console` |
| `LANGFUSE_PUBLIC_KEY` | _(unset)_ | LangFuse observability (optional) |

## Profile validation

The `validate_against_profile` tool supports shorthand aliases:

| Alias | Profile URL |
|-------|------------|
| `us-core-patient` | `http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient` |
| `us-core-observation` | `http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-clinical-result` |
| `us-core-condition` | `http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns` |
| `us-core-medication-request` | `http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationrequest` |
| `us-core-encounter` | `http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter` |
| `ips-patient` | `http://hl7.org/fhir/uv/ips/StructureDefinition/Patient-uv-ips` |

Profile validation requires the HAPI validator sidecar (included in
`docker-compose.yml` at repo root).

## Development

```bash
# From monorepo root
uv sync
uv run pytest packages/mcp-fhir/tests -v
# Integration tests (requires HAPI public server access)
uv run pytest packages/mcp-fhir/tests -m integration
```

## Architecture

```
Client (Claude / GPT-4o)
    │  MCP protocol (stdio or SSE)
    ▼
mcp-fhir server (Python, anyio)
    ├── fhir_read ──────────► FHIR R4 server (configurable)
    ├── fhir_search ─────────► FHIR R4 server
    └── validate_against_profile
              │
              ▼
        HAPI validator sidecar (markiantorno/validator-wrapper)
              │
              ▼
        LangFuse (optional observability)
```

## License

[Apache-2.0](../../LICENSE)
