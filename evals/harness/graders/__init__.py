"""Graders score one transcript against one check, from 0.0 to 1.0.

Prefer the code graders in code.py: they are free, fast and deterministic.
Use llm_judge only for what code cannot check (tone, groundedness).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agent_core import Transcript


@dataclass
class Grade:
    grader: str
    score: float
    explanation: str = ""


GraderFn = Callable[[dict[str, Any], Transcript, Any], Grade]
GRADERS: dict[str, GraderFn] = {}


def grader(name: str) -> Callable[[GraderFn], GraderFn]:
    def register(fn: GraderFn) -> GraderFn:
        GRADERS[name] = fn
        return fn

    return register


def grade(spec: dict[str, Any], transcript: Transcript, case: Any) -> Grade:
    fn = GRADERS.get(spec["type"])
    if fn is None:
        raise KeyError(f"unknown grader type {spec['type']!r} in case {case.id}")
    return fn(spec, transcript, case)


from evals.harness.graders import code, llm_judge  # noqa: E402,F401  (registers graders)
