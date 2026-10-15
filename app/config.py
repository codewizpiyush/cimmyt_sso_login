"""SSO Application Configuration."""
from functools import lru_cache
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Central SSO & Identity Service"
    sso_host: str = "0.0.0.0"
    sso_port: int = 8005

    # Security
    jwt_secret: str = "sso-secret-key-super-secure-change-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expires_hours: int = 24

    # PostgreSQL Database for SSO
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "sso_db"
    db_user: str = "piyush"
    db_password: str = ""
    db_pool_min: int = 1
    db_pool_max: int = 10

    # Initial Admin Seed
    initial_admin_email: str = "admin@example.org"
    initial_admin_username: str = "admin"
    initial_admin_password: str = "Admin@12345"
    initial_admin_name: str = "Global Administrator"

    # CORS: Allowed origins for e-Agrology, Agrotutor, and local environments
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:8001,http://127.0.0.1:8001,"
        "https://eagrology-revamp.indevconsultancy.in,"
        "https://revamp.agrotutor.co"
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
