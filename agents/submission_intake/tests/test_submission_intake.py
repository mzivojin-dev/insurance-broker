"""Unit tests: no model calls here. Behaviour is specified in evals/datasets/submission_intake/."""

from submission_intake.agent import run, system_prompt


def test_system_prompt_loads():
    assert system_prompt().strip()


def test_run_returns_transcript():
    t = run({})
    assert hasattr(t, "tool_calls")
