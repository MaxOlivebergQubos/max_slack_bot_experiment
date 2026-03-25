from abc import ABC, abstractmethod

from search.base import SearchResult


class BaseFormatter(ABC):
    """Abstract base class for response formatters."""

    @abstractmethod
    def format(
        self,
        llm_response: str,
        search_results: list[SearchResult],
        ticker: str = "",
    ) -> str:
        """Combine an LLM answer and search results into a single message string.

        Args:
            llm_response:   The natural-language answer from the LLM.
            search_results: A list of SearchResult instances.
            ticker:         Optional ticker symbol used as the message header.

        Returns:
            A formatted string ready to post to Slack.
        """
