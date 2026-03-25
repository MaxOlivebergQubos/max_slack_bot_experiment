"""Unit tests for SlackFormatter."""
from formatting.slack_formatter import SlackFormatter
from llm.models import NewsResult, Source


def test_formats_result_with_summary_and_sources():
    formatter = SlackFormatter()
    result = NewsResult(
        summary="• Revenue up 8% YoY\n• New buyback announced",
        sources=[
            Source(title="Reuters: Apple Q1", url="https://reuters.com/apple"),
            Source(title="Yahoo: Apple news", url="https://yahoo.com/apple"),
        ],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "📈 *AAPL — News Summary*" in msg
    assert "Revenue up 8% YoY" in msg
    assert "*Sources:*" in msg
    assert "<https://reuters.com/apple|Reuters: Apple Q1>" in msg
    assert "<https://yahoo.com/apple|Yahoo: Apple news>" in msg


def test_formats_result_with_no_sources():
    formatter = SlackFormatter()
    result = NewsResult(summary="No recent news found for XYZ.", sources=[])
    msg = formatter.format(result, ticker="XYZ")

    assert "📈 *XYZ — News Summary*" in msg
    assert "No recent news found for XYZ." in msg
    assert "*Sources:*" not in msg


def test_formats_with_no_ticker():
    formatter = SlackFormatter()
    result = NewsResult(summary="Some summary", sources=[])
    msg = formatter.format(result)

    assert "📈 *News Summary*" in msg
    assert "Some summary" in msg


def test_formats_empty_summary_no_sources():
    formatter = SlackFormatter()
    result = NewsResult(summary="", sources=[])
    msg = formatter.format(result, ticker="AAPL")

    assert "📈 *AAPL — News Summary*" in msg
    assert "*Sources:*" not in msg


def test_slack_link_format_in_output():
    formatter = SlackFormatter()
    result = NewsResult(
        summary="Brief summary.",
        sources=[Source(title="My Title", url="https://example.com/article")],
    )
    msg = formatter.format(result, ticker="AAPL")

    assert "<https://example.com/article|My Title>" in msg
