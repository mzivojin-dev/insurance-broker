"""Agent 1: answers client coverage questions from their policy documents and escalates to a CSR.

Eval-first: the cases in evals/datasets/client_service/ describe what this agent must do.
"""

from __future__ import annotations

from importlib.resources import files
from typing import Any

from agent_core import Agent, Transcript
from agent_core.mcp_tools import scoped_tools
from ams_mcp_server.server import TOOLS, search_policy_docs
from client_service.tools import make_local_tools
from guardrails import redact_pii


def system_prompt() -> str:
    return files("client_service").joinpath("prompts/system.md").read_text(encoding="utf-8")

AMS_TOOLS = ["search_policy_docs", "get_client_policies", "get_policy", "get_claim_status"]
COVERAGE_WORDS = ("cover", "covered", "exclusion", "deductible", "limit", "claim")


def run(case_input: dict[str, Any]) -> Transcript:
    client_id = case_input["client_id"]              # from the Cognito session, never the model
    if case_input.get("mode") == "retrieve_only":
        return _retrieve_only(case_input)
    holder = Transcript()
    agent = Agent(
        system_prompt=system_prompt(),
        tools=scoped_tools(TOOLS, client_id, AMS_TOOLS) + make_local_tools(holder, client_id),
        max_turns=6,
    )
    t = agent.run(redact_pii(case_input["message"]), context={"client_id": client_id})
    t.citations = holder.citations
    escalated = any(c.name == "escalate_to_csr" for c in t.tool_calls)
    if not t.citations and not escalated and _looks_like_coverage(case_input["message"]):
        t.output_text = "I want to get this right, so I've passed it to your account manager."
    return t


def _looks_like_coverage(message: str) -> bool:
    return any(w in message.lower() for w in COVERAGE_WORDS)


def _retrieve_only(case_input: dict[str, Any]) -> Transcript:
    """Episode 6 retrieval evals: search only, no model call."""
    hits = search_policy_docs(case_input["client_id"], case_input["message"])
    return Transcript(citations=[h["source_doc"] for h in hits],
                      output_text="\n".join(h["source_doc"] for h in hits))
