from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    redis_url: str = "redis://localhost:6379/0"
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
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
