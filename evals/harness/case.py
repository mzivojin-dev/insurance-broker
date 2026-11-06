"""Eval cases are YAML lists under evals/datasets/<agent>/. One file per feature."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DATASETS = Path(__file__).resolve().parents[1] / "datasets"
AGENTS = ("client_service", "submission_intake", "book_analyst")
PATH_KEYS = ("file",)  # input keys holding paths relative to the dataset file


@dataclass
class Case:
    id: str
    agent: str
    input: dict[str, Any]
    graders: list[dict[str, Any]]
    tags: list[str] = field(default_factory=list)
    threshold: float = 1.0
    base_dir: Path = DATASETS

    def resolve(self, rel: str) -> Path:
        return (self.base_dir / rel).resolve()

    def agent_input(self) -> dict[str, Any]:
        out = dict(self.input)
        for key in PATH_KEYS:
            if key in out:
                out[key] = str(self.resolve(out[key]))
        return out


def load_cases(
    root: Path = DATASETS, agent: str | None = None, tag: str | None = None
) -> list[Case]:
    cases: list[Case] = []
    seen: set[str] = set()
    for name in AGENTS:
        if agent and name != agent:
            continue
        for path in sorted((root / name).glob("*.yaml")):
            for raw in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
                case = Case(
                    id=raw["id"],
                    agent=name,
                    input=raw.get("input", {}),
                    graders=raw["graders"],
                    tags=raw.get("tags", []),
                    threshold=float(raw.get("threshold", 1.0)),
                    base_dir=path.parent,
                )
                if case.id in seen:
                    raise ValueError(f"duplicate case id {case.id} in {path}")
                seen.add(case.id)
                if tag in (None, "all") or tag in case.tags:
                    cases.append(case)
    return cases
