"""Run one agent turn end to end and send the trace to the configured tracing backend.

    uv run --env-file .env python -m agent_core.demo ["your question"]

Set TRACING_BACKEND=phoenix (local Phoenix on :6006) or langfuse in the env file;
see agent_core.tracing for the other settings.
"""

import json
import sys

from agent_core.loop import Agent
from agent_core.models import REASONING
from agent_core.tools import tool
from agent_core.tracing import flush

# A tiny in-memory book of business so the demo needs no database or MCP server.
POLICIES = {
    "POL-1001": {
        "insured": "Harbor Bakery LLC", "line": "BOP", "premium": 4200, "renews": "2027-01-15",
    },
    "POL-1002": {
        "insured": "Harbor Bakery LLC", "line": "Workers Comp", "premium": 9800,
        "renews": "2027-03-01",
    },
    "POL-2001": {
        "insured": "Ridge Logistics", "line": "Commercial Auto", "premium": 31500,
        "renews": "2026-12-01",
    },
}

DEFAULT_QUESTION = (
    "What does Harbor Bakery pay in total premium, and when is the next renewal?"
)


@tool
def find_policies(insured: str) -> list[str]:
    """List policy numbers for an insured. Matches on a case-insensitive substring of the name."""
    return [num for num, p in POLICIES.items() if insured.lower() in p["insured"].lower()]


@tool
def get_policy(policy_number: str) -> dict:
    """Get line of business, annual premium (USD) and renewal date for one policy number."""
    if policy_number not in POLICIES:
        raise KeyError(f"no policy {policy_number}")
    return POLICIES[policy_number]


agent = Agent(
    system_prompt=(
        "You are an assistant at a commercial insurance brokerage. Answer from the tools only; "
        "if the tools don't have it, say so. Be brief."
    ),
    tools=[find_policies, get_policy],
    model=REASONING,
)


def main() -> None:
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    transcript = agent.run(question)
    flush()  # short-lived process: send the trace before exiting

    print(f"\nQ: {question}\nA: {transcript.output_text or '(no text returned)'}\n")
    for call in transcript.tool_calls:
        print(f"  tool {call.name}({json.dumps(call.args)}) -> {call.result}")
    print(
        f"\n  tokens in/out: {transcript.input_tokens}/{transcript.output_tokens}"
        f"  latency: {transcript.latency_ms:.0f} ms  error: {transcript.error}"
    )


if __name__ == "__main__":
    main()
