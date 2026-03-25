"""Site-scoped news search provider for stock tickers."""
import os
from urllib.parse import urlparse

import httpx

from search.base import BaseSearchProvider, SearchResult

_BING_SEARCH_URL = "https://api.bing.microsoft.com/v7.0/search"
_DEFAULT_TIMEOUT = 10.0

# Friendly display names keyed by the domain fragment used in the site: filter
_SOURCE_LABELS: dict[str, str] = {
    "reuters.com": "Reuters",
    "finance.yahoo.com": "Yahoo Finance",
    "investing.com": "Investing.com",
}

_DEFAULT_SITES = list(_SOURCE_LABELS.keys())


def _label_for_url(url: str) -> str:
    """Derive a human-readable source name from a URL."""
    host = urlparse(url).netloc.lstrip("www.")
    # Exact match first
    if host in _SOURCE_LABELS:
        return _SOURCE_LABELS[host]
    # Partial match (e.g. "uk.reuters.com" → "Reuters")
    for domain, label in _SOURCE_LABELS.items():
        if host.endswith(domain):
            return label
    # Fallback: capitalise the bare hostname
    return host.split(".")[0].capitalize()


class NewsSearchProvider(BaseSearchProvider):
    """Search provider that scopes Bing queries to trusted financial news sites.

    By default the trusted sites are Reuters, Yahoo Finance, and Investing.com.
    Pass a custom ``sites`` list to the constructor to override.

    Args:
        api_key:    Bing Search API key.  Falls back to the ``BING_API_KEY``
                    environment variable.
        sites:      List of domain strings to restrict results to, e.g.
                    ``["reuters.com", "finance.yahoo.com"]``.  Defaults to
                    :attr:`_DEFAULT_SITES`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        sites: list[str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        resolved_key = api_key or os.environ.get("BING_API_KEY")
        if not resolved_key:
            raise ValueError(
                "Bing API key is required. Set the BING_API_KEY environment variable "
                "or pass api_key= to NewsSearchProvider()."
            )
        self._api_key = resolved_key
        self._sites = sites if sites is not None else _DEFAULT_SITES
        self._timeout = timeout

    def _build_query(self, ticker: str) -> str:
        site_filter = " OR ".join(f"site:{s}" for s in self._sites)
        return f"{ticker} stock news ({site_filter})"

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search for recent news about *query* (treated as a ticker symbol).

        Args:
            query:       The stock ticker to search for (e.g. ``"AAPL"``).
            num_results: Maximum number of results to return (default 5).

        Returns:
            A list of :class:`~search.base.SearchResult` instances, each with
            a ``source`` field derived from the article URL.
        """
        bing_query = self._build_query(query)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                _BING_SEARCH_URL,
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                params={"q": bing_query, "count": num_results},
            )
        response.raise_for_status()
        data = response.json()

        results: list[SearchResult] = []
        for item in data.get("webPages", {}).get("value", [])[:num_results]:
            url = item.get("url", "")
            results.append(
                SearchResult(
                    title=item.get("name", ""),
                    url=url,
                    snippet=item.get("snippet", ""),
                    source=_label_for_url(url),
                )
            )
        return results
