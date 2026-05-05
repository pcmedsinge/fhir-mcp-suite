# mcp-clinical-reasoner

> Rule-based drug interactions, dose check, and allergy MCP server (RxNav backend).
> Part of the [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite) monorepo.

[![PyPI](https://img.shields.io/pypi/v/mcp-clinical-reasoner)](https://pypi.org/project/mcp-clinical-reasoner/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../../LICENSE)

> **Status: Coming weeks 6-7 (Phase 3.4)**
>
> Watch this repo for updates or ⭐ star it to follow progress.

## What it will do

`mcp-clinical-reasoner` will expose rule-based clinical safety checks via MCP.
No LLM hallucination — answers are always backed by a structured knowledge source.

| Tool (planned) | Description | Backend |
|----------------|-------------|---------|
| `check_drug_interactions` | DDI check for a medication list | NLM RxNav `/interaction` |
| `check_dose` | Dose range validation (age/weight) | NLM RxNav `/rxclass` + dose tables |
| `check_allergies` | Cross-reactivity check for FHIR AllergyIntolerance list | NLM RxNav + SNOMED hierarchy |

## Why this is unique

No other MCP server provides point-of-care clinical safety checks.
All existing servers are read/search proxies.
This server is a **reasoning layer** that returns structured verdicts,
not raw data.

## Quick start (preview)

```bash
# Not yet available — target: weeks 6-7
uvx mcp-clinical-reasoner   # coming soon
```

## License

[Apache-2.0](../../LICENSE)
