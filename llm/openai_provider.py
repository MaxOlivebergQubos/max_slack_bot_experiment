import os

from openai import AsyncOpenAI

from llm.base import BaseLLMProvider
from search.base import SearchResult

_SYSTEM_PROMPT = (
    "You are a financial news summarizer bot. You will be given a stock ticker "
    "and a set of recent news headlines/snippets from trusted financial news sources. "
    "Your job is to produce a VERY brief, headline-style summary (2-3 short bullet "
    "points max) of what's happening with this stock. Be concise — think Bloomberg "
    "terminal brevity. Do not add disclaimers or caveats. Do not make up information "
    "not present in the provided snippets."
)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4")

    async def generate(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""

    async def summarize_news(
        self, ticker: str, search_results: list[SearchResult]
    ) -> str:
        """Produce a terse bullet-point summary of news for *ticker*.

        Args:
            ticker:         The stock ticker symbol (e.g. ``"AAPL"``).
            search_results: Recent news snippets from trusted sources.

        Returns:
            A short, headline-style natural-language summary string.
        """
        if not search_results:
            return f"No recent news found for {ticker}."

        snippets = "\n".join(
            f"- [{r.source}] {r.title}: {r.snippet}" for r in search_results
        )
        prompt = (
            f"Ticker: {ticker}\n\n"
            f"Recent news snippets:\n{snippets}\n\n"
            "Summarize in 2-3 bullet points."
        )
        return await self.generate(prompt)
