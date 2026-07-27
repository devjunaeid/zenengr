from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"  # noqa: S105
    environment: str = "local"
    cors_origins: str = "http://localhost:5173"
    admin_portal_base_url: str = "http://localhost:5173"
    invite_ttl_hours: int = 72
    password_reset_ttl_hours: int = 24
    client_portal_base_url: str = "http://localhost:5173/client"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
