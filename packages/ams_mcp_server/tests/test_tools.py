import pytest
from ams_mcp_server import server as s

def test_policies_are_scoped_to_caller():
    rows = s.get_client_policies(client_id="C-1042")
    assert {r["policy_id"] for r in rows} == {"POL-1042", "POL-1043"}

def test_cannot_read_another_clients_policy():
    with pytest.raises(PermissionError):
        s.get_policy(client_id="C-1042", policy_id="POL-2001")   # POL-2001 belongs to C-2001

def test_write_requires_approval_token():
    with pytest.raises(PermissionError):
        s.create_submission(payload={"named_insured": "X"}, approval_token="forged")

def test_no_bind_or_cancel_tool_exists():
    assert not set(s.TOOLS) & {"bind_policy", "cancel_policy", "update_policy_status"}