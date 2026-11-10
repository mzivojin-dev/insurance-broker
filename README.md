# ai4all: insurance broker agents

Three AI agents for an independent insurance broker, built eval-first and deployed to AWS.
Part of the ai4all YouTube series; each episode ends with a repo tag (`ep04-agent-loop`, ...).

| Agent | What it does | Package |
| --- | --- | --- |
| Client service | Answers coverage questions from the client's policy documents, escalates to a CSR | `agents/client_service` |
| Submission intake | Reads ACORD forms and loss runs into submissions queued for CSR review | `agents/submission_intake` |
| Book analyst | Answers book-of-business questions with read-only SQL | `agents/book_analyst` |

## Eval-first

Like TDD, but for agents: write eval cases first (red), make them pass (green), then cut cost
with scores holding (refactor). CI blocks a PR when scores fall below the committed baseline.
Details in [evals/README.md](evals/README.md). Right now every agent is a stub, so every eval
case is red: that is the starting point, not a bug.

## Layout

```text
agents/<agent>/          agent code, prompts/system.md, FastAPI entrypoint, Dockerfile, unit tests
packages/agent_core/     the agent loop and Transcript type shared by all agents
packages/ams_mcp_server/ MCP server over the agency database
packages/guardrails/     PII redaction and other input/output filters
evals/harness/           case loader, graders, runner, report + baseline gate
evals/datasets/<agent>/  YAML eval cases (the spec) and fixtures
evals/baselines/         committed scores the PR gate compares against
data/seed/               synthetic agency data
docker-compose.yml       local stack (db, seed, 3 agents, gateway): the pre-prod environment
infra/                   Terraform: bootstrap (OIDC roles), modules, envs/prod
.github/workflows/       pr.yml (unit, eval gate, terraform plan), deploy.yml (local stack, approve, apply prod); nightly-evals.yml in EP12
docs/incident-log.md     everything that broke, for episode 14
```

## Getting started

Needs Python 3.12, [uv](https://docs.astral.sh/uv/) and Docker.

```bash
uv sync --all-packages                     # install everything
uv run pytest -q                           # unit tests, no model calls
cp .env.example .env                       # add ANTHROPIC_API_KEY

# local Postgres with pgvector, seeded with --small (the full stack below also starts it)
docker compose up -d db seed

# run the smoke evals for one agent, then gate against the baseline
uv run python -m evals.harness.run --agent client_service --tag smoke
uv run python -m evals.harness.report --results results/client_service.json --baseline evals/baselines/client_service.json --gate

# red/green on one feature
uv run python -m pytest evals --agent client_service --tag escalation -v
```

## Local stack (no staging environment)

There is no cloud staging. Pre-prod testing runs the real agent images on Docker, on your
machine and in CI, with the same `/<agent>/...` paths as the prod load balancer:

```bash
docker compose up -d --build                         # db + seed + 3 agents + gateway on :8080
scripts/smoke_check.sh http://localhost:8080         # every agent answers /health
uv run python -m evals.harness.run --agent client_service --target http://localhost:8080/client_service
SEED_ARGS=--large docker compose run --rm seed       # reseed with the large synthetic book
docker compose down                                  # add -v to drop the database volume
```

Ports: `DB_PORT` (default 5432) and `GATEWAY_PORT` (default 8080).

On PowerShell, set env vars with `$env:DATABASE_URL = "postgresql://ai4all:ai4all@localhost:5432/ai4all"`.
With `make` available, `make eval AGENT=client_service TAG=escalation` and friends wrap these.

## CI/CD setup

1. Push to GitHub and protect `main`: require the `unit` and `eval-gate` checks.
2. Add the `ANTHROPIC_API_KEY` repository secret.
3. Apply `infra/bootstrap` once with admin credentials, then set the repository variables
   `AWS_REGION`, `AWS_PLAN_ROLE_ARN`, `AWS_PROD_DEPLOY_ROLE_ARN`.
   The plan job skips until `AWS_PLAN_ROLE_ARN` is set, the deploy job until `AWS_PROD_DEPLOY_ROLE_ARN` is.
   `pr.yml` posts `terraform plan` for `infra/envs/prod` on any `infra/**` change; `deploy.yml`
   builds the images (tag = git sha), pushes them to ECR and runs `terraform apply`.
4. Create a `production` environment and add yourself as required reviewer. There is no staging
   environment: `deploy.yml` brings up `docker compose` on the runner and smoke-checks it (EP13
   adds the full eval suite there), then waits for approval and deploys to prod. Prod is
   ephemeral, so on days you aren't recording, reject the pending approval.

## Prod is ephemeral

Prod runs only while recording or chasing a prod-only issue. At the end of the day:

```bash
scripts/prod_down.sh          # terraform destroy of infra/envs/prod, then lists anything still tagged
```

`var.ephemeral` (default `true`) turns off RDS deletion protection and the final snapshot and
empties S3/ECR on destroy, so the teardown never gets stuck. `infra/bootstrap` (state bucket, OIDC
roles) stays; it costs nothing. Next session: tag a release (or rerun `deploy.yml`) and reseed.
