"""What an agent run produced. Eval graders only ever look at a Transcript."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    result: Any = None


@dataclass
class Transcript:
    output_text: str = ""
    output_json: dict[str, Any] | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    sql: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Transcript:
        calls = [ToolCall(**c) for c in d.get("tool_calls", [])]
        return cls(**{**d, "tool_calls": calls})
