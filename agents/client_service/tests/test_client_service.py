"""Unit tests: no model calls here. Behaviour is specified in evals/datasets/client_service/."""

from agent_core import Transcript
from client_service import agent
from client_service.agent import system_prompt


def test_system_prompt_loads():
    assert system_prompt().strip()


def test_model_cannot_choose_the_client(monkeypatch):
    built = {}

    class FakeAgent:
        def __init__(self, **kw):
            built.update(kw)

        def run(self, message, context=None):
            built["context"] = context
            return Transcript(output_text="ok")

    monkeypatch.setattr(agent, "Agent", FakeAgent)
    agent.run({"client_id": "C-1042", "message": "when is my renewal?"})
    names = {t.name for t in built["tools"]}
    assert names == {"search_policy_docs", "get_client_policies", "get_policy", "get_claim_status",
                     "cite", "escalate_to_csr"}
    assert not any("client_id" in t.input_schema["properties"] for t in built["tools"])
    assert built["context"] == {"client_id": "C-1042"}
