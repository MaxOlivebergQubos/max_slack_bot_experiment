from abc import ABC, abstractmethod

from llm.models import FilteredResponse, LLMDebugInfo


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def search_and_summarize(
        self, ticker: str, date: str | None = None,
        *, no_filter: bool = False, jar_jar: bool = False,
        verbose: bool = False,
    ) -> tuple[FilteredResponse, LLMDebugInfo]:
        """Search the web for news about *ticker* and return structured, filtered results.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).
            date: Optional YYYY-MM-DD date string.
            no_filter: When True, skip domain-based source filtering.
            jar_jar: Kept for backward compatibility; prefer verbose=True.
            verbose: When True, instruct the LLM to produce full paragraph summaries.

        Returns:
            A tuple of (FilteredResponse, LLMDebugInfo). FilteredResponse contains
            news items, events, and a count of filtered links. LLMDebugInfo contains
            the intermediate prompt/response data for debugging.
        """

    @abstractmethod
    async def reformulate_as_jar_jar(self, text: str) -> str:
        """Reformulate *text* in the style of Jar Jar Binks.

        Args:
            text: The original paragraph to reformulate.

        Returns:
            The reformulated text in Jar Jar Binks style.
        """
