# mcp-clinical-reasoner — Overview

`mcp-clinical-reasoner` exposes rule-based and API-grounded clinical safety
checks as MCP tools. All answers are backed by structured knowledge sources —
no LLM hallucination.

**Status:** ✅ v1.0 — `uvx mcp-clinical-reasoner`

## Tools

| Tool | Description | Backend |
|------|-------------|--------|
| `lookup_drug` | Look up a drug by name or RxNorm CUI. Returns canonical name, drug class, allergen class, and dose reference data | NLM RxNav REST |
| `check_drug_interactions` | Check for drug-drug interactions (DDIs) among 2–10 drugs by name. Handles class-level warnings (e.g. "ACE inhibitors", "NSAIDs") | OpenFDA drug label API (`api.fda.gov`) |
| `check_dose` | Validate a proposed dose against a built-in reference table (~20 common drugs). Returns: `within_range`, `exceeds_single_dose`, `exceeds_daily_dose`, or `below_typical` | Rule-based table (no network) |
| `check_allergy_conflicts` | Check a drug for cross-reactivity conflicts given a list of known allergies. Covers penicillin↔cephalosporin, NSAID class, sulfonamide class | Rule-based table (no network) |

## Architecture

```
Claude / GPT-4o  ──MCP──►  mcp-clinical-reasoner server
                               ├── lookup_drug ──────────────► NLM RxNav REST
                               ├── check_drug_interactions ──► OpenFDA drug label API
                               ├── check_dose ────────────────► built-in dose table
                               └── check_allergy_conflicts ───► built-in cross-reactivity table
                                                                        │
                                                                   LangFuse traces
```

## Notes

- NLM removed the RxNav `/interaction` endpoint in May 2026 (v3.1.353). Drug interaction
  checks now use the FDA drug label database, which is the authoritative source for
  approved interaction language.
- `check_dose` and `check_allergy_conflicts` make zero network calls — suitable for
  low-latency or offline use.
- All tool inputs are Pydantic-validated; prompt-injection defense is applied at every boundary.
