from abc import ABC, abstractmethod

from llm.models import NewsResult


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def search_and_summarize(self, ticker: str, date: str | None = None) -> NewsResult:
        """Search the web for news about *ticker* and return a summary with sources.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).
            date: Optional YYYY-MM-DD date string. If provided, search for news
                around that specific date instead of the latest news.

        Returns:
            A :class:`NewsResult` containing a terse bullet-point summary and
            a list of cited :class:`Source` objects.
        """
