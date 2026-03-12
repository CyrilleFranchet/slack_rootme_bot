from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    slack_bot_token: str
    slack_signing_secret: str
    slack_app_token: str
    rootme_api_key: str
    database_path: Path
    cache_ttl_seconds: int = 300
    rootme_request_delay_ms: int = 500

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            slack_bot_token=_require_env("SLACK_BOT_TOKEN"),
            slack_signing_secret=_require_env("SLACK_SIGNING_SECRET"),
            slack_app_token=_require_env("SLACK_APP_TOKEN"),
            rootme_api_key=_require_env("ROOTME_API_KEY"),
            database_path=Path(os.getenv("DATABASE_PATH", "./data/bot.db")),
            cache_ttl_seconds=_get_int_env("CACHE_TTL_SECONDS", default=300),
            rootme_request_delay_ms=_get_int_env("ROOTME_REQUEST_DELAY_MS", default=500),
        )


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise ValueError(f"Missing required environment variable: {name}")


def _get_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc
