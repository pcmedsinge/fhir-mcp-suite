# mcp-terminology — Overview

`mcp-terminology` provides a unified MCP interface to clinical terminology
systems: LOINC, SNOMED CT, RxNorm, and ICD-10-CM.

**Status:** ✅ v1.0 — `uvx mcp-terminology`

## Tools

| Tool | Description | Backend |
|------|-------------|--------|
| `lookup_code` | Look up a single code in a terminology system using FHIR `$lookup`. Supports `loinc`, `snomed`, `rxnorm`, `icd-10-cm` or canonical URI | tx.fhir.org |
| `search_codes` | Search for codes by free text within a terminology system | tx.fhir.org |
| `translate_code` | Translate a code from one terminology system to another using FHIR `$translate` | tx.fhir.org |
| `expand_valueset` | Expand a FHIR ValueSet to retrieve all (or filtered) codes it contains. Accepts any canonical ValueSet URL hosted on tx.fhir.org | tx.fhir.org |

## Architecture

```
Claude / GPT-4o  ──MCP──►  mcp-terminology server
                               ├── lookup_code / search_codes ──► tx.fhir.org $lookup
                               ├── translate_code ──────────────► tx.fhir.org $translate
                               └── expand_valueset ─────────────► tx.fhir.org $expand
                                                                        │
                                                                   LangFuse traces
```

## Supported terminology systems

| Alias | Canonical URI | System |
|-------|--------------|--------|
| `loinc` | `http://loinc.org` | LOINC |
| `snomed` | `http://snomed.info/sct` | SNOMED CT |
| `rxnorm` | `http://www.nlm.nih.gov/research/umls/rxnorm` | RxNorm |
| `icd-10-cm` | `http://hl7.org/fhir/sid/icd-10-cm` | ICD-10-CM |
