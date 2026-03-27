"""Shared data models for the LLM layer."""
from dataclasses import dataclass, field


@dataclass
class NewsItem:
    """A single news bullet from the LLM response."""
    date: str            # e.g. "2026-03-27"
    headline: str        # Short headline-style summary
    source_url: str      # Full URL to the article
    source_name: str     # e.g. "Reuters", "Yahoo Finance"


@dataclass
class EventItem:
    """A single upcoming/recent event from the LLM response."""
    date: str            # e.g. "2026-04-24"
    description: str     # e.g. "Q1 2026 earnings call"
    source_url: str      # URL or empty string
    source_name: str     # e.g. "Yahoo Finance"


@dataclass
class FilteredResponse:
    """The final structured result after parsing + filtering the LLM JSON."""
    news: list[NewsItem] = field(default_factory=list)
    events: list[EventItem] = field(default_factory=list)
    filtered_count: int = 0  # How many items were removed by domain filter
