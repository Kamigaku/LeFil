"""
Couche d'accès aux données (Repository Pattern).

Toutes les interactions PostgreSQL passent par ce fichier.
Le code applicatif (scrapers, API) n'écrit jamais de SQL directement.

Trois repositories :
  • UserRepository   — utilisateurs et mots-clés d'intérêt
  • EntryRepository  — insertion et lecture des articles
  • StatusRepository — statuts par utilisateur (lu, favori, masqué, tags)

Connexion :
    Pool psycopg2, thread-safe pour FastAPI + threads de scraping.

Variable d'environnement :
    DATABASE_URL = postgresql://user:password@host:5432/datascraper
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator
from uuid import UUID

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

from structure.models import Entry

logger = logging.getLogger("lefil.structure.models.db")

psycopg2.extras.register_uuid()


# ─────────────────────────────────────────────────────────────────────────────
# Pool de connexions
# ─────────────────────────────────────────────────────────────────────────────

_pool: SimpleConnectionPool | None = None


def init_pool(database_url: str | None = None, minconn: int = 1, maxconn: int = 10) -> None:
    """
    Initialise le pool de connexions PostgreSQL.
    À appeler une seule fois au démarrage de l'application.

    Args:
        database_url : URL de connexion. Si None, lit DATABASE_URL depuis l'environnement.
        minconn      : Connexions maintenues en permanence.
        maxconn      : Connexions simultanées maximum.
    """
    global _pool
    url = database_url or os.environ["DATABASE_URL"]
    _pool = SimpleConnectionPool(minconn, maxconn, dsn=url)
    logger.info(f"Pool PostgreSQL initialisé (min={minconn}, max={maxconn})")


def close_pool() -> None:
    """Ferme toutes les connexions. À appeler à l'arrêt de l'application."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Pool PostgreSQL fermé.")


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager : emprunte une connexion du pool et la rend automatiquement.
    Commit si tout va bien, rollback en cas d'exception.

    Usage :
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    if _pool is None:
        raise RuntimeError("Pool non initialisé. Appelle init_pool() au démarrage.")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


