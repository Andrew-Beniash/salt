"""Application settings loaded once at startup via Pydantic Settings.

Every field without a default is *required*.  A missing or invalid value
raises a clear ``ValidationError`` that prevents the process from starting.

Priority (highest → lowest):
  1. Real environment variables (set by Docker / the OS shell)
  2. Values in the .env file (searched in ./ then ../)
  3. Field defaults defined here
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Searched in order; the first file found wins per-key.
        # Works whether uvicorn is run from backend/ or the project root.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_url: str = "http://localhost:8000"
    # min_length=32 ensures the key is long enough for HMAC safety
    secret_key: str = Field(min_length=32)
    cors_origins: str = "http://localhost:3000"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://salt:salt@db:5432/salt"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── Supabase Auth ─────────────────────────────────────────────────────────
    supabase_url: str = Field(min_length=1)
    supabase_anon_key: str = Field(min_length=1)
    supabase_jwt_secret: str = Field(min_length=1)

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = Field(min_length=1)
    openai_model: str = "gpt-4o-mini"

    # ── Azure Document Intelligence ───────────────────────────────────────────
    azure_di_endpoint: str = Field(min_length=1)
    azure_di_key: str = Field(min_length=1)

    # ── OCR confidence thresholds ─────────────────────────────────────────────
    ocr_tier1_confidence_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    ocr_tier2_confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)

    # ── Microsoft / OneDrive ──────────────────────────────────────────────────
    microsoft_client_id: str = Field(min_length=1)
    microsoft_client_secret: str = Field(min_length=1)
    microsoft_tenant_id: str = Field(min_length=1)

    # ── Fernet encryption (MS refresh tokens stored at rest) ──────────────────
    fernet_key: str = Field(min_length=1)

    # ── Storage ───────────────────────────────────────────────────────────────
    storage_backend: Literal["local", "azure_blob"] = "local"
    storage_path: str = "/storage"

    # ── Email ─────────────────────────────────────────────────────────────────
    email_provider: Literal["sendgrid", "smtp"] = "sendgrid"
    sendgrid_api_key: str = Field(min_length=1)
    email_from: str = "noreply@example.com"

    # ── Flower ────────────────────────────────────────────────────────────────
    flower_basic_auth: str = "admin:change-me"

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS (comma-separated) into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Cross-field validation ─────────────────────────────────────────────────
    @field_validator("fernet_key")
    @classmethod
    def _validate_fernet_key(cls, v: str) -> str:
        """Reject keys that are not valid Fernet keys at startup."""
        try:
            from cryptography.fernet import Fernet

            Fernet(v.encode())
        except Exception:
            raise ValueError(
                "FERNET_KEY is not a valid Fernet key. "
                "Generate one with: "
                "python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application-wide Settings singleton (cached after first call).

    Import and call this everywhere settings are needed::

        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()
