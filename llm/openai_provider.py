import os

from openai import AsyncOpenAI

from llm.base import BaseLLMProvider
from llm.models import NewsResult, Source

_INSTRUCTIONS = (
    "You are a financial news summarizer bot. "
    "Search reuters.com, finance.yahoo.com, and investing.com for recent news "
    "about the given stock ticker. "
    "Produce a VERY brief, headline-style summary (2-3 short bullet points max) "
    "of what's happening with this stock. "
    "Be concise — think Bloomberg terminal brevity. "
    "Do not add disclaimers or caveats."
)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI Responses API with built-in web search."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-search-preview")

    async def search_and_summarize(self, ticker: str) -> NewsResult:
        """Search the web for news about *ticker* and return a summary with sources.

        Uses the OpenAI Responses API with the built-in ``web_search`` tool so
        that a single API call performs both the search and the summarization.

        Args:
            ticker: The stock ticker symbol (e.g. ``"AAPL"``).

        Returns:
            A :class:`NewsResult` containing a terse bullet-point summary and
            a list of cited :class:`Source` objects extracted from the response
            annotations.
        """
        response = await self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search"}],
            instructions=_INSTRUCTIONS,
            input=(
                f"Search for the latest news about {ticker} stock on "
                "reuters.com, finance.yahoo.com, and investing.com. "
                "Summarize in 2-3 bullet points."
            ),
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

