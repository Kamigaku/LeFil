"""
api/routes/auth.py — Authentification : email+mot de passe et Google OAuth.

Endpoints :
    POST /auth/register           — Inscription email + mdp
    POST /auth/login              — Connexion → JWT
    GET  /auth/google             — Redirige vers Google
    GET  /auth/google/callback    — Reçoit le code Google → JWT
    GET  /auth/me                 — Profil de l'utilisateur connecté
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import psycopg2

from api.config import settings
from api.dependencies import create_access_token, get_current_user
from fastapi import Depends
from structure.models.db import UserRepository

router = APIRouter()
_users = UserRepository()

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"


# ── Schémas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Email + mot de passe ──────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    """
    Crée un compte avec username + mot de passe.
    Retourne directement un JWT pour connecter l'utilisateur immédiatement.
    """
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe trop court (8 caractères minimum)")

    try:
        user = _users.create_user(body.username.strip(), body.password)
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris")

    token = create_access_token(user["id"], user["username"])
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Connexion email + mot de passe. Retourne un JWT."""
    user = _users.authenticate(body.username.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = create_access_token(user["id"], user["username"])
    return TokenResponse(access_token=token)


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    """
    Redirige le navigateur vers la page de consentement Google.
    Le frontend pointe sur cette URL pour initier l'OAuth.
    """
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth non configuré")

    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  settings.google_redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/google/callback")
def google_callback(code: str):
    """
    Google redirige ici après consentement avec un `code`.
    On l'échange contre un access_token, puis on récupère le profil.
    Crée le compte si c'est la première connexion.
    Redirige vers le frontend avec le JWT en paramètre d'URL.
    """
    # 1. Échange le code contre un token Google
    with httpx.Client() as client:
        token_resp = client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri":  settings.google_redirect_uri,
            "grant_type":    "authorization_code",
        })
        token_resp.raise_for_status()
        google_token = token_resp.json()["access_token"]

        # 2. Récupère le profil Google
        profile_resp = client.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {google_token}"})
        profile_resp.raise_for_status()
        profile = profile_resp.json()

    # Le username = email Google (stable et unique)
    username = profile["email"]

    # 3. Crée le compte si première connexion, sinon récupère l'existant
    try:
        # Mot de passe inutilisable (l'utilisateur se connecte toujours via Google)
        user = _users.create_user(username, f"google_oauth_{profile['sub']}")
    except psycopg2.errors.UniqueViolation:
        # Compte déjà existant → authentification directe par username
        # On utilise authenticate avec un mdp impossible → introuvable
        # On passe par get_by_username à la place
        user = _users.get_by_username(username)
        if not user:
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération du compte")

    token = create_access_token(user["id"], user["username"])

    # 4. Redirige vers le frontend avec le JWT (le frontend le stocke en mémoire/cookie)
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={token}")


# ── Profil ────────────────────────────────────────────────────────────────────

@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    """Retourne le profil de l'utilisateur authentifié."""
    return {
        "id":            str(user["id"]),
        "username":      user["username"],
        "created_at":    user["created_at"],
        "last_login_at": user["last_login_at"],
    }