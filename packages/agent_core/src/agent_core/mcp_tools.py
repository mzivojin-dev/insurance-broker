from typing import Any

from agent_core.tools import tool


def scoped_tools(tools: dict[str, Any], client_id: str, names: list[str]):
    """Wrap AMS tool functions as agent Tools with client_id fixed by the caller."""
    out = []
    for name in names:
        t = tool(tools[name])
        schema = dict(t.input_schema)
        schema["properties"] = {k: v for k, v in schema["properties"].items() if k != "client_id"}
        schema["required"] = [r for r in schema.get("required", []) if r != "client_id"]
        fn = t.fn
        t.input_schema = schema
        t.fn = lambda _fn=fn, **kw: _fn(client_id=client_id, **kw)
        out.append(t)
    return out