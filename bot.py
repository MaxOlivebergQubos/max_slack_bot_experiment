"""Main entrypoint for the maxbot Slack bot.

Wires together all providers and starts the bot in Socket Mode.
"""
import logging
import os

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from formatting.slack_formatter import SlackFormatter
from llm.openai_provider import OpenAIProvider
from parsing.ticker_parser import TickerMessageParser
from search.news_search_provider import NewsSearchProvider

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instantiate providers (swap any of these with your own implementation)
# ---------------------------------------------------------------------------
parser = TickerMessageParser()
llm = OpenAIProvider()
searcher = NewsSearchProvider()
formatter = SlackFormatter()

# ---------------------------------------------------------------------------
# Slack app
# ---------------------------------------------------------------------------
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("message")
async def handle_message(event: dict, say) -> None:
    """Handle incoming Slack messages."""
    text: str = event.get("text") or ""
    ticker_query = parser.parse(text)

    if ticker_query is None:
        return

    thread_ts: str = event.get("thread_ts") or event["ts"]

    try:
        search_results = await searcher.search(ticker_query.ticker)
        llm_response = await llm.summarize_news(ticker_query.ticker, search_results)
    except Exception as exc:
        logger.exception(
            "Error while processing ticker %s", ticker_query.ticker
        )
        await say(
            text=f"Sorry, something went wrong: {exc}",
            thread_ts=thread_ts,
        )
        return

    message = formatter.format(llm_response, search_results, ticker=ticker_query.ticker)
    await say(text=message, thread_ts=thread_ts)


async def main() -> None:
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
