"""Unit tests for OpenAIProvider (all mocked — no real API calls)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm.openai_provider import OpenAIProvider


def _make_response(output_text=None, annotations=None):
    """Build a mock Responses API response mirroring the real output structure."""
    mock_response = MagicMock()

    if output_text is None:
        mock_response.output = []
        return mock_response

    mock_block = MagicMock()
    mock_block.type = "output_text"
    mock_block.text = output_text
    mock_block.annotations = annotations or []

    mock_message = MagicMock()
    mock_message.type = "message"
    mock_message.content = [mock_block]

    mock_response.output = [mock_message]
    return mock_response


def _make_annotation(title, url):
    ann = MagicMock()
    ann.type = "url_citation"
    ann.title = title
    ann.url = url
    return ann


@pytest.fixture
def provider():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        p = OpenAIProvider(api_key="test-key")
    return p


@pytest.mark.asyncio
async def test_parses_response_with_output_text_and_annotations(provider):
    annotation = _make_annotation("Reuters: AAPL earnings", "https://reuters.com/aapl")
    mock_response = _make_response(
        output_text="• AAPL revenue up 8%\n• New $100B buyback",
        annotations=[annotation],
    )
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result = await provider.search_and_summarize("AAPL")

    assert "revenue up 8%" in result.summary
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://reuters.com/aapl"
    assert result.sources[0].title == "Reuters: AAPL earnings"


@pytest.mark.asyncio
async def test_fallback_summary_on_empty_response(provider):
    mock_response = _make_response(output_text=None)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result = await provider.search_and_summarize("XYZ")

    assert "No recent news found for XYZ." in result.summary
    assert result.sources == []


@pytest.mark.asyncio
async def test_sources_empty_when_no_annotations(provider):
    mock_response = _make_response(
        output_text="Some summary text.", annotations=[]
    )
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result = await provider.search_and_summarize("TSLA")

    assert result.summary == "Some summary text."
    assert result.sources == []


@pytest.mark.asyncio
async def test_captures_multiple_annotations(provider):
    annotations = [
        _make_annotation("Reuters article", "https://reuters.com/1"),
        _make_annotation("Yahoo article", "https://finance.yahoo.com/2"),
        _make_annotation("Investing article", "https://investing.com/3"),
    ]
    mock_response = _make_response(
        output_text="• Up 5%\n• New product launch",
        annotations=annotations,
    )
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result = await provider.search_and_summarize("NVDA")

    assert len(result.sources) == 3
    assert result.sources[0].url == "https://reuters.com/1"
    assert result.sources[1].url == "https://finance.yahoo.com/2"
    assert result.sources[2].url == "https://investing.com/3"


@pytest.mark.asyncio
async def test_latest_prompt_used_when_no_date(provider):
    """When date=None, the prompt should ask for the latest news."""
    mock_response = _make_response(output_text="• AAPL up 5%")
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    await provider.search_and_summarize("AAPL")

    call_kwargs = provider._client.responses.create.call_args.kwargs
    assert "latest" in call_kwargs["input"].lower()


@pytest.mark.asyncio
async def test_date_prompt_used_when_date_provided(provider):
    """When date is provided, the prompt should reference that specific date."""
    mock_response = _make_response(output_text="• AAPL news from Jan 31")
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    await provider.search_and_summarize("AAPL", date="2025-01-31")

    call_kwargs = provider._client.responses.create.call_args.kwargs
    assert "2025-01-31" in call_kwargs["input"]
    assert "latest" not in call_kwargs["input"].lower()


# --- Domain-filter tests ---


def test_is_allowed_source_accepts_allowed_domains():
    from llm.openai_provider import _is_allowed_source

    assert _is_allowed_source("https://reuters.com/article/aapl") is True
    assert _is_allowed_source("https://finance.yahoo.com/quote/AAPL") is True
    assert _is_allowed_source("https://investing.com/equities/apple") is True
    assert _is_allowed_source("https://marketwatch.com/story/aapl") is True


def test_is_allowed_source_accepts_subdomains():
    from llm.openai_provider import _is_allowed_source

    assert _is_allowed_source("https://www.reuters.com/article/aapl") is True
    assert _is_allowed_source("https://uk.investing.com/equities/bp") is True


def test_is_allowed_source_rejects_disallowed_domains():
    from llm.openai_provider import _is_allowed_source

    assert _is_allowed_source("https://bloomberg.com/news/aapl") is False
    assert _is_allowed_source("https://yahoo.com/news/aapl") is False
    assert _is_allowed_source("https://cnbc.com/2026/03/26/aapl") is False


def test_is_allowed_source_handles_invalid_url():
    from llm.openai_provider import _is_allowed_source

    assert _is_allowed_source("not-a-url") is False
    assert _is_allowed_source("") is False


@pytest.mark.asyncio
async def test_hard_filter_removes_offsite_sources(provider):
    """Sources from outside allowed domains must be filtered out."""
    annotations = [
        _make_annotation("Reuters article", "https://reuters.com/aapl"),
        _make_annotation("Bloomberg article", "https://bloomberg.com/aapl"),
        _make_annotation("MarketWatch article", "https://marketwatch.com/aapl"),
    ]
    mock_response = _make_response(
        output_text="• AAPL up 5%",
        annotations=annotations,
    )
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result = await provider.search_and_summarize("AAPL")

    urls = [s.url for s in result.sources]
    assert "https://reuters.com/aapl" in urls
    assert "https://marketwatch.com/aapl" in urls
    assert "https://bloomberg.com/aapl" not in urls
    assert len(result.sources) == 2
