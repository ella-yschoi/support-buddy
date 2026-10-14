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

# Pre-download the chromadb ONNX embedding model as appuser so the cache lands
# in /home/appuser/.cache/chroma — exactly where it will be looked up at runtime.
# Without this the 79 MB download happens on first request and OOM-kills the process.
RUN .venv/bin/python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

COPY start.sh ./start.sh
RUN chmod +x start.sh

CMD ["./start.sh"]
