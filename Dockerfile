# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install all dependencies including chromadb (Linux has onnxruntime wheels)
RUN uv sync --frozen --no-dev --extra knowledge

# Copy source
COPY src/ ./src/
COPY data/ ./data/

# Non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD [".venv/bin/uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
