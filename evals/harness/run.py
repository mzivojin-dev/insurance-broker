"""CLI: python -m evals.harness.run --agent <name> [--tag smoke] [--runs 1] [--target URL]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.harness.case import AGENTS, load_cases
from evals.harness.runner import results_doc, run_suite


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agent", required=True, choices=AGENTS)
    p.add_argument("--tag", default="smoke", help="smoke | full | regression | all | any tag")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--target", help="base URL of a deployed agent; omit to run in process")
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()

    cases = load_cases(agent=a.agent, tag=a.tag)
    if not cases:
        raise SystemExit(f"no cases for agent={a.agent} tag={a.tag}")
    doc = results_doc(a.agent, a.tag, a.runs, run_suite(cases, a.runs, a.target))
    s = doc["summary"]
    print(f"\n{a.agent} [{a.tag}]: {s['passed']}/{s['total']} passed ({s['pass_rate']:.0%})")

    out = a.out or Path("results") / f"{a.agent}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"results written to {out}")


if __name__ == "__main__":
    main()
