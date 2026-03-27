"""Unit tests for OpenAIProvider (all mocked — no real API calls)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm.openai_provider import OpenAIProvider
from llm.models import FilteredResponse, LLMDebugInfo, NewsItem, EventItem


def _make_response(output_text=None):
    """Build a mock Responses API response mirroring the real output structure."""
    mock_response = MagicMock()

    if output_text is None:
        mock_response.output = []
        return mock_response

    mock_block = MagicMock()
    mock_block.type = "output_text"
    mock_block.text = output_text

    mock_message = MagicMock()
    mock_message.type = "message"
    mock_message.content = [mock_block]

    mock_response.output = [mock_message]
    return mock_response


def _make_json_response(news=None, events=None):
    """Build a mock response whose text is a valid JSON payload."""
    payload = {
        "news": news or [],
        "events": events or [],
    }
    return _make_response(output_text=json.dumps(payload))


@pytest.fixture
def provider():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        p = OpenAIProvider(api_key="test-key")
    return p


@pytest.mark.asyncio
async def test_parses_json_news_items(provider):
    news = [
        {"date": "2026-03-27", "headline": "AAPL revenue up 8%", "source_url": "https://reuters.com/aapl", "source_name": "Reuters"},
        {"date": "2026-03-27", "headline": "New $100B buyback", "source_url": "https://finance.yahoo.com/aapl", "source_name": "Yahoo Finance"},
    ]
    mock_response = _make_json_response(news=news)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert isinstance(result, FilteredResponse)
    assert isinstance(debug_info, LLMDebugInfo)
    assert len(result.news) == 2
    assert result.news[0].headline == "AAPL revenue up 8%"
    assert result.news[0].source_url == "https://reuters.com/aapl"
    assert result.news[1].source_name == "Yahoo Finance"


@pytest.mark.asyncio
async def test_parses_json_events(provider):
    events = [
        {"date": "2026-04-25", "description": "Q2 2026 earnings call", "source_url": "https://finance.yahoo.com/aapl/events", "source_name": "Yahoo Finance"},
    ]
    mock_response = _make_json_response(events=events)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert len(result.events) == 1
    assert result.events[0].description == "Q2 2026 earnings call"
    assert result.events[0].date == "2026-04-25"


@pytest.mark.asyncio
async def test_fallback_on_empty_response(provider):
    mock_response = _make_response(output_text=None)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("XYZ")

    assert isinstance(result, FilteredResponse)
    assert len(result.news) == 1
    assert "No recent news found for XYZ." in result.news[0].headline
    assert result.events == []


@pytest.mark.asyncio
async def test_fallback_on_invalid_json(provider):
    mock_response = _make_response(output_text="This is not JSON at all.")
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("TSLA")

    assert isinstance(result, FilteredResponse)
    assert "No recent news found for TSLA." in result.news[0].headline
    assert result.filtered_count == 0


@pytest.mark.asyncio
async def test_strips_markdown_code_fences(provider):
    payload = json.dumps({"news": [{"date": "2026-03-27", "headline": "Test", "source_url": "https://reuters.com/t", "source_name": "Reuters"}], "events": []})
    fenced = f"```json\n{payload}\n```"
    mock_response = _make_response(output_text=fenced)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert len(result.news) == 1
    assert result.news[0].headline == "Test"


@pytest.mark.asyncio
async def test_hard_filter_removes_offsite_news_urls(provider):
    """Source URLs from outside allowed domains must be cleared and counted."""
    news = [
        {"date": "2026-03-27", "headline": "Allowed", "source_url": "https://reuters.com/aapl", "source_name": "Reuters"},
        {"date": "2026-03-27", "headline": "Blocked", "source_url": "https://bloomberg.com/aapl", "source_name": "Bloomberg"},
    ]
    mock_response = _make_json_response(news=news)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert result.news[0].source_url == "https://reuters.com/aapl"
    assert result.news[1].source_url == ""  # cleared
    assert result.filtered_count == 1


@pytest.mark.asyncio
async def test_hard_filter_removes_offsite_event_urls(provider):
    """Event URLs from outside allowed domains must be cleared and counted."""
    events = [
        {"date": "2026-04-25", "description": "Earnings", "source_url": "https://cnbc.com/events", "source_name": "CNBC"},
    ]
    mock_response = _make_json_response(events=events)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert result.events[0].source_url == ""
    assert result.filtered_count == 1


@pytest.mark.asyncio
async def test_empty_source_url_not_counted_as_filtered(provider):
    """An empty source_url in the LLM response should not increment filtered_count."""
    news = [
        {"date": "2026-03-27", "headline": "No link available", "source_url": "", "source_name": "Reuters"},
    ]
    mock_response = _make_json_response(news=news)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert result.filtered_count == 0


@pytest.mark.asyncio
async def test_latest_prompt_used_when_no_date(provider):
    """When date=None, the prompt should contain today's date."""
    from datetime import date as _date
    mock_response = _make_json_response(news=[{"date": "2026-03-27", "headline": "Up 5%", "source_url": "", "source_name": "Reuters"}])
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    await provider.search_and_summarize("AAPL")

    call_kwargs = provider._client.responses.create.call_args.kwargs
    assert _date.today().isoformat() in call_kwargs["input"]


