"""Main entrypoint for the gaston Slack bot.

Wires together all providers and starts the bot in Socket Mode.
"""
import logging
import os

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from config import allowed_domains, source_names_str
from debug.slack_debug_logger import SlackDebugLogger
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

# ---------------------------------------------------------------------------
# Help text for --info flag
# ---------------------------------------------------------------------------
_INFO_TEXT = (
    "📈 *Gaston — Your Stock News Bot*\n\n"
    "*How to use:*\n"
    "• `!gaston AAPL` — Get today's top news for a ticker\n"
    "• `!gaston TSLA 2026-03-20` — Get news from a specific date\n"
    "• `!gaston III.L` — Works with international tickers too\n\n"
    "*Options:*\n"
    "• `--no-filter` — Include sources from any website (not just Reuters, Yahoo Finance, etc.)\n"
    "• `--info` — Show this help message\n\n"
    f"*Sources:* {source_names_str()}\n"
    "*Tip:* Gaston responds in the thread so your channel stays tidy! 🧵"
)

# ---------------------------------------------------------------------------
# Optional debug logger (disabled when SLACK_LOG_CHANNEL is unset/empty)
# SLACK_LOG_CHANNEL must be a channel ID (e.g. C1234567890), not a channel name.
# ---------------------------------------------------------------------------
_log_channel = os.environ.get("SLACK_LOG_CHANNEL", "").strip()
debug_logger: SlackDebugLogger | None = (
    SlackDebugLogger(app, _log_channel) if _log_channel else None
)


@app.event("message")
async def handle_message(event: dict, say) -> None:
    """Handle incoming Slack messages."""
    text: str = event.get("text") or ""
    ticker_query = parser.parse(text)

    if ticker_query is None:
        return

    thread_ts: str = event.get("thread_ts") or event["ts"]

    # --- Start debug trace (best-effort) ---
    log_thread_ts: str | None = None
    if debug_logger is not None:
        try:
            log_thread_ts = await debug_logger.start_trace(text)
        except Exception:
            pass

    if ticker_query.info:
        await say(text=_INFO_TEXT, thread_ts=thread_ts)
        return

    if not ticker_query.ticker:
        await say(
            text="👋 I can only look up news about stock tickers! Try something like `!gaston AAPL`, `!gaston III.L`, or `!gaston TSLA 2025-01-31`.",
            thread_ts=thread_ts,
        )
        return

    if debug_logger is not None:
        try:
            await debug_logger.log_parsed_query(
                log_thread_ts,
                ticker=ticker_query.ticker,
                date=ticker_query.date,
                raw_message=text,
            )
        except Exception:
            pass

    try:
        # Compute per-query effective domain set (never mutates module-level state)
        effective_domains = (
            frozenset(ticker_query.websites)
            if ticker_query.websites is not None
            else allowed_domains()
        )
        if ticker_query.plus_websites is not None:
            effective_domains = effective_domains | frozenset(ticker_query.plus_websites)

        # When the user explicitly provides custom domains, disable the hard
        # filter — they deliberately chose those sites, so we should trust them.
        has_custom_domains = (
            ticker_query.websites is not None or ticker_query.plus_websites is not None
        )

        news_result, debug_info = await llm.search_and_summarize(
            ticker_query.ticker,
            date=ticker_query.date,
            no_filter=ticker_query.no_filter or has_custom_domains,
            jar_jar=ticker_query.jar_jar,
            domains=effective_domains,
        )
    except Exception as exc:
        logger.exception(
            "Error while processing ticker %s", ticker_query.ticker
        )
        if debug_logger is not None:
            try:
                await debug_logger.log_error(log_thread_ts, exc)
            except Exception:
                pass
        await say(
            text=f"Sorry, something went wrong: {exc}",
            thread_ts=thread_ts,
        )
        return

    if debug_logger is not None:
        try:
            await debug_logger.log_system_prompt(log_thread_ts, debug_info.system_prompt)
        except Exception:
            pass
        try:
            await debug_logger.log_input_prompt(log_thread_ts, debug_info.input_prompt)
        except Exception:
            pass
        try:
            await debug_logger.log_raw_response(log_thread_ts, debug_info.raw_response_text)
        except Exception:
            pass
        try:
            await debug_logger.log_filtered_result(log_thread_ts, news_result)
        except Exception:
            pass

    message = formatter.format(news_result, ticker=ticker_query.ticker)

    if debug_logger is not None:
        try:
            await debug_logger.log_final_message(log_thread_ts, message)
        except Exception:
            pass

    await say(text=message, thread_ts=thread_ts)


async def main() -> None:
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
