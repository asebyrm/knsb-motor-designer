"""Runtime configuration from environment variables (Section 12, 12.1, 12.2).

Secrets are read from ``os.environ`` only. In a non-dev environment the app refuses
to start if ``SECRET_KEY`` is missing or left at the placeholder - no secret ever
lives in code (Section 12.1).
"""

from __future__ import annotations

import os
import secrets
import sys
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDERS = {"", "changeme", "change-me", "<your-secret-key-here>", "secret"}


@lru_cache
def _ephemeral_dev_key() -> str:
    """One stable random key per process for dev/test when SECRET_KEY is unset."""
    return "dev-" + secrets.token_urlsafe(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="KNSB Motor Designer", alias="APP_NAME")
    # development | production | test
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    # security
    secret_key: str = Field(default="", alias="SECRET_KEY")
    access_token_minutes: int = Field(default=15, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=30, alias="REFRESH_TOKEN_DAYS")
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    cookie_domain: str | None = Field(default=None, alias="COOKIE_DOMAIN")

    # database
    database_url: str = Field(default="sqlite+pysqlite:///./knsb_dev.db", alias="DATABASE_URL")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")

    # concurrency (Section 12.2)
    api_workers: int = Field(default=4, alias="API_WORKERS")
    solver_processes: int = Field(default=2, alias="SOLVER_PROCESSES")
    sim_thread_workers: int = Field(default=4, alias="SIM_THREAD_WORKERS")
    simulation_timeout_s: int = Field(default=20, alias="SIMULATION_TIMEOUT_S")
    mission_timeout_s: int = Field(default=45, alias="MISSION_TIMEOUT_S")

    # rate limits (per IP)
    rate_limit_login_per_min: int = Field(default=5, alias="RATE_LIMIT_LOGIN_PER_MIN")
    rate_limit_sim_per_min: int = Field(default=30, alias="RATE_LIMIT_SIM_PER_MIN")
    rate_limit_mission_per_min: int = Field(default=10, alias="RATE_LIMIT_MISSION_PER_MIN")

    # email verification (optional; disabled when SMTP not configured)
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    email_from: str = Field(default="no-reply@example.com", alias="EMAIL_FROM")

    # misc
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    outputs_dir: str = Field(default="./outputs", alias="OUTPUTS_DIR")
    locales_dir: str | None = Field(default=None, alias="LOCALES_DIR")
    public_base_url: str = Field(default="http://localhost:8000", alias="PUBLIC_BASE_URL")

    @property
    def is_production(self) -> bool:
        return self.environment.lower().startswith("prod")

    @property
    def is_test(self) -> bool:
        return self.environment.lower() == "test"

    @property
    def email_verification_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_secret_key(self) -> str:
        if self.secret_key and self.secret_key not in _PLACEHOLDERS:
            return self.secret_key
        if self.is_production:
            sys.stderr.write(
                "FATAL: SECRET_KEY is not set (or is a placeholder). Refusing to start in "
                "production. Set a strong random SECRET_KEY in the environment.\n"
            )
            raise SystemExit(1)
        return _ephemeral_dev_key()


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.locales_dir:
        os.environ.setdefault("LOCALES_DIR", s.locales_dir)
    return s
