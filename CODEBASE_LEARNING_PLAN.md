# fhir-mcp-suite — Codebase Learning Plan

> A structured guide to understanding the entire codebase from scratch,
> layer by layer, from project structure through to deployment.
> Work through each layer in order — understand before moving on.

---

## How to use this document

Each layer has:
- **What you will understand** — the outcome
- **Files to read** — in order, with what to focus on in each
- **Key questions** — test your understanding before moving to next layer
- **Common confusions** — things that trip people up

---

## Layer 1 — Project Structure & Configuration

### What you will understand
How a Python monorepo is organised with `uv`, why `shared/` is separate from `packages/`,
and how all the config files relate to each other.

### Files to read

| File | What to focus on |
|------|-----------------|
| `pyproject.toml` (root) | `[tool.uv.workspace]` members list — this is what makes it a monorepo. `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` — shared quality config for ALL packages |
| `uv.lock` | Don't read line by line — just understand it pins ALL transitive deps for ALL packages in one file |
| `.env.example` | What environment variables exist across the suite |
| `.gitignore` | What is intentionally excluded (`.venv/`, `.env`, `dist/`) |
| `.gitattributes` | Enforces LF line endings — prevents CRLF issues on Windows |
| `packages/` (directory listing) | 3 subdirectories: `mcp-fhir/`, `mcp-terminology/`, `mcp-clinical-reasoner/` |
| `shared/` (directory listing) | One package: `fhir-mcp-shared` — internal infra, also on PyPI |

### Why `shared/` is NOT inside `packages/`

`packages/` = the 3 user-facing MCP servers (what end users install)
`shared/` = internal infrastructure (logging, observability, Pydantic models, eval harness)

`shared` is in a separate directory to signal that it is a dependency of the others,
not a peer. It must be published to PyPI first because the 3 packages depend on it.

### Structure of each package directory

Every package (e.g. `packages/mcp-fhir/`) follows the same layout:

```
packages/mcp-fhir/
├── pyproject.toml         ← package metadata, dependencies, build config
├── README.md              ← PyPI description + mcp-name marker for MCP Registry
├── Dockerfile             ← for containerised deployment
├── src/
│   └── mcp_fhir/          ← actual Python source (src layout prevents import confusion)
│       ├── __init__.py
│       ├── server.py      ← MCP server entrypoint
│       ├── settings.py    ← environment variable config (Pydantic Settings)
│       ├── http_client.py ← auth-aware HTTP helper
│       ├── smart_auth.py  ← SMART-on-FHIR OAuth 2.0 (mcp-fhir only)
│       ├── hapi/          ← HAPI validator client (mcp-fhir only)
│       │   ├── __init__.py
│       │   └── client.py
│       └── tools/         ← one file per MCP tool
│           ├── __init__.py
│           ├── fhir_capabilities.py
│           ├── fhir_read.py
│           ├── fhir_search.py
│           └── validate_profile.py
└── tests/
    ├── __init__.py
    ├── test_tools.py      ← unit tests (no external services)
    └── test_smart_auth.py ← SMART auth tests
```

### `shared/` structure

```
shared/
├── pyproject.toml
├── README.md
└── src/
    └── fhir_mcp_shared/
        ├── __init__.py
        ├── logging.py      ← structlog JSON/console setup
        ├── langfuse.py     ← LangFuse tracing (graceful no-op if unconfigured)
        ├── models/
        │   ├── __init__.py
        │   ├── fhir.py     ← FhirResource, FhirSearchParams Pydantic models
        │   └── validation.py ← ValidationReport, ValidationIssue, ValidationSeverity
        └── eval/
            └── __init__.py ← GoldenCase, EvalResult, EvalRunner
```

### Key questions for Layer 1

1. Why does each package use `src/mcp_fhir/` layout instead of just `mcp_fhir/` at the root?
2. What does `[tool.uv.workspace] members = ["packages/*", "shared"]` actually do?
3. Why is `uv.lock` committed to git but `.venv/` is not?
4. The 3 packages all list `fhir-mcp-shared>=0.1.0` as a dependency. How does `uv` know to use the local `shared/` folder during development instead of downloading from PyPI?

### Answers

1. **src layout** — prevents accidentally importing the package source directly during tests. With `src/`, Python must install the package (even in editable mode) to import it, which catches packaging bugs early.

2. **uv workspace** — tells uv that these directories are all part of one logical project. `uv sync --all-packages` installs all of them plus their shared dev dependencies into one `.venv`.

3. **uv.lock committed** — ensures every developer and CI gets identical package versions. `.venv/` is machine-specific (absolute paths baked in) so it cannot be shared.

4. **`[tool.uv.sources]`** — each package's `pyproject.toml` has:
   ```toml
   [tool.uv.sources]
   fhir-mcp-shared = { workspace = true }
   ```
   This tells uv: "during development, resolve `fhir-mcp-shared` from the local workspace, not PyPI." This override is stripped from the published wheel — users get the PyPI version.

