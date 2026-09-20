"""Application configuration settings."""

from pathlib import Path
from typing import Optional

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL

# Root of YogyataMitra workspace
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Core settings loaded from environment or .env file."""

    PROJECT_NAME: str = "YogyataMitra"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # JWT Settings for Officer Portal (Phase 14)
    # INSECURE_DEV_FALLBACK_KEY is only used in development/demo/test when SECRET_KEY is not set.
    # In production, SECRET_KEY MUST be explicitly provided and cannot use dev fallback.
    SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Flag for demo accounts: strictly forbidden and forced False in production
    ENABLE_DEMO_ACCOUNTS: bool = True

    # AI Policy Discovery Settings (Phase 15)
    AI_PROVIDER: str = "mock"  # "mock" or "gemini"
    AI_DISCOVERY_PROVIDER: str = "mock"  # "mock" or "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Allowed CORS origins for local development frontend
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # PostgreSQL connection parameters
    POSTGRES_USER: str = "yogyata_admin"
    POSTGRES_PASSWORD: str = "yogyata_secure_dev_pass"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "yogyatamitra_db"

    # Optional direct database URL override
    DATABASE_URL_OVERRIDE: Optional[str] = None

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct the asyncpg connection string."""
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    @model_validator(mode="after")
    def validate_environment_and_secrets(self) -> "Settings":
        env = (self.ENVIRONMENT or "development").lower().strip()
        if env == "production":
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                raise ValueError(
                    "SECRET_KEY must be explicitly configured in production environment."
                )
            if self.SECRET_KEY.startswith("dev-") or "insecure" in self.SECRET_KEY.lower():
                raise ValueError(
                    "Insecure development SECRET_KEY cannot be used in production environment."
                )
            if self.ENABLE_DEMO_ACCOUNTS:
                raise ValueError(
                    "ENABLE_DEMO_ACCOUNTS cannot be enabled in production environment."
                )
        else:
            # Non-production (development, demo, test): provide clearly marked insecure fallback
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                self.SECRET_KEY = (
                    "insecure-dev-secret-key-yogyatamitra-phase14-jwt-signing-2026-non-production-only"
                )
        return self

    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
