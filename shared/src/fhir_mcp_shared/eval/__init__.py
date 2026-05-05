"""Eval harness skeleton — golden-query runner for all three MCP servers.

Usage::

    from fhir_mcp_shared.eval import EvalRunner, GoldenCase, EvalResult

    runner = EvalRunner(cases=load_golden("evals/mcp-fhir/golden_queries.json"))
    results = await runner.run(invoke_fn=my_tool_fn)
    runner.assert_threshold(results, min_pass_rate=0.90)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger(__name__)


class GoldenCase(BaseModel):
    """A single golden-query test case."""

    id: str
    description: str
    tool: str = Field(description="MCP tool name to invoke")
    input: dict[str, Any] = Field(description="Tool input arguments")
    expected: dict[str, Any] = Field(description="Expected fields in the response")
    tags: list[str] = Field(default_factory=list)


class EvalResult(BaseModel):
    """Outcome of running a single golden case."""

    case_id: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0, description="0.0 = fail, 1.0 = full pass")
    actual: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class EvalRunner:
    """Runs a golden-query suite against an async tool-invoke function."""

    def __init__(self, cases: list[GoldenCase]) -> None:
        self.cases = cases

    @classmethod
    def from_file(cls, path: str | Path) -> "EvalRunner":
        """Load golden cases from a JSON file."""
        data = json.loads(Path(path).read_text())
        return cls(cases=[GoldenCase.model_validate(c) for c in data])

    async def run(
        self,
        invoke_fn: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
        tags: list[str] | None = None,
    ) -> list[EvalResult]:
        """Run all cases (optionally filtered by tag) and return results.

        Args:
            invoke_fn: An async callable ``(tool_name, input) -> dict``.
            tags:      If provided, only run cases whose tags overlap.
        """
        results: list[EvalResult] = []
        for case in self.cases:
            if tags and not set(tags) & set(case.tags):
                continue
            log.info("eval_case_start", case_id=case.id, tool=case.tool)
            try:
                actual = await invoke_fn(case.tool, case.input)
                passed, score, notes = self._check(case.expected, actual)
            except Exception as exc:
                log.warning("eval_case_error", case_id=case.id, error=str(exc))
                passed, score, notes = False, 0.0, f"exception: {exc}"
                actual = {}
            results.append(
                EvalResult(
                    case_id=case.id, passed=passed, score=score, actual=actual, notes=notes
                )
            )
            log.info("eval_case_done", case_id=case.id, passed=passed, score=score)
        return results

    def _check(
        self, expected: dict[str, Any], actual: dict[str, Any]
    ) -> tuple[bool, float, str]:
        """Check that all expected keys/values appear in actual (subset match).

        Returns (passed, score, notes).
        """
        if not expected:
            return True, 1.0, "no assertions defined"

        hits = 0
        misses: list[str] = []
        for key, expected_val in expected.items():
            actual_val = actual.get(key)
            if actual_val == expected_val:
                hits += 1
            else:
                misses.append(f"{key}: expected {expected_val!r}, got {actual_val!r}")

        score = hits / len(expected)
        passed = len(misses) == 0
        notes = "; ".join(misses) if misses else "all assertions passed"
        return passed, score, notes

    @staticmethod
    def assert_threshold(results: list[EvalResult], min_pass_rate: float = 0.85) -> None:
        """Raise AssertionError if pass rate is below threshold (used in CI)."""
        if not results:
            raise AssertionError("No eval results to check")
        pass_rate = sum(r.passed for r in results) / len(results)
        if pass_rate < min_pass_rate:
            failures = [r for r in results if not r.passed]
            details = "\n".join(f"  {r.case_id}: {r.notes}" for r in failures)
            raise AssertionError(
                f"Eval pass rate {pass_rate:.1%} < threshold {min_pass_rate:.1%}\n{details}"
            )
