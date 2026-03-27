from abc import ABC, abstractmethod

from llm.models import FilteredResponse


class BaseFormatter(ABC):
    """Abstract base class for response formatters."""

    @abstractmethod
    def format(self, response: FilteredResponse, ticker: str = "") -> str:
        """Compose a FilteredResponse into a single message string.

        Args:
            response: The structured, filtered result from the LLM.
            ticker:   Optional ticker symbol used as the message header.

        Returns:
            A formatted string ready to post to Slack.
        """
