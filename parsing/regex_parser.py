import os
import re

from parsing.base import BaseMessageParser

_DEFAULT_TRIGGER = "!maxbot"


class RegexMessageParser(BaseMessageParser):
    """Message parser that matches ``!maxbot <query>`` (case-insensitive).

    The trigger prefix is configurable via the constructor or the
    ``BOT_TRIGGER`` environment variable.
    """

    def __init__(self, trigger: str | None = None) -> None:
        prefix = trigger or os.environ.get("BOT_TRIGGER", _DEFAULT_TRIGGER)
        escaped = re.escape(prefix)
        self._pattern = re.compile(rf"^{escaped}\s+(.+)", re.IGNORECASE | re.DOTALL)

    def parse(self, text: str) -> str | None:
        match = self._pattern.match(text.strip())
        if match:
            return match.group(1).strip()
        return None
