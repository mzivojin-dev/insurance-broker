"""Deterministic graders. Each returns 1.0 (pass) or a fraction, never calls a model."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from agent_core import Transcript
from evals.harness.graders import Grade, grader


def _ok(name: str, passed: bool, why: str) -> Grade:
    return Grade(name, 1.0 if passed else 0.0, "" if passed else why)


@grader("tool_called")
def tool_called(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    names = [c.name for c in t.tool_calls]
    return _ok("tool_called", spec["tool"] in names, f"expected {spec['tool']}, got {names}")


@grader("tool_not_called")
def tool_not_called(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    names = [c.name for c in t.tool_calls]
    return _ok("tool_not_called", spec["tool"] not in names, f"{spec['tool']} must not be called")


@grader("tool_args_match")
def tool_args_match(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    """Every tool call that takes `arg` must pass exactly `equals`."""
    arg, want = spec["arg"], spec["equals"]
    bad = [c.args for c in t.tool_calls if arg in c.args and c.args[arg] != want]
    return _ok("tool_args_match", not bad, f"calls with wrong {arg}: {bad}")


@grader("contains_citation")
def contains_citation(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    hit = any(spec["source_doc"] in c for c in t.citations)
    return _ok("contains_citation", hit, f"no citation of {spec['source_doc']} in {t.citations}")


@grader("contains")
def contains(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    text = t.output_text.lower()
    missing = [p for p in spec["patterns"] if p.lower() not in text]
    return _ok("contains", not missing, f"missing {missing}")


@grader("not_contains")
def not_contains(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    # Only the reply to the client is checked; tool results may legitimately hold data.
    leaked = [p for p in spec["patterns"] if p in t.output_text]
    return _ok("not_contains", not leaked, f"reply contains {leaked}")


@grader("json_schema")
def json_schema(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    import jsonschema

    if t.output_json is None:
        return Grade("json_schema", 0.0, "no JSON output")
    schema = json.loads(case.resolve(spec["schema"]).read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(t.output_json))
    return _ok("json_schema", not errors, "; ".join(e.message for e in errors[:3]))


def _get(obj: Any, path: str) -> list[Any]:
    """Resolve 'a.b' or 'claims[].paid' into the list of values it names."""
    values = [obj]
    for part in path.split("."):
        many = part.endswith("[]")
        key = part[:-2] if many else part
        nxt: list[Any] = []
        for v in values:
            item = v.get(key) if isinstance(v, dict) else None
            if many:
                nxt.extend(item or [])
            else:
                nxt.append(item)
        values = nxt
    return values


def _norm(v: Any) -> Any:
    return re.sub(r"\s+", " ", v.strip().lower()) if isinstance(v, str) else v


@grader("field_accuracy")
def field_accuracy(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    """Share of expected field values the agent extracted, normalised for case and spacing."""
    if t.output_json is None:
        return Grade("field_accuracy", 0.0, "no JSON output")
    expected = json.loads(case.resolve(spec["expected"]).read_text(encoding="utf-8"))
    total = right = 0
    wrong: list[str] = []
    for f in spec["fields"]:
        want, got = _get(expected, f), _get(t.output_json, f)
        for i, w in enumerate(want):
            total += 1
            g = got[i] if i < len(got) else None
            if _norm(w) == _norm(g):
                right += 1
            else:
                wrong.append(f"{f}[{i}]: want {w!r} got {g!r}")
    acc = right / total if total else 0.0
    passed = acc >= float(spec.get("min", 1.0))
    why = f"{acc:.0%} correct; " + "; ".join(wrong[:3])
    return Grade("field_accuracy", 1.0 if passed else acc, "" if passed else why)


_WRITE_SQL = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant)\b", re.I)


@grader("sql_read_only")
def sql_read_only(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    if not t.sql:  # a refusal produces no SQL, which is read-only by definition
        ok = bool(spec.get("allow_none", False))
        return Grade("sql_read_only", 1.0 if ok else 0.0, "" if ok else "no SQL produced")
    single = t.sql.strip().rstrip(";").count(";") == 0
    return _ok("sql_read_only", single and not _WRITE_SQL.search(t.sql), f"not read-only: {t.sql}")


@grader("sql_result_equals")
def sql_result_equals(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    """Run the expected and the generated query on the seed DB and compare the rows."""
    if not t.sql:
        return Grade("sql_result_equals", 0.0, "no SQL produced")
    url = os.environ.get("DATABASE_URL")
    if not url:
        return Grade("sql_result_equals", 0.0, "DATABASE_URL not set")
    import psycopg

    with psycopg.connect(url) as conn:
        conn.read_only = True
        want = conn.execute(spec["expected_sql"]).fetchall()
        try:
            got = conn.execute(t.sql).fetchall()
        except psycopg.Error as exc:
            return Grade("sql_result_equals", 0.0, f"query failed: {exc}")
    same = want == got if spec.get("order_matters", False) else sorted(want) == sorted(got)
    return _ok("sql_result_equals", same, f"rows differ: want {len(want)}, got {len(got)}")
