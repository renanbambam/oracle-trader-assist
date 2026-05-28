"""Centralised application settings loaded from environment variables.

All configuration lives here. Modules import `get_settings()` and read what
they need — nothing reads os.environ directly.
"""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "Oracle Trader Assist"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | production | test
    DEBUG: bool = False

    # ── API ───────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "oracle"
    POSTGRES_PASSWORD: str = ""  # Required — set via .env
    POSTGRES_DB: str = "oracle_db"

    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Claude AI ─────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""  # Required for AI features
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_OPUS_MODEL: str = "claude-opus-4-7"
    CLAUDE_MAX_TOKENS: int = 8096

    # ── Context Window ────────────────────────────────────────────────────────
    MAX_CONTEXT_TOKENS: int = 150_000
    SYSTEM_PROMPT_RESERVE_TOKENS: int = 5_000
    CONTEXT_RESERVE_TOKENS: int = 10_000
    HISTORY_BUDGET_TOKENS: int = 80_000

    # ── External Data APIs ────────────────────────────────────────────────────
    NEWS_API_KEY: str = ""      # newsapi.org — required for news context
    FINNHUB_API_KEY: str = ""   # finnhub.io  — required for calendar context

    # ── Telegram Notifications ────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""  # Bot token from @BotFather — leave blank to disable
    TELEGRAM_CHAT_ID: str = ""    # Target chat or group ID

    # ── Scheduler ─────────────────────────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TIMEZONE: str = "America/Sao_Paulo"
    BRIEFING_ASSETS: list[str] = ["PETR4", "VALE3", "WINFUT", "WDOFUT"]

    # ── MetaTrader5 ───────────────────────────────────────────────────────────
    MT5_LOGIN: int | None = None      # None = use MockMarketAdapter instead
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""

    # ── WebSocket ─────────────────────────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds between ping/pong
    WS_MAX_CONNECTIONS: int = 100

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_SERIALIZE: bool = False  # True in production → JSON output

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the singleton settings instance (cached after first call)."""
    return Settings()
