# mcp-fhir

> FHIR R4 MCP server — read, search, paginate, validate resources against US Core/IPS profiles,
> and authenticate against Epic/Cerner EHR sandboxes via SMART-on-FHIR OAuth 2.0.  
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

## SMART-on-FHIR authentication

`mcp-fhir` v1.1.0 adds SMART-on-FHIR **backend services** (`client_credentials` grant, RFC 6749)
so the server can authenticate against real Epic / Cerner sandboxes — no browser redirect needed.

When `SMART_ENABLED=true`, every FHIR request gets an `Authorization: Bearer <token>` header.
Tokens are cached in-process and refreshed automatically 30 s before expiry.

### SMART environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_ENABLED` | `false` | Set `true` to activate SMART auth |
| `SMART_CLIENT_ID` | `""` | App client ID from EHR registration portal |
| `SMART_CLIENT_SECRET` | `""` | Client secret (stored as `SecretStr`, never logged) |
| `SMART_TOKEN_URL` | `""` | Token endpoint URL; auto-discovered if blank |
| `SMART_SCOPES` | `system/*.read` | Space-separated OAuth 2.0 scopes |
| `SMART_GRANT_TYPE` | `client_credentials` | OAuth grant type (only `client_credentials` supported) |
| `SMART_TOKEN_TIMEOUT_S` | `15.0` | HTTP timeout for token requests |

When `SMART_TOKEN_URL` is blank the server performs SMART auto-discovery:  
`GET {FHIR_BASE_URL}/.well-known/smart-configuration → token_endpoint`.  
Falls back to `{FHIR_BASE_URL}/oauth2/token` if discovery returns a non-200.

### Epic sandbox quick-start

1. Register at <https://fhir.epic.com/> → **My Apps** → create a backend-services app.
2. Note your **Client ID** and **Client Secret**.
3. Create `.env` in the monorepo root (already in `.gitignore`):

```dotenv
FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
SMART_ENABLED=true
SMART_CLIENT_ID=your-epic-client-id
SMART_CLIENT_SECRET=your-epic-client-secret
# SMART_TOKEN_URL is optional — auto-discovered from FHIR_BASE_URL
```

### Cerner sandbox quick-start

1. Register at <https://code.cerner.com/> → create a backend-services app.
2. Note your **Client ID** and the token endpoint URL.
3. Update `.env`:

```dotenv
FHIR_BASE_URL=https://fhir-ehr-code.cerner.com/r4/your-tenant-id
SMART_ENABLED=true
SMART_CLIENT_ID=your-cerner-client-id
SMART_CLIENT_SECRET=your-cerner-client-secret
SMART_TOKEN_URL=https://authorization.cerner.com/tenants/your-tenant-id/protocols/oauth2/profiles/smart-v1/token
```

### Claude Desktop config with SMART auth

```json
{
  "mcpServers": {
    "mcp-fhir": {
      "command": "uvx",
      "args": ["mcp-fhir"],
      "env": {
        "FHIR_BASE_URL": "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
        "SMART_ENABLED": "true",
        "SMART_CLIENT_ID": "your-epic-client-id",
        "SMART_CLIENT_SECRET": "your-epic-client-secret"
      }
    }
  }
}
```

### Running SMART integration tests

```bash
# Requires real sandbox credentials in .env
uv run pytest packages/mcp-fhir/tests -m smart_integration -v
```

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
