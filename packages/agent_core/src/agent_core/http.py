"""ASGI helpers shared by the agent HTTP entrypoints."""

from __future__ import annotations

import hmac
import os
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Header, HTTPException

Scope = dict[str, Any]
ASGIApp = Callable[[Scope, Any, Any], Awaitable[None]]


class StripPrefix:
    """Serve an app at both /<path> and /<prefix>/<path>.

    The prod load balancer routes /client_service/* to the client_service tasks but, unlike the
    local nginx gateway, cannot strip the prefix. ECS container health checks still hit /health.
    """

    def __init__(self, app: ASGIApp, prefix: str) -> None:
        self.app = app
        self.prefix = "/" + prefix.strip("/")

    async def __call__(self, scope: Scope, receive: Any, send: Any) -> None:
        if scope["type"] in ("http", "websocket"):
            path: str = scope["path"]
            if path == self.prefix or path.startswith(self.prefix + "/"):
                scope = dict(scope, path=path[len(self.prefix) :] or "/")
                scope.pop("raw_path", None)
        await self.app(scope, receive, send)


def require_eval_key(x_eval_key: str = Header(default="")) -> None:
    """FastAPI dependency for POST /run, the eval harness endpoint.

    /run trusts its body completely (client_service takes client_id from it), so only callers
    holding EVAL_KEY may use it. Unset EVAL_KEY refuses everything rather than opening it up.
    Prod generates the key on the first deploy of the day (secret ai4all-prod/eval-key).
    """
    expected = os.environ.get("EVAL_KEY", "")
    if not expected:
        raise HTTPException(503, "EVAL_KEY is not set on this service")
    if not hmac.compare_digest(x_eval_key.encode(), expected.encode()):
        raise HTTPException(401, "missing or wrong X-Eval-Key")
