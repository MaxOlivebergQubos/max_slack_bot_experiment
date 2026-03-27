import json
import os
import re
from urllib.parse import urlparse

from openai import AsyncOpenAI

from config import allowed_domains
from llm.base import BaseLLMProvider
from llm.models import EventItem, FilteredResponse, LLMDebugInfo, NewsItem
from llm.prompts import INPUT_LATEST, INPUT_WITH_DATE, SYSTEM_INSTRUCTION, build_system_instruction

_ALLOWED_DOMAINS = allowed_domains()


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

    async def search_and_summarize(
        self, ticker: str, date: str | None = None,
        *, no_filter: bool = False, jar_jar: bool = False,
    ) -> tuple[FilteredResponse, LLMDebugInfo]:
        """Search the web for news about *ticker* and return structured, filtered results.

        Uses the OpenAI Responses API with the built-in ``web_search`` tool so
        that a single API call performs both the search and the summarization.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).
            date: Optional YYYY-MM-DD date string. If provided, search for news
                around that specific date instead of the latest news.

        Returns:
            A tuple of (:class:`FilteredResponse`, :class:`LLMDebugInfo`).
            FilteredResponse contains parsed news items, events, and a count of
            how many items were removed by the domain filter.
            LLMDebugInfo contains the system prompt, input prompt, and raw
            response text for debugging purposes.
        """
        if date is None:
            input_prompt = INPUT_LATEST.format(ticker=ticker)
        else:
            input_prompt = INPUT_WITH_DATE.format(ticker=ticker, date=date)
        system_instruction = build_system_instruction(jar_jar=jar_jar)
        response = await self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search"}],
            instructions=system_instruction,
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

        debug_info = LLMDebugInfo(
            system_prompt=system_instruction,
            input_prompt=input_prompt,
            raw_response_text=raw_text,
        )

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
                if url and not no_filter and not _is_allowed_source(url):
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
                if url and not no_filter and not _is_allowed_source(url):
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
            ), debug_info

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
            ), debug_info

