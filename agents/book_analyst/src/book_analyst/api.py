"""HTTP entrypoint for ECS Fargate. The eval harness calls POST /run with --target."""

from typing import Any

from fastapi import Depends, FastAPI

from agent_core.http import StripPrefix, require_eval_key
from book_analyst.agent import run

app = FastAPI(title="book_analyst")
app.add_middleware(StripPrefix, prefix="book_analyst")  # the prod ALB keeps the path prefix


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", dependencies=[Depends(require_eval_key)])   # harness only
def run_endpoint(case_input: dict[str, Any]) -> dict[str, Any]:
    return run(case_input).to_dict()
