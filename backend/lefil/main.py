"""
Point d'entrée principal — exemple de configuration et d'exécution.
Lance tous les scrapers et affiche un résumé des entrées collectées.

Usage :
    python main.py
"""

from __future__ import annotations

import asyncio
import logging
from logging.handlers import RotatingFileHandler

from structure.models.db import init_pool, EntryRepository, close_pool

from config import settings
from scraper.helper import add_logger
from scraper.helper.constants import context, C__DEFAULT_SLEEP_TIME_IN_S
from scraper.operations import GroqSummarizer
from scraper.runner import ScraperRunner
from scraper.scrapers import RedditScraper, HackerNewsScraper, GitHubTrendingsScraper


async def main(debug: bool = False):
    # Configuration des logs
    handler = RotatingFileHandler(filename='lefil.log',
                                  encoding='utf-8',
                                  mode='w',
                                  backupCount=5,
                                  maxBytes=32 * 1024 * 1024)  # 32 MiB
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    handler.setFormatter(logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{'))

    console_handler: logging.StreamHandler | None = None
    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'))

    logger = add_logger("lefil",
                        default_handler=handler,
                        default_console_handler=console_handler,
                        debug=debug)

    # Configuration du Summarizer
    context.summarizer = GroqSummarizer()

    runner = ScraperRunner(max_workers=3)

    # Reddit
    runner.register(
        RedditScraper(
            config={
                "subreddits": {
                    "dataengineering": dict(flairs=["blog", "link"],
                                            min_score=30,
                                            time_filter=60 * 60 * 12),
                    "programming": dict(flairs=[],
                                        min_score=50,
                                        time_filter=60 * 60 * 18),
                    "webdev": dict(flairs=[],
                                        min_score=30,
                                        time_filter=60 * 60 * 18),
                    "datascience": dict(flairs=[],
                                        min_score=30,
                                        time_filter=60 * 60 * 12),
                    "devops": dict(flairs=[],
                                        min_score=50,
                                        time_filter=60 * 60 * 12),
                    "netsec": dict(flairs=[],
                                   min_score=30,
                                   time_filter=60 * 60 * 12),
                    "database": dict(flairs=[],
                                     min_score=20,
                                     time_filter=60 * 60 * 24),
                    "java": dict(flairs=[],
                                     min_score=20,
                                     time_filter=60 * 60 * 24),
                    "python": dict(flairs=[],
                                   min_score=30,
                                   time_filter=60 * 60 * 18),
                    "rust": dict(flairs=[],
                                 min_score=45,
                                 time_filter=60 * 60 * 12),
                    "cpp": dict(flairs=[],
                                min_score=20,
                                time_filter=60 * 60 * 18),
                    "csharp": dict(flairs=[],
                                   min_score=20,
                                   time_filter=60 * 60 * 24),
                    "sql": dict(flairs=[],
                                min_score=20,
                                time_filter=60 * 60 * 24),
                }
            }
        )
    )

    # HackerNews (pas de clé requise)
    runner.register(HackerNewsScraper(config={
        "min_score": 80,
        "limit": 10
    }))

    # GitHub Releases
    runner.register(GitHubTrendingsScraper())

    # runner.register(DevToScraper())

    init_pool(settings.database_url)
    try:
        entries = await runner.run_all()
        EntryRepository().upsert_many(entries=entries)
    except Exception as e:
        logger.error(f"Error during the loop", exc_info=e)
    finally:
        close_pool()


if __name__ == "__main__":
    asyncio.run(main(True))
