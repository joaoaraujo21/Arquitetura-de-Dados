"""Application settings loaded from environment variables."""
from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings.

    Reads configuration from environment variables / .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ───── App ─────
    app_name: str = "openrouteraula"
    app_env: str = "development"
    app_debug: bool = False
    app_log_level: str = "INFO"

    # ───── Database ─────
    database_url: str = "postgresql://dataeng:dataeng@localhost:5432/dataeng"
    warehouse_url: str = "postgresql://dataeng:dataeng@localhost:5432/warehouse"
    db_max_connections: int = 10
    db_timeout: int = 30

    # ───── Cloud Storage (S3) ─────
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: str = "openrouter-data-lake"

    # ───── API Keys ─────
    openai_api_key: Optional[str] = None

    # ───── Airflow ─────
    airflow_fernet_key: str = ""

    # ───── Data Quality ─────
    quality_fail_on_error: bool = False

    # ───── Logging ─────
    log_json: bool = True
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Return True if running in development environment."""
        return self.app_env.lower() == "development"


def get_settings() -> Settings:
    """Factory function returning a Settings instance."""
    return Settings()


settings = get_settings()