"""mcp-fhir eval runner.

Runs the golden query suite against a live FHIR + HAPI validator stack and
produces a pass/fail report. Designed for both local development and CI.

Usage
-----
# Run all cases (requires HAPI sidecar + FHIR server):
  uv run python evals/mcp-fhir/run_eval.py

# Run only smoke tests:
  uv run python evals/mcp-fhir/run_eval.py --tags smoke

# CI mode (exits 1 if pass rate < threshold):
  uv run python evals/mcp-fhir/run_eval.py --ci --threshold 0.85

Environment variables (same as server):
  FHIR_BASE_URL, HAPI_VALIDATOR_URL, LANGFUSE_*
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

# Allow running from repo root or from this directory.
REPO_ROOT = Path(__file__).parent.parent.parent
GOLDEN_FILE = Path(__file__).parent / "golden_queries.json"

sys.path.insert(0, str(REPO_ROOT / "shared" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "mcp-fhir" / "src"))

from fhir_mcp_shared.eval import EvalResult, EvalRunner, GoldenCase  # noqa: E402  (EvalRunner used for assert_threshold + type)
from fhir_mcp_shared.logging import configure_logging  # noqa: E402

configure_logging(level="INFO", fmt="console")
log = structlog.get_logger("eval")


# ── Custom invoke adapters (programmatic checks for non-dict assertions) ────

async def _invoke(tool: str, input_args: dict[str, Any]) -> dict[str, Any]:
    """Route to the appropriate async tool function."""
    if tool == "fhir_capabilities":
        from mcp_fhir.tools.fhir_capabilities import fhir_capabilities
        return await fhir_capabilities()

    if tool == "fhir_read":
        from mcp_fhir.tools.fhir_read import fhir_read
        return await fhir_read(**input_args)

    if tool == "fhir_search":
        from mcp_fhir.tools.fhir_search import fhir_search
        return await fhir_search(**input_args)

    if tool == "validate_against_profile":
        from mcp_fhir.tools.validate_profile import validate_against_profile
        return await validate_against_profile(**input_args)

    raise ValueError(f"Unknown tool: {tool!r}")


def _programmatic_check(case: GoldenCase, result: dict[str, Any]) -> tuple[bool, str]:
    """Extra assertions that can't be expressed as simple dict equality."""
    cid = case.id

    if cid == "cap_001_fhir_version":
        ver = result.get("fhir_version") or ""
        ok = str(ver).startswith("4.0")
        return ok, f"fhir_version={ver!r} (expected 4.0.x)"

    if cid == "cap_002_resource_count":
        count = result.get("resource_count", 0)
        ok = int(count) >= 10
        return ok, f"resource_count={count} (expected >= 10)"

    if cid in ("validate_004_obs_missing_fields_fails_us_core",
               "validate_007_error_count_field_present"):
        if cid == "validate_007_error_count_field_present":
            ok = "error_count" in result and "issues" in result
            return ok, f"keys present: error_count={'error_count' in result}, issues={'issues' in result}"

    if cid == "read_002_id_preserved":
        ok = "id" in result
        return ok, f"'id' present: {ok}"

    return True, ""   # no additional programmatic check


def _subset_check(
    expected: dict[str, Any], actual: dict[str, Any]
) -> tuple[bool, float, str]:
    """Return (passed, score, notes) — mirrors EvalRunner._check logic."""
    if not expected:
        return True, 1.0, "no dict assertions"
    hits = 0
    misses: list[str] = []
    for k, v in expected.items():
        if actual.get(k) == v:
            hits += 1
        else:
            misses.append(f"{k}: expected {v!r}, got {actual.get(k)!r}")
    score = hits / len(expected)
    return len(misses) == 0, score, "; ".join(misses) if misses else "ok"


async def run_eval(tags: list[str] | None = None) -> list[EvalResult]:
    cases = [GoldenCase.model_validate(c)
             for c in json.loads(GOLDEN_FILE.read_text())]

    results: list[EvalResult] = []
    for case in cases:
        if tags and not (set(tags) & set(case.tags)):
            continue

        log.info("case_start", id=case.id, tool=case.tool)
        t0 = time.perf_counter()
        try:
            result = await _invoke(case.tool, case.input)
            elapsed = time.perf_counter() - t0

            # 1. Dict subset check
            passed, score, notes = _subset_check(case.expected, result)

            # 2. Programmatic check (may override)
            prog_ok, prog_notes = _programmatic_check(case, result)
            if not prog_ok:
                passed, score, notes = False, 0.0, prog_notes
            elif prog_notes:
                notes = prog_notes

            er = EvalResult(case_id=case.id, passed=passed, score=score,
                            actual=result, notes=notes)

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            er = EvalResult(case_id=case.id, passed=False, score=0.0, notes=str(exc))

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


def _print_summary(results: list[EvalResult]) -> None:
    passed = sum(r.passed for r in results)
    total = len(results)
    rate = passed / total if total else 0

    print(f"\n{'─'*60}")
    print(f"  mcp-fhir eval — {passed}/{total} passed ({rate:.1%})")
    print(f"{'─'*60}")
    for r in results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.case_id:<50}  {r.notes[:50] if r.notes else ''}")
    print(f"{'─'*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="mcp-fhir golden eval runner")
    parser.add_argument("--tags", nargs="*", help="Filter by tag (e.g. smoke validate)")
    parser.add_argument("--ci", action="store_true", help="Exit 1 if below threshold")
    parser.add_argument("--threshold", type=float, default=0.85, help="Min pass rate for CI")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Write results JSON to file (for CI artefacts)",
    )
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

    print("Eval complete.")


if __name__ == "__main__":
    main()
