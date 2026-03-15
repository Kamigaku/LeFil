"""
api/dependencies.py — JWT helpers et dépendance get_current_user.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from structure.models.db import UserRepository

from api.config import settings

bearer = HTTPBearer()
_user_repo = UserRepository()


def create_access_token(user_id: UUID, username: str) -> str:
    """Génère un JWT signé avec l'ID et le username de l'utilisateur."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """Décode et vérifie un JWT. Lève HTTPException 401 si invalide."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    """
    Dépendance FastAPI : extrait et valide le token Bearer,
    retourne le dict utilisateur depuis la base.

    Usage dans une route :
        @router.get("/me")
        def me(user = Depends(get_current_user)):
            return user
    """
    payload = decode_token(credentials.credentials)
    user_id = UUID(payload["sub"])
    user = _user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    return user