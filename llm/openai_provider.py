import os

from openai import AsyncOpenAI

from llm.base import BaseLLMProvider
from llm.models import NewsResult, Source

_INSTRUCTIONS = (
    "You are a financial news summarizer bot. "
    "Search reuters.com, finance.yahoo.com, and investing.com for news "
    "about the given stock ticker. "
    "Produce a VERY brief, headline-style summary (2-3 short bullet points max) "
    "of what's happening with this stock. "
    "Be concise — think Bloomberg terminal brevity. "
    "Do not add disclaimers or caveats. "
    "IMPORTANT: For every bullet point, you MUST prefix it with the article's "
    "publication date in [YYYY-MM-DD] format. Example: "
    "• [2026-03-25] iPhone 16 sales beat expectations in Q1. "
    "If you cannot determine the exact publication date of an article, use your "
    "best estimate but always include a date. "
    "Only include news from the date specified in the query, or within 1-2 days "
    "of it. Do NOT include old or outdated articles."
)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI Responses API with built-in web search."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-search-preview")

    async def search_and_summarize(self, ticker: str, date: str | None = None) -> NewsResult:
        """Search the web for news about *ticker* and return a summary with sources.

        Uses the OpenAI Responses API with the built-in ``web_search`` tool so
        that a single API call performs both the search and the summarization.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).
            date: Optional YYYY-MM-DD date string. If provided, search for news
                around that specific date instead of the latest news.

        Returns:
            A :class:`NewsResult` containing a terse bullet-point summary and
            a list of cited :class:`Source` objects extracted from the response
            annotations.
        """
        if date is None:
            input_prompt = (
                f"Search for the latest news about {ticker} stock from TODAY on "
                "reuters.com, finance.yahoo.com, and investing.com. "
                "Only include articles published today or yesterday. "
                "Summarize in 2-3 bullet points. Include the publication date for each."
            )
        else:
            input_prompt = (
                f"Search for news about {ticker} stock from {date} on "
                "reuters.com, finance.yahoo.com, and investing.com. "
                f"Only include articles published on {date} or within 1-2 days of it. "
                "Do NOT include old or outdated articles. "
                "Summarize in 2-3 bullet points. Include the publication date for each."
            )
        response = await self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search"}],
            instructions=_INSTRUCTIONS,
            input=input_prompt,
        )

        summary_text = ""
        sources: list[Source] = []

        for item in response.output:
            if item.type == "message":
                for block in item.content:
                    if block.type == "output_text":
                        summary_text = block.text
                        for annotation in block.annotations:
                            if annotation.type == "url_citation":
                                sources.append(
                                    Source(
                                        title=annotation.title,
                                        url=annotation.url,
                                    )
                                )

        if not summary_text:
            summary_text = f"No recent news found for {ticker}."

        return NewsResult(summary=summary_text, sources=sources)

