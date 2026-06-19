"""LangFuse v3 wrapper — gracefully degrades when credentials are absent.

Usage in any MCP server::

    from fhir_mcp_shared.langfuse import span, generation, trace

    # Per-request trace (wraps one MCP tool call)
    with trace("fhir_read", session_id="session-abc", user_id="user-1") as t:
        with span("http_get", parent=t, resource_type="Patient") as s:
            result = await do_read()
            if s:
                s.update(output={"bytes": len(result)})

    # Simpler span without explicit trace:
    with span("fhir_search", resource_type="Patient") as s:
        ...

    # LLM generation (for mcp-clinical-reasoner):
    with generation("llm_call", model="gpt-4o-mini", input=prompt) as gen:
        resp = await openai_client.chat.completions.create(...)
        if gen:
            gen.update(output=resp.choices[0].message.content,
                       usage_details={"input": resp.usage.prompt_tokens,
                                      "output": resp.usage.completion_tokens})

If ``LANGFUSE_PUBLIC_KEY`` / ``LANGFUSE_SECRET_KEY`` are not set, all
helpers are no-ops and the server runs without observability.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from contextlib import contextmanager, suppress
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
        from langfuse import Langfuse  # type: ignore
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
def trace(
    name: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
    **metadata: Any,
) -> Generator[Any, None, None]:
    """Context manager that creates a top-level LangFuse trace.

    A trace represents one logical request (e.g. one MCP ``call_tool``
    invocation). Nest ``span()`` calls inside with ``parent=t``.

    Yields the trace object (or ``None`` if LangFuse is disabled).

    Example::

        with trace("fhir_read", session_id=session_id) as t:
            with span("http_get", parent=t, resource_type="Patient"):
                ...
    """
    client = get_client()
    if client is None:
        yield None
        return

    trace_id = str(uuid.uuid4())
    try:
        tr = client.trace(
            id=trace_id,
            name=name,
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
            metadata=metadata,
        )
        try:
            yield tr
        finally:
            with suppress(Exception):
                client.flush()
    except Exception as exc:
        log.warning("langfuse_trace_error", name=name, error=str(exc))
        yield None


@contextmanager
def span(
    name: str,
    *,
    parent: Any = None,
    **kwargs: Any,
) -> Generator[Any, None, None]:
    """Context manager that wraps a logical step in a LangFuse span.

    Args:
        name:   Span name (e.g. ``"fhir_read"``).
        parent: A trace or span object to nest under (optional).
        **kwargs: Metadata attached to the span.

    Yields the span object (or ``None`` if LangFuse is disabled) so callers
    can attach output metadata::

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
        kwargs_clean = {k: v for k, v in kwargs.items() if v is not None}
        if parent is not None:
            s = parent.span(name=name, metadata=kwargs_clean)
        else:
            s = client.start_span(name=name, metadata=kwargs_clean)
        try:
            yield s
        finally:
            s.end()
    except Exception as exc:
        log.warning("langfuse_span_error", name=name, error=str(exc))
        yield None


@contextmanager
def generation(
    name: str,
    model: str = "",
    *,
    parent: Any = None,
    **kwargs: Any,
) -> Generator[Any, None, None]:
    """Context manager for an LLM generation span.

    Callers should call ``gen.update(output=..., usage_details=...)`` inside
    the block for cost/token tracking.

    Args:
        name:   Generation name.
        model:  Model identifier (e.g. ``"gpt-4o-mini"``).
        parent: Parent trace or span (optional).
        **kwargs: Extra metadata.
    """
    client = get_client()
    if client is None:
        yield None
        return

    try:
        kwargs_clean = {k: v for k, v in kwargs.items() if v is not None}
        if parent is not None:
            g = parent.generation(name=name, model=model, metadata=kwargs_clean)
        else:
            g = client.start_generation(name=name, model=model, metadata=kwargs_clean)
        try:
            yield g
        finally:
            g.end()
    except Exception as exc:
        log.warning("langfuse_generation_error", name=name, error=str(exc))
        yield None
