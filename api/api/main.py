"""
api/main.py — Point d'entrée FastAPI.

Lance avec :
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structure.models import init_pool, close_pool

from api.routes import auth, entries, keywords, status
from api.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise et ferme le pool PostgreSQL avec le cycle de vie de l'app."""
    init_pool(database_url=settings.database_url, minconn=2, maxconn=10)
    yield
    close_pool()


app = FastAPI(
    title="LeFil API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(entries.router, prefix="/entries", tags=["entries"])
app.include_router(keywords.router, prefix="/keywords", tags=["keywords"])
app.include_router(status.router,   prefix="/entries",  tags=["status"])


@app.get("/health")
def health():
    return {"status": "ok"}

def start():
    """Launched with `poetry run start` at root level"""
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)