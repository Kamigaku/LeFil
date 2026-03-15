"""
api/routes/status.py — Statuts par utilisateur × article.

Endpoints :
    PATCH /entries/{id}/read    — Marquer lu/non lu
    PATCH /entries/{id}/saved   — Sauvegarder/désauvegarder
    PATCH /entries/{id}/hidden  — Masquer
    POST  /entries/{id}/tags    — Ajouter un tag
    DELETE /entries/{id}/tags/{tag} — Retirer un tag
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from structure.models.db import StatusRepository

from api.dependencies import get_current_user

router = APIRouter()
_status = StatusRepository()


class BoolBody(BaseModel):
    value: bool

class TagBody(BaseModel):
    tag: str


def _serialize(row: dict) -> dict:
    if not row:
        return {}
    return {
        **row,
        "id":         str(row["id"])       if row.get("id")       else None,
        "user_id":    str(row["user_id"])   if row.get("user_id")  else None,
        "entry_id":   str(row["entry_id"])  if row.get("entry_id") else None,
        "read_at":    row["read_at"].isoformat()    if row.get("read_at")    else None,
        "saved_at":   row["saved_at"].isoformat()   if row.get("saved_at")   else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


@router.patch("/{entry_id}/read")
def mark_read(entry_id: UUID, body: BoolBody, user: dict = Depends(get_current_user)):
    result = _status.mark_read(user["id"], entry_id, body.value)
    return _serialize(result)


@router.patch("/{entry_id}/saved")
def mark_saved(entry_id: UUID, body: BoolBody, user: dict = Depends(get_current_user)):
    result = _status.mark_saved(user["id"], entry_id, body.value)
    return _serialize(result)


@router.patch("/{entry_id}/hidden")
def mark_hidden(entry_id: UUID, body: BoolBody, user: dict = Depends(get_current_user)):
    result = _status.mark_hidden(user["id"], entry_id, body.value)
    return _serialize(result)


@router.post("/{entry_id}/tags", status_code=201)
def add_tag(entry_id: UUID, body: TagBody, user: dict = Depends(get_current_user)):
    result = _status.add_tag(user["id"], entry_id, body.tag)
    return _serialize(result)


@router.delete("/{entry_id}/tags/{tag}")
def remove_tag(entry_id: UUID, tag: str, user: dict = Depends(get_current_user)):
    result = _status.remove_tag(user["id"], entry_id, tag)
    return _serialize(result)