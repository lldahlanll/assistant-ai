"""
Centralized configuration menggunakan Pydantic Settings.
Semua config dibaca dari .env — tidak ada hardcode di sini.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = Field(..., description="Token dari @BotFather")

    # OpenRouter
    openrouter_api_key: str = Field(..., description="API Key dari openrouter.ai")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    max_history_length: int = 20
    request_timeout: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


# Singleton — import ini di mana saja
settings = Settings()        