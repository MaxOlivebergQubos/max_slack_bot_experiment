from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseMessageParser(ABC, Generic[T]):
    """Abstract base class for message parsers.

    The type parameter ``T`` is the return type of :meth:`parse`, allowing
    subclasses to return richer objects (e.g. a ``TickerQuery``) rather than
    a plain string.
    """

    @abstractmethod
    def parse(self, text: str) -> T | None:
        """Extract the query from a message if it matches the trigger pattern.

        Args:
            text: The raw message text from Slack.

        Returns:
            The extracted query object if the message matches, otherwise None.
        """
