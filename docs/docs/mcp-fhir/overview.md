# mcp-fhir — Overview

`mcp-fhir` is an MCP server that exposes FHIR R4 read, search, and
**HAPI-backed profile validation** as MCP tools.

## Tools

| Tool | Description |
|------|-------------|
| `fhir_read` | Read a single FHIR resource by type + ID |
| `fhir_search` | Search with FHIR query parameters, returns a Bundle |
| `validate_against_profile` | Validate a resource against US Core / IPS profiles |

## Unique value

`validate_against_profile` is not available in any other FHIR MCP server
(as of May 2026). It calls the HAPI validator sidecar and returns a
structured `ValidationReport` with `is_conformant`, error count, and
per-issue details — enabling clinical AI pipelines to enforce data quality.

## Architecture

```
Claude / GPT-4o  ──MCP──►  mcp-fhir server
                               ├── fhir_read/search ──► FHIR R4 server
                               └── validate ──────────► HAPI validator
                                                             │
                                                        LangFuse traces
```