@pytest.mark.asyncio
async def test_date_prompt_used_when_date_provided(provider):
    """When date is provided, the prompt should reference that specific date."""
    mock_response = _make_json_response(news=[{"date": "2025-01-31", "headline": "News", "source_url": "", "source_name": "Reuters"}])
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    await provider.search_and_summarize("AAPL", date="2025-01-31")

    call_kwargs = provider._client.responses.create.call_args.kwargs
    assert "2025-01-31" in call_kwargs["input"]
    assert "latest" not in call_kwargs["input"].lower()


@pytest.mark.asyncio
async def test_debug_info_contains_prompts_and_raw_response(provider):
    """LLMDebugInfo must carry the system prompt, input prompt, and raw text."""
    payload = json.dumps({"news": [], "events": []})
    mock_response = _make_response(output_text=payload)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL")

    assert isinstance(debug_info, LLMDebugInfo)
    assert len(debug_info.system_prompt) > 0
    assert "AAPL" in debug_info.input_prompt
    assert debug_info.raw_response_text == payload


# --- Domain-filter helper tests ---


def test_is_allowed_source_accepts_allowed_domains():
    from llm.openai_provider import _is_allowed_source
    from config import ALLOWED_SOURCES

    for source in ALLOWED_SOURCES:
        assert _is_allowed_source(f"https://{source.domain}/article/test") is True


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


# --- Flag behaviour tests ---


@pytest.mark.asyncio
async def test_no_filter_keeps_offsite_urls(provider):
    """With no_filter=True, URLs from outside allowed domains are kept as-is."""
    news = [
        {"date": "2026-03-27", "headline": "Allowed", "source_url": "https://reuters.com/aapl", "source_name": "Reuters"},
        {"date": "2026-03-27", "headline": "Blocked normally", "source_url": "https://bloomberg.com/aapl", "source_name": "Bloomberg"},
    ]
    mock_response = _make_json_response(news=news)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL", no_filter=True)

    assert result.news[0].source_url == "https://reuters.com/aapl"
    assert result.news[1].source_url == "https://bloomberg.com/aapl"  # kept
    assert result.filtered_count == 0


@pytest.mark.asyncio
async def test_jar_jar_flag_adds_style_to_system_prompt(provider):
    """With jar_jar=True, the system prompt should contain Jar Jar style instructions."""
    mock_response = _make_json_response(news=[])
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL", jar_jar=True)

    assert "Jar Jar" in debug_info.system_prompt


@pytest.mark.asyncio
async def test_jar_jar_false_no_style_in_prompt(provider):
    """Without jar_jar flag, the system prompt should NOT contain Jar Jar style."""
    mock_response = _make_json_response(news=[])
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL", jar_jar=False)

    assert "Jar Jar" not in debug_info.system_prompt


@pytest.mark.asyncio
async def test_no_filter_false_still_filters(provider):
    """With no_filter=False (default), offsite URLs are still filtered out."""
    news = [
        {"date": "2026-03-27", "headline": "Blocked", "source_url": "https://bloomberg.com/aapl", "source_name": "Bloomberg"},
    ]
    mock_response = _make_json_response(news=news)
    provider._client.responses.create = AsyncMock(return_value=mock_response)

    result, debug_info = await provider.search_and_summarize("AAPL", no_filter=False)

    assert result.news[0].source_url == ""
    assert result.filtered_count == 1
