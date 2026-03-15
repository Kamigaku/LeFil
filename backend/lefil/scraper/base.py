from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterator

from structure.models.entry import Entry

logger = logging.getLogger("lefil.scraper.base")


class BaseScraper(ABC):
    """
    Classe abstraite dont héritent tous les scrapers.

    Chaque scraper concret doit implémenter `_fetch()` qui yield des Entry brutes.
    La méthode publique `scrape()` encapsule la gestion d'erreurs et le logging,
    de sorte que le runner n'ait jamais à gérer ça lui-même.

    Exemple d'implémentation :
        class MySourceScraper(BaseScraper):
            SOURCE = "mysource"

            def _fetch(self) -> Iterator[Entry]:
                # ... logique spécifique à la source
                yield Entry(origin=self.SOURCE, ...)
    """

    SOURCE: str  # À définir dans chaque sous-classe (ex: "reddit")

    def __init__(self, config: dict | None = None) -> None:
        """
        Args:
            config: Dictionnaire de configuration propre à chaque scraper
                    (credentials, subreddits cibles, seuils d'engagement, etc.)
        """
        self.config = config or {}

    @abstractmethod
    def _fetch(self) -> Iterator[Entry]:
        """
        Contient la logique de scraping propre à la source.
        Doit yielder des objets Entry valides.
        Ne doit PAS gérer les exceptions — c'est le rôle de scrape().
        """
        ...

    def scrape(self) -> list[Entry]:
        """
        Point d'entrée public appelé par le runner.
        Collecte tous les Entry et isole les erreurs pour ne pas bloquer le pipeline.

        Returns:
            Liste d'Entry valides collectées depuis la source.
        """
        results: list[Entry] = []
        logger.info(f"[{self.SOURCE}] Démarrage du scraping...")

        try:
            for entry in self._fetch():
                results.append(entry)
        except Exception as e:
            # On log l'erreur mais on ne crash pas le runner
            # Les autres scrapers continuent à tourner
            logger.error(f"[{self.SOURCE}] Erreur critique pendant le scraping : {e}", exc_info=True)

        logger.info(f"[{self.SOURCE}] {len(results)} entrées collectées.")
        return results