"""Debug logger that posts step-by-step traces to a Slack log channel."""
import json
import logging

from slack_bolt.async_app import AsyncApp

from llm.models import FilteredResponse

logger = logging.getLogger(__name__)

_TRUNCATE_LIMIT = 3000
_TRUNCATE_SUFFIX = "... (truncated)"


def _truncate(text: str, limit: int = _TRUNCATE_LIMIT) -> str:
    """Truncate *text* to *limit* characters, appending a suffix if cut."""
    if len(text) <= limit:
        return text
    return text[:limit] + _TRUNCATE_SUFFIX


class SlackDebugLogger:
    """Posts step-by-step debug traces to a Slack log channel."""

    def __init__(self, app: AsyncApp, channel: str) -> None:
        """
        Args:
            app: The Slack Bolt AsyncApp instance (used for posting).
            channel: Channel ID (starting with ``C``) or name (e.g. ``#gaston-log``).
        """
        self._app = app
        self._channel_input = channel
        self._channel_id: str | None = None

    async def _resolve_channel(self) -> str | None:
        """Return the channel ID, resolving a name to an ID on first use."""
        if self._channel_id is not None:
            return self._channel_id

        channel = self._channel_input.lstrip("#")

        # If it already looks like a Slack channel ID, use it directly.
        if channel.startswith("C") and channel == channel.upper():
            self._channel_id = channel
            return self._channel_id

        # Otherwise look it up via conversations_list.
        try:
            cursor = None
            while True:
                kwargs: dict = {"limit": 200}
                if cursor:
                    kwargs["cursor"] = cursor
                resp = await self._app.client.conversations_list(**kwargs)
                for ch in resp.get("channels", []):
                    if ch.get("name") == channel:
                        self._channel_id = ch["id"]
                        return self._channel_id
                cursor = resp.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
        except Exception as exc:
            logger.warning("slack_debug_logger: could not resolve channel %r: %s", self._channel_input, exc)

        return None

    async def start_trace(self, user_id: str, raw_text: str) -> str | None:
        """Post the header message and return the thread_ts for follow-up replies.

        Returns ``None`` if logging is disabled or the post fails.
        """
        channel_id = await self._resolve_channel()
        if channel_id is None:
            return None

        try:
            resp = await self._app.client.chat_postMessage(
                channel=channel_id,
                text=f"🔍 User <@{user_id}> invoked Gaston: `{raw_text}`",
            )
            return resp["ts"]
        except Exception as exc:
            logger.warning("slack_debug_logger: failed to start trace: %s", exc)
            return None

    async def log_step(self, thread_ts: str | None, text: str) -> None:
        """Post a single debug step as a reply in the trace thread."""
        if thread_ts is None:
            return
        channel_id = await self._resolve_channel()
        if channel_id is None:
            return
        try:
            await self._app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=text,
            )
        except Exception as exc:
            logger.warning("slack_debug_logger: failed to post step: %s", exc)

    async def log_parsed_query(
        self,
        thread_ts: str | None,
        ticker: str,
        date: str | None,
        raw_message: str,
    ) -> None:
        await self.log_step(
            thread_ts,
            f"📋 *Parsed query:*\nTicker: {ticker}\nDate: {date}\nRaw message: {raw_message}",
        )

    async def log_system_prompt(self, thread_ts: str | None, system_prompt: str) -> None:
        await self.log_step(
            thread_ts,
            f"🤖 *System prompt sent to OpenAI:*\n```{_truncate(system_prompt)}```",
        )

    async def log_input_prompt(self, thread_ts: str | None, input_prompt: str) -> None:
        await self.log_step(
            thread_ts,
            f"📝 *Input prompt sent to OpenAI:*\n```{_truncate(input_prompt)}```",
        )

    async def log_raw_response(self, thread_ts: str | None, raw_text: str) -> None:
        await self.log_step(
            thread_ts,
            f"📨 *Raw LLM response text:*\n```{_truncate(raw_text)}```",
        )

    async def log_filtered_result(self, thread_ts: str | None, result: FilteredResponse) -> None:
        json_dump = json.dumps(
            {
                "news": [vars(item) for item in result.news],
                "events": [vars(item) for item in result.events],
                "filtered_count": result.filtered_count,
            },
            indent=2,
        )
        await self.log_step(
            thread_ts,
            f"✅ *Parsed & filtered result:*\n```{_truncate(json_dump)}```",
        )

    async def log_final_message(self, thread_ts: str | None, message: str) -> None:
        await self.log_step(
            thread_ts,
            f"💬 *Final message sent to user:*\n```{_truncate(message)}```",
        )

    async def log_error(self, thread_ts: str | None, error: Exception) -> None:
        await self.log_step(
            thread_ts,
            f"❌ *Error:* `{error}`",
        )
