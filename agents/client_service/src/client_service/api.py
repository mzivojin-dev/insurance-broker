"""HTTP entrypoint for ECS Fargate. The eval harness calls POST /run with --target."""

from typing import Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from agent_core.http import StripPrefix, require_eval_key
from client_service.agent import run
from client_service.auth import signed_in_client

app = FastAPI(title="client_service")
app.add_middleware(StripPrefix, prefix="client_service")  # the prod ALB keeps the path prefix


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", dependencies=[Depends(require_eval_key)])   # harness only
def run_endpoint(case_input: dict[str, Any]) -> dict[str, Any]:
    return run(case_input).to_dict()

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)   # the body carries only the message


@app.post("/chat")
def chat_endpoint(body: ChatIn, client_id: str = Depends(signed_in_client)) -> dict[str, Any]:
    t = run({"client_id": client_id, "message": body.message})
    return {"output_text": t.output_text, "citations": t.citations, "error": t.error}
