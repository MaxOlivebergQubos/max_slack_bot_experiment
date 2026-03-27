"""Unit tests for SlackFormatter."""
from formatting.slack_formatter import SlackFormatter
from llm.models import FilteredResponse, NewsItem, EventItem


def test_formats_news_items_with_links():
    formatter = SlackFormatter()
    result = FilteredResponse(
        news=[
            NewsItem(date="2026-03-27", headline="Revenue up 8% YoY", source_url="https://reuters.com/apple", source_name="Reuters"),
            NewsItem(date="2026-03-27", headline="New buyback announced", source_url="https://finance.yahoo.com/aapl", source_name="Yahoo Finance"),
        ],
        events=[],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "📈 *AAPL — News Summary*" in msg
    assert "[2026-03-27] Revenue up 8% YoY" in msg
    assert "(<https://reuters.com/apple|Reuters>)" in msg
    assert "(<https://finance.yahoo.com/aapl|Yahoo Finance>)" in msg


def test_formats_news_item_without_link():
    formatter = SlackFormatter()
    result = FilteredResponse(
        news=[NewsItem(date="2026-03-27", headline="No link available", source_url="", source_name="Reuters")],
        events=[],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "• [2026-03-27] No link available" in msg
    assert "(<" not in msg


def test_no_news_shows_placeholder():
    formatter = SlackFormatter()
    result = FilteredResponse(news=[], events=[])
    msg = formatter.format(result, ticker="XYZ")

    assert "_No recent news found for XYZ._" in msg


def test_formats_events_with_links():
    formatter = SlackFormatter()
    result = FilteredResponse(
        news=[],
        events=[EventItem(date="2026-04-25", description="Q1 2026 earnings call", source_url="https://finance.yahoo.com/events", source_name="Yahoo Finance")],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "*Upcoming Events:*" in msg
    assert "📅 [2026-04-25] Q1 2026 earnings call" in msg
    assert "(<https://finance.yahoo.com/events|Yahoo Finance>)" in msg


def test_formats_event_without_link():
    formatter = SlackFormatter()
    result = FilteredResponse(
        news=[],
        events=[EventItem(date="2026-04-25", description="Investor Day", source_url="", source_name="Reuters")],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "📅 [2026-04-25] Investor Day" in msg
    assert "(<" not in msg


def test_no_events_shows_placeholder():
    formatter = SlackFormatter()
    result = FilteredResponse(news=[], events=[])
    msg = formatter.format(result, ticker="AAPL")

    assert "📅 _No relevant upcoming events found for AAPL._" in msg


def test_filtered_count_note_shown_when_nonzero():
    formatter = SlackFormatter()
    result = FilteredResponse(news=[], events=[], filtered_count=3)
    msg = formatter.format(result, ticker="AAPL")

    assert "_ℹ️ 3 link(s) from non-approved sources were filtered out._" in msg


def test_filtered_count_note_hidden_when_zero():
    formatter = SlackFormatter()
    result = FilteredResponse(news=[], events=[], filtered_count=0)
    msg = formatter.format(result, ticker="AAPL")

    assert "filtered out" not in msg


def test_formats_with_no_ticker():
    formatter = SlackFormatter()
    result = FilteredResponse(news=[], events=[])
    msg = formatter.format(result)

    assert "📈 *News Summary*" in msg


def test_news_item_without_date_omits_date_prefix():
    formatter = SlackFormatter()
    result = FilteredResponse(
        news=[NewsItem(date="", headline="Some news", source_url="", source_name="Reuters")],
        events=[],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "• Some news" in msg
    assert "[]" not in msg
