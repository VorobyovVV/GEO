from functools import lru_cache
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "City Places API"
    version: str = "1.0.0"

    db_host: str = Field(default_factory=lambda: os.getenv("DB_HOST", "db"))
    db_port: int = Field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    db_name: str = Field(default_factory=lambda: os.getenv("DB_NAME", "geodb"))
    db_user: str = Field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    db_password: str = Field(default_factory=lambda: os.getenv("DB_PASSWORD", "postgres"))

    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "change-me-in-prod"))
    jwt_algorithm: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    jwt_expires_minutes: int = Field(default_factory=lambda: int(os.getenv("JWT_EXPIRES_MINUTES", "60")))

    cors_origins: str = Field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*"))
    admin_users: str = Field(default_factory=lambda: os.getenv("ADMIN_USERS", ""))

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

