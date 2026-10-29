"""Settings, read from the environment.

Local development needs nothing configured: SQLite in a file and a throwaway
signing key. Production overrides `database_url` with Postgres and `secret_key`
with something real — and refuses to boot if the key is still the default.
"""

from __future__ import annotations


from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]

DEV_SECRET = "dev-only-insecure-key-change-before-deploying"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"

    #: SQLite locally; swap for a Postgres URL in production. The schema uses
    #: only portable types so this switch needs no code change.
    database_url: str = f"sqlite:///{API_ROOT / 'local.db'}"

    secret_key: str = DEV_SECRET
    access_token_hours: int = 24 * 14

    #: Where the browser app runs, for CORS during development.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- AI ---------------------------------------------------------------
    #: First choice when multiple provider keys are configured.
    ai_provider: str = "groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    anthropic_api_key: str | None = None
    #: Used for planning, where getting valid JSON matters most.
    anthropic_model: str = "claude-sonnet-5"
    #: Used for classification inside a running app — high volume, so cheap.
    anthropic_fast_model: str = "claude-haiku-4-5"

    # --- Limits (free tier) ----------------------------------------------
    max_projects_per_user: int = 10
    max_runs_per_month: int = 500
    max_generations_per_day: int = 30

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def resolved_provider(self) -> str:
        """The provider we can actually use, given which keys are present."""
        configured = {
            "groq": bool(self.groq_api_key),
            "gemini": bool(self.gemini_api_key),
            "anthropic": bool(self.anthropic_api_key),
        }
        order = [self.ai_provider, "groq", "gemini", "anthropic"]
        providers = list(dict.fromkeys(name for name in order if configured.get(name)))
        return "+".join(providers) if providers else "echo"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    if settings.is_production and settings.secret_key == DEV_SECRET:
        raise RuntimeError(
            "SECRET_KEY is still the development default. Set a real one before "
            "running in production."
        )

    return settings