---

## Layer 2 — Shared Library (`fhir-mcp-shared`)

### What you will understand
The infrastructure that every server uses: structured logging, LangFuse observability,
Pydantic data models, and the eval harness.

### Files to read (in order)

| File | What to focus on |
|------|-----------------|
| `shared/src/fhir_mcp_shared/logging.py` | `configure_logging()` — called once at server startup. Two modes: `json` (production) and `console` (dev). Uses structlog. |
| `shared/src/fhir_mcp_shared/langfuse.py` | `trace()`, `span()` context managers. The `try/except ImportError` pattern — graceful no-op if LangFuse not installed. |
| `shared/src/fhir_mcp_shared/models/validation.py` | `ValidationSeverity` enum, `ValidationIssue`, `ValidationReport`. `model_post_init` auto-calculates error/warning counts. |
| `shared/src/fhir_mcp_shared/models/fhir.py` | `FhirResource`, `FhirSearchParams` — simple Pydantic models used in type hints |
| `shared/src/fhir_mcp_shared/eval/__init__.py` | `GoldenCase`, `EvalResult`, `EvalRunner` — the eval harness. `EvalRunner.run()` is the key method. |

### Key questions for Layer 2

1. Why does `configure_logging()` accept `fmt="json"` or `fmt="console"` instead of just always using JSON?
2. What happens if `LANGFUSE_PUBLIC_KEY` is not set? Does the server crash?
3. In `ValidationReport`, why are `error_count` and `warning_count` computed in `model_post_init` instead of being set by the caller?
4. What is the purpose of `EvalRunner.assert_threshold(results, min_pass_rate=0.90)`?

---

## Layer 3 — mcp-fhir: Settings & Auth

### What you will understand
How configuration flows from environment variables into the server,
and how SMART-on-FHIR OAuth 2.0 authentication works.

### Files to read (in order)

| File | What to focus on |
|------|-----------------|
| `packages/mcp-fhir/src/mcp_fhir/settings.py` | `Settings(BaseSettings)` — every env var the server reads. Defaults mean it works with zero config. `smart_client_secret: SecretStr` — why SecretStr? |
| `packages/mcp-fhir/src/mcp_fhir/http_client.py` | `get_fhir_headers()` — called by every tool. Returns `{"Accept": "application/fhir+json"}` normally. Adds `Authorization: Bearer <token>` when SMART is enabled. |
| `packages/mcp-fhir/src/mcp_fhir/smart_auth.py` | `get_access_token()` — the main function. Token cache (`_cache` dict + `asyncio.Lock`). `discover_token_url()` — reads `/.well-known/smart-configuration`. `_acquire_client_credentials()` — the actual OAuth POST. |

### Key questions for Layer 3

1. Why is `smart_client_secret` typed as `SecretStr` instead of `str`?
2. What happens if you call `get_access_token()` twice in 30 seconds? Does it make two HTTP calls?
3. Why is `_cache_lock` initialised lazily (inside `_get_lock()`) instead of at module level?
4. What is `/.well-known/smart-configuration` and why does the server try to call it?

---

## Layer 4 — mcp-fhir: One Tool End to End (fhir_read)

### What you will understand
The complete lifecycle of an MCP tool call — from Claude sending a request,
through the server, to the FHIR API, and back.

### Files to read (in order)

| File | What to focus on |
|------|-----------------|
| `packages/mcp-fhir/src/mcp_fhir/server.py` | `_build_server()` — how tools are registered. `@server.list_tools()` — what Claude calls on connect. `@server.call_tool()` — the dispatcher. The `lf_trace` context manager wrapping every call. Error handling pattern (`try/except` returns `TextContent` not exception). |
| `packages/mcp-fhir/src/mcp_fhir/tools/fhir_read.py` | Input validation (empty check, ID regex). URL construction. `get_fhir_headers()` call. `httpx.AsyncClient` usage. `response.raise_for_status()`. |

### The full call flow for `fhir_read("Patient", "example")`

```
Claude Desktop
    │
    │  MCP: tools/call { name: "fhir_read", arguments: { resource_type: "Patient", resource_id: "example" } }
    ▼
server.py — @server.call_tool()
    │  opens lf_trace span
    │  routes to fhir_read()
    ▼
tools/fhir_read.py — fhir_read("Patient", "example")
    │  validates resource_type not empty
    │  validates resource_id: alphanumeric + hyphens + dots, max 64 chars
    │  constructs URL: https://hapi.fhir.org/baseR4/Patient/example
    │  calls get_fhir_headers() → {"Accept": "application/fhir+json"}
    │  opens httpx.AsyncClient
    │  GET https://hapi.fhir.org/baseR4/Patient/example
    ▼
FHIR Server (hapi.fhir.org)
    │  returns Patient JSON
    ▼
tools/fhir_read.py
    │  response.raise_for_status() ← raises if 4xx/5xx
    │  returns response.json()
    ▼
server.py
    │  json.dumps(result, indent=2)
    │  updates LangFuse span with latency + response size
    │  returns [TextContent(type="text", text=payload)]
    ▼
Claude Desktop
    receives Patient JSON as tool result
```

