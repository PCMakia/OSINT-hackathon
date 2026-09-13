"""Environment configuration loaded from `.env` at import time."""

from __future__ import annotations

import os

from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

_REQUIRED_KEYS = ("DISCORD_TOKEN", "TAVILY_API_KEY", "ANTHROPIC_API_KEY")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return ""
    return value.strip()


_missing = [key for key in _REQUIRED_KEYS if not _require_env(key)]
if _missing:
    raise RuntimeError(
        "Missing required environment variable(s): "
        + ", ".join(_missing)
        + ". Copy .env.example to .env and fill in all API keys."
    )

DISCORD_TOKEN = _require_env("DISCORD_TOKEN")
TAVILY_API_KEY = _require_env("TAVILY_API_KEY")
ANTHROPIC_API_KEY = _require_env("ANTHROPIC_API_KEY")
