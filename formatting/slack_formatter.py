from formatting.base import BaseFormatter
from search.base import SearchResult


class SlackFormatter(BaseFormatter):
    """Formats a stock-news LLM summary and search results into Slack mrkdwn.

    Example output::

        📈 *AAPL — News Summary*

        • iPhone 16 sales beat expectations in Q1, revenue up 8% YoY
        • Apple announces $100B buyback program, largest in history

        *Sources:*
        • <https://reuters.com/...|Reuters: Apple Q1 earnings beat...>
    """

    def format(
        self,
        llm_response: str,
        search_results: list[SearchResult],
        ticker: str = "",
    ) -> str:
        parts: list[str] = []

        header = f"📈 *{ticker} — News Summary*" if ticker else "📈 *News Summary*"
        parts.append(header)
        parts.append("")

        if llm_response:
            parts.append(llm_response)

        if search_results:
            parts.append("")
            parts.append("*Sources:*")
            for result in search_results:
                label = result.source or result.title
                parts.append(f"• <{result.url}|{label}: {result.title}>")

        return "\n".join(parts)
