"""Tracing for the agent loop, with a switchable backend.

Pick the backend with TRACING_BACKEND:

    phoenix   local Arize Phoenix. PHOENIX_COLLECTOR_ENDPOINT (default http://localhost:6006),
              PHOENIX_PROJECT_NAME (default insurance-broker), PHOENIX_API_KEY if auth is on.
    langfuse  Langfuse. LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL.
    none      no tracing (the default, so unit tests never send anything).

The loop only uses `observe(name, as_type, **fields)` and `.update(**fields)` with Langfuse-style
fields (input, output, metadata, model, model_parameters, usage_details, level, status_message);
each backend maps those onto its own format.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from typing import Any, Protocol


class Observation(Protocol):
    def update(self, **fields: Any) -> None: ...


class Backend(Protocol):
    def observe(self, name: str, as_type: str, fields: dict[str, Any]) -> Any: ...
    def flush(self) -> None: ...


# --- none ---------------------------------------------------------------------------------


class _NoOp:
    def update(self, **_: Any) -> None:
        pass


class _NoOpBackend:
    @contextmanager
    def observe(self, name: str, as_type: str, fields: dict[str, Any]) -> Generator[_NoOp]:
        yield _NoOp()

    def flush(self) -> None:
        pass


# --- langfuse -----------------------------------------------------------------------------


class _LangfuseBackend:
    def __init__(self) -> None:
        from langfuse import get_client

        self.client = get_client()

    def observe(self, name: str, as_type: str, fields: dict[str, Any]) -> Any:
        return self.client.start_as_current_observation(name=name, as_type=as_type, **fields)

    def flush(self) -> None:
        self.client.flush()


# --- phoenix (OpenTelemetry + OpenInference conventions) ----------------------------------

_SPAN_KIND = {"agent": "AGENT", "generation": "LLM", "tool": "TOOL", "span": "CHAIN"}


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


class _PhoenixObservation:
    def __init__(self, span: Any, name: str, as_type: str) -> None:
        self.span = span
        self.metadata: dict[str, Any] = {}
        span.set_attribute("openinference.span.kind", _SPAN_KIND.get(as_type, "UNKNOWN"))
        if as_type == "tool":
            span.set_attribute("tool.name", name)

    def update(self, **fields: Any) -> None:
        from opentelemetry.trace import Status, StatusCode

        s = self.span
        for key in ("input", "output"):
            if fields.get(key) is not None:
                value = fields[key]
                is_text = isinstance(value, str)
                s.set_attribute(f"{key}.value", value if is_text else _json(value))
                s.set_attribute(f"{key}.mime_type", "text/plain" if is_text else "application/json")
        if fields.get("model"):
            s.set_attribute("llm.model_name", fields["model"])
        if fields.get("model_parameters"):
            s.set_attribute("llm.invocation_parameters", _json(fields["model_parameters"]))
        if usage := fields.get("usage_details"):
            prompt, completion = usage.get("input", 0), usage.get("output", 0)
            s.set_attribute("llm.token_count.prompt", prompt)
            s.set_attribute("llm.token_count.completion", completion)
            s.set_attribute("llm.token_count.total", prompt + completion)
        if fields.get("metadata"):
            self.metadata.update(fields["metadata"])
            s.set_attribute("metadata", _json(self.metadata))
        if fields.get("level") == "ERROR":
            s.set_status(Status(StatusCode.ERROR, fields.get("status_message")))
        elif fields.get("status_message"):
            s.set_attribute("status_message", fields["status_message"])


class _PhoenixBackend:
    def __init__(self) -> None:
        from phoenix.otel import register

        endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
        self.provider = register(
            endpoint=endpoint.rstrip("/") + "/v1/traces",
            project_name=os.environ.get("PHOENIX_PROJECT_NAME", "insurance-broker"),
            protocol="http/protobuf",
            batch=True,
            set_global_tracer_provider=False,
            verbose=False,
        )
        self.tracer = self.provider.get_tracer("agent_core")

    @contextmanager
    def observe(
        self, name: str, as_type: str, fields: dict[str, Any]
    ) -> Generator[_PhoenixObservation]:
        with self.tracer.start_as_current_span(name) as span:
            obs = _PhoenixObservation(span, name, as_type)
            obs.update(**fields)
            yield obs

    def flush(self) -> None:
        self.provider.force_flush()


# --- public API ---------------------------------------------------------------------------

_BACKENDS = {"none": _NoOpBackend, "langfuse": _LangfuseBackend, "phoenix": _PhoenixBackend}


@cache
def backend() -> Backend:
    name = os.environ.get("TRACING_BACKEND", "none").strip().lower()
    if name not in _BACKENDS:
        raise ValueError(f"TRACING_BACKEND={name!r}; expected one of {', '.join(_BACKENDS)}")
    if name == "none":
        print("Tracing is off (set TRACING_BACKEND=phoenix or langfuse to turn it on).")
    return _BACKENDS[name]()


@contextmanager
def observe(name: str, as_type: str = "span", **fields: Any) -> Generator[Observation]:
    """Open an observation (span, generation, tool, agent...) as the current one."""
    with backend().observe(name, as_type, fields) as obs:
        yield obs


def flush() -> None:
    """Send buffered observations now. Call before a short-lived process exits."""
    backend().flush()
