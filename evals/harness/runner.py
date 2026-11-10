"""Run eval cases against an agent, in process or over HTTP, and write a results file.

    uv run python -m evals.harness.run --agent client_service --tag smoke --out results/cs.json
    uv run python -m evals.harness.run --agent client_service --target http://localhost:8080/client_service

Case failures do not fail this command; `evals.harness.report --gate` decides that.
"""

from __future__ import annotations

import importlib
import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from agent_core import Transcript
from evals.harness.case import Case
from evals.harness.graders import Grade, grade


@dataclass
class RunResult:
    score: float
    grades: list[Grade]
    tokens: int
    latency_ms: float
    error: str | None = None

    def explain(self) -> str:
        bad = [f"{g.grader}={g.score:.2f} ({g.explanation})" for g in self.grades if g.score < 1]
        if self.error:
            bad.insert(0, f"agent error: {self.error}")
        return "; ".join(bad) or "all graders passed"


@dataclass
class CaseResult:
    id: str
    tags: list[str]
    threshold: float
    runs: list[RunResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.runs) and min(r.score for r in self.runs) >= self.threshold

    @property
    def flaky(self) -> bool:
        outcomes = {r.score >= self.threshold for r in self.runs}
        return len(outcomes) > 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tags": self.tags,
            "passed": self.passed,
            "flaky": self.flaky,
            "scores": [r.score for r in self.runs],
            "tokens": sum(r.tokens for r in self.runs) / max(len(self.runs), 1),
            "latency_ms": max((r.latency_ms for r in self.runs), default=0.0),
            "explain": self.runs[-1].explain() if self.runs else "",
            "error": self.runs[-1].error if self.runs else None,
        }


def call_agent(agent: str, case: Case, target: str | None = None) -> Transcript:
    if target:
        req = urllib.request.Request(
            target.rstrip("/") + "/run",
            data=json.dumps(case.agent_input()).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return Transcript.from_dict(json.load(resp))
    module = importlib.import_module(f"{agent}.agent")
    return module.run(case.agent_input())


def run_case(case: Case, target: str | None = None) -> RunResult:
    started = time.perf_counter()
    try:
        t = call_agent(case.agent, case, target)
    except Exception as exc:  # an agent crash is a failed case, not a crashed suite
        t = Transcript(error=f"{type(exc).__name__}: {exc}")
    elapsed = (time.perf_counter() - started) * 1000
    grades = [grade(spec, t, case) for spec in case.graders]
    weights = [float(spec.get("weight", 1.0)) for spec in case.graders]
    score = sum(g.score * w for g, w in zip(grades, weights, strict=True)) / sum(weights)
    if t.error:  # a crashed or unimplemented agent never passes, even "must not" checks
        score = 0.0
    tokens = t.input_tokens + t.output_tokens
    return RunResult(score, grades, tokens, t.latency_ms or elapsed, t.error)


def summarise(results: list[CaseResult]) -> dict[str, Any]:
    n = len(results)
    lat = sorted(r.to_dict()["latency_ms"] for r in results)
    return {
        "total": n,
        "passed": sum(r.passed for r in results),
        "pass_rate": round(sum(r.passed for r in results) / n, 4) if n else 0.0,
        "flaky": [r.id for r in results if r.flaky],
        "mean_tokens": round(sum(r.to_dict()["tokens"] for r in results) / n, 1) if n else 0.0,
        "p95_latency_ms": round(lat[min(n - 1, int(0.95 * n))], 1) if n else 0.0,
    }


def run_suite(cases: list[Case], runs: int = 1, target: str | None = None) -> list[CaseResult]:
    out = []
    for case in cases:
        cr = CaseResult(case.id, case.tags, case.threshold)
        cr.runs = [run_case(case, target) for _ in range(runs)]
        detail = "" if cr.passed else cr.runs[-1].explain()
        print(f"{'PASS' if cr.passed else 'FAIL'}  {case.id}  {detail}")
        out.append(cr)
    return out


def results_doc(agent: str, tag: str, runs: int, results: list[CaseResult]) -> dict[str, Any]:
    return {
        "agent": agent,
        "tag": tag,
        "runs": runs,
        "summary": summarise(results),
        "cases": [r.to_dict() for r in results],
    }


__all__ = ["CaseResult", "RunResult", "results_doc", "run_case", "run_suite"]
