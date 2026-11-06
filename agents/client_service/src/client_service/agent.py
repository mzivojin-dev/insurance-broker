"""Agent 1: answers client coverage questions from their policy documents and escalates to a CSR.

Eval-first: the cases in evals/datasets/client_service/ describe what this agent must do.
They fail (red) until this module is built in episodes 6 and 7.
"""

from __future__ import annotations

from importlib.resources import files
from typing import Any

from agent_core import Transcript


def system_prompt() -> str:
    return files("client_service").joinpath("prompts/system.md").read_text(encoding="utf-8")


def run(case_input: dict[str, Any]) -> Transcript:
    """Entry point used by the eval harness and the HTTP API."""
    # TODO(episodes 6 and 7): build an agent_core.Agent with system_prompt() and this agent's tools,
    # then return agent.run(...). Until then every eval case for this agent is red.
    return Transcript(error="not implemented yet")
