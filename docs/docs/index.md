# fhir-mcp-suite

Three coherent MCP servers for clinical AI:

- **[mcp-fhir](mcp-fhir/overview.md)** — FHIR R4 read/search/pagination + HAPI profile validation ✅ v1.0
- **[mcp-terminology](mcp-terminology/overview.md)** — Unified LOINC/SNOMED/RxNorm/ICD-10 lookup, search, translate, ValueSet expand ✅ v1.0
- **[mcp-clinical-reasoner](mcp-clinical-reasoner/overview.md)** — Drug lookup, interactions (OpenFDA), dose check, allergy conflicts ✅ v1.0

## Why this suite

> No other MCP server validates FHIR resources against profiles.
> `mcp-fhir` is the first to combine FHIR R4 read/search with HAPI profile
> validation in a single MCP tool — a requirement for any production clinical AI pipeline.

## Quick start

```bash
uvx mcp-fhir
```

See [mcp-fhir installation](mcp-fhir/installation.md) for Claude Desktop setup.
