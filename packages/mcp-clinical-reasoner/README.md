# mcp-clinical-reasoner

<!-- mcp-name: io.github.pcmedsinge/mcp-clinical-reasoner -->

> **Part of [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite)** — v1.0.0

An MCP server providing four clinical pharmacology tools backed by the free
[NLM RxNav REST API](https://rxnav.nlm.nih.gov/) and a built-in rule-based
reference table. No API key required. No PHI processed.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](../../LICENSE)

---

## Tools

| Tool | Transport | Description |
|------|-----------|-------------|
| `lookup_drug` | RxNav API | Resolve drug name or RxNorm CUI → canonical name, RxCUI, drug-class membership, dose reference |
| `check_drug_interactions` | RxNav API | Detect drug-drug interactions (DDIs) for 2–10 RxNorm CUIs, sorted by severity |
| `check_dose` | Rule-based | Validate a proposed single dose (mg) against a built-in table of ~20 common drugs |
| `check_allergy_conflicts` | Rule-based | Cross-reactivity check against 12 allergen classes using built-in table |

---

## Architecture

```
Claude Desktop / LangGraph agent
          │  MCP (stdio or SSE)
          ▼
 mcp-clinical-reasoner  (:8002 in SSE mode)
    ├── lookup_drug ────────────────► rxnav.nlm.nih.gov/REST
    ├── check_drug_interactions ────► rxnav.nlm.nih.gov/REST
    ├── check_dose ─────────────────► built-in DOSE_TABLE (20 drugs)
    └── check_allergy_conflicts ────► built-in ALLERGEN_CLASSES (12 classes)
```

All tool calls traced via **LangFuse** (session-scoped, latency + response bytes).

---

## Built-in Dose Table

Covers 20 common drugs: acetaminophen, ibuprofen, aspirin, naproxen, metformin,
lisinopril, atorvastatin, metoprolol, amlodipine, omeprazole, amoxicillin,
azithromycin, warfarin, furosemide, sertraline, gabapentin, clopidogrel,
hydrochlorothiazide, prednisone, albuterol.

Brand aliases are resolved automatically (e.g. `"Tylenol"` → `acetaminophen`,
`"Advil"` → `ibuprofen`).

## Built-in Allergen Classes

12 classes: penicillin, cephalosporin, sulfonamide, nsaid, macrolide,
fluoroquinolone, statin, ace_inhibitor, angiotensin_receptor_blocker,
beta_blocker, thiazide_diuretic, tetracycline.

---

## Quick start

```bash
# Install (uv workspace from repo root)
uv sync --all-packages

# Run (stdio, default)
uv run mcp-clinical-reasoner

# Run (SSE on port 8002)
MCP_TRANSPORT=sse uv run mcp-clinical-reasoner
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RXNAV_BASE_URL` | `https://rxnav.nlm.nih.gov/REST` | RxNav API base URL |
| `RXNAV_TIMEOUT_S` | `30.0` | HTTP timeout (seconds) |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `MCP_HOST` | `0.0.0.0` | SSE bind host |
| `MCP_PORT` | `8002` | SSE port |
| `LANGFUSE_PUBLIC_KEY` | *(optional)* | LangFuse tracing |
| `LANGFUSE_SECRET_KEY` | *(optional)* | LangFuse tracing |
| `LANGFUSE_HOST` | *(optional)* | LangFuse host |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Claude Desktop configuration

```json
{
  "mcpServers": {
    "clinical-reasoner": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/fhir-mcp-suite",
        "run", "--package", "mcp-clinical-reasoner",
        "mcp-clinical-reasoner"
      ]
    }
  }
}
```

---

## Tests

```bash
# Unit tests (36 tests, no network required)
uv run pytest packages/mcp-clinical-reasoner/tests/ -v -m "not integration and not eval"

# Offline eval (dose + allergy + error validation)
uv run python evals/mcp-clinical-reasoner/run_eval.py --tags dose allergy error

# Full eval suite (requires rxnav.nlm.nih.gov)
uv run python evals/mcp-clinical-reasoner/run_eval.py
```

### Eval results (offline, no network)

| Tag set | Cases | Pass rate |
|---------|-------|-----------|
| error | 6 | 100% |
| dose + allergy | 12 | 100% |

---

## Disclaimer

This server is for **research and educational purposes only**. It does **not**
replace clinical judgement, pharmacist review, or professional medical advice.
All dose limits and cross-reactivity rules are from general adult references
and must be individualised for each patient.

---

## License

Apache-2.0 — see [LICENSE](../../LICENSE).
