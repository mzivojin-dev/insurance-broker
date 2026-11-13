"""Langfuse tracing for the agent loop.

Configured only from LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY and LANGFUSE_BASE_URL.
Without those keys (unit tests, local runs without .env) every observation is a no-op.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from typing import Any


class _NoOp:
    def update(self, **_: Any) -> None:
        pass


@cache
def _client() -> Any:
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        print("Langfuse keys not set; tracing is disabled.")
        return None
    from langfuse import get_client

    return get_client()


@contextmanager
def observe(name: str, as_type: str = "span", **fields: Any) -> Generator[Any]:
    """Open a Langfuse observation (span, generation, tool, agent...) as the current one.

    `fields` are Langfuse's own (input, output, metadata, model, usage_details, ...).
    Yields an object with `.update(**fields)`.
    """
    client = _client()
    if client is None:
        yield _NoOp()
        return
    with client.start_as_current_observation(name=name, as_type=as_type, **fields) as obs:
        yield obs


def flush() -> None:
    """Send buffered observations now. Call before a short-lived process exits."""
    client = _client()
    if client is not None:
        client.flush()
