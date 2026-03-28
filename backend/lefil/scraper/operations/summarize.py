"""
summarize.py — Propose une implementation d'un résumé en utilisant Ollama + modèle léger.

Produit un résumé fluide et cohérent, reformulé.
Nécessite qu'Ollama tourne sur la machine.
"""

from __future__ import annotations

import logging
import typing

from groq import AsyncGroq
from groq.types.chat import ChatCompletion
from ollama import GenerateResponse, AsyncClient
from structure.models.summarizer import Summarizer

from config import settings

logger = logging.getLogger("lefil.backend.scraper.operations.summarize")


class OllamaSummarizer(Summarizer):

    def __init__(self, url: str = "http://localhost:11434",
                 model: str = "qwen2.5:1.5b",
                 timeout: float = 180.0,
                 output_sentences: int = 2,
                 output_keywords: int = 2):
        self.__url: str = url
        self.__model: str = model
        self.__timeout: float = timeout
        self.__output_sentences: int = output_sentences
        self.__output_keywords: int = output_keywords

        # region Prompt
        self.__prompt: typing.Final[str] = """You are a technical summarizer writing for a data engineering newsletter.

Task:
Summarize the article in exactly {} sentences.

The summary must:
- Clearly identify the main technology, system, or concept discussed.
- Explain what is new, changed, or technically important.
- Include concrete numbers, benchmarks, or findings if they appear in the article.

Style requirements:
- Write in plain, factual English.
- Do not start with phrases such as "This article", "The author", or similar meta references.
- Do not add opinions or information not present in the text.
- Do not use bullet points or lists.

After the summary, output exactly {} keywords that categorize the article.

Keyword rules:
- Single words only
- Lowercase
- Separated by a comma
- Prefer technical terms (e.g., spark, parquet, kubernetes)

Output format (strictly follow this format):

Summary: <two sentences>
Keywords: <keyword1>, <keyword2>

Article:
{}"""
        # endregion Prompt

    async def _execute(self, content: str) -> GenerateResponse:
        return await AsyncClient().generate(
            model=self.__model,
            prompt=self.__prompt.format(self.__output_sentences, self.__output_keywords, content),
            options=dict(temperature=0.2,
                         num_predict=200,
                         top_p=0.9,
                         repeat_penalty=1.1)
        )

    async def summarize(self, content: str) -> tuple[str, list[str]] | None:
        result = await self._execute(content)
        response = result.response.strip()
        if not response.startswith("Summary:"):
            return None
        split_by_keywords = response.split("Keywords:")
        summary = split_by_keywords[0].strip().split("Summary:")[1].strip()
        keywords = [kw.strip() for kw in response.split("Keywords:")[1].strip().split(",")]
        if len(keywords) > 0 and keywords[-1].endswith("."):
            keywords[-1] =  keywords[-1][:-1]
        return summary, keywords


class GroqSummarizer(Summarizer):

    def __init__(self,
                 model: str = "qwen/qwen3-32b",
                 output_sentences: int = 2,
                 output_keywords: int = 2):
        self.__model: str = model
        self.__output_sentences: int = output_sentences
        self.__output_keywords: int = output_keywords
        self.__reasoning_prompt: typing.Final[str] = """You are a technical summarizer writing for a data engineering newsletter.

Task:
Summarize the article in exactly {} sentences.

The summary must:
- Clearly identify the main technology, system, or concept discussed.
- Explain what is new, changed, or technically important.
- Include concrete numbers, benchmarks, or findings if they appear in the article.

Specific rule :
- The content should be related to programming or with close connection to programming. If the content doesn't relate to those subject, give the answer "Not related".

Style requirements:
- Write in plain, factual English.
- Do not start with phrases such as "This article", "The author", or similar meta references.
- Do not add opinions or information not present in the text.
- Do not use bullet points or lists.

After the summary, output exactly {} keywords that categorize the article.

Keyword rules:
- Single words only
- Lowercase
- Separated by a comma
- Prefer technical terms (e.g., spark, parquet, kubernetes)

Output format (strictly follow this format):

Summary: <two sentences>
Keywords: <keyword1>, <keyword2>"""
        self.__client: AsyncGroq = AsyncGroq(api_key=settings.groq_api_key)

    async def _execute(self, content: str) -> ChatCompletion:
        return await self.__client.chat.completions.create(
            model=self.__model,
            messages=[
                dict(role="system",
                     content=self.__reasoning_prompt),
                dict(role="user",
                     content=f"Summarize this article: {content}")
            ],
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=0.95,
            reasoning_effort="none",
            stream=False,
            stop=None)

    async def summarize(self, content: str) -> tuple[str, list[str]] | None:
        result: ChatCompletion = await self._execute(content)
        response = result.choices[0].message.content
        logger.debug(f"Result is {response}")
        if not response.startswith("Summary:"):
            return None
        split_by_keywords = response.split("Keywords:")
        summary = split_by_keywords[0].strip().split("Summary:")[1].strip()
        keywords = [kw.strip() for kw in response.split("Keywords:")[1].strip().split(",")]
        if len(keywords) > 0 and keywords[-1].endswith("."):
            keywords[-1] = keywords[-1][:-1]
        return summary, keywords