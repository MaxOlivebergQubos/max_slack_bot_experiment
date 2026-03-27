"""Central configuration for the Gaston bot.

This module is the single source of truth for the list of allowed news sources.
All other modules should import from here rather than hard-coding domain names
or display names.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AllowedSource:
    domain: str        # e.g. "reuters.com"  — used for URL filtering
    display_name: str  # e.g. "Reuters"      — used in prompts and help text


ALLOWED_SOURCES: tuple[AllowedSource, ...] = (
    AllowedSource(domain="reuters.com", display_name="Reuters"),
    AllowedSource(domain="finance.yahoo.com", display_name="Yahoo Finance"),
    AllowedSource(domain="investing.com", display_name="Investing.com"),
    AllowedSource(domain="marketwatch.com", display_name="MarketWatch"),
)


def allowed_domains() -> frozenset[str]:
    """Return the set of allowed domains for URL filtering."""
    return frozenset(s.domain for s in ALLOWED_SOURCES)


def source_names_str() -> str:
    """Return a comma-separated list of display names, e.g. 'Reuters, Yahoo Finance, ...'."""
    return ", ".join(s.display_name for s in ALLOWED_SOURCES)


def domains_str() -> str:
    """Return a comma-and-'and'-separated domain list for prompt text.

    Example: 'reuters.com, finance.yahoo.com, investing.com, and marketwatch.com'
    """
    domains = [s.domain for s in ALLOWED_SOURCES]
    if len(domains) <= 1:
        return domains[0] if domains else ""
    return ", ".join(domains[:-1]) + ", and " + domains[-1]
