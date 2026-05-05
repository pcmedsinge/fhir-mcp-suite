# Contributing

Contributions are welcome! Please:

1. Fork the repo and create a feature branch
2. Run `uv sync` and `pre-commit install`
3. Make your change, add tests, run `uv run pytest -m "not integration"`
4. Open a PR against `main`

## Code style

- Python 3.12+, ruff for lint + format, mypy strict for `mcp-fhir` and `shared`
- All public functions need docstrings
- Pydantic models at every tool boundary

## Running the full stack locally

```bash
docker compose up hapi-fhir hapi-validator postgres -d
uv run mcp-fhir   # stdio transport
```