class UserRepository:
    """
    Gestion des utilisateurs et de leurs mots-clés d'intérêt.

    Les mots de passe sont hashés par PostgreSQL via pgcrypto (bcrypt).
    Ils ne transitent jamais en clair après création.
    """

    # ── Utilisateurs ──────────────────────────────────────────────────────────

    def create_user(self, username: str, password: str) -> dict:
        """
        Crée un utilisateur. Hash le mot de passe via bcrypt (pgcrypto).

        Raises:
            psycopg2.errors.UniqueViolation si le username existe déjà.
        """
        sql = """
            INSERT INTO users (username, password_hash)
            VALUES (%s, crypt(%s, gen_salt('bf')))
            RETURNING id, username, created_at
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (username, password))
                return dict(cur.fetchone())

    def authenticate(self, username: str, password: str) -> dict | None:
        """
        Vérifie les credentials. Retourne l'utilisateur si valide, None sinon.
        La comparaison est faite en base via crypt() pour éviter les timing attacks.
        """
        sql = """
            SELECT id, username, created_at, last_login_at
            FROM users
            WHERE username = %s
              AND password_hash = crypt(%s, password_hash)
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (username, password))
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "UPDATE users SET last_login_at = now() WHERE id = %s",
                        (row["id"],)
                    )
                    return dict(row)
                return None

    def get_by_id(self, user_id: UUID) -> dict | None:
        sql = """
            SELECT id, username, created_at, last_login_at
            FROM users WHERE id = %s
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def get_by_username(self, username: str) -> dict | None:
        sql = """
            SELECT id, username, created_at, last_login_at
            FROM users WHERE username = %s
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (username,))
                row = cur.fetchone()
                return dict(row) if row else None

    # ── Mots-clés utilisateur ─────────────────────────────────────────────────

    def get_keywords(self, user_id: UUID) -> list[str]:
        """Retourne les mots-clés d'intérêt déclarés par l'utilisateur."""
        sql = """
            SELECT keyword FROM user_keywords
            WHERE user_id = %s
            ORDER BY keyword ASC
        """
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                return [row[0] for row in cur.fetchall()]

    def add_keyword(self, user_id: UUID, keyword: str) -> dict:
        """
        Ajoute un mot-clé. Ignore silencieusement si déjà présent (ON CONFLICT DO NOTHING).
        """
        sql = """
            INSERT INTO user_keywords (user_id, keyword)
            VALUES (%s, %s)
            ON CONFLICT (user_id, keyword) DO NOTHING
            RETURNING id, keyword
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id, keyword.lower().strip()))
                row = cur.fetchone()
                return dict(row) if row else {"keyword": keyword.lower().strip()}

    def remove_keyword(self, user_id: UUID, keyword: str) -> bool:
        """Supprime un mot-clé. Retourne True si supprimé, False si introuvable."""
        sql = "DELETE FROM user_keywords WHERE user_id = %s AND keyword = %s"
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, keyword.lower().strip()))
                return cur.rowcount > 0

    def set_keywords(self, user_id: UUID, keywords: list[str]) -> list[str]:
        """
        Remplace entièrement la liste de mots-clés d'un utilisateur.
        Pratique pour la mise à jour depuis le dashboard (liste complète).
        """
        cleaned = [k.lower().strip() for k in keywords if k.strip()]
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_keywords WHERE user_id = %s", (user_id,))
                if cleaned:
                    psycopg2.extras.execute_values(
                        cur,
                        "INSERT INTO user_keywords (user_id, keyword) VALUES %s ON CONFLICT DO NOTHING",
                        [(user_id, kw) for kw in cleaned],
                    )
        return cleaned


class EntryRepository:
    """
    Gestion des articles scrappés.

    Déduplication par URL : INSERT ... ON CONFLICT (link) DO UPDATE
    fusionne les sources JSONB sans créer de doublon.
    """

    def upsert(self, entry: Entry) -> tuple[UUID, bool]:
        """
        Insère un article ou enrichit ses sources s'il existe déjà (même URL).

        Stratégie ON CONFLICT :
          - title, description, keywords, published_at sont conservés depuis l'original
          - sources JSONB est fusionné avec || (merge)
          - scraped_at reste la date de première découverte

        Returns:
            (entry_id, created) — created=True si nouvel article, False si mise à jour
        """
        sql = """
            INSERT INTO entries (origin, link, title, description, keywords, published_at, sources)
            VALUES (%(origin)s, %(link)s, %(title)s, %(description)s,
                    %(keywords)s, %(published_at)s, %(sources)s)
            ON CONFLICT (link) DO UPDATE
                SET sources = entries.sources || EXCLUDED.sources
            RETURNING id, (xmax = 0) AS created
        """
        sources = json.dumps({entry.origin: entry.metadata})

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, {
                    "origin":       entry.origin,
                    "link":         entry.link,
                    "title":        entry.title,
                    "description":  entry.description,
                    "keywords":     entry.keywords,
                    "published_at": entry.published_at,
                    "sources":      sources,
                })
                row = cur.fetchone()
                return row["id"], row["created"]

    def upsert_many(self, entries: list[Entry]) -> dict[str, int]:
        """
        Insère une liste d'articles.

        Returns:
            {"created": N, "updated": N, "total": N}
        """
        created = updated = 0
        for entry in entries:
            _, is_new = self.upsert(entry)
            if is_new:
                created += 1
            else:
                updated += 1

        logger.info(f"[db] upsert_many — {created} créées, {updated} mises à jour")
        return {"created": created, "updated": updated, "total": len(entries)}

    def get_feed(
        self,
        user_id: UUID,
        limit: int = 21,
        cursor_dt: datetime | None = None,
        cursor_id: UUID | None = None,
        origin: str | None = None,
        only_unread: bool = False,
        only_saved: bool = False,
        keyword: str | None = None,
    ) -> list[dict]:
        """
        Retourne le feed personnalisé avec pagination par curseur.

        Pagination par curseur (cursor-based) :
          - Plus stable que l'offset quand des articles arrivent toutes les heures
          - Le curseur encode (published_at, id) pour une position unique et stable
          - Premier appel : cursor_dt=None → articles les plus récents
          - Appels suivants : passe les valeurs du dernier article reçu

        Args:
            cursor_dt   : published_at du dernier article de la page précédente
            cursor_id   : id du dernier article (disambiguïse les published_at égaux)
            origin      : Filtre par source ("reddit", "hackernews", "github")
            only_unread : N'affiche que les articles non lus
            only_saved  : N'affiche que les favoris
            keyword     : Filtre les articles contenant ce mot-clé dans keywords[]
        """
        conditions = ["(ues.is_hidden IS NULL OR ues.is_hidden = false)"]
        params: list = [user_id]

        # Clause de curseur : articles strictement antérieurs au dernier reçu
        if cursor_dt and cursor_id:
            conditions.append(
                "(e.published_at, e.id) < (%s, %s)"
            )
            params += [cursor_dt, cursor_id]

        if origin:
            conditions.append("e.origin = %s")
            params.append(origin)

        if only_unread:
            conditions.append("(ues.is_read IS NULL OR ues.is_read = false)")

        if only_saved:
            conditions.append("ues.is_saved = true")

        if keyword:
            conditions.append("%s = ANY(e.keywords)")
            params.append(keyword.lower().strip())

        where = " AND ".join(conditions)
        params.append(limit)

        sql = f"""
            SELECT
                e.id,
                e.origin,
                e.link,
                e.title,
                e.description,
                e.keywords,
                e.published_at,
                e.sources,
                e.scraped_at,
                COALESCE(ues.is_read,   false)  AS is_read,
                COALESCE(ues.is_saved,  false)  AS is_saved,
                COALESCE(ues.is_hidden, false)  AS is_hidden,
                COALESCE(ues.tags,      '{{}}') AS tags,
                ues.read_at,
                ues.saved_at
            FROM entries e
            LEFT JOIN user_entry_status ues
                ON ues.entry_id = e.id AND ues.user_id = %s
            WHERE {where}
            ORDER BY e.published_at DESC, e.id DESC
            LIMIT %s
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]

    def get_by_id(self, entry_id: UUID) -> dict | None:
        sql = "SELECT * FROM entries WHERE id = %s"
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (entry_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def entry_exist_by_link(self, url: str) -> bool:
        sql = "SELECT * FROM entries WHERE link = %s"
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (url,))
                row = cur.fetchone()
                return True if row else False

    def count(self, origin: str | None = None) -> int:
        """Nombre total d'articles, optionnellement filtré par source."""
        sql = "SELECT COUNT(*) FROM entries"
        params = []
        if origin:
            sql += " WHERE origin = %s"
            params.append(origin)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()[0]


