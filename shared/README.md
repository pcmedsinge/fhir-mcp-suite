# fhir-mcp-shared

Internal shared utilities for the [fhir-mcp-suite](https://github.com/pcmedsinge/fhir-mcp-suite) monorepo.

Not published to PyPI. Used as a uv workspace dependency by `mcp-fhir`, `mcp-terminology`, and `mcp-clinical-reasoner`.

## Contents

- `logging.py` — structlog configuration (JSON + console renderers)
- `langfuse.py` — LangFuse v3 wrapper with graceful no-op degradation
- `models/` — shared Pydantic models (`FhirResource`, `ValidationReport`, etc.)
- `eval/` — golden-query eval harness (`EvalRunner`, `GoldenCase`, `EvalResult`)
