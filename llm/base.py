from abc import ABC, abstractmethod

from llm.models import FilteredResponse, LLMDebugInfo


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def search_and_summarize(self, ticker: str, date: str | None = None) -> tuple[FilteredResponse, LLMDebugInfo]:
        """Search the web for news about *ticker* and return structured, filtered results.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).
            date: Optional YYYY-MM-DD date string.

        Returns:
            A tuple of (FilteredResponse, LLMDebugInfo). FilteredResponse contains
            news items, events, and a count of filtered links. LLMDebugInfo contains
            the intermediate prompt/response data for debugging.
        """
