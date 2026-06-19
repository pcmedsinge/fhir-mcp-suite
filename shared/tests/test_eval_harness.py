"""Placeholder tests for shared library."""

from fhir_mcp_shared.eval import EvalRunner, GoldenCase


def test_eval_runner_all_pass() -> None:
    cases = [
        GoldenCase(
            id="t1",
            description="basic pass",
            tool="fhir_read",
            input={"resource_type": "Patient", "resource_id": "1"},
            expected={"resourceType": "Patient"},
        )
    ]
    runner = EvalRunner(cases=cases)

    async def invoke(_tool: str, _input: dict) -> dict:  # type: ignore[type-arg]
        return {"resourceType": "Patient", "id": "1"}

    import asyncio

    results = asyncio.run(runner.run(invoke_fn=invoke))
    assert len(results) == 1
    assert results[0].passed
    EvalRunner.assert_threshold(results, min_pass_rate=1.0)


def test_eval_runner_fail_threshold() -> None:
    cases = [
        GoldenCase(
            id="t1",
            description="fail case",
            tool="fhir_read",
            input={},
            expected={"resourceType": "Patient"},
        )
    ]
    runner = EvalRunner(cases=cases)

    async def invoke(_tool: str, _input: dict) -> dict:  # type: ignore[type-arg]
        return {}

    import asyncio

    results = asyncio.run(runner.run(invoke_fn=invoke))
    assert not results[0].passed

    import pytest

    with pytest.raises(AssertionError, match="pass rate"):
        EvalRunner.assert_threshold(results, min_pass_rate=0.85)
