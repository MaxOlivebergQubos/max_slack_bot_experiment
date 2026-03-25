"""Unit tests for TickerMessageParser."""
import pytest

from parsing.ticker_parser import TickerMessageParser, TickerQuery


@pytest.fixture
def parser():
    return TickerMessageParser(trigger="!maxbot")


def test_extracts_ticker_from_normal_message(parser):
    result = parser.parse("!maxbot AAPL is going crazy")
    assert result == TickerQuery(ticker="AAPL", raw_message="AAPL is going crazy")


def test_returns_none_without_trigger(parser):
    assert parser.parse("hello AAPL world") is None


def test_returns_none_when_only_stop_words(parser):
    result = parser.parse("!maxbot CAN you check THE news?")
    assert result is None


def test_trigger_is_case_insensitive(parser):
    result = parser.parse("!MAXBOT TSLA what's happening?")
    assert result is not None
    assert result.ticker == "TSLA"


def test_extracts_ticker_mid_sentence(parser):
    result = parser.parse("!maxbot what is happening with NVDA today?")
    assert result is not None
    assert result.ticker == "NVDA"


def test_returns_none_with_no_following_text(parser):
    assert parser.parse("!maxbot") is None


def test_handles_extra_whitespace(parser):
    result = parser.parse("!maxbot   MSFT   is up today")
    assert result is not None
    assert result.ticker == "MSFT"


def test_custom_trigger_prefix():
    custom_parser = TickerMessageParser(trigger="!stockbot")
    result = custom_parser.parse("!stockbot AMZN news please")
    assert result is not None
    assert result.ticker == "AMZN"


def test_picks_first_valid_ticker_when_multiple_present(parser):
    result = parser.parse("!maxbot TSLA and NVDA")
    assert result is not None
    assert result.ticker == "TSLA"
