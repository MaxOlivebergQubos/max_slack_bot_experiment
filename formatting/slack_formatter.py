from formatting.base import BaseFormatter
from llm.models import NewsResult


class SlackFormatter(BaseFormatter):
    """Formats a stock-news LLM summary and sources into Slack mrkdwn.

    Example output::

        📈 *AAPL — News Summary*

        • iPhone 16 sales beat expectations in Q1, revenue up 8% YoY
        • Apple announces $100B buyback program, largest in history

        *Sources:*
        • <https://reuters.com/...|Apple Q1 earnings beat...>
    """

    def format(self, news_result: NewsResult, ticker: str = "") -> str:
        parts: list[str] = []

        header = f"📈 *{ticker} — News Summary*" if ticker else "📈 *News Summary*"
        parts.append(header)
        parts.append("")

        if news_result.summary:
            parts.append(news_result.summary)

        if news_result.sources:
            parts.append("")
            parts.append("*Sources:*")
            for source in news_result.sources:
                if source.published_date:
                    parts.append(f"• <{source.url}|{source.title}> ({source.published_date})")
                else:
                    parts.append(f"• <{source.url}|{source.title}>")

        return "\n".join(parts)
