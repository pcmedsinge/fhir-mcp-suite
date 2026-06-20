# fhir-mcp-suite

> Three coherent MCP servers for clinical AI — FHIR R4, terminologies, and clinical reasoning.

[![CI](https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/ci.yml)
[![mcp-fhir PyPI](https://img.shields.io/pypi/v/mcp-fhir?label=mcp-fhir)](https://pypi.org/project/mcp-fhir/)
[![mcp-terminology PyPI](https://img.shields.io/pypi/v/mcp-terminology?label=mcp-terminology)](https://pypi.org/project/mcp-terminology/)
[![mcp-clinical-reasoner PyPI](https://img.shields.io/pypi/v/mcp-clinical-reasoner?label=mcp-clinical-reasoner)](https://pypi.org/project/mcp-clinical-reasoner/)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-listed-blue)](https://registry.modelcontextprotocol.io/?search=io.github.pcmedsinge)
[![Glama](https://img.shields.io/badge/Glama-listed-orange)](https://glama.ai/mcp/servers/pcmedsinge/fhir-mcp-suite)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)

## What's in the suite

| Server | Status | Install | What it does |
|--------|--------|---------|-------------|
| **mcp-fhir** | ✅ v1.1.1 on PyPI | `uvx mcp-fhir` | FHIR R4 read/search + **HAPI profile validation** |
| **mcp-terminology** | ✅ v1.0 on PyPI | `uvx mcp-terminology` | Unified LOINC / SNOMED / RxNorm / ICD-10 lookup + ValueSet expansion |
| **mcp-clinical-reasoner** | ✅ v1.0 on PyPI | `uvx mcp-clinical-reasoner` | Drug interactions (OpenFDA), dose check, allergy conflicts |

## Why this suite is different

Every FHIR MCP server available today (June 2026) is a **read proxy** — they retrieve resources but
never tell you whether the resource is **valid**. `mcp-fhir` adds HAPI profile validation as a
first-class MCP tool. Composing `fhir_read` → `validate_against_profile` in one Claude session
enables clinical AI pipelines that are actually safe.

**Three sharp differentiators:**
1. **Profile validation built into `mcp-fhir`** — HAPI validator sidecar, US Core + IPS profiles supported out of the box
2. **Composable suite** — three coherent servers sharing one install, one config convention, one eval harness
3. **Production rigor** — latency benchmarks, golden-query eval suite, structured JSON logs, `/health` + LangFuse traces

## Quick start — mcp-fhir

```bash
# 1-command install (requires Python 3.12+)
uvx mcp-fhir

# Validate a Patient against US Core
# (requires HAPI validator sidecar — see docker-compose.yml)
uvx mcp-fhir --transport sse  # or set MCP_TRANSPORT=sse
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`  
(Windows: `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "fhir": {
      "command": "uvx",
      "args": ["mcp-fhir"],
      "env": {
        "FHIR_BASE_URL": "https://hapi.fhir.org/baseR4"
      }
    },
    "terminology": {
      "command": "uvx",
      "args": ["mcp-terminology"]
    },
    "clinical-reasoner": {
      "command": "uvx",
      "args": ["mcp-clinical-reasoner"]
    }
  }
}
```

## Local dev stack

```bash
# Start HAPI FHIR + validator + Postgres
docker compose up hapi-fhir hapi-validator postgres

# Install workspace
uv sync

# Run unit tests
uv run pytest -m "not integration and not eval"

# Run mcp-fhir locally (stdio, points at local HAPI)
FHIR_BASE_URL=http://localhost:8081/fhir \
HAPI_VALIDATOR_URL=http://localhost:8082 \
  uv run mcp-fhir
```

## Repo layout

```
fhir-mcp-suite/
├── packages/
│   ├── mcp-fhir/              # PyPI: mcp-fhir          ✅ v1.1
│   ├── mcp-terminology/       # PyPI: mcp-terminology   ✅ v1.0
│   └── mcp-clinical-reasoner/ # PyPI: mcp-clinical-reasoner ✅ v1.0
├── shared/                    # structlog, LangFuse, base Pydantic models, eval harness
├── evals/                     # golden query sets per server
├── docs/                      # MkDocs Material site
├── .github/workflows/         # ci.yml (matrix) + release.yml (per-package PyPI on tag)
├── docker-compose.yml         # all 3 + HAPI validator + Postgres
├── pyproject.toml             # uv workspace root
└── mkdocs.yml
```

## Releases

| Package | Version | Released |
|---------|---------|----------|
| `mcp-fhir` | v1.1 | June 2026 |
| `mcp-terminology` | v1.0 | June 2026 |
| `mcp-clinical-reasoner` | v1.0 | June 2026 |

## Contributing

See [CONTRIBUTING.md](docs/docs/dev/contributing.md).
Apache-2.0 licensed — PRs welcome.
