"""
Application configuration loaded from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Central configuration. Values are loaded from .env file or environment variables.

    YOUTUBE_API_KEY: Your YouTube Data API v3 key (required).
    DATABASE_URL: SQLAlchemy database URL. Defaults to local SQLite file.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    youtube_api_key: str
    database_url: str = "sqlite:///./youtube_trend_scout.db"

    # --- Future settings (uncomment as needed) ---
    # vidiq_api_key: str = ""              # For vidIQ warehouse layer
    # snapshot_interval_minutes: int = 60  # How often to capture VPH snapshots
    # default_max_results: int = 50        # Default page size for video fetches


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached Settings instance so the .env file is only read once
    per process lifetime.
    """
    return Settings()
