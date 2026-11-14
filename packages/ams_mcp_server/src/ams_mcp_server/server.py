"""Exposes the agency database to all three agents as MCP tools. The rules live here."""

import json

from mcp.server.mcpserver import MCPServer

from ams_mcp_server.db import audit, conn

mcp = MCPServer("ams")
TOOLS: dict = {}   # name -> function, so agents in the same process can call tools directly


def register(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


@register
def get_client_policies(client_id: str) -> list[dict]:
    """List the policies held by one client: id, product, premium, renewal date, status."""
    audit("get_client_policies", client_id, {})
    with conn() as c:
        return c.execute(
            "SELECT policy_id, product, premium, renewal_date, status FROM policies"
            " WHERE client_id = %s ORDER BY policy_id", (client_id,)
        ).fetchall()


@register
def get_policy(client_id: str, policy_id: str) -> dict:
    """One policy with its coverages. Fails if the policy belongs to another client."""
    audit("get_policy", client_id, {"policy_id": policy_id})
    with conn() as c:
        row = c.execute("SELECT * FROM policies WHERE policy_id = %s AND client_id = %s",
                        (policy_id, client_id)).fetchone()
        if row is None:
            raise PermissionError("policy not found for this client")
        row["coverages"] = c.execute("SELECT coverage, limit_amount, deductible FROM coverages"
                                     " WHERE policy_id = %s", (policy_id,)).fetchall()
        return row


@register
def get_claim_status(client_id: str, claim_id: str) -> dict:
    """Status and paid amount of one claim on this client's policies."""
    audit("get_claim_status", client_id, {"claim_id": claim_id})
    with conn() as c:
        row = c.execute(
            "SELECT cl.claim_id, cl.status, cl.paid, cl.date_of_loss FROM claims cl"
            " JOIN policies p USING (policy_id) WHERE cl.claim_id = %s AND p.client_id = %s",
            (claim_id, client_id)).fetchone()
    if row is None:
        raise PermissionError("claim not found for this client")
    return row

@register
def create_submission(payload: dict, approval_token: str) -> dict:
    """Write a CSR-approved submission to the AMS. Needs a token from the review screen."""
    with conn() as c:
        ok = c.execute(
            "UPDATE approvals SET used_at = now() WHERE token = %s AND used_at IS NULL"
            " AND expires_at > now() RETURNING submission_id, approved_by", (approval_token,)
        ).fetchone()
        if ok is None:
            audit("create_submission", "agent", payload, "REFUSED")
            raise PermissionError("missing, used or expired approval token")
        c.execute("INSERT INTO submissions (submission_id, payload) VALUES (%s, %s)",
                  (ok["submission_id"], json.dumps(payload)))
    audit("create_submission", "agent", payload, approval_token)
    return {"submission_id": ok["submission_id"], "approved_by": ok["approved_by"]}

# There is deliberately no bind, cancel, quote or update_policy_status tool.

if __name__ == "__main__":
    mcp.run(transport="streamable-http")   # Fargate service; Claude Desktop and the inspector use this