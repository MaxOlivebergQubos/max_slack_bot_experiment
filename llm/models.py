"""Shared data models for the LLM layer."""
from dataclasses import dataclass, field


@dataclass
class Source:
    """A single cited source returned by the LLM."""

    title: str
    url: str
    published_date: str = ""  # e.g. "2025-01-31" or empty if unknown


@dataclass
class NewsResult:
    """The result of a search-and-summarize operation."""

    summary: str
    sources: list[Source] = field(default_factory=list)
