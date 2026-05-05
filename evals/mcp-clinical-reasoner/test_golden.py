"""pytest entry-point for the mcp-clinical-reasoner golden eval suite.

Marked with ``@pytest.mark.eval`` so they are excluded from the fast unit-test
run and only executed explicitly.

Error-validation cases (``--tags error``) are network-independent and run
as part of CI:

    uv run pytest -m "eval" evals/mcp-clinical-reasoner/test_golden.py -k "error"

Full suite (requires rxnav.nlm.nih.gov):

    uv run pytest -m "eval and integration" evals/mcp-clinical-reasoner/test_golden.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "shared" / "src"))
sys.path.insert(0, str(_REPO / "packages" / "mcp-clinical-reasoner" / "src"))


@pytest.mark.eval
@pytest.mark.integration
def test_golden_suite_threshold() -> None:
    """Run the full golden eval suite and assert >= 85% pass rate."""
    from evals.mcp_clinical_reasoner.run_eval import run_eval  # type: ignore[import]
    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(run_eval())
    EvalRunner.assert_threshold(results, min_pass_rate=0.85)


@pytest.mark.eval
def test_golden_error_cases() -> None:
    """Run only error-validation cases (network-independent)."""
    import importlib.util
    from pathlib import Path as _P

    spec = importlib.util.spec_from_file_location(
        "run_eval_cr", _P(__file__).parent / "run_eval.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval(tags=["error"]))
    assert results, "No error cases found"
    EvalRunner.assert_threshold(results, min_pass_rate=1.0)


@pytest.mark.eval
def test_golden_offline_cases() -> None:
    """Run dose + allergy + error cases (all offline, no network needed)."""
    import importlib.util
    from pathlib import Path as _P

    spec = importlib.util.spec_from_file_location(
        "run_eval_cr2", _P(__file__).parent / "run_eval.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    from fhir_mcp_shared.eval import EvalRunner

    results = asyncio.run(mod.run_eval(tags=["dose", "allergy", "error"]))
    assert results, "No offline cases found"
    EvalRunner.assert_threshold(results, min_pass_rate=1.0)
