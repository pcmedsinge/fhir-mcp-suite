FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

RUN pip install uv --no-cache-dir

WORKDIR /app

# ── deps layer ──────────────────────────────────────────────────────────────
FROM base AS deps

COPY shared/pyproject.toml /app/shared/pyproject.toml
COPY shared/src /app/shared/src
COPY packages/mcp-fhir/pyproject.toml /app/packages/mcp-fhir/pyproject.toml

# Install shared lib first (editable), then server deps
RUN uv pip install /app/shared && \
    uv pip install --no-deps /app/packages/mcp-fhir

# Install remaining runtime deps declared in server's pyproject.toml
RUN uv pip install "mcp[cli]>=1.6" httpx pydantic pydantic-settings structlog langfuse

# ── final image ─────────────────────────────────────────────────────────────
FROM base AS final

COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin/mcp-fhir /usr/local/bin/mcp-fhir

COPY shared/src /app/shared/src
COPY packages/mcp-fhir/src /app/packages/mcp-fhir/src

# Health-check (SSE mode only; stdio mode has no HTTP endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD \
    [ "$MCP_TRANSPORT" = "sse" ] && curl -sf http://localhost:${MCP_PORT:-8000}/sse || exit 0

EXPOSE 8000

ENTRYPOINT ["mcp-fhir"]
