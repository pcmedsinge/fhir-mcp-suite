# mcp-terminology

> Unified LOINC / SNOMED CT / RxNorm / ICD-10 MCP server.
> Part of the [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite) monorepo.

[![PyPI](https://img.shields.io/pypi/v/mcp-terminology)](https://pypi.org/project/mcp-terminology/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../../LICENSE)

> **Status: Coming weeks 4-5 (Phase 3.3)**
>
> Watch this repo for updates or ⭐ star it to follow progress.

## What it will do

`mcp-terminology` will provide a single MCP server with tools for querying
four major clinical terminology systems:

| Tool (planned) | System | Backend |
|----------------|--------|---------|
| `loinc_lookup` | LOINC | FHIR tx.fhir.org `$lookup` |
| `snomed_lookup` | SNOMED CT | FHIR tx.fhir.org `$lookup` |
| `rxnorm_lookup` | RxNorm | NLM RxNav REST API |
| `icd10_lookup` | ICD-10-CM | CMS FHIR `$lookup` |
| `expand_value_set` | Any FHIR ValueSet | tx.fhir.org `$expand` |

## Why this matters

Clinical AI applications constantly need to map between terminologies.
Having all four systems accessible through a single MCP server,
with a unified response schema, eliminates per-system integration work.

## Quick start (preview)

```bash
# Not yet available — target: weeks 4-5
uvx mcp-terminology   # coming soon
```

## License

[Apache-2.0](../../LICENSE)
