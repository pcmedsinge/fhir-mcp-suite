# fhir-mcp-suite

Three coherent MCP servers for clinical AI:

- **[mcp-fhir](mcp-fhir/overview.md)** — FHIR R4 read/search + profile validation ✅ available now
- **[mcp-terminology](mcp-terminology/overview.md)** — Unified LOINC/SNOMED/RxNorm/ICD-10 (coming weeks 4-5)
- **[mcp-clinical-reasoner](mcp-clinical-reasoner/overview.md)** — Drug interactions + dose check (coming weeks 6-7)

## Why this suite

> No other MCP server validates FHIR resources against profiles.
> `mcp-fhir` is the first to combine FHIR R4 read/search with HAPI profile
> validation in a single MCP tool — a requirement for any production clinical AI pipeline.

## Quick start

```bash
uvx mcp-fhir
```

See [mcp-fhir installation](mcp-fhir/installation.md) for Claude Desktop setup.
