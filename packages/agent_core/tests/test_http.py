"""POST /run is for the eval harness only: it needs X-Eval-Key."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from agent_core.http import require_eval_key

app = FastAPI()


@app.post("/run", dependencies=[Depends(require_eval_key)])
def run() -> dict:
    return {"ok": True}


client = TestClient(app)


@pytest.mark.parametrize("key, status", [("s3cret-key", 200), ("wrong", 401), (None, 401)])
def test_run_needs_the_eval_key(monkeypatch, key, status):
    monkeypatch.setenv("EVAL_KEY", "s3cret-key")
    headers = {"X-Eval-Key": key} if key else {}
    assert client.post("/run", headers=headers).status_code == status


def test_run_is_closed_when_no_key_is_configured(monkeypatch):
    monkeypatch.delenv("EVAL_KEY", raising=False)
    assert client.post("/run", headers={"X-Eval-Key": ""}).status_code == 503