### Key questions for Layer 4

1. Why does `server.py` return `[TextContent(...)]` (a list) instead of just the JSON string?
2. What happens when `fhir_read("Patient", "../../etc/passwd")` is called? Trace through the validation.
3. Why does the server catch ALL exceptions and return `TextContent(type="text", text=f"Error: {exc}")` instead of letting the exception propagate?
4. What is `lf_trace` and what does it record?

---

## Layer 5 — mcp-fhir: Remaining Tools

### Files to read

| File | Key concept to understand |
|------|--------------------------|
| `packages/mcp-fhir/src/mcp_fhir/tools/fhir_search.py` | `_validate_search_params()` regex allowlist. `_extract_next_link()` pagination helper. `_normalize_netloc()` + SSRF guard in `fhir_search_next`. |
| `packages/mcp-fhir/src/mcp_fhir/tools/fhir_capabilities.py` | CapabilityStatement parsing — why we summarise instead of returning the full JSON. |
| `packages/mcp-fhir/src/mcp_fhir/tools/validate_profile.py` | `PROFILE_ALIASES` dict. `_resolve_profile()`. Calling the HAPI validator sidecar. `ValidationReport` from shared models. |
| `packages/mcp-fhir/src/mcp_fhir/hapi/client.py` | How the HAPI validator sidecar is called. Response parsing into `ValidationReport`. |

### Key concept: SSRF protection in `fhir_search_next`

When `fhir_search` returns a Bundle with a `next` link, Claude will call `fhir_search_next(next_url)`.
A malicious FHIR server (or prompt injection) could return a `next` link pointing to an internal IP
(`http://169.254.169.254/` — AWS metadata, for example) to steal credentials.

The guard:
```python
if _normalize_netloc(parsed) != _normalize_netloc(configured):
    raise ValueError("next_url host does not match configured FHIR server")
```

`_normalize_netloc` strips default ports so `https://host:443/` == `https://host/`.

---

## Layer 6 — mcp-terminology

### What you will understand
Same MCP pattern as mcp-fhir but calling a FHIR terminology server instead of a FHIR data server.

### Files to read (in order)

| File | Key concept |
|------|-------------|
| `packages/mcp-terminology/src/mcp_terminology/settings.py` | `TERMINOLOGY_BASE_URL` defaults to `https://tx.fhir.org/r4` |
| `packages/mcp-terminology/src/mcp_terminology/validation.py` | `resolve_system()` — maps aliases (`loinc`, `snomed`) to canonical URIs (`http://loinc.org`) |
| `packages/mcp-terminology/src/mcp_terminology/tools/lookup_code.py` | FHIR `CodeSystem/$lookup` operation |
| `packages/mcp-terminology/src/mcp_terminology/tools/search_codes.py` | `ValueSet/$expand?filter=` — how free-text search works in FHIR terminology |
| `packages/mcp-terminology/src/mcp_terminology/tools/translate_code.py` | `ConceptMap/$translate` — cross-system code translation |
| `packages/mcp-terminology/src/mcp_terminology/tools/expand_valueset.py` | `ValueSet/$expand` — full expansion of a ValueSet by URL |
| `packages/mcp-terminology/src/mcp_terminology/server.py` | Same `_build_server()` pattern as mcp-fhir |

### FHIR operations vs REST

FHIR has a concept of "operations" — RPC-style calls that don't fit REST.
They use `$` syntax: `GET /CodeSystem/$lookup?system=...&code=...`

This is why the terminology tools look different from `fhir_read` — they call operations,
not standard CRUD endpoints.

---

## Layer 7 — mcp-clinical-reasoner

### What you will understand
A different pattern — mostly offline/rule-based tools that only occasionally call external APIs.

### Files to read (in order)

