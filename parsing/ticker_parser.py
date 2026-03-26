"""Ticker-aware message parser for the gaston stock-news bot."""
import os
import re
from dataclasses import dataclass, field

from parsing.base import BaseMessageParser

_DEFAULT_TRIGGER = "!gaston"

# Common English words (all-caps) that are NOT stock tickers
_STOP_WORDS = frozenset(
    {
        "A", "I", "AM", "AN", "AS", "AT", "BE", "BY", "DO",
        "GO", "IF", "IN", "IS", "IT", "ME", "MY", "NO", "OF",
        "ON", "OR", "SO", "TO", "UP", "US", "WE",
        "AND", "ARE", "CAN", "FOR", "GET", "GOT", "HAS", "HAD",
        "HIM", "HIS", "HOW", "ITS", "LET", "MAY", "NEW", "NOT",
        "NOW", "OLD", "OUR", "OUT", "OWN", "SAY", "SHE", "THE",
        "TOO", "TWO", "WAS", "WHO", "WHY", "YET", "YOU",
        "ABLE", "ALSO", "BEEN", "BOTH", "COME", "DOES", "EACH",
        "EVEN", "FROM", "GIVE", "GOOD", "HAVE", "HERE", "INTO",
        "JUST", "KNOW", "LIKE", "LOOK", "MADE", "MAKE", "MANY",
        "MORE", "MOST", "MUCH", "NEED", "ONLY", "OVER", "SAID",
        "SAME", "SEEM", "SOME", "SUCH", "TAKE", "THAN", "THAT",
        "THEM", "THEN", "THEY", "THIS", "TIME", "TOOK", "UPON",
        "VERY", "WANT", "WELL", "WERE", "WHAT", "WHEN", "WITH",
        "WILL", "YOUR",
        "ABOUT", "AFTER", "AGAIN", "BEING", "COULD", "DOING",
        "EVERY", "GOING", "GREAT", "HELLO", "MAYBE", "MIGHT",
        "NEVER", "OTHER", "QUITE", "READY", "THEIR", "THERE",
        "THESE", "THOSE", "THREE", "TODAY", "UNDER", "UNTIL",
        "USING", "WHICH", "WHILE", "WOULD",
        "NEWS", "STOCK", "CHECK", "CRAZY",
    }
)

# Matches 1-5 uppercase ASCII letters surrounded by word boundaries
_TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")

# Matches YYYY-MM-DD date patterns
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


@dataclass
class TickerQuery:
    """Result of parsing a ticker-bot message."""

    ticker: str
    raw_message: str
    date: str | None = None  # e.g. "2025-01-31", None means "latest"


class TickerMessageParser(BaseMessageParser[TickerQuery]):
    """Message parser that extracts a stock ticker from a ``!gaston`` message.

    Triggers on ``!gaston <any text>``, then scans the text for the first
    1–5 uppercase letter sequence that does not look like a common English
    word.  Returns a :class:`TickerQuery` containing the identified ticker
    and the original message body, or ``None`` if no trigger / ticker is found.

    The trigger prefix is configurable via the ``trigger`` constructor
    argument or the ``BOT_TRIGGER`` environment variable.
    """

    def __init__(self, trigger: str | None = None) -> None:
        prefix = trigger or os.environ.get("BOT_TRIGGER", _DEFAULT_TRIGGER)
        escaped = re.escape(prefix)
        self._trigger_pattern = re.compile(
            rf"^{escaped}\s+(.+)", re.IGNORECASE | re.DOTALL
        )

    def parse(self, text: str) -> TickerQuery | None:
        match = self._trigger_pattern.match(text.strip())
        if not match:
            return None

        raw_message = match.group(1).strip()
        ticker = self._extract_ticker(raw_message)

        date_match = _DATE_RE.search(raw_message)
        date = date_match.group(1) if date_match else None

        if ticker is None:
            return TickerQuery(ticker="", raw_message=raw_message, date=date)

        return TickerQuery(ticker=ticker, raw_message=raw_message, date=date)

    @staticmethod
    def _extract_ticker(text: str) -> str | None:
        """Return the first uppercase word that looks like a ticker symbol."""
        for candidate in _TICKER_RE.findall(text):
            if candidate not in _STOP_WORDS:
                return candidate
        return None