class StatusRepository:
    """
    Gestion des statuts par utilisateur × article.

    Toutes les méthodes sont idempotentes (UPSERT) :
    appeler mark_read deux fois ne cause pas d'erreur.
    """

    def _upsert(self, user_id: UUID, entry_id: UUID, **fields) -> dict:
        """
        Méthode interne générique pour créer ou mettre à jour un statut.
        Ne gère pas les champs avec des valeurs SQL (ex: now()) — voir mark_read.
        """
        cols = list(fields.keys())
        insert_cols = ", ".join(["user_id", "entry_id"] + cols)
        insert_vals = ", ".join(["%s"] * (2 + len(cols)))
        set_clause  = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)

        sql = f"""
            INSERT INTO user_entry_status ({insert_cols})
            VALUES ({insert_vals})
            ON CONFLICT (user_id, entry_id) DO UPDATE
                SET {set_clause}
            RETURNING *
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, [user_id, entry_id] + list(fields.values()))
                return dict(cur.fetchone())

    def mark_read(self, user_id: UUID, entry_id: UUID, read: bool = True) -> dict:
        sql = """
            INSERT INTO user_entry_status (user_id, entry_id, is_read, read_at)
            VALUES (%s, %s, %s, CASE WHEN %s THEN now() ELSE NULL END)
            ON CONFLICT (user_id, entry_id) DO UPDATE
                SET is_read = EXCLUDED.is_read,
                    read_at = EXCLUDED.read_at
            RETURNING *
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id, entry_id, read, read))
                return dict(cur.fetchone())

    def mark_saved(self, user_id: UUID, entry_id: UUID, saved: bool = True) -> dict:
        sql = """
            INSERT INTO user_entry_status (user_id, entry_id, is_saved, saved_at)
            VALUES (%s, %s, %s, CASE WHEN %s THEN now() ELSE NULL END)
            ON CONFLICT (user_id, entry_id) DO UPDATE
                SET is_saved = EXCLUDED.is_saved,
                    saved_at = EXCLUDED.saved_at
            RETURNING *
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id, entry_id, saved, saved))
                return dict(cur.fetchone())

    def mark_hidden(self, user_id: UUID, entry_id: UUID, hidden: bool = True) -> dict:
        return self._upsert(user_id, entry_id, is_hidden=hidden)

    def set_tags(self, user_id: UUID, entry_id: UUID, tags: list[str]) -> dict:
        """Remplace entièrement la liste de tags."""
        cleaned = [t.lower().strip() for t in tags if t.strip()]
        return self._upsert(user_id, entry_id, tags=cleaned)

    def add_tag(self, user_id: UUID, entry_id: UUID, tag: str) -> dict:
        """Ajoute un tag sans écraser les existants."""
        cleaned = tag.lower().strip()
        sql = """
            INSERT INTO user_entry_status (user_id, entry_id, tags)
            VALUES (%s, %s, ARRAY[%s])
            ON CONFLICT (user_id, entry_id) DO UPDATE
                SET tags = CASE
                    WHEN %s = ANY(user_entry_status.tags) THEN user_entry_status.tags
                    ELSE array_append(user_entry_status.tags, %s)
                END
            RETURNING *
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id, entry_id, cleaned, cleaned, cleaned))
                return dict(cur.fetchone())

    def remove_tag(self, user_id: UUID, entry_id: UUID, tag: str) -> dict:
        """Retire un tag de la liste."""
        sql = """
            UPDATE user_entry_status
            SET tags = array_remove(tags, %s::text)
            WHERE user_id = %s AND entry_id = %s
            RETURNING *
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (tag.lower().strip(), user_id, entry_id))
                row = cur.fetchone()
                return dict(row) if row else {}

    def get_status(self, user_id: UUID, entry_id: UUID) -> dict | None:
        """Statut complet d'un article pour un utilisateur donné."""
        sql = """
            SELECT * FROM user_entry_status
            WHERE user_id = %s AND entry_id = %s
        """
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (user_id, entry_id))
                row = cur.fetchone()
                return dict(row) if row else None