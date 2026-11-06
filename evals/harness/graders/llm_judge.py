"""LLM-as-judge grader for what code cannot check. Costs money and can drift: use sparingly
and check its verdicts against your own labels (episode 12)."""

from __future__ import annotations

import os
import re
from typing import Any

from agent_core import Transcript
from evals.harness.graders import Grade, grader

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-5-5")

PROMPT = """You are grading an insurance agency assistant's reply.

<question>{question}</question>
<reply>{reply}</reply>
<rubric>{rubric}</rubric>

Think briefly, then end with a line `SCORE: <number between 0 and 1>`."""


@grader("llm_judge")
def llm_judge(spec: dict[str, Any], t: Transcript, case: Any) -> Grade:
    if not t.output_text:
        return Grade("llm_judge", 0.0, "empty reply")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return Grade("llm_judge", 0.0, "ANTHROPIC_API_KEY not set")
    import anthropic

    resp = anthropic.Anthropic().messages.create(
        model=JUDGE_MODEL,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                question=case.input.get("message", case.input),
                reply=t.output_text,
                rubric=spec["rubric"],
            ),
        }],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    m = re.search(r"SCORE:\s*([01](?:\.\d+)?)", text)
    score = float(m.group(1)) if m else 0.0
    return Grade("llm_judge", score, text[-300:] if score < 1 else "")
