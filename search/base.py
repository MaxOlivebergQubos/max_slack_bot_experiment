from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str


class BaseSearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    async def search(self, query: str, num_results: int = 3) -> list[SearchResult]:
        """Search the web and return a list of results.

        Args:
            query: The search query string.
            num_results: Maximum number of results to return.

        Returns:
            A list of SearchResult dataclass instances.
        """
