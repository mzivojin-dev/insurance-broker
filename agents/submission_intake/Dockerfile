FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv
WORKDIR /app
COPY . .
RUN uv sync --frozen --no-dev --package submission_intake
EXPOSE 8080
CMD ["uv", "run", "--no-sync", "uvicorn", "submission_intake.api:app", "--host", "0.0.0.0", "--port", "8080"]
