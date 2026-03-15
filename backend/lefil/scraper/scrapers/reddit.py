from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Iterator, Any

import httpx
from structure.models.entry import Entry

from scraper.base import BaseScraper
from scraper.helper import get_dict_value
from scraper.operations import extract

logger = logging.getLogger("lefil.scrapper.reddit")

RD_BASE_URL = "https://old.reddit.com/r/"

# Subreddits pertinents pour le data engineering non-cloud
DEFAULT_SUBREDDITS = {}

# Seuil minimum d'upvotes pour filtrer le bruit
DEFAULT_MIN_SCORE = 20


class RedditScraper(BaseScraper):
    """
    Scraper Reddit utilisant l'API officielle via PRAW.

    Configuration attendue (config dict) :
        subreddits    : Liste de subreddits à scraper et des informations complémentaires

    Exemple de config :
        {
            "subreddits": {
                "dataengineering": {
                    "flairs": ["discussion", "link"],
                    "min_score": 30,
                    "time_filter": 60
                },
                "databasedevelopment": {
                    "flairs": ["discussion", "link"],
                    "min_score": 30,
                    "time_filter": 60
                }
            }
        }
    """

    SOURCE = "reddit"

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self._client = httpx.Client(timeout=10.0)
        self._subreddits_and_infos: dict[str, dict[str, Any]] = self.config.get("subreddits", DEFAULT_SUBREDDITS)
        self._xml_namespaces: dict[str, str] = dict(atom="http://www.w3.org/2005/Atom")
        # utiliser le flux RSS en faisait {subreddit_name}.rss => récupère un fichier XML à parser

    def _fetch(self) -> Iterator[Entry]:
        for subreddit_name in self._subreddits_and_infos.keys():
            logger.info(f"[reddit] Scraping r/{subreddit_name}...")
            try:
                resp = self._client.get(f"{RD_BASE_URL}{subreddit_name}.json")
                resp.raise_for_status()
                # Retrieve a XML file containing information
                all_entries = get_dict_value(resp.json(), "data/children", modifier=list, default=[])
                for entry in all_entries:
                    data = get_dict_value(entry, "data", default=None)
                    if data is None:
                        continue

                    # Creation date
                    created_utc = get_dict_value(data, "created_utc", modifier=lambda d: datetime.fromtimestamp(d, tz=timezone.utc))
                    if created_utc is None:
                        continue
                    if created_utc < datetime.now(timezone.utc) - timedelta(minutes=self._subreddits_and_infos[subreddit_name]["time_filter"]):
                        continue

                    # Retrieve score
                    post_score = get_dict_value(data, "score", default=0)
                    if post_score < self._subreddits_and_infos[subreddit_name]["min_score"]:
                        continue


                    # On ignore les posts épinglés (annonces de mods, etc.)
                    post_stickied = get_dict_value(data, "stickied", default=False)
                    if post_stickied:
                        continue

                    # On ignore les posts possédant un flair qui ne nous intéresse pas
                    link_flair_text = get_dict_value(data, "link_flair_text", default=None)
                    if link_flair_text is None:
                        continue
                    if len(self._subreddits_and_infos[subreddit_name]["flairs"]) > 1:
                        if link_flair_text.lower() not in [p.lower() for p in self._subreddits_and_infos[subreddit_name]["flairs"]]:
                            continue

                    # On ne lit que les liens externes
                    permalink = get_dict_value(data, "permalink", default=None)
                    url = get_dict_value(data, "url", default=None)
                    if url is None or permalink is None:
                        continue
                    if permalink in url:
                        continue

                    # On ne lit pas les images
                    reddit_media_domain = get_dict_value(data, "is_reddit_media_domain", default=False)
                    if reddit_media_domain:
                        continue

                    # page_title, page_text = extract.fetch_page_text(url)
                    data["description"] = url

                    yield self._to_entry(data, subreddit_name)

            except Exception as e:
                # Erreur sur un subreddit spécifique : on log et on continue les autres
                logger.warning(f"[reddit] Erreur sur r/{subreddit_name} : {e}")
                continue


    def _to_entry(self, post: dict[str, str], subreddit_name: str) -> Entry:
        """Convertit un post en Entry normalisée."""
        return Entry(
            origin=self.SOURCE,
            link=get_dict_value(post, "url", default=None),
            title=get_dict_value(post, "title", default=None),
            description=get_dict_value(post, "description", default=None),
            keywords=[],
            published_at=get_dict_value(post, "created_utc", modifier=lambda d: datetime.fromtimestamp(d, tz=timezone.utc)),
            metadata={
                "subreddit": subreddit_name,
                "score": get_dict_value(post, "score", modifier=str, default=None),
                "num_comments": get_dict_value(post, "num_comments", modifier=str, default=None),
                "author": get_dict_value(post, "author_fullname", default="deleted"),
                "flair": get_dict_value(post, "link_flair_text", default=None),
                "reddit_url": get_dict_value(post, "url", modifier=lambda t: f"{RD_BASE_URL}/{subreddit_name}/{t}"),
            },
        )