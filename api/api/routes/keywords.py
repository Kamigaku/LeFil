"""
api/routes/keywords.py — Gestion des mots-clés favoris de l'utilisateur.

Endpoints :
    GET    /keywords        — Liste des mots-clés de l'utilisateur
    POST   /keywords        — Ajoute un mot-clé
    DELETE /keywords/{kw}   — Supprime un mot-clé
    PUT    /keywords        — Remplace toute la liste d'un coup
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from structure.models.db import UserRepository

from api.dependencies import get_current_user

router = APIRouter()
_users = UserRepository()


class KeywordBody(BaseModel):
    keyword: str

class KeywordsBody(BaseModel):
    keywords: list[str]


@router.get("")
def list_keywords(user: dict = Depends(get_current_user)):
    """Retourne les mots-clés déclarés par l'utilisateur."""
    return {"keywords": _users.get_keywords(user["id"])}


@router.post("", status_code=201)
def add_keyword(body: KeywordBody, user: dict = Depends(get_current_user)):
    """Ajoute un mot-clé à la liste favorite."""
    kw = body.keyword.strip().lower()
    if not kw:
        raise HTTPException(status_code=400, detail="Mot-clé vide")
    result = _users.add_keyword(user["id"], kw)
    return result


@router.delete("/{keyword}")
def remove_keyword(keyword: str, user: dict = Depends(get_current_user)):
    """Supprime un mot-clé de la liste favorite."""
    deleted = _users.remove_keyword(user["id"], keyword.lower())
    if not deleted:
        raise HTTPException(status_code=404, detail="Mot-clé introuvable")
    return {"deleted": keyword.lower()}


@router.put("")
def set_keywords(body: KeywordsBody, user: dict = Depends(get_current_user)):
    """
    Remplace entièrement la liste de mots-clés.
    Pratique pour les mises à jour depuis le panneau de settings du dashboard.
    """
    result = _users.set_keywords(user["id"], body.keywords)
    return {"keywords": result}