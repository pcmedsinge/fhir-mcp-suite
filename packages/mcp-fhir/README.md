# mcp-fhir

> FHIR R4 MCP server — read, search, paginate, and validate resources against US Core/IPS profiles.  
> Part of the [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite) monorepo.

[![PyPI](https://img.shields.io/pypi/v/mcp-fhir)](https://pypi.org/project/mcp-fhir/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mcp-fhir)](https://pypi.org/project/mcp-fhir/)
[![CI](https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../../LICENSE)

## What it does

`mcp-fhir` exposes **five MCP tools** that let any MCP-compatible AI (Claude, GPT-4o, etc.)
interact with any FHIR R4 server — and validate resources against US Core and IPS profiles —
in a single server process. No other public FHIR MCP server combines search + validation today.

| Tool | Description |
|------|-------------|
| `fhir_capabilities` | CapabilityStatement summary — what the server supports |
| `fhir_read` | Read a single resource by type + logical ID |
| `fhir_search` | Search a resource type with FHIR query params; returns Bundle with `_next_url` when paginated |
| `fhir_search_next` | Follow a `_next_url` pagination link (SSRF-guarded) |
| `validate_against_profile` | Validate a resource via the HAPI validator; supports US Core & IPS aliases |

## Architecture

```
Claude Desktop / AI client
        │  MCP (stdio or SSE)
        ▼
┌───────────────────────────────┐
│        mcp-fhir  v1.0         │
│  ┌───────────────────────────┐│
│  │  tools/                   ││
│  │  ├─ fhir_capabilities.py  ││
│  │  ├─ fhir_read.py          ││
│  │  ├─ fhir_search.py        ││   ──► FHIR R4 server
│  │  └─ validate_profile.py   ││   ──► HAPI validator sidecar
│  └───────────────────────────┘│
│  fhir-mcp-shared               │
│  ├─ LangFuse traces (session)  │
│  ├─ Pydantic structured output │
│  └─ structlog JSON logging     │
└───────────────────────────────┘
```

## Quick start

```bash
# requires Python 3.12+ and uv
uvx mcp-fhir           # stdio transport (Claude Desktop, default)

# SSE transport (HTTP, for API access)
MCP_TRANSPORT=sse uvx mcp-fhir
```

### Claude Desktop config (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "mcp-fhir": {
      "command": "uvx",
      "args": ["mcp-fhir"],
      "env": {
        "FHIR_BASE_URL": "https://hapi.fhir.org/baseR4",
        "HAPI_VALIDATOR_URL": "http://localhost:8082"
      }
    }
  }
}
```

See [full installation guide](https://pcmedsinge.github.io/fhir-mcp-suite/mcp-fhir/installation/)
for HAPI validator setup, troubleshooting, and self-hosted FHIR server configuration.

## Eval results

Golden query suite — run against the public HAPI demo server (`hapi.fhir.org/baseR4`):

| Category | Cases | Target pass rate |
|---|---|---|
| `fhir_capabilities` | 2 | 100 % |
| `fhir_read` | 2 | 100 % |
| `fhir_search` | 8 | 100 % |
| `validate_against_profile` | 8 | ≥ 87.5 % |
| **Total** | **20** | **≥ 90 %** |

> Run locally: `uv run python evals/mcp-fhir/run_eval.py --ci --threshold 0.9`

## Configuration

All settings via environment variables (see [`.env.example`](../../.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `FHIR_BASE_URL` | `https://hapi.fhir.org/baseR4` | FHIR server base URL |
| `HAPI_VALIDATOR_URL` | `http://localhost:8080` | HAPI validator sidecar |
| `FHIR_TIMEOUT_S` | `30` | HTTP timeout in seconds |
| `FHIR_MAX_RESULTS` | `20` | Default `_count` for searches |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `MCP_PORT` | `8000` | Port for SSE transport |
| `LOG_FORMAT` | `json` | `json` (prod) or `console` (dev) |
| `LANGFUSE_PUBLIC_KEY` | _(unset)_ | LangFuse observability (optional) |
| `LANGFUSE_SECRET_KEY` | _(unset)_ | LangFuse observability (optional) |

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
