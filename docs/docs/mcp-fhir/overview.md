# mcp-fhir — Overview

`mcp-fhir` is an MCP server that exposes FHIR R4 read, search, pagination,
server capabilities, and **HAPI-backed profile validation** as MCP tools.

**Status:** ✅ v1.0 — `uvx mcp-fhir`

## Tools

| Tool | Description | Backend |
|------|-------------|--------|
| `fhir_capabilities` | Retrieve a summary of the FHIR server's CapabilityStatement (version, resources, operations) | Configured FHIR R4 server |
| `fhir_read` | Read a single FHIR R4 resource by type and logical ID | Configured FHIR R4 server |
| `fhir_search` | Search a FHIR R4 resource type with query parameters; returns a Bundle | Configured FHIR R4 server |
| `fhir_search_next` | Follow a Bundle pagination link returned by `fhir_search` | Configured FHIR R4 server |
| `validate_against_profile` | Validate a FHIR R4 resource against a StructureDefinition profile (US Core, IPS) | HAPI validator sidecar |

## Unique value

`validate_against_profile` is not available in any other FHIR MCP server
(as of May 2026). It calls the HAPI validator sidecar and returns a
structured `ValidationReport` with `is_conformant`, error count, and
per-issue details — enabling clinical AI pipelines to enforce data quality.

## Architecture

```
Claude / GPT-4o  ──MCP──►  mcp-fhir server
                               ├── fhir_capabilities/read/search/next ──► FHIR R4 server
                               └── validate_against_profile ────────────► HAPI validator sidecar
                                                                                │
                                                                           LangFuse traces
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `FHIR_BASE_URL` | `https://hapi.fhir.org/baseR4` | FHIR server to query |
| `HAPI_VALIDATOR_URL` | `http://localhost:8082` | HAPI validator sidecar |
| `SMART_ENABLED` | `false` | Enable SMART-on-FHIR auth |
