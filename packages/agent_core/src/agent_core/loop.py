"""The agent loop from episode 4: call the model, run the tools it asks for, repeat.

Kept deliberately small. Each agent package builds an Agent with its own prompt and tools.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agent_core.tracing import observe
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
    token_budget: int = 40_000          # whole run, input + output
    timeout_s: float = 60.0
    client: Any = None                  # tests pass a fake

    def run(self, user_message: str, context: dict[str, Any] | None = None) -> Transcript:
        client = self.client or _default_client(self.timeout_s)
        tools_by_name = {t.name: t for t in self.tools}
        system = self.system_prompt
        if context:
            system += "\n\n<context>\n" + "\n".join(f"{k}: {v}" for k, v in context.items())
            system += "\n</context>"

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        transcript = Transcript()
        started = time.perf_counter()

        with observe("agent", as_type="agent", input=user_message,
                     metadata={"model": self.model, "context": context}) as root:
            for turn in range(self.max_turns):
                with observe(f"llm.turn{turn + 1}", as_type="generation", model=self.model,
                             input=[{"role": "system", "content": system}, *messages],
                             model_parameters={"max_tokens": self.max_tokens}) as gen:
                    resp = client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        system=system,
                        tools=[t.spec() for t in self.tools],  # type: ignore[misc]
                        messages=messages,  # type: ignore[arg-type]
                    )
                    gen.update(
                        output=[_block_dict(b) for b in resp.content],
                        usage_details={"input": resp.usage.input_tokens,
                                       "output": resp.usage.output_tokens},
                        metadata={"stop_reason": str(resp.stop_reason)},
                    )

                # Count every response, including the final one, before deciding anything.
                transcript.input_tokens += resp.usage.input_tokens
                transcript.output_tokens += resp.usage.output_tokens
                transcript.output_text += "".join(b.text for b in resp.content if b.type == "text")

                if resp.stop_reason != "tool_use":
                    break                               # final answer: done
                if transcript.input_tokens + transcript.output_tokens > self.token_budget:
                    transcript.error = "token_budget"
                    break

                messages.append({"role": "assistant", "content": resp.content})
                tool_results = [self._call_tool(b, tools_by_name, transcript)
                                for b in resp.content if b.type == "tool_use"]
                messages.append({"role": "user", "content": tool_results})
            else:
                transcript.error = "max_turns"          # every turn asked for more tools

            transcript.latency_ms = (time.perf_counter() - started) * 1000
            root.update(
                output=transcript.output_text,
                level="WARNING" if transcript.error else "DEFAULT",
                status_message=transcript.error,
                metadata={"input_tokens": transcript.input_tokens,
                          "output_tokens": transcript.output_tokens,
                          "tool_calls": len(transcript.tool_calls)},
            )
        return transcript

    @staticmethod
    def _call_tool(
        block: Any, tools_by_name: dict[str, Tool], transcript: Transcript
    ) -> dict[str, Any]:
        with observe(block.name, as_type="tool", input=dict(block.input)) as obs:
            tool = tools_by_name.get(block.name)
            try:
                result = tool.fn(**block.input) if tool else f"unknown tool {block.name}"
                obs.update(output=result)
            except Exception as exc:  # surface tool errors to the model
                result = f"error: {exc}"
                obs.update(output=result, level="ERROR", status_message=str(exc))
        transcript.tool_calls.append(ToolCall(block.name, dict(block.input), result))
        return {"type": "tool_result", "tool_use_id": block.id, "content": str(result)}


def _block_dict(block: Any) -> dict[str, Any]:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "name": block.name, "input": dict(block.input)}
    return {"type": str(block.type)}


def _default_client(timeout_s: float):
    import anthropic

    if os.environ.get("USE_BEDROCK") == "1":
        return anthropic.AnthropicBedrock(timeout=timeout_s)
    return anthropic.Anthropic(timeout=timeout_s, max_retries=2)