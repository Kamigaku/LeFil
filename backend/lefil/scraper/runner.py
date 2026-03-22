from __future__ import annotations

import logging
import os
from asyncio import TaskGroup, Task
from concurrent.futures import ThreadPoolExecutor, as_completed

from structure.models.entry import Entry

from scraper.base import BaseScraper
from scraper.helper.constants import context, C__DEFAULT_BLACKLIST_FILE

logger = logging.getLogger("lefil.scraper.runner")


class ScraperRunner:
    """
    Orchestre l'exécution de tous les scrapers enregistrés.

    Les scrapers tournent en parallèle (threads) pour ne pas attendre
    que Reddit finisse avant de lancer GitHub, etc.

    Usage :
        runner = ScraperRunner()
        runner.register(RedditScraper(config={...}))
        runner.register(HackerNewsScraper(config={...}))
        runner.register(GitHubReleasesScraper(config={...}))

        entries = runner.run_all()
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._scrapers: list[BaseScraper] = []
        self._max_workers = max_workers

    def register(self, scraper: BaseScraper) -> "ScraperRunner":
        """Enregistre un scraper. Retourne self pour le chaining."""
        self._scrapers.append(scraper)
        logger.info(f"Scraper enregistré : {scraper.__class__.__name__} (source: {scraper.SOURCE})")
        return self

    async def run_all(self) -> list[Entry]:
        """
        Lance tous les scrapers en parallèle et agrège les résultats.

        Returns:
            Liste de toutes les Entry collectées, toutes sources confondues.
        """
        if not self._scrapers:
            logger.warning("Aucun scraper enregistré.")
            return []

        all_entries: list[Entry] = []

        # TODO: utiliser Asyncio plutôt que des futures
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_scraper = {
                executor.submit(scraper.scrape): scraper
                for scraper in self._scrapers
            }

            for future in as_completed(future_to_scraper):
                scraper = future_to_scraper[future]
                try:
                    entries = future.result()
                    all_entries.extend(entries)
                    logger.info(
                        f"[{scraper.SOURCE}] {len(entries)} entrées récupérées."
                    )
                except Exception as e:
                    logger.error(
                        f"[{scraper.SOURCE}] Échec inattendu du scraper : {e}",
                        exc_info=True,
                    )

        logger.info(f"Run terminé. Total : {len(all_entries)} entrées collectées.")

        # Ici on va venir filter toutes les entries et changer la description
        active_tasks: list[tuple[Entry, Task]] = []
        entries_to_return: list[Entry] = []

        # Read the blacklist files
        with open(C__DEFAULT_BLACKLIST_FILE, "r", encoding="utf-8") as f:
            blacklisted_links = f.read().splitlines()

        async with TaskGroup() as tg:
            for i in range(len(all_entries)):
                if all_entries[i].link in blacklisted_links:
                    continue
                if all_entries[i].summarize_description:
                    active_tasks.append((all_entries[i],
                                         tg.create_task(context.summarizer.summarize(all_entries[i].link))))
                else:
                    entries_to_return.append(all_entries[i])

        for i in range(len(active_tasks)):
            try:
                result = active_tasks[i][1].result()
                if result is None or result[0] == "Not related":
                    logger.info(f"[runner] Adding entry {active_tasks[i][0].link} to the blacklist.")
                    with open(C__DEFAULT_BLACKLIST_FILE, mode="a+", encoding="utf-8") as f:
                        f.write(f"{active_tasks[i][0].link}{os.linesep}")
                    continue
                active_tasks[i][0].description = result[0]
                active_tasks[i][0].keywords = result[1]
                entries_to_return.append(active_tasks[i][0])
            except Exception as e:
                logger.error(f"[runner] Failed during the retrieval of a task", exc_info=e)

        return entries_to_return

    @property
    def registered_sources(self) -> list[str]:
        return [s.SOURCE for s in self._scrapers]