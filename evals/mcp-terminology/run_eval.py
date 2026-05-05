"""mcp-terminology eval runner.

Runs the golden query suite against the free public FHIR R4 terminology server
(tx.fhir.org/r4) and produces a pass/fail report.

Usage
-----
# Run all cases (requires internet — tx.fhir.org):
  uv run python evals/mcp-terminology/run_eval.py

# Run only smoke tests:
  uv run python evals/mcp-terminology/run_eval.py --tags smoke

# Run only error-validation cases (offline-safe):
  uv run python evals/mcp-terminology/run_eval.py --tags error

# CI mode (exits 1 if pass rate < threshold):
  uv run python evals/mcp-terminology/run_eval.py --ci --threshold 0.85

Environment variables:
  TERMINOLOGY_BASE_URL   (default: https://tx.fhir.org/r4)
  LANGFUSE_*             (optional, for tracing)
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
sys.path.insert(0, str(REPO_ROOT / "packages" / "mcp-terminology" / "src"))

from fhir_mcp_shared.eval import EvalResult, EvalRunner, GoldenCase  # noqa: E402
from fhir_mcp_shared.logging import configure_logging  # noqa: E402

configure_logging(level="INFO", fmt="console")
log = structlog.get_logger("eval.terminology")


# ── Tool dispatch ─────────────────────────────────────────────────────────────

async def _invoke(tool: str, input_args: dict[str, Any]) -> dict[str, Any]:
    """Route to the appropriate async tool function."""
    if tool == "lookup_code":
        from mcp_terminology.tools.lookup_code import lookup_code
        return await lookup_code(**input_args)

    if tool == "search_codes":
        from mcp_terminology.tools.search_codes import search_codes
        return await search_codes(**input_args)

    if tool == "translate_code":
        from mcp_terminology.tools.translate_code import translate_code
        return await translate_code(**input_args)

    if tool == "expand_valueset":
        from mcp_terminology.tools.expand_valueset import expand_valueset
        return await expand_valueset(**input_args)

    raise ValueError(f"Unknown tool: {tool!r}")


# ── Programmatic assertions ───────────────────────────────────────────────────

def _programmatic_check(
    case: GoldenCase, result: dict[str, Any]
) -> tuple[bool, str]:
    """Handle special assertion keys in expected:

    - ``display_contains``  : result["display"].lower() contains value
    - ``any_display_contains``: any result["results"][*]["display"] contains value
    - ``first_contains_code``: result["results"][0]["code"] == value
    - ``total_gte``         : result["total"] >= value
    - ``contains_code``     : any result["codes"][*]["code"] == value
    """
    exp = case.expected
    checks: list[tuple[bool, str]] = []

    if "display_contains" in exp:
        needle = exp["display_contains"].lower()
        display = str(result.get("display", "")).lower()
        ok = needle in display
        checks.append((ok, f"display contains {needle!r}: got {display!r}"))

    if "any_display_contains" in exp:
        needle = exp["any_display_contains"].lower()
        items = result.get("results", result.get("codes", []))
        ok = any(needle in str(item.get("display", "")).lower() for item in items)
        checks.append((ok, f"any display contains {needle!r}"))

    if "first_contains_code" in exp:
        items = result.get("results", [])
        first_code = items[0]["code"] if items else None
        ok = first_code == exp["first_contains_code"]
        checks.append((ok, f"first code={first_code!r}, expected {exp['first_contains_code']!r}"))

    if "total_gte" in exp:
        total = result.get("total", result.get("returned", len(result.get("results", result.get("codes", [])))))
        ok = int(total) >= int(exp["total_gte"])
        checks.append((ok, f"total={total} (expected >= {exp['total_gte']})"))

    if "contains_code" in exp:
        codes = [c["code"] for c in result.get("codes", result.get("results", []))]
        ok = exp["contains_code"] in codes
        checks.append((ok, f"{exp['contains_code']!r} in codes: {codes[:8]}"))

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
        "display_contains", "any_display_contains", "first_contains_code",
        "total_gte", "contains_code", "error_contains",
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
                # Expected an error but got a result — fail
                er = EvalResult(
                    case_id=case.id, passed=False, score=0.0,
                    actual=result,
                    notes=f"Expected error containing {case.expected['error_contains']!r} but tool succeeded",
                )
            else:
                # Plain assertions
                plain_ok, plain_score, plain_notes = _subset_check(case.expected, result)

                # Programmatic assertions
                prog_ok, prog_notes = _programmatic_check(case, result)

                passed = plain_ok and prog_ok
                score = plain_score if plain_ok else plain_score * 0.5
                if not prog_ok:
                    score = min(score, 0.5)
                notes = "; ".join(filter(None, [plain_notes if not plain_ok else "", prog_notes]))
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
    print(f"  mcp-terminology eval — {passed}/{total} passed ({rate:.1%})")
    print(f"{'─'*62}")
    for r in results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.case_id:<40}  {(r.notes or '')[:60]}")
    print(f"{'─'*62}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="mcp-terminology golden eval runner")
    parser.add_argument("--tags", nargs="*",
                        help="Filter by tag(s): smoke lookup search translate expand error")
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
