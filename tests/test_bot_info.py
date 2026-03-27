"""Tests for bot --info flag short-circuit behavior."""
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _import_bot():
    """Import bot with env vars mocked to avoid real credential requirements."""
    env_patch = {
        "SLACK_BOT_TOKEN": "xoxb-test",
        "SLACK_APP_TOKEN": "xapp-test",
        "OPENAI_API_KEY": "sk-test",
    }
    mock_app = MagicMock()
    # Make @app.event("message") a pass-through decorator so handle_message
    # stays an awaitable async function rather than being replaced by a MagicMock.
    mock_app.event.return_value = lambda f: f
    with patch.dict(os.environ, env_patch), \
         patch("slack_bolt.async_app.AsyncApp", return_value=mock_app), \
         patch("slack_bolt.adapter.socket_mode.async_handler.AsyncSocketModeHandler"):
        # Remove cached module so it's re-imported fresh each time
        sys.modules.pop("bot", None)
        import bot as _bot
        return _bot


@pytest.fixture(scope="module")
def bot_module():
    return _import_bot()


@pytest.fixture
def say():
    return AsyncMock()


@pytest.fixture
def event_factory():
    def _make(text, ts="111.111", thread_ts=None):
        e = {"text": text, "ts": ts, "user": "U123"}
        if thread_ts is not None:
            e["thread_ts"] = thread_ts
        return e
    return _make


@pytest.mark.asyncio
async def test_info_flag_responds_with_help_text(bot_module, say, event_factory):
    """--info returns _INFO_TEXT without calling the LLM."""
    with patch.object(bot_module, "debug_logger", None), \
         patch.object(bot_module.llm, "search_and_summarize", new_callable=AsyncMock) as mock_llm:
        await bot_module.handle_message(event_factory("!gaston --info"), say)

    say.assert_called_once_with(text=bot_module._INFO_TEXT, thread_ts="111.111")
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_info_flag_with_ticker_still_short_circuits(bot_module, say, event_factory):
    """--info takes priority even when a ticker is present."""
    with patch.object(bot_module, "debug_logger", None), \
         patch.object(bot_module.llm, "search_and_summarize", new_callable=AsyncMock) as mock_llm:
        await bot_module.handle_message(event_factory("!gaston AAPL --info"), say)

    say.assert_called_once_with(text=bot_module._INFO_TEXT, thread_ts="111.111")
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_info_flag_uses_thread_ts(bot_module, say, event_factory):
    """--info reply goes into the correct thread."""
    with patch.object(bot_module, "debug_logger", None):
        await bot_module.handle_message(
            event_factory("!gaston --info", ts="aaa.bbb", thread_ts="root.ts"), say
        )

    say.assert_called_once_with(text=bot_module._INFO_TEXT, thread_ts="root.ts")


def test_info_text_does_not_mention_jar_jar(bot_module):
    """The easter-egg --jar-jar flag must not appear in the help text."""
    assert "jar-jar" not in bot_module._INFO_TEXT.lower()
    assert "jar jar" not in bot_module._INFO_TEXT.lower()
