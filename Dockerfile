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

# Pre-download the chromadb ONNX embedding model at build time so it is
# baked into the image. Without this the 79 MB download happens on first
# request and spikes memory enough to OOM-kill the process on small VMs.
RUN .venv/bin/python - <<'EOF'
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
ONNXMiniLM_L6_V2()  # triggers model download into ~/.cache/chroma
EOF

# Non-root user — created after the model download so the cache is owned by root
# and readable by all (chromadb only reads it at runtime).
RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD [".venv/bin/uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
