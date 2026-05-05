"""pytest entry-point for the mcp-terminology golden eval suite.

Marked with ``@pytest.mark.eval`` so they are excluded from the fast unit-test
run and only executed when network access to tx.fhir.org is available:

    uv run pytest -m "eval and integration" evals/mcp-terminology/test_golden.py

The error-validation cases (``--tags error``) are network-independent and run
as part of CI:

    uv run pytest -m "eval" evals/mcp-terminology/test_golden.py -k "error"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "shared" / "src"))
sys.path.insert(0, str(_REPO / "packages" / "mcp-terminology" / "src"))


@pytest.mark.eval
@pytest.mark.integration
def test_golden_suite_threshold(request: pytest.FixtureRequest) -> None:
    """Run the full golden eval suite and assert >= 85% pass rate."""
    import importlib.util

    threshold = float(request.config.getoption("--threshold", default="0.85"))
    spec = importlib.util.spec_from_file_location(
        "run_eval_terminology", Path(__file__).parent / "run_eval.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval())
    EvalRunner.assert_threshold(results, min_pass_rate=threshold)


@pytest.mark.eval
@pytest.mark.integration
def test_golden_smoke_threshold() -> None:
    """Run only 'smoke' cases — all must pass (100%)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_eval_terminology", Path(__file__).parent / "run_eval.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval(tags=["smoke"]))
    EvalRunner.assert_threshold(results, min_pass_rate=1.0)


@pytest.mark.eval
def test_golden_error_cases() -> None:
    """Run only error-validation cases — network-independent, all must pass."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_eval_terminology", Path(__file__).parent / "run_eval.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval(tags=["error"]))
    EvalRunner.assert_threshold(results, min_pass_rate=1.0)
