"""
Configuration — загружается из .env через pydantic-settings
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Discord ──────────────────────────────────────────────────
    discord_token: str
    discord_guild_id: int

    discord_monitored_channels: str = ""      # raw CSV
    discord_monitored_categories: str = ""    # raw CSV
    discord_tickets_channel_id: int = 0
    discord_watched_role_ids: str = ""        # raw CSV

    # parsed lists (populated in validator)
    monitored_channel_ids: List[int] = []
    monitored_category_ids: List[int] = []
    watched_role_ids: List[int] = []

    # ── Telegram ─────────────────────────────────────────────────
    telegram_bot_token: str
    telegram_notifications_chat_id: int
    telegram_pings_chat_id: int
    telegram_tickets_chat_id: int
    telegram_owner_id: int

    # ── PostgreSQL ───────────────────────────────────────────────
    postgres_user: str = "bridge_user"
    postgres_password: str = "password"
    postgres_db: str = "bridge_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # ── Redis ────────────────────────────────────────────────────
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # ── App ──────────────────────────────────────────────────────
    log_level: str = "INFO"
    environment: str = "production"

    # ─────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def parse_csv_fields(self) -> "Settings":
        def _parse(raw: str) -> List[int]:
            return [int(x.strip()) for x in raw.split(",") if x.strip()]

        self.monitored_channel_ids = _parse(self.discord_monitored_channels)
        self.monitored_category_ids = _parse(self.discord_monitored_categories)
        self.watched_role_ids = _parse(self.discord_watched_role_ids)
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()