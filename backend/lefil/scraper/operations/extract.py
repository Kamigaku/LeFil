import logging
import re

import httpx
import trafilatura

logger = logging.getLogger("lefil.operations.extract")


def fetch_page_text(url: str, timeout: float = 15.0) -> tuple[str, str]:
    """
    Télécharge une page et extrait son contenu textuel principal.

    Cascade de 4 stratégies, chacune étant le fallback de la précédente :
      1. trafilatura (favor_recall)     — couvre ~90% des cas
      2. trafilatura (fallback interne) — pour les sites avec HTML ambigu
      3. readability-lxml               — Reader Mode Firefox
      4. BeautifulSoup <article>/<main> — extraction structurelle brute

    Returns:
        (title, text)
    Raises:
        ValueError si aucune stratégie ne produit suffisamment de contenu
    """
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; datascraper/1.0)"
        })
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise ValueError(f"Impossible de fetcher {url} : {e}") from e

    html = resp.text

    # Titre extrait une seule fois, partagé par tous les fallbacks
    meta = trafilatura.extract_metadata(html)
    title = (meta.title if meta and meta.title else "") or _extract_title_fallback(html)

    # Stratégie 1 — trafilatura en mode recall (permissif)
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        favor_recall=True,
    )
    if text and len(text.strip()) >= 100:
        logger.debug("Extraction OK via trafilatura (recall)")
        return title.strip(), text.strip()

    # Stratégie 2 — trafilatura avec fallback interne
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        favor_recall=True,
        with_metadata=False,
    )
    if text and len(text.strip()) >= 100:
        logger.debug("Extraction OK via trafilatura (fallback interne)")
        return title.strip(), text.strip()

    # Stratégie 3 — readability-lxml
    try:
        from readability import Document
        from bs4 import BeautifulSoup as BS
        doc = Document(html)
        soup = BS(doc.summary(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        title = title or doc.title()
        if text and len(text.strip()) >= 100:
            logger.debug("Extraction OK via readability-lxml")
            return title.strip(), text.strip()
    except ImportError:
        logger.debug("readability-lxml non installé")
    except Exception as e:
        logger.debug(f"readability-lxml a échoué : {e}")

    # Stratégie 4 — BeautifulSoup sur balises sémantiques
    try:
        from bs4 import BeautifulSoup as BS
        soup = BS(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header",
                          "aside", "form", "noscript", "iframe"]):
            tag.decompose()
        content_node = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", class_=lambda c: c and "content" in c.lower())
            or soup.body
        )
        if content_node:
            text = content_node.get_text(separator="\n", strip=True)
            if text and len(text.strip()) >= 100:
                logger.debug("Extraction OK via BeautifulSoup")
                return title.strip(), text.strip()
    except ImportError:
        logger.debug("beautifulsoup4 non installé")
    except Exception as e:
        logger.debug(f"BeautifulSoup a échoué : {e}")

    raise ValueError(
        f"Aucune stratégie d'extraction n'a fonctionné pour {url}. "
        "La page nécessite peut-être un rendu JavaScript (SPA)."
    )


def _extract_title_fallback(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else "Sans titre"