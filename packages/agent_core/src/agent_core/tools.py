from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from pydantic import create_model

from agent_core.loop import Tool


def tool(fn: Callable[..., Any]) -> Tool:
    params = {
        name: (p.annotation, ... if p.default is inspect.Parameter.empty else p.default)
        for name, p in inspect.signature(fn).parameters.items()
    }
    model = create_model(f"{fn.__name__}_args", **params)  # type: ignore[call-overload]

    def run(**kwargs: Any) -> Any:
        return fn(**model(**kwargs).model_dump())   # validates the model's arguments

    return Tool(fn.__name__, inspect.getdoc(fn) or "", model.model_json_schema(), run)