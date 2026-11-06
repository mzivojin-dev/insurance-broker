"""HTTP entrypoint for ECS Fargate. The eval harness calls POST /run with --target."""

from typing import Any

from fastapi import FastAPI

from book_analyst.agent import run

app = FastAPI(title="book_analyst")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run_endpoint(case_input: dict[str, Any]) -> dict[str, Any]:
    return run(case_input).to_dict()
