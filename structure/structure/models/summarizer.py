import abc


class Summarizer(abc.ABC):

    @abc.abstractmethod
    async def summarize(self, content: str) -> tuple[str, list[str]] | None:
        pass