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
# When set, all API requests (except /health) must supply: Authorization: Bearer <key>.
# Never ship this value to a browser: it must not appear in any VITE_* variable.
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
# "production" refuses to serve data without API_SECRET_KEY; anything else leaves a missing
# secret meaning "open", which is only for local development.
APP_ENV = os.getenv("APP_ENV", "development")
# Calls per UTC day to endpoints that spend Anthropic money. 0 turns them off.
AI_DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "100"))
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "")

# Haiku: fast & cheap - used for classification, simple tasks
MODEL_FAST = os.getenv("ANTHROPIC_MODEL_FAST", "claude-haiku-4-5-20251001")
# Sonnet: balanced - used for complex analysis, log insights, response drafting
MODEL_STANDARD = os.getenv("ANTHROPIC_MODEL_STANDARD", "claude-sonnet-4-5")

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "chroma_data"))

BRIEFING_DB_PATH = Path(
    os.getenv("BRIEFING_DB_PATH", str(PROJECT_ROOT / "briefing_data" / "briefings.db"))
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
