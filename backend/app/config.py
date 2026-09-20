from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal['development', 'test', 'staging', 'production']


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    app_name: str = Field(default='the-textile-care-api')
    app_env: Environment = Field(default='development')
    app_port: int = Field(default=8000)
    app_base_url: str = Field(default='http://localhost:8000')
    api_base_url: str = Field(default='http://localhost:8000')
    database_url: str = Field(
        default='postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres'
    )
    redis_url: str = Field(default='redis://localhost:6379/0')
    auth_secret: str = Field(default='change-me')
    cors_allowed_origins: str = Field(default='http://localhost:3000,http://localhost:3001')
    sentry_dsn: str | None = None
    otel_exporter_otlp_endpoint: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
