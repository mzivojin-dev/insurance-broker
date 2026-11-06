"""Unit tests: no model calls here. Behaviour is specified in evals/datasets/client_service/."""

from client_service.agent import run, system_prompt


def test_system_prompt_loads():
    assert system_prompt().strip()


def test_run_returns_transcript():
    t = run({})
    assert hasattr(t, "tool_calls")
