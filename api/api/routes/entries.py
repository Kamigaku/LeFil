"""
api/routes/entries.py — Feed d'articles avec pagination par curseur.

Pagination par curseur (cursor-based) plutôt qu'offset :
  - L'offset devient instable quand de nouveaux articles arrivent toutes les heures.
    Si 10 articles s'insèrent entre deux pages, l'offset décale et tu vois des doublons.
  - Le curseur utilise published_at + id comme position stable dans le temps.

Endpoints :
    GET /entries        — Feed paginé (infinite scroll)
    GET /entries/{id}   — Détail d'un article
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_user
from structure.models.db import EntryRepository

router = APIRouter()
_entries = EntryRepository()


@router.get("")
def get_feed(
    # Pagination par curseur
    cursor: Optional[str] = Query(None, description="Valeur opaque retournée par la page précédente"),
    limit: int = Query(20, ge=1, le=100),
    # Filtres
    origin: Optional[str]  = Query(None, description="reddit | hackernews | github | rss"),
    only_unread: bool       = Query(False),
    only_saved: bool        = Query(False),
    keyword: Optional[str] = Query(None, description="Filtre articles contenant ce mot-clé"),
    # Auth
    user: dict = Depends(get_current_user),
):
    """
    Retourne une page du feed personnalisé.

    Pagination infinie :
      - Premier appel : pas de cursor → retourne les N articles les plus récents
      - Appels suivants : passe le `next_cursor` reçu pour la page suivante
      - Quand `has_more` est False, il n'y a plus d'articles à charger

    Le cursor encode published_at + id pour une position stable même
    quand de nouveaux articles arrivent entre deux appels.
    """
    # Décode le curseur si présent
    cursor_dt: Optional[datetime] = None
    cursor_id: Optional[UUID]     = None

    if cursor:
        try:
            dt_str, id_str = cursor.split("|")
            cursor_dt = datetime.fromisoformat(dt_str)
            cursor_id = UUID(id_str)
        except (ValueError, AttributeError):
            cursor_dt = None
            cursor_id = None

    items = _entries.get_feed(
        user_id=user["id"],
        limit=limit + 1,        # On demande N+1 pour savoir s'il y a une page suivante
        cursor_dt=cursor_dt,
        cursor_id=cursor_id,
        origin=origin,
        only_unread=only_unread,
        only_saved=only_saved,
        keyword=keyword,
    )

    has_more = len(items) > limit
    page     = items[:limit]

    # Construit le curseur pour la prochaine page
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = f"{last['published_at'].isoformat()}|{last['id']}"

    return {
        "items":       [_serialize(e) for e in page],
        "has_more":    has_more,
        "next_cursor": next_cursor,
        "count":       len(page),
    }


@router.get("/{entry_id}")
def get_entry(entry_id: UUID, user: dict = Depends(get_current_user)):
    """Retourne le détail complet d'un article."""
    entry = _entries.get_by_id(entry_id)
    if not entry:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article introuvable")
    return _serialize(entry)


def _serialize(entry: dict) -> dict:
    """Convertit les types PostgreSQL en types JSON-sérialisables."""
    return {
        **entry,
        "id":           str(entry["id"]),
        "published_at": entry["published_at"].isoformat() if entry.get("published_at") else None,
        "scraped_at":   entry["scraped_at"].isoformat()   if entry.get("scraped_at")   else None,
        "read_at":      entry["read_at"].isoformat()       if entry.get("read_at")      else None,
        "saved_at":     entry["saved_at"].isoformat()      if entry.get("saved_at")     else None,
    }