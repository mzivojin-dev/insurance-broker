"""Exposes the agency database to all three agents as MCP tools.

TODO (episode 5): write tool-level eval cases first, then implement each tool.
Every tool takes the caller's client_id and must scope its query to it.
"""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("ams")


@mcp.tool()
def get_client_policies(client_id: str) -> list[dict]:
    """List the policies held by one client."""
    raise NotImplementedError("episode 5")


if __name__ == "__main__":
    mcp.run()
