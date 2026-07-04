"""Конфигурация приложения. Секреты — только из окружения (§14)."""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ARKAND CRM"
    env: str = "development"

    # БД: Postgres на Railway; SQLite — локальная разработка/тесты (§2).
    database_url: str = "sqlite:///./arkand.db"
    auto_create_tables: bool = True  # dev-удобство; в проде — Alembic

    # Auth (§14): короткий access + refresh; argon2.
    jwt_secret: str = "dev-only-change-in-production-via-env"
    jwt_alg: str = "HS256"
    access_token_expire_min: int = 30
    refresh_token_expire_days: int = 14

    # Realtime (§12): Redis Pub/Sub; без него — in-process fallback.
    redis_url: str | None = None

    # Порог «крупного расхода» — согласование троих (§8.2).
    # TODO: уточнить у заказчика — порог задают владельцы; значение по умолчанию.
    large_expense_threshold: Decimal = Decimal("50000.00")

    # CORS для фронта (Vercel) и локальной разработки.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
