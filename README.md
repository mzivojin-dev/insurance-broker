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
infra/                   Terraform: bootstrap (OIDC roles), modules, envs/staging, envs/prod
.github/workflows/       pr.yml (gate), deploy.yml (staging, full evals, prod), nightly-evals.yml
docs/incident-log.md     everything that broke, for episode 14
```

## Getting started

Needs Python 3.12, [uv](https://docs.astral.sh/uv/) and Docker.

```bash
uv sync --all-packages                     # install everything
uv run pytest -q                           # unit tests, no model calls
cp .env.example .env                       # add ANTHROPIC_API_KEY

# local Postgres with pgvector for evals
docker run -d --name ai4all-db -e POSTGRES_USER=ai4all -e POSTGRES_PASSWORD=ai4all -e POSTGRES_DB=ai4all -p 5432:5432 pgvector/pgvector:pg16
uv run python -m data.seed --small

# run the smoke evals for one agent, then gate against the baseline
uv run python -m evals.harness.run --agent client_service --tag smoke
uv run python -m evals.harness.report --results results/client_service.json --baseline evals/baselines/client_service.json --gate

# red/green on one feature
uv run python -m pytest evals --agent client_service --tag escalation -v
```

On PowerShell, set env vars with `$env:DATABASE_URL = "postgresql://ai4all:ai4all@localhost:5432/ai4all"`.
With `make` available, `make eval AGENT=client_service TAG=escalation` and friends wrap these.

## CI/CD setup

1. Push to GitHub and protect `main`: require the `unit` and `eval-gate` checks.
2. Add the `ANTHROPIC_API_KEY` repository secret.
3. Apply `infra/bootstrap` once with admin credentials, then set the repository variables
   `AWS_REGION`, `AWS_PLAN_ROLE_ARN`, `AWS_DEPLOY_ROLE_ARN`, `AWS_PROD_DEPLOY_ROLE_ARN`.
   Deploy jobs skip until `AWS_DEPLOY_ROLE_ARN` is set.
4. Create `staging` and `production` environments; add yourself as required reviewer on production.
