from formatting.base import BaseFormatter
from llm.models import FilteredResponse


class SlackFormatter(BaseFormatter):
    """Formats structured news/events data into Slack mrkdwn."""

    def format(self, response: FilteredResponse, ticker: str = "") -> str:
        parts: list[str] = []

        # Header
        header = f"📈 *{ticker} — News Summary*" if ticker else "📈 *News Summary*"
        parts.append(header)
        parts.append("")

        # News bullets
        if response.news:
            for item in response.news:
                date_prefix = f"[{item.date}] " if item.date else ""
                if item.source_url:
                    parts.append(f"• {date_prefix}{item.headline} (<{item.source_url}|{item.source_name}>)")
                else:
                    parts.append(f"• {date_prefix}{item.headline}")
        else:
            parts.append(f"_No recent news found for {ticker}._")

        # Events section
        parts.append("")
        if response.events:
            parts.append("*Upcoming Events:*")
            for event in response.events:
                date_prefix = f"[{event.date}] " if event.date else ""
                if event.source_url:
                    parts.append(f"📅 {date_prefix}{event.description} (<{event.source_url}|{event.source_name}>)")
                else:
                    parts.append(f"📅 {date_prefix}{event.description}")
        else:
            parts.append(f"📅 _No relevant upcoming events found for {ticker}._")

        # Filtered links note
        if response.filtered_count > 0:
            parts.append("")
            parts.append(f"_ℹ️ {response.filtered_count} link(s) from non-approved sources were filtered out._")

        return "\n".join(parts)
