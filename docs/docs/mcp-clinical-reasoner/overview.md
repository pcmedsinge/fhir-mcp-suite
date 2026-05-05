# mcp-clinical-reasoner — Overview

> **Status: Coming weeks 6-7 (Phase 3.4)**

`mcp-clinical-reasoner` will expose rule-based clinical safety checks as MCP tools.
All answers are backed by structured knowledge sources — no LLM hallucination.

## Planned tools

| Tool | Description | Backend |
|------|-------------|---------|
| `check_drug_interactions` | DDI check for a medication list | NLM RxNav `/interaction` |
| `check_dose` | Dose range validation by age/weight | RxNav + dose tables |
| `check_allergies` | Cross-reactivity for FHIR AllergyIntolerance | RxNav + SNOMED |

Watch the [GitHub repo](https://github.com/pcmedsinge/fhir-mcp-suite) for updates.
