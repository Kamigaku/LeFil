import logging
import typing
from typing import Iterator

import httpx
import pytumblr
from lxml import etree
from structure.models import Entry
from structure.models.db import EntryRepository

from scraper.base import BaseScraper


logger = logging.getLogger("lefil.scraper.devto")

DEV_TO_BASE_URL: typing.Final[str] = "https://dev.to"
DEV_TO_TOPIC_URL: typing.Final[str] = "{}/t/{}"

class TumblrScraper(BaseScraper):
    """
    Scraper du site dev.to

    """

    SOURCE = "dev.to"

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)

        self._client = pytumblr.TumblrRestClient(
    'E8aHViDhHPlelJeY0GIb2XzHSXa2Uy7zxQjahGokKErVMRTcVB',
    '4N3laNfsbV7Tm5itWp9f78S9xhJtOxs9UNRw9e9AzzXpAedH0V',
            'z5s79r1lHDCHrcsAIWGZWsf3fY64juyYR3ketFa3DIwZfwHW8X',
            'tPGOrPuP252mEJPs4vXdHdrlSJbYox41Ydjf1yVXTKhJbfjPEq'
)

    def _fetch(self) -> Iterator[Entry]:
        try:
            response = self._client.get(DEV_TO_TOPIC_URL.format(DEV_TO_BASE_URL, "programming"))
            parser = etree.HTMLParser()
            html_root = etree.fromstring(response.content, parser)
            all_articles = html_root.xpath("//div[contains(@class, 'crayons-story')]")
            for article in all_articles:
                header = article.xpath("./h2")
                if header is None or len(header) != 1:  # Ne contient pas d'entête
                    continue
                header_content = "".join([t for t in header[0].itertext()]).strip()
                if header_content.upper() != "TRENDING REPOSITORY":
                    continue


                project_element = article.xpath(".//h3")
                if project_element is None or len(project_element) != 1:
                    continue

                # Link
                link_element = project_element[0].xpath(".//a")
                if link_element is None:
                    continue
                project_link = f"{GITHUB_DEFAULT_URL}{link_element[-1].get("href")}"

                if EntryRepository().entry_exist_by_link(project_link):
                    logger.debug(f"[GitHub] {project_link} already exists, skipping.")
                    continue

                # Title
                project_full_title: str = "".join([p.strip() for p in project_element[0].itertext()])
                project_author: str = project_full_title.split("/")[0]
                project_title: str = project_full_title.split("/")[1]

                # Description
                description_element = article.xpath(".//p")
                if description_element is None or len(description_element) != 1:
                    continue
                project_description: str = "".join([p.strip() for p in description_element[0].itertext()])

                # Keywords
                keywords_element = article.xpath("./div")[-1].xpath(".//a")
                if keywords_element is None:
                    continue
                keywords: list[str] = [k.strip()
                                       for keyword in keywords_element
                                       for k in keyword.itertext()]

                # Retrieve programming language to add it to the keywords
                programming_element = article.xpath(".//span[contains(@itemprop, 'programmingLanguage')]")
                if programming_element is None:
                    continue
                programming_language: str = programming_element[0].text.strip().lower()
                if programming_language not in keywords:
                    keywords.append(programming_language)


                # Stars count
                stars_element = article.xpath(".//span[contains(@id, 'repo-stars-counter-star')]")
                if stars_element is None:
                    continue
                stars: str = stars_element[0].text.strip()

                yield self._to_entry(repo=project_title,
                                     elements=dict(keywords=keywords,
                                                   description=project_description,
                                                   link=project_link,
                                                   author=project_author,
                                                   stars=stars))
        except httpx.HTTPError as e:
            logger.error(f"[Github Trendings] Error during the retrieval of the trendings", exc_info=e)

    def _to_entry(self, repo: str, elements: dict) -> Entry | None:
        try:
            return Entry(
                origin=self.SOURCE,
                link=elements["link"],
                title=repo,
                description=elements["description"],
                published_at=datetime.now(timezone.utc),
                keywords=elements["keywords"],
                summarize_description=False,
                metadata={
                    "score": elements["stars"]
                },
            )
        except Exception as e:
            logger.warning(f"[github] Impossible de convertir release de {repo}: {e}")
            return None

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass