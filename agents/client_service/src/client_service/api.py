"""HTTP entrypoint for ECS Fargate. The eval harness calls POST /run with --target."""

from typing import Any

from fastapi import FastAPI

from agent_core.http import StripPrefix
from client_service.agent import run

app = FastAPI(title="client_service")
app.add_middleware(StripPrefix, prefix="client_service")  # the prod ALB keeps the path prefix


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run_endpoint(case_input: dict[str, Any]) -> dict[str, Any]:
    return run(case_input).to_dict()
