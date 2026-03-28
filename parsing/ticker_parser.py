"""Ticker-aware message parser for the gaston stock-news bot."""
import os
import re
from dataclasses import dataclass

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

# Matches tickers: 1-5 uppercase letters/digits (starting with a letter),
# optionally followed by a dot and 1-4 uppercase letters (exchange suffix),
# e.g. AAPL, VOW3, III.L, RDSA.AS, VOW3.DE
_TICKER_RE = re.compile(r"\b([A-Z][A-Z0-9]{0,4}(?:\.[A-Z]{1,4})?)\b")
_FLAG_NO_FILTER = re.compile(r"--no-filter", re.IGNORECASE)
_FLAG_JAR_JAR = re.compile(r"--jar-jar", re.IGNORECASE)
_FLAG_INFO = re.compile(r"--info", re.IGNORECASE)
_FLAG_VERBOSE = re.compile(r"--verbose", re.IGNORECASE)
_FLAG_WEBSITES = re.compile(r"--websites\s*\[([^\]]*)\]", re.IGNORECASE)
_FLAG_PLUS_WEBSITES = re.compile(r"--plus-websites\s*\[([^\]]*)\]", re.IGNORECASE)

# Matches YYYY-MM-DD date patterns
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


@dataclass
class TickerQuery:
    """Result of parsing a ticker-bot message."""

    ticker: str
    raw_message: str
    date: str | None = None  # e.g. "2025-01-31", None means "latest"
    no_filter: bool = False
    jar_jar: bool = False
    info: bool = False
    verbose: bool = False
    websites: list[str] | None = None
    plus_websites: list[str] | None = None


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

        no_filter = bool(_FLAG_NO_FILTER.search(raw_message))
        jar_jar = bool(_FLAG_JAR_JAR.search(raw_message))
        info = bool(_FLAG_INFO.search(raw_message))
        verbose = bool(_FLAG_VERBOSE.search(raw_message))

        websites_match = _FLAG_WEBSITES.search(raw_message)
        websites = (
            [d.strip() for d in websites_match.group(1).split(",") if d.strip()]
            if websites_match else None
        )

        plus_websites_match = _FLAG_PLUS_WEBSITES.search(raw_message)
        plus_websites = (
            [d.strip() for d in plus_websites_match.group(1).split(",") if d.strip()]
            if plus_websites_match else None
        )

        # Strip flags before ticker/date extraction so they don't interfere
        clean_message = _FLAG_NO_FILTER.sub("", raw_message)
        clean_message = _FLAG_JAR_JAR.sub("", clean_message)
        clean_message = _FLAG_INFO.sub("", clean_message)
        clean_message = _FLAG_VERBOSE.sub("", clean_message)
        clean_message = _FLAG_WEBSITES.sub("", clean_message)
        clean_message = _FLAG_PLUS_WEBSITES.sub("", clean_message)
        clean_message = clean_message.strip()

        ticker = self._extract_ticker(clean_message)

        date_match = _DATE_RE.search(clean_message)
        date = date_match.group(1) if date_match else None

        if ticker is None:
            return TickerQuery(ticker="", raw_message=raw_message, date=date,
                               no_filter=no_filter, jar_jar=jar_jar, info=info,
                               verbose=verbose, websites=websites, plus_websites=plus_websites)

        return TickerQuery(ticker=ticker, raw_message=raw_message, date=date,
                           no_filter=no_filter, jar_jar=jar_jar, info=info,
                           verbose=verbose, websites=websites, plus_websites=plus_websites)

    @staticmethod
    def _extract_ticker(text: str) -> str | None:
        """Return the first word that looks like a ticker symbol."""
        for candidate in _TICKER_RE.findall(text):
            # Only filter stop words for plain tickers (no exchange suffix)
            if "." not in candidate and candidate in _STOP_WORDS:
                continue
            return candidate
        return None
