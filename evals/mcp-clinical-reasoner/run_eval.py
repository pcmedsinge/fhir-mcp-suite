"""mcp-clinical-reasoner eval runner.

Runs the golden query suite against the NLM RxNav API (rxnav.nlm.nih.gov)
for network cases, and fully offline for rule-based tools.

Usage
-----
# Run all error/offline cases (no network required):
  uv run python evals/mcp-clinical-reasoner/run_eval.py --tags error

# Run offline tool cases (dose + allergy):
  uv run python evals/mcp-clinical-reasoner/run_eval.py --tags dose,allergy

# Run full suite (requires rxnav.nlm.nih.gov):
  uv run python evals/mcp-clinical-reasoner/run_eval.py

# CI mode (exits 1 if pass rate < threshold):
  uv run python evals/mcp-clinical-reasoner/run_eval.py --ci --threshold 0.85

Environment variables:
  RXNAV_BASE_URL   (default: https://rxnav.nlm.nih.gov/REST)
  LANGFUSE_*       (optional, for tracing)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import structlog

REPO_ROOT = Path(__file__).parent.parent.parent
GOLDEN_FILE = Path(__file__).parent / "golden_queries.json"

sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "mcp-clinical-reasoner" / "src"))

from fhir_mcp_shared.eval import EvalResult, EvalRunner, GoldenCase  # noqa: E402
from fhir_mcp_shared.logging import configure_logging  # noqa: E402

configure_logging(level="INFO", fmt="console")
log = structlog.get_logger("eval.clinical_reasoner")


# ── Tool dispatch ─────────────────────────────────────────────────────────────

async def _invoke(tool: str, input_args: dict[str, Any]) -> dict[str, Any]:
    """Route to the appropriate async tool function."""
    if tool == "lookup_drug":
        from mcp_clinical_reasoner.tools.lookup_drug import lookup_drug
        return await lookup_drug(**input_args)

    if tool == "check_drug_interactions":
        from mcp_clinical_reasoner.tools.check_drug_interactions import check_drug_interactions
        return await check_drug_interactions(**input_args)

    if tool == "check_dose":
        from mcp_clinical_reasoner.tools.check_dose import check_dose
        return await check_dose(**input_args)

    if tool == "check_allergy_conflicts":
        from mcp_clinical_reasoner.tools.check_allergy_conflicts import check_allergy_conflicts
        return await check_allergy_conflicts(**input_args)

    raise ValueError(f"Unknown tool: {tool!r}")


# ── Programmatic assertions ───────────────────────────────────────────────────

def _programmatic_check(
    case: GoldenCase, result: dict[str, Any]
) -> tuple[bool, str]:
    """Handle special assertion keys in expected.

    Keys:
    - ``found``             : result["found"] == value (bool)
    - ``has_high_severity`` : result["has_high_severity"] == value
    - ``has_conflicts``     : result["has_conflicts"] == value
    - ``assessment``        : result["assessment"] == value
    - ``canonical_name``    : result["canonical_name"] == value
    """
    exp = case.expected
    checks: list[tuple[bool, str]] = []

    for key in ("found", "has_high_severity", "has_conflicts"):
        if key in exp:
            actual_val = result.get(key)
            ok = actual_val == exp[key]
            checks.append((ok, f"{key}={actual_val!r} (expected {exp[key]!r})"))

    for key in ("assessment", "canonical_name"):
        if key in exp:
            actual_val = result.get(key)
            ok = actual_val == exp[key]
            checks.append((ok, f"{key}={actual_val!r} (expected {exp[key]!r})"))

    if not checks:
        return True, ""

    failed = [(ok, msg) for ok, msg in checks if not ok]
    if failed:
        return False, "; ".join(msg for _, msg in failed)
    return True, "; ".join(msg for _, msg in checks)


def _subset_check(
    expected: dict[str, Any], actual: dict[str, Any]
) -> tuple[bool, float, str]:
    """Check plain key=value assertions from expected dict, skipping special keys."""
    SPECIAL = {
        "found", "has_high_severity", "has_conflicts", "assessment",
        "canonical_name", "error_contains",
    }
    plain = {k: v for k, v in expected.items() if k not in SPECIAL}
    if not plain:
        return True, 1.0, "no plain assertions"
    hits = 0
    misses: list[str] = []
    for k, v in plain.items():
        if actual.get(k) == v:
            hits += 1
        else:
            misses.append(f"{k}: expected {v!r}, got {actual.get(k)!r}")
    score = hits / len(plain)
    return len(misses) == 0, score, "; ".join(misses) if misses else "ok"


# ── Eval loop ─────────────────────────────────────────────────────────────────

async def run_eval(tags: list[str] | None = None) -> list[EvalResult]:
    cases = [GoldenCase.model_validate(c)
             for c in json.loads(GOLDEN_FILE.read_text())]

    results: list[EvalResult] = []
    for case in cases:
        if tags and not (set(tags) & set(case.tags)):
            continue

        log.info("case_start", id=case.id, tool=case.tool)
        t0 = time.perf_counter()
        error_expected = "error_contains" in case.expected

        try:
            result = await _invoke(case.tool, case.input)
            elapsed = time.perf_counter() - t0

            if error_expected:
                er = EvalResult(
                    case_id=case.id, passed=False, score=0.0,
                    actual=result,
                    notes=f"Expected error containing {case.expected['error_contains']!r} but tool succeeded",
                )
            else:
                plain_ok, plain_score, plain_notes = _subset_check(case.expected, result)
                prog_ok, prog_notes = _programmatic_check(case, result)

                passed = plain_ok and prog_ok
                score = plain_score if plain_ok else plain_score * 0.5
                if not prog_ok:
                    score = min(score, 0.5)
                notes = "; ".join(filter(None, [
                    plain_notes if not plain_ok else "",
                    prog_notes if not prog_ok else prog_notes,
                ]))
                if not notes:
                    notes = "all assertions passed"

                er = EvalResult(case_id=case.id, passed=passed, score=score,
                                actual=result, notes=notes)

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            exc_str = str(exc)

            if error_expected:
                needle = case.expected["error_contains"].lower()
                ok = needle in exc_str.lower()
                er = EvalResult(
                    case_id=case.id, passed=ok, score=1.0 if ok else 0.0,
                    notes=f"error={exc_str[:120]!r}" + (
                        "" if ok else f" (expected {needle!r})"
                    ),
                )
            else:
                er = EvalResult(
                    case_id=case.id, passed=False, score=0.0,
                    notes=f"unexpected exception: {exc_str[:120]}",
                )

        log.info(
            "case_done",
            id=case.id,
            passed=er.passed,
            score=round(er.score, 2),
            elapsed_s=round(elapsed, 2),
            notes=(er.notes or "")[:120],
        )
        results.append(er)

    return results


# ── Output helpers ────────────────────────────────────────────────────────────

def _print_summary(results: list[EvalResult]) -> None:
    passed = sum(r.passed for r in results)
    total = len(results)
    rate = passed / total if total else 0.0

    print(f"\n{'─'*62}")
    print(f"  mcp-clinical-reasoner eval — {passed}/{total} passed ({rate:.1%})")
    print(f"{'─'*62}")
    for r in results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.case_id:<40}  {(r.notes or '')[:60]}")
    print(f"{'─'*62}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="mcp-clinical-reasoner golden eval runner"
    )
    parser.add_argument(
        "--tags", nargs="*",
        help="Filter by tag(s): smoke lookup interactions dose allergy error security integration alias"
    )
    parser.add_argument("--ci", action="store_true",
                        help="Exit 1 if pass rate below threshold")
    parser.add_argument("--threshold", type=float, default=0.85,
                        help="Minimum pass rate for CI gate (default 0.85)")
    parser.add_argument("--output-json", type=Path, default=None,
                        help="Write results JSON to path (for CI artefacts)")
    args = parser.parse_args()

    results = asyncio.run(run_eval(tags=args.tags))
    _print_summary(results)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps([r.model_dump() for r in results], indent=2)
        )
        log.info("results_written", path=str(args.output_json))

    if args.ci:
        try:
            EvalRunner.assert_threshold(results, min_pass_rate=args.threshold)
        except AssertionError as exc:
            print(f"\nCI GATE FAILED: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
