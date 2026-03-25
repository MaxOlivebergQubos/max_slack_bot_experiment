from formatting.base import BaseFormatter
from search.base import SearchResult


class SlackFormatter(BaseFormatter):
    """Formats an LLM answer and search results into Slack mrkdwn."""

    def format(self, llm_response: str, search_results: list[SearchResult]) -> str:
        parts: list[str] = [llm_response]

        if search_results:
            parts.append("\n*Relevant links:*")
            for result in search_results:
                parts.append(f"• <{result.url}|{result.title}>")
                if result.snippet:
                    parts.append(f"  _{result.snippet}_")

        return "\n".join(parts)
