import os

import httpx

from search.base import BaseSearchProvider, SearchResult

_BING_SEARCH_URL = "https://api.bing.microsoft.com/v7.0/search"


class BingSearchProvider(BaseSearchProvider):
    """Search provider backed by the Bing Web Search v7 API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ["BING_API_KEY"]

    async def search(self, query: str, num_results: int = 3) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                _BING_SEARCH_URL,
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                params={"q": query, "count": num_results},
            )
        response.raise_for_status()
        data = response.json()

        results: list[SearchResult] = []
        for item in data.get("webPages", {}).get("value", [])[:num_results]:
            results.append(
                SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                )
            )
        return results
