"""Main entrypoint for the gaston Slack bot.

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

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instantiate providers (swap any of these with your own implementation)
# ---------------------------------------------------------------------------
parser = TickerMessageParser()
llm = OpenAIProvider()
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

    if not ticker_query.ticker:
        await say(
            text="👋 I can only look up news about stock tickers! Try something like `!gaston AAPL` or `!gaston TSLA 2025-01-31`.",
            thread_ts=thread_ts,
        )
        return

    try:
        news_result = await llm.search_and_summarize(ticker_query.ticker, date=ticker_query.date)
    except Exception as exc:
        logger.exception(
            "Error while processing ticker %s", ticker_query.ticker
        )
        await say(
            text=f"Sorry, something went wrong: {exc}",
            thread_ts=thread_ts,
        )
        return

    message = formatter.format(news_result, ticker=ticker_query.ticker)
    await say(text=message, thread_ts=thread_ts)


async def main() -> None:
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
