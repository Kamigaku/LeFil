"""
api/config.py — Configuration centralisée via variables d'environnement.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de données
    database_url: str = Field(..., alias="DATABASE_URL")

    # GROQ
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()