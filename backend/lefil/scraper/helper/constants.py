from structure.meta import SingletonMeta
from structure.models.summarizer import Summarizer


C__DEFAULT_SLEEP_TIME_IN_S: int = 60 * 5


class ApplicationContext(metaclass=SingletonMeta):

    def __init__(self):
        self.__summarizer: Summarizer | None = None

    @property
    def summarizer(self) -> Summarizer | None:
        return self.__summarizer

    @summarizer.setter
    def summarizer(self, value: Summarizer | None = None):
        self.__summarizer = value

context: ApplicationContext = ApplicationContext()