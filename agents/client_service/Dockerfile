FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --package client_service
EXPOSE 8080
CMD ["uv", "run", "--no-sync", "uvicorn", "client_service.api:app", "--host", "0.0.0.0", "--port", "8080"]
