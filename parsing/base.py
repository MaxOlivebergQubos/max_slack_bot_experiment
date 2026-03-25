from abc import ABC, abstractmethod


class BaseMessageParser(ABC):
    """Abstract base class for message parsers."""

    @abstractmethod
    def parse(self, text: str) -> str | None:
        """Extract the query from a message if it matches the trigger pattern.

        Args:
            text: The raw message text from Slack.

        Returns:
            The extracted query string if the message matches, otherwise None.
        """