| File | Key concept |
|------|-------------|
| `packages/mcp-clinical-reasoner/src/mcp_clinical_reasoner/constants.py` | `DOSE_TABLE`, `ALLERGEN_CLASSES`, `DRUG_ALIASES` — the built-in reference data. This is the "knowledge base". |
| `packages/mcp-clinical-reasoner/src/mcp_clinical_reasoner/validation.py` | `validate_drug_name()`, `validate_rxcui()` — input validation for clinical data |
| `packages/mcp-clinical-reasoner/src/mcp_clinical_reasoner/tools/lookup_drug.py` | Calls `rxnav.nlm.nih.gov` REST API. `is_rxcui()` to detect if input is a CUI or a name. |
| `packages/mcp-clinical-reasoner/src/mcp_clinical_reasoner/tools/check_drug_interactions.py` | Calls `api.fda.gov` (OpenFDA). `_fetch_interaction_text()` + `_find_mention()` — how DDIs are detected from label text. `_aliases()` — why class-level matching matters (FDA labels say "NSAIDs" not "ibuprofen"). |
| `packages/mcp-clinical-reasoner/src/mcp_clinical_reasoner/tools/check_dose.py` | Fully offline — no network calls. `_parse_frequency()` converts `"bid"` → `2.0` doses/day. |
| `packages/mcp-clinical-reasoner/src/mcp_clinical_reasoner/tools/check_allergy_conflicts.py` | Fully offline. Three conflict types: `direct_match`, `class_membership`, `cross_reactivity`. |

### Key concept: why rule-based instead of LLM for dose/allergy?

These tools are called BY an LLM. Using another LLM inside them would:
1. Add latency and cost
2. Risk hallucination on safety-critical data
3. Create non-deterministic behaviour (same input → different output)

Rule-based + authoritative data sources (FDA, NLM) = deterministic, auditable, trustworthy.

---

## Layer 8 — Infrastructure

### Files to read

| File | What to understand |
|------|-------------------|
| `docker-compose.yml` | 4 services: `hapi-fhir` (port 8081), `hapi-validator` (port 8082), `postgres` (5432), `mcp-fhir` (8000, SSE mode). Health checks. Volume for IG package cache. |
| `packages/mcp-fhir/Dockerfile` | How the server is containerised for SSE deployment |
| `.github/workflows/ci.yml` | 4 jobs: lint (ruff), typecheck (mypy), test (matrix per package), build (wheel). Pinned to Python 3.12. |
| `.github/workflows/release.yml` | Triggered by version tags. Parses package name from tag. Verifies pyproject.toml version matches. Builds wheel + sdist. Publishes via OIDC. Creates GitHub Release. |

### Key concept: OIDC trusted publishing

Traditional PyPI publish: store an API token as a GitHub secret — if leaked, anyone can publish.

OIDC publish: PyPI trusts GitHub Actions directly. When the workflow runs on a specific
repo + workflow + environment, PyPI issues a short-lived token automatically. No stored secret.

---

## Layer 9 — Evals

### Files to read

| File | What to understand |
|------|-------------------|
| `evals/mcp-fhir/golden_queries.json` | Structure of a `GoldenCase`: `{id, description, tool, input, expected, tags}`. How `expected` is a partial match (subset, not exact). |
| `evals/mcp-fhir/run_eval.py` | How `EvalRunner` is used. `--tags smoke` filter. `--ci --threshold 0.85` for CI mode. |
| `shared/src/fhir_mcp_shared/eval/__init__.py` | `EvalRunner.run()` — calls tools directly (no MCP transport). `_subset_match()` — why partial matching. |
| `evals/mcp-terminology/golden_queries.json` | Same structure, different tools |
| `evals/mcp-clinical-reasoner/golden_queries.json` | Same structure |

### Key concept: why golden queries matter

Unit tests check that validation logic works (e.g. bad input raises ValueError).
Golden queries check that the actual tool behaviour is correct end-to-end:
"given this FHIR search, do we get a Bundle back with the right structure?"

They run against real external services, so they're marked `@pytest.mark.integration`
and not run in CI by default — only manually or in scheduled runs.

---

## Layer 10 — Deployment (recap)

### What happens at each publish step

| Step | Command | What it does |
|------|---------|-------------|
| PyPI release | `git tag mcp-fhir-v1.1.1 && git push origin mcp-fhir-v1.1.1` | Triggers `release.yml` → builds wheel → publishes to PyPI via OIDC |
| MCP Registry | `mcp-publisher publish` (from `packages/mcp-fhir/`) | Reads `server.json`, validates mcp-name in PyPI README, registers metadata |
| Glama | Web form + Docker build config | Glama builds a container, runs quality checks, lists in search results |
| GitHub | Just push | README, badges, and code are already there |

See `PUBLISHING.md` for the complete step-by-step with all failure cases documented.

---

## Progress tracker

Mark each layer as you complete it:

- [ ] Layer 1 — Project Structure
- [ ] Layer 2 — Shared Library
- [ ] Layer 3 — mcp-fhir Settings & Auth
- [ ] Layer 4 — mcp-fhir: fhir_read end to end
- [ ] Layer 5 — mcp-fhir: remaining tools
- [ ] Layer 6 — mcp-terminology
- [ ] Layer 7 — mcp-clinical-reasoner
- [ ] Layer 8 — Infrastructure
- [ ] Layer 9 — Evals
- [ ] Layer 10 — Deployment recap
