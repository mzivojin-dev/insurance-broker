"""The agent loop from episode 4: call the model, run the tools it asks for, repeat.

Kept deliberately small. Each agent package builds an Agent with its own prompt and tools.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agent_core.transcript import ToolCall, Transcript

DEFAULT_MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-5-5")


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]

    def spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass
class Agent:
    system_prompt: str
    tools: list[Tool] = field(default_factory=list)
    model: str = DEFAULT_MODEL
    max_turns: int = 8
    max_tokens: int = 1024

    def run(self, user_message: str, context: dict[str, Any] | None = None) -> Transcript:
        import anthropic  # imported lazily so unit tests never need the SDK configured

        client = anthropic.Anthropic()
        tools_by_name = {t.name: t for t in self.tools}
        system = self.system_prompt
        if context:
            system += "\n\n<context>\n" + "\n".join(f"{k}: {v}" for k, v in context.items())
            system += "\n</context>"

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        transcript = Transcript()
        started = time.perf_counter()

        for _ in range(self.max_turns):
            resp = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=[t.spec() for t in self.tools],  # type: ignore[misc]
                messages=messages,  # type: ignore[arg-type]
            )
            transcript.input_tokens += resp.usage.input_tokens
            transcript.output_tokens += resp.usage.output_tokens
            messages.append({"role": "assistant", "content": resp.content})

            tool_results = []
            for block in resp.content:
                if block.type == "text":
                    transcript.output_text += block.text
                elif block.type == "tool_use":
                    tool = tools_by_name.get(block.name)
                    try:
                        result = tool.fn(**block.input) if tool else f"unknown tool {block.name}"
                    except Exception as exc:  # surface tool errors to the model
                        result = f"error: {exc}"
                    transcript.tool_calls.append(ToolCall(block.name, dict(block.input), result))
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}
                    )

            if resp.stop_reason != "tool_use":
                break
            messages.append({"role": "user", "content": tool_results})

        transcript.latency_ms = (time.perf_counter() - started) * 1000
        return transcript
