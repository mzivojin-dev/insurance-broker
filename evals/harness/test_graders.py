"""Unit tests for the graders themselves: a wrong grader makes every eval lie."""

from pathlib import Path

from agent_core import ToolCall, Transcript
from evals.harness.case import Case, load_cases
from evals.harness.graders import grade
from evals.harness.report import compare


def _case(**kw) -> Case:
    return Case(id="t", agent="client_service", input={}, graders=[], base_dir=Path("."), **kw)


def test_tool_graders():
    t = Transcript(tool_calls=[ToolCall("escalate_to_csr", {"client_id": "C-1"})])
    assert grade({"type": "tool_called", "tool": "escalate_to_csr"}, t, _case()).score == 1
    assert grade({"type": "tool_not_called", "tool": "escalate_to_csr"}, t, _case()).score == 0
    spec = {"type": "tool_args_match", "arg": "client_id", "equals": "C-2"}
    assert grade(spec, t, _case()).score == 0


def test_sql_read_only():
    spec = {"type": "sql_read_only"}
    assert grade(spec, Transcript(sql="SELECT 1"), _case()).score == 1
    assert grade(spec, Transcript(sql="SELECT 1; DELETE FROM policies"), _case()).score == 0
    assert grade(spec, Transcript(sql="UPDATE policies SET premium = 0"), _case()).score == 0
    assert grade({**spec, "allow_none": True}, Transcript(), _case()).score == 1


def test_field_accuracy(tmp_path):
    (tmp_path / "e.json").write_text('{"claims": [{"paid": 1}, {"paid": 2}]}')
    case = Case(id="t", agent="x", input={}, graders=[], base_dir=tmp_path)
    spec = {"type": "field_accuracy", "expected": "e.json", "fields": ["claims[].paid"], "min": 1}
    half = Transcript(output_json={"claims": [{"paid": 1}, {"paid": 9}]})
    assert grade(spec, half, case).score == 0.5


def test_all_datasets_load():
    cases = load_cases(tag="all")
    assert {c.agent for c in cases} == {"client_service", "submission_intake", "book_analyst"}


def test_gate_flags_regressed_critical_case():
    results = {
        "tag": "smoke",
        "summary": {"pass_rate": 0.5, "flaky": [], "mean_tokens": 0, "p95_latency_ms": 0},
        "cases": [{"id": "a", "tags": ["critical"], "passed": False}],
    }
    baseline = {"smoke": {"pass_rate": 0.5, "passing_cases": ["a"]}}
    breaches, _ = compare(results, baseline)
    assert any("a (critical)" in b for b in breaches)
