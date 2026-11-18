"""HTTP entrypoint for ECS Fargate. The eval harness calls POST /run with --target."""

from typing import Any

from fastapi import Depends, FastAPI

from agent_core.http import StripPrefix, require_eval_key
from submission_intake.agent import run

app = FastAPI(title="submission_intake")
app.add_middleware(StripPrefix, prefix="submission_intake")  # the prod ALB keeps the path prefix


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", dependencies=[Depends(require_eval_key)])   # harness only
def run_endpoint(case_input: dict[str, Any]) -> dict[str, Any]:
    return run(case_input).to_dict()
