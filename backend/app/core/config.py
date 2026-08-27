from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://") :]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://") :]

            # asyncpg parameter compatibility: convert sslmode -> ssl, drop unsupported params
            if "sslmode=" in v:
                v = (
                    v.replace("sslmode=require", "ssl=require")
                    .replace("sslmode=prefer", "ssl=prefer")
                    .replace("sslmode=disable", "ssl=disable")
                )
            if "channel_binding=" in v:
                import re

                v = re.sub(r"[&?]channel_binding=[^&]*", "", v)
                if "?" not in v and "&" in v:
                    v = v.replace("&", "?", 1)
        return v
    redis_url: str = "redis://localhost:6379/0"
    cache_backend: str = "memory"  # "memory" | "redis"
    cache_ttl_seconds: int = 60
    jwt_secret: str = "dev-only-change-me-secret-key-2026"  # noqa: S105
    environment: str = "local"
    cors_origins: str = "http://localhost:5173"
    admin_portal_base_url: str = "http://localhost:5173"
    invite_ttl_hours: int = 72
    password_reset_ttl_hours: int = 24
    client_portal_base_url: str = "http://localhost:5173/client"
    uploads_dir: str = "uploads"
    # File storage backend (FEAT-012): "local" | "s3"
    storage_backend: str = "local"
    storage_local_dir: str = "storage"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""  # noqa: S105
    # Max single-upload size in MB (FEAT-012)
    file_max_upload_mb: int = 25

    @property
    def cors_origin_list(self) -> list[str]:
        origins: list[str] = []
        for o in self.cors_origins.split(","):
            clean = o.strip().rstrip("/")
            if clean:
                origins.append(clean)
        return origins

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
