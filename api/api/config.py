"""
api/config.py — Configuration centralisée via variables d'environnement.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de données
    database_url: str = Field(..., alias="DATABASE_URL")

    # JWT
    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 jours

    # Google OAuth
    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # CORS — origines autorisées (frontend Next.js)
    cors_origins: list[str] = ["http://localhost:3000"]

    # URL publique du frontend (pour les redirections OAuth)
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()