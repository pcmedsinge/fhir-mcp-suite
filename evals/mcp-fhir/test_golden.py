"""pytest entry-point for the golden eval suite.

Marked with `@pytest.mark.eval` so they are excluded from the fast unit-test
run and only executed when a real FHIR stack is available:

    uv run pytest -m eval --threshold=0.85
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Make sure repo packages are importable from any cwd.
_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "shared" / "src"))
sys.path.insert(0, str(_REPO / "packages" / "mcp-fhir" / "src"))


@pytest.mark.eval
@pytest.mark.integration
def test_golden_suite_threshold(request: pytest.FixtureRequest) -> None:
    """Run the full golden eval suite and assert ≥ 85% pass rate."""
    import importlib.util

    threshold = float(request.config.getoption("--threshold", default="0.85"))
    spec = importlib.util.spec_from_file_location("run_eval", Path(__file__).parent / "run_eval.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval())
    EvalRunner.assert_threshold(results, min_pass_rate=threshold)


@pytest.mark.eval
@pytest.mark.integration
def test_golden_smoke_threshold() -> None:
    """Run only 'smoke' cases — must all pass."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_eval", Path(__file__).parent / "run_eval.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval(tags=["smoke"]))
    EvalRunner.assert_threshold(results, min_pass_rate=1.0)
