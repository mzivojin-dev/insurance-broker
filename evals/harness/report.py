"""Compare a results file with the committed baseline, write a PR comment, and gate.

    uv run python -m evals.harness.report --results results/cs.json \
        --baseline evals/baselines/client_service.json --markdown results/cs.md --gate
    uv run python -m evals.harness.report --results results/cs.json \
        --baseline evals/baselines/client_service.json --update-baseline

Gate rules (exit 1 on any breach):
  1. pass rate below baseline pass rate minus tolerance
  2. a case tagged critical or regression that passed in the baseline now fails
  3. mean tokens or p95 latency more than 20% above baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

GUARDED_TAGS = {"critical", "regression"}
COST_SLACK = 1.20


def compare(results: dict[str, Any], baseline: dict[str, Any]) -> tuple[list[str], list[str]]:
    tag = results["tag"]
    base = baseline.get(tag, {})
    tol = float(baseline.get("tolerance", 0.02))
    s = results["summary"]
    breaches: list[str] = []
    warnings: list[str] = []

    if s["pass_rate"] < base.get("pass_rate", 0.0) - tol:
        breaches.append(
            f"pass rate {s['pass_rate']:.0%} is below baseline {base['pass_rate']:.0%} - {tol:.0%}"
        )

    was_passing = set(base.get("passing_cases", []))
    for c in results["cases"]:
        if c["passed"] or c["id"] not in was_passing:
            continue
        if GUARDED_TAGS & set(c["tags"]):
            breaches.append(f"{c['id']} ({', '.join(c['tags'])}) passed in baseline, now fails")
        else:
            warnings.append(f"{c['id']} passed in baseline, now fails")

    for c in results["cases"]:
        if "critical" in c["tags"] and not c["passed"] and c["id"] not in was_passing:
            warnings.append(f"{c['id']} is critical and not passing yet")

    for key, label in (("mean_tokens", "mean tokens"), ("p95_latency_ms", "p95 latency")):
        ref = base.get(key)
        floor = 500 if key == "p95_latency_ms" else 200  # ignore noise on tiny numbers
        if ref and s[key] > ref * COST_SLACK and s[key] - ref > floor:
            breaches.append(f"{label} {s[key]} is more than 20% above baseline {ref}")

    if s["flaky"]:
        warnings.append("flaky cases: " + ", ".join(s["flaky"]))
    return breaches, warnings


def markdown(results: dict[str, Any], baseline: dict[str, Any], breaches: list[str],
             warnings: list[str]) -> str:
    s, base = results["summary"], baseline.get(results["tag"], {})
    status = "Gate failed" if breaches else "Gate passed"
    lines = [
        f"### Evals: `{results['agent']}` [{results['tag']}] - {status}",
        "",
        "| Metric | This PR | Baseline |",
        "| --- | --- | --- |",
        f"| Pass rate | {s['pass_rate']:.0%} ({s['passed']}/{s['total']}) "
        f"| {base.get('pass_rate', 0):.0%} |",
        f"| Mean tokens per case | {s['mean_tokens']} | {base.get('mean_tokens') or '-'} |",
        f"| p95 latency (ms) | {s['p95_latency_ms']} | {base.get('p95_latency_ms') or '-'} |",
        "",
    ]
    if breaches:
        lines += ["**Breaches**", *[f"- {b}" for b in breaches], ""]
    if warnings:
        lines += ["**Warnings**", *[f"- {w}" for w in warnings], ""]
    failing = [c for c in results["cases"] if not c["passed"]]
    if failing:
        lines += ["<details><summary>Failing cases</summary>", ""]
        lines += [f"- `{c['id']}`: {c['error'] or c['explain']}" for c in failing]
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def update_baseline(results: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    s = results["summary"]
    baseline[results["tag"]] = {
        "pass_rate": s["pass_rate"],
        "passing_cases": sorted(c["id"] for c in results["cases"] if c["passed"]),
        "mean_tokens": s["mean_tokens"] or None,
        "p95_latency_ms": s["p95_latency_ms"] or None,
    }
    return baseline


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--markdown", type=Path)
    p.add_argument("--gate", action="store_true", help="exit 1 on a gate breach")
    p.add_argument("--update-baseline", action="store_true")
    a = p.parse_args()

    results = json.loads(a.results.read_text(encoding="utf-8"))
    baseline = json.loads(a.baseline.read_text(encoding="utf-8")) if a.baseline.exists() else {}

    if a.update_baseline:
        a.baseline.write_text(json.dumps(update_baseline(results, baseline), indent=2) + "\n",
                              encoding="utf-8")
        print(f"baseline updated: {a.baseline}")
        return

    breaches, warnings = compare(results, baseline)
    md = markdown(results, baseline, breaches, warnings)
    print(md)
    if a.markdown:
        a.markdown.parent.mkdir(parents=True, exist_ok=True)
        a.markdown.write_text(md, encoding="utf-8")
    if a.gate and breaches:
        sys.exit(1)


if __name__ == "__main__":
    main()
