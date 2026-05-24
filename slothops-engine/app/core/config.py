"""Centralized config / env wiring.

Today configuration is read inline from os.environ scattered across
modules. This is the future home for a typed Settings object. The
stub below mirrors the env vars main.py reads, so callers can begin
importing ``settings`` instead of hitting ``os.environ`` directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _read_github_pem() -> str | None:
    raw = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
    if raw and os.path.isfile(raw):
        with open(raw, "r") as f:
            return f.read()
    if raw:
        return raw.replace("\\n", "\n")
    return None


@dataclass(frozen=True)
class Settings:
    github_app_id: str | None
    github_app_private_key: str | None
    database_path: str
    log_level: str
    github_webhook_secret: str
    base_url: str


def load_settings() -> Settings:
    return Settings(
        github_app_id=os.getenv("GITHUB_APP_ID"),
        github_app_private_key=_read_github_pem(),
        database_path=os.getenv("DATABASE_PATH", "./slothops.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
        base_url=os.getenv("BASE_URL", ""),
    )
