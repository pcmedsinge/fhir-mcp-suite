# mcp-terminology — Overview

> **Status: Coming weeks 4-5 (Phase 3.3)**

`mcp-terminology` will provide a unified MCP interface to four major
clinical terminology systems: LOINC, SNOMED CT, RxNorm, and ICD-10.

## Planned tools

| Tool | Terminology | Backend |
|------|------------|---------|
| `loinc_lookup` | LOINC | tx.fhir.org `$lookup` |
| `snomed_lookup` | SNOMED CT | tx.fhir.org `$lookup` |
| `rxnorm_lookup` | RxNorm | NLM RxNav REST |
| `icd10_lookup` | ICD-10-CM | CMS FHIR `$lookup` |
| `expand_value_set` | Any FHIR ValueSet | tx.fhir.org `$expand` |

Watch the [GitHub repo](https://github.com/pcmedsinge/fhir-mcp-suite) for updates.
