"""Application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
SAMPLE_LOGS_DIR = DATA_DIR / "sample_logs"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Haiku: fast & cheap — used for classification, simple tasks
MODEL_FAST = os.getenv("ANTHROPIC_MODEL_FAST", "claude-haiku-4-5-20251001")
# Sonnet: balanced — used for complex analysis, log insights, response drafting
MODEL_STANDARD = os.getenv("ANTHROPIC_MODEL_STANDARD", "claude-sonnet-4-20250514")

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "chroma_data"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
