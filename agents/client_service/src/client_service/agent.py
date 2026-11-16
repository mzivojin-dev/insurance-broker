"""Agent 1: answers client coverage questions from their policy documents and escalates to a CSR.

Eval-first: the cases in evals/datasets/client_service/ describe what this agent must do.
They fail (red) until this module is built in episodes 6 and 7.
"""

from __future__ import annotations

from importlib.resources import files
from typing import Any

from agent_core import Transcript
from ams_mcp_server.server import search_policy_docs

def system_prompt() -> str:
    return files("client_service").joinpath("prompts/system.md").read_text(encoding="utf-8")


def run(case_input: dict[str, Any]) -> Transcript:
    """Entry point used by the eval harness and the HTTP API."""
    if case_input.get("mode") == "retrieve_only":
        hits = search_policy_docs(case_input["client_id"], case_input["message"])
        return Transcript(citations=[h["source_doc"] for h in hits],
                          output_text="\n".join(h["source_doc"] for h in hits))
    return Transcript(error="answering lands in episode 7")
