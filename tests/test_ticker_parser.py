"""Unit tests for TickerMessageParser."""
import pytest

from parsing.ticker_parser import TickerMessageParser, TickerQuery


@pytest.fixture
def parser():
    return TickerMessageParser(trigger="!gaston")


def test_extracts_ticker_from_normal_message(parser):
    result = parser.parse("!gaston AAPL is going crazy")
    assert result == TickerQuery(ticker="AAPL", raw_message="AAPL is going crazy")


def test_returns_none_without_trigger(parser):
    assert parser.parse("hello AAPL world") is None


def test_returns_empty_ticker_when_only_stop_words(parser):
    result = parser.parse("!gaston CAN you check THE news?")
    assert result is not None
    assert result.ticker == ""


def test_trigger_is_case_insensitive(parser):
    result = parser.parse("!GASTON TSLA what's happening?")
    assert result is not None
    assert result.ticker == "TSLA"


def test_extracts_ticker_mid_sentence(parser):
    result = parser.parse("!gaston what is happening with NVDA today?")
    assert result is not None
    assert result.ticker == "NVDA"


def test_returns_none_with_no_following_text(parser):
    assert parser.parse("!gaston") is None


def test_handles_extra_whitespace(parser):
    result = parser.parse("!gaston   MSFT   is up today")
    assert result is not None
    assert result.ticker == "MSFT"


def test_custom_trigger_prefix():
    custom_parser = TickerMessageParser(trigger="!stockbot")
    result = custom_parser.parse("!stockbot AMZN news please")
    assert result is not None
    assert result.ticker == "AMZN"


def test_picks_first_valid_ticker_when_multiple_present(parser):
    result = parser.parse("!gaston TSLA and NVDA")
    assert result is not None
    assert result.ticker == "TSLA"


# --- Date extraction tests ---


def test_extracts_date_from_message(parser):
    result = parser.parse("!gaston AAPL 2025-01-31")
    assert result is not None
    assert result.ticker == "AAPL"
    assert result.date == "2025-01-31"


def test_date_is_none_when_not_present(parser):
    result = parser.parse("!gaston AAPL latest news")
    assert result is not None
    assert result.date is None


def test_date_extracted_with_stop_words_only(parser):
    result = parser.parse("!gaston hello 2025-06-15")
    assert result is not None
    assert result.ticker == ""
    assert result.date == "2025-06-15"


def test_extracts_first_date_when_multiple_present(parser):
    result = parser.parse("!gaston TSLA between 2025-01-01 and 2025-03-31")
    assert result is not None
    assert result.ticker == "TSLA"
    assert result.date == "2025-01-01"


# --- International ticker tests ---


def test_extracts_lse_ticker(parser):
    result = parser.parse("!gaston III.L what is happening?")
    assert result is not None
    assert result.ticker == "III.L"


def test_extracts_amsterdam_ticker(parser):
    result = parser.parse("!gaston RDSA.AS news")
    assert result is not None
    assert result.ticker == "RDSA.AS"


def test_extracts_frankfurt_ticker_with_digit(parser):
    result = parser.parse("!gaston VOW3.DE latest news")
    assert result is not None
    assert result.ticker == "VOW3.DE"


def test_extracts_plain_lse_ticker(parser):
    result = parser.parse("!gaston BP.L")
    assert result is not None
    assert result.ticker == "BP.L"


def test_stop_word_with_exchange_suffix_passes(parser):
    """FOR is a stop word, but FOR.L is a valid LSE ticker and should pass."""
    result = parser.parse("!gaston FOR.L")
    assert result is not None
    assert result.ticker == "FOR.L"


def test_plain_stop_word_still_filtered(parser):
    """Plain stop words without exchange suffix are still filtered."""
    result = parser.parse("!gaston FOR THE news")
    assert result is not None
    assert result.ticker == ""
