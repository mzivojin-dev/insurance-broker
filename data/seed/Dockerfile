# One-shot seed job for the local stack (docker-compose.yml). Build context is the repo root.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev
ENTRYPOINT ["uv", "run", "--no-sync", "python", "-m", "data.seed"]
CMD ["--small"]
