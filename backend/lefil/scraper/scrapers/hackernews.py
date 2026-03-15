from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Iterator

import httpx
from structure.models.db import EntryRepository
from structure.models.entry import Entry

from scraper.base import BaseScraper

from lefil.scraper.helper import get_dict_value
from scraper.operations import extract

logger = logging.getLogger("lefil.scraper.scrapers.hackernews")

# API HackerNews publique (pas de clé nécessaire)
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class HackerNewsScraper(BaseScraper):
    """
    Scraper HackerNews utilisant l'API publique Firebase (sans authentification).

    HN est une source excellente pour le data engineering :
    - Les posts "Show HN" présentent souvent de nouvelles libs
    - La communauté est très technique et filtre naturellement la qualité

    Configuration attendue (config dict) :
        min_score       : Seuil de points minimum (défaut: 30)
        limit           : Nombre d'items Top Stories à inspecter (défaut: 100)
        max_workers     : Threads parallèles pour fetcher les items (défaut: 10)
        keyword_filter  : Activer le filtre par mots-clés (défaut: True)

    Note : L'API HN ne permet pas de filtrer par date côté serveur.
           On récupère les Top Stories du moment et on applique nos filtres localement.
    """

    SOURCE = "hackernews"

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self._min_score: int = self.config.get("min_score", 30)
        self._limit: int = self.config.get("limit", 100)
        self._max_workers: int = self.config.get("max_workers", 10)
        # Client HTTP avec timeout raisonnable
        self._client = httpx.Client(timeout=10.0)


    def _get_top_story_ids(self) -> list[int]:
        """
        Retrieve the top stories directly from the HN API.
        Format is:
            [ incremental_number (int) : top_story_id (int)
        :return:
        """
        resp = self._client.get(f"{HN_API_BASE}/topstories.json")
        resp.raise_for_status()
        return resp.json()


    def _fetch(self) -> Iterator[Entry]:
        # 1. Récupère la liste des Top Stories (IDs uniquement)
        top_ids = self._get_top_story_ids()
        logger.info(f"[hackernews] {len(top_ids)} top stories à inspecter...")

        # 2. Fetch parallèle des items pour aller vite
        hackernews_items = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_idx = [executor.submit(self._fetch_story_description, story_id)
                             for story_id in top_ids[:self._limit]]
            for future in as_completed(future_to_idx):
                result = future.result()
                if result is None:
                    continue
                hackernews_items.append(result)


        # 3. Filtre et conversion
        for item in hackernews_items:
            if item is None:
                continue
            logger.info(item)
            # On vient récupérer item.url

            if not self._is_relevant(item):
                continue
            entry = self._to_entry(item)
            if entry:
                yield entry

    def _fetch_story_description(self, story_id: int):
        try:
            resp = self._client.get(f"{HN_API_BASE}/item/{story_id}.json")
            resp.raise_for_status()
            # Retrieve the url
            hackernews_item = resp.json()
            story_url_destination: str | None = get_dict_value(hackernews_item, "url", modifier=str)
            if not story_url_destination:
                logger.warning(f"[hackernews] No destination url found for item {story_id}")
                return None
            try:
                if EntryRepository().entry_exist_by_link(story_url_destination):
                    logger.debug(f"[hackernews] {story_url_destination} already exists, skipping.")
                    return None
                # page_title, page_text = extract.fetch_page_text(story_url_destination)
                hackernews_item["description"] = story_url_destination
                return hackernews_item
            except ValueError as ve:
                logger.error(f"[hackernews] Failed to retrieve content for {story_url_destination}.{os.linesep}"
                                   f"Stack trace: {ve}")
                return None
        except Exception as e:
            logger.error(f"[hackernews] Failed to fetch item {story_id}: {e}")
            return None

    def _is_relevant(self, item: dict) -> bool:
        """Filtre rapide avant l'embedding."""
        # On ne garde que les "story" (pas les jobs, polls, etc.)
        if item.get("type") != "story":
            return False
        if item.get("score", 0) < self._min_score:
            return False
        if item.get("dead") or item.get("deleted"):
            return False

        return True
        # if not self._keyword_filter:
        #     return True
        #
        # # Filtre par mots-clés sur le titre
        # title = (item.get("title") or "").lower()
        # return any(kw in title for kw in RELEVANT_KEYWORDS)

    def _to_entry(self, item: dict) -> Entry | None:
        try:
            title = item.get("title", "")
            # URL de l'article original si disponible, sinon thread HN
            url = item.get("url", "")
            if url is None:
                url = f"https://news.ycombinator.com/item?id={item['id']}"

            # Description = title + URL externe pour contextualiser l'embedding

            return Entry(
                origin=self.SOURCE,
                link=url,
                title=title,
                description=item.get("description", ""),
                published_at=datetime.fromtimestamp(item["time"], tz=timezone.utc),
                keywords=[],
                metadata={
                    "hn_id": str(item["id"]),
                    "score": str(item.get("score", 0)),
                    "num_comments": str(item.get("descendants", 0)),
                    "author": item.get("by", ""),
                    "type": item.get("type", "story")
                },
            )
        except Exception as e:
            logger.warning(f"[hackernews] Impossible de convertir item {item.get('id')}: {e}")
            return None

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass