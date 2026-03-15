from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, field_validator


class Entry(BaseModel):
    """
    Contrat commun retourné par tous les scrapers.
    Garantit que le pipeline de tri reçoit toujours la même structure,
    quelle que soit la source.

    Attributes:
        origin      : Identifiant de la source (ex: "reddit", "hackernews", "github")
        link        : URL canonique vers le contenu original
        title       : Titre court du contenu (utilisé pour l'embedding)
        description : Texte principal montré à l'utilisateur
        keywords    : Liste des mots clés définissant le contenu
        published_at: Date de publication (UTC) — utilisée pour le score de fraîcheur
        metadata    : Données propres à chaque source (upvotes, subreddit, etc.)
    """

    origin: str
    link: str
    title: str
    description: str
    keywords: list[str]
    published_at: datetime
    metadata: dict[str, str]
    summarize_description: bool = True

    @field_validator("origin")
    @classmethod
    def origin_must_be_known(cls, v: str) -> str:
        allowed = {"reddit", "hackernews", "github", "rss"}
        if v not in allowed:
            raise ValueError(f"Origin '{v}' non reconnue. Valeurs acceptées : {allowed}")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("La description ne peut pas être vide.")
        return v.strip()

    def full_text(self) -> str:
        """
        Concatène titre + description pour l'embedding.
        C'est ce texte qui sera vectorisé par le pipeline de scoring.
        """
        return f"{self.title}. {self.description}"

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
