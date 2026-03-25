from abc import ABC, abstractmethod

from llm.models import NewsResult


class BaseFormatter(ABC):
    """Abstract base class for response formatters."""

    @abstractmethod
    def format(self, news_result: NewsResult, ticker: str = "") -> str:
        """Combine a NewsResult into a single message string.

        Args:
            news_result: The summary and sources returned by the LLM.
            ticker:      Optional ticker symbol used as the message header.

        Returns:
            A formatted string ready to post to Slack.
        """
