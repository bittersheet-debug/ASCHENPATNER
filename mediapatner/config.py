"""
Configuration module for MEDIAPATNER BOT.
Reads environment variables securely and provides immutable constants for permanent settings.
"""

from typing import List, Optional
import os
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot API Token (Mandatory, never expose in logs or dashboard)
    bot_token: SecretStr = Field(
        default=SecretStr(
            os.getenv("MEDIAPATNER_BOT_TOKEN")
            or "9068758227:AAEOuuxsLvDznlEvAqjgQ-H8jafPg15XHv4"
        ),
        validation_alias="BOT_TOKEN",
    )

    @field_validator("bot_token", mode="before")
    @classmethod
    def validate_bot_token(cls, v):
        # 1. Prioritize MEDIAPATNER_BOT_TOKEN
        mp_token = os.getenv("MEDIAPATNER_BOT_TOKEN")
        if mp_token and ":" in mp_token:
            return SecretStr(mp_token.strip())

        # 2. Inspect value from validation_alias (only accept if it's the official Media Partner bot token)
        raw = ""
        if isinstance(v, SecretStr):
            raw = v.get_secret_value().strip()
        elif v is not None:
            raw = str(v).strip()

        # Only accept if it starts with 9068 (Media Partner Bot), otherwise use fallback
        if raw and raw.startswith("9068"):
            return SecretStr(raw)

        # 3. Fallback to official Media Partner Bot Token (@PATNERASCHENBOT)
        return SecretStr("9068758227:AAEOuuxsLvDznlEvAqjgQ-H8jafPg15XHv4")

    # Main Broadcast Channel Configuration
    channel_username: str = Field(default="@ASCHENEO", validation_alias="CHANNEL_USERNAME")
    channel_link: str = Field(default="https://t.me/ASCHENEO", validation_alias="CHANNEL_LINK")

    # Permanent Notification Channel ID (-1004479248551)
    # Status: PERMANENT - Cannot be altered via dashboard or config
    notification_channel_id: int = Field(
        default=-1004479248551,
        frozen=True,
    )

    # Timezone: Asia/Jakarta (WIB)
    timezone: str = Field(default="Asia/Jakarta", frozen=True)

    # Admin Password for /admin access
    admin_password: str = Field(default="aschen2026", validation_alias="ADMIN_PASSWORD")

    # Admin IDs (comma-separated list in env: e.g. ADMIN_IDS=12345678,87654321)
    admin_ids: List[int] = Field(default_factory=list, validation_alias="ADMIN_IDS")

    # Database Path
    database_path: str = Field(
        default="/tmp/mediapatner.db" if (os.getenv("VERCEL") or os.getenv("NOW_REGION")) else "data/mediapatner.db",
        validation_alias="DATABASE_PATH"
    )

    # Posting intervals and limits
    post_interval_seconds: int = Field(default=8, validation_alias="POST_INTERVAL_SECONDS")
    retry_max_attempts: int = Field(default=3, validation_alias="RETRY_MAX_ATTEMPTS")
    retry_delay_seconds: int = Field(default=60, validation_alias="RETRY_DELAY_SECONDS")

    # Rate limiting for users (seconds between submissions)
    rate_limit_seconds: int = Field(default=30, validation_alias="RATE_LIMIT_SECONDS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if not v:
            v = os.getenv("ADMIN_IDS") or os.getenv("ADMIN_TELEGRAM_IDS") or ""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        if isinstance(v, (list, tuple, set)):
            return [int(x) for x in v if str(x).isdigit()]
        return []

    def get_token_plain(self) -> str:
        """Returns plain token string safely only for Telegram Bot initialization."""
        return self.bot_token.get_secret_value()

    def is_admin(self, user_id: int) -> bool:
        """Checks if a Telegram user ID is an authorized administrator."""
        # If admin_ids is empty in development, consider allowing, or require at least one admin
        return user_id in self.admin_ids


# Global settings instance getter
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
