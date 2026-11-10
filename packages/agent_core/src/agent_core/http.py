"""ASGI helpers shared by the agent HTTP entrypoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

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
