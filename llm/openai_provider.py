import json
import os
import re
from urllib.parse import urlparse

from openai import AsyncOpenAI

from llm.base import BaseLLMProvider
from llm.models import EventItem, FilteredResponse, NewsItem

_ALLOWED_DOMAINS = frozenset({
    "reuters.com",
    "finance.yahoo.com",
    "investing.com",
    "marketwatch.com",
})

_INSTRUCTIONS = (
    "You are a financial news summarizer bot. "
    "Search reuters.com, finance.yahoo.com, investing.com, and marketwatch.com for news "
    "about the given stock ticker. "
    "Also search for upcoming events (earnings, ex-dividend dates, shareholder meetings). "
    "You MUST respond with ONLY a JSON object — no markdown, no commentary, no extra text. "
    "The JSON must match this exact schema:\n"
    "{\n"
    '  "news": [\n'
    '    {"date": "YYYY-MM-DD", "headline": "short headline", "source_url": "https://...", "source_name": "Reuters"}\n'
    "  ],\n"
    '  "events": [\n'
    '    {"date": "YYYY-MM-DD", "description": "event description", "source_url": "https://...", "source_name": "Yahoo Finance"}\n'
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- news: 2-3 items max. Each headline should be Bloomberg-terminal terse.\n"
    "- events: 0-2 items. Include earnings dates, ex-dividend dates, investor days, etc.\n"
    "- date: Always YYYY-MM-DD format.\n"
    "- source_url: MUST be from reuters.com, finance.yahoo.com, investing.com, or marketwatch.com ONLY.\n"
    "- source_name: Human-readable site name.\n"
    "- If no news found, set news to an empty array [].\n"
    "- If no events found, set events to an empty array [].\n"
    "- Do NOT include any text outside the JSON object.\n"
    "- Only include news from the date specified in the query, or within 1-2 days of it."
)


def _is_allowed_source(url: str) -> bool:
    """Return True if the URL's domain ends with one of the allowed domains."""
    try:
        hostname = urlparse(url).hostname or ""
        return any(hostname == domain or hostname.endswith("." + domain) for domain in _ALLOWED_DOMAINS)
    except Exception:
        return False


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) the LLM might wrap around JSON."""
    text = text.strip()
    # Remove leading ```json or ``` fence
    text = re.sub(r"^```(?:json)?\s*", "", text)
    # Remove trailing ``` fence
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI Responses API with built-in web search."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-search-preview")

    async def search_and_summarize(self, ticker: str, date: str | None = None) -> FilteredResponse:
        """Search the web for news about *ticker* and return structured, filtered results.

        Uses the OpenAI Responses API with the built-in ``web_search`` tool so
        that a single API call performs both the search and the summarization.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).
            date: Optional YYYY-MM-DD date string. If provided, search for news
                around that specific date instead of the latest news.

        Returns:
            A :class:`FilteredResponse` with parsed news items, events, and a
            count of how many items were removed by the domain filter.
        """
        if date is None:
            input_prompt = (
                f"Search for the latest news about {ticker} stock from TODAY on "
                "reuters.com, finance.yahoo.com, investing.com, and marketwatch.com. "
                "Only include articles published today or yesterday. "
                f"Also check for any upcoming events (earnings, dividends, etc.) for {ticker}."
            )
        else:
            input_prompt = (
                f"Search for news about {ticker} stock from {date} on "
                "reuters.com, finance.yahoo.com, investing.com, and marketwatch.com. "
                f"Only include articles published on {date} or within 1-2 days of it. "
                "Do NOT include old or outdated articles. "
                f"Also check for any upcoming events (earnings, dividends, etc.) for {ticker}."
            )
        response = await self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search"}],
            instructions=_INSTRUCTIONS,
            input=input_prompt,
        )

        raw_text = ""
        for item in response.output:
            if item.type == "message":
                for block in item.content:
                    if block.type == "output_text":
                        raw_text = block.text
                        break
                if raw_text:
                    break

        try:
            cleaned = _strip_code_fences(raw_text)
            data = json.loads(cleaned)

            raw_news = data.get("news", [])
            raw_events = data.get("events", [])

            news_items: list[NewsItem] = []
            events_items: list[EventItem] = []
            filtered_count = 0

            for entry in raw_news:
                url = entry.get("source_url", "")
                if url and not _is_allowed_source(url):
                    filtered_count += 1
                    url = ""
                news_items.append(NewsItem(
                    date=entry.get("date", ""),
                    headline=entry.get("headline", ""),
                    source_url=url,
                    source_name=entry.get("source_name", ""),
                ))

            for entry in raw_events:
                url = entry.get("source_url", "")
                if url and not _is_allowed_source(url):
                    filtered_count += 1
                    url = ""
                events_items.append(EventItem(
                    date=entry.get("date", ""),
                    description=entry.get("description", ""),
                    source_url=url,
                    source_name=entry.get("source_name", ""),
                ))

            return FilteredResponse(
                news=news_items,
                events=events_items,
                filtered_count=filtered_count,
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            return FilteredResponse(
                news=[NewsItem(
                    date="",
                    headline=f"No recent news found for {ticker}.",
                    source_url="",
                    source_name="",
                )],
                events=[],
                filtered_count=0,
            )

