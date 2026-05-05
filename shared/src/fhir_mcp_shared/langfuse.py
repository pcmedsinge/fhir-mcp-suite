"""LangFuse v3 wrapper — gracefully degrades when credentials are absent.

Usage in any MCP server::

    from fhir_mcp_shared.langfuse import span, generation

    with span("fhir_read", resource_type="Patient", resource_id="123"):
        result = await do_read()

    with generation("llm_call", model="gpt-4o-mini", input=prompt) as gen:
        resp = await openai_client.chat.completions.create(...)
        if gen:
            gen.update(output=resp.choices[0].message.content)

If ``LANGFUSE_PUBLIC_KEY`` / ``LANGFUSE_SECRET_KEY`` are not set, all
helpers are no-ops and the server runs without observability.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_client: Any | None = None
_initialized: bool = False


def get_client() -> Any | None:
    """Return a singleton Langfuse client, or ``None`` if credentials aren't set."""
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        log.debug("langfuse_disabled", reason="LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set")
        return None

    try:
        from langfuse import Langfuse  # type: ignore[import-untyped]
    except ImportError as exc:
        log.warning("langfuse_import_failed", error=str(exc))
        return None

    try:
        _client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        log.info("langfuse_initialized", host=host)
    except Exception as exc:
        log.warning("langfuse_init_failed", error=str(exc))
    return _client


@contextmanager
def span(name: str, **kwargs: Any) -> Generator[Any, None, None]:
    """Context manager that wraps a logical step in a LangFuse span.

    Yields the span object (or ``None`` if LangFuse is disabled) so callers
    can attach metadata::

        with span("validate", profile=profile_url) as s:
            result = validate(resource)
            if s:
                s.update(output=result.model_dump())
    """
    client = get_client()
    if client is None:
        yield None
        return

    try:
        s = client.start_span(name=name, metadata=kwargs)
        try:
            yield s
        finally:
            s.end()
    except Exception as exc:
        log.warning("langfuse_span_error", name=name, error=str(exc))
        yield None


@contextmanager
def generation(name: str, model: str = "", **kwargs: Any) -> Generator[Any, None, None]:
    """Context manager for an LLM generation span.

    Callers should call ``gen.update(output=..., usage_details=...)`` inside
    the block for cost/token tracking.
    """
    client = get_client()
    if client is None:
        yield None
        return

    try:
        g = client.start_generation(name=name, model=model, metadata=kwargs)
        try:
            yield g
        finally:
            g.end()
    except Exception as exc:
        log.warning("langfuse_generation_error", name=name, error=str(exc))
        yield None
