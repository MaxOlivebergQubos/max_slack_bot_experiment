"""Prompt building blocks for the LLM layer.

Each constant is a self-contained piece of the system prompt or user prompt.
Edit any block independently without touching the others.
"""

from config import domains_str, domains_str_from

# -- System prompt building blocks ------------------------------------------

ROLE = (
    "You are a financial news summarizer bot."
)

SEARCH_SITES = (
    f"Search {domains_str()} "
    "for news about the given stock ticker."
)

EVENTS_INSTRUCTION = (
    "Also search for upcoming events (earnings, ex-dividend dates, shareholder meetings)."
)

JSON_SCHEMA = (
    "You MUST respond with ONLY a JSON object — no markdown, no commentary, no extra text. "
    "The JSON must match this exact schema:\n"
    "{\n"
    '  "news": [\n'
    '    {"date": "YYYY-MM-DD", "headline": "short headline", '
    '"source_url": "https://...", "source_name": "Reuters"}\n'
    "  ],\n"
    '  "events": [\n'
    '    {"date": "YYYY-MM-DD", "description": "event description", '
    '"source_url": "https://...", "source_name": "Yahoo Finance"}\n'
    "  ]\n"
    "}"
)

JSON_RULES = (
    "Rules:\n"
    "- news: 2-3 items max. Each headline should be Bloomberg-terminal terse.\n"
    "- events: 0-2 items. Include earnings dates, ex-dividend dates, investor days, etc.\n"
    "- date: Always YYYY-MM-DD format.\n"
    f"- source_url: MUST be from {domains_str()} ONLY.\n"
    "- source_name: Human-readable site name.\n"
    "- If no news found, set news to an empty array [].\n"
    "- If no events found, set events to an empty array [].\n"
    "- Do NOT include any text outside the JSON object."
)

RECENCY_RULE = (
    "Only include news from the date specified in the query, or within 1-2 days of it."
)

JAR_JAR_STYLE = (
    "Reformulate the following paragraph as if you are Jar Jar Binks from Star Wars, "
    "but ALSO you are a degenerate r/WallStreetBets retail trader who is EXTREMELY "
    "bullish on everything. You love diamond hands 💎🙌, rockets 🚀🚀🚀, tendies 🍗, "
    "and calling everything a YOLO play. You think every stock is going to the moon. "
    "Bears are always wrong. Every dip is a buying opportunity. "
    "Use Jar Jar's speech patterns and vocabulary "
    "(e.g., 'meesa', 'yousa', 'muy muy', 'bombad', 'okeday') "
    "mixed with WSB slang (e.g., 'diamond hands', 'to the moon', 'tendies', "
    "'smooth brain', 'ape strong together', 'wife\\'s boyfriend', 'HODL', "
    "'this is not financial advice', 'sir this is a Wendy\\'s', 'buy the dip'). "
    "Sprinkle in rocket emojis 🚀 and diamond emojis 💎 liberally. "
    "The factual financial content MUST remain accurate — do NOT change any numbers, "
    "dates, company names, or events — but the tone should be unhinged optimism "
    "filtered through Jar Jar's mangled grammar. "
    "Keep it as a single paragraph.\n\n"
    "Original:\n{text}"
)

JAR_JAR_JSON_RULES = (
    "Rules:\n"
    "- news: 2-3 items max. Each headline should be a full paragraph summarising the article in detail.\n"
    "- events: 0-2 items. Include earnings dates, ex-dividend dates, investor days, etc.\n"
    "- date: Always YYYY-MM-DD format.\n"
    f"- source_url: MUST be from {domains_str()} ONLY.\n"
    "- source_name: Human-readable site name.\n"
    "- If no news found, set news to an empty array [].\n"
    "- If no events found, set events to an empty array [].\n"
    "- Do NOT include any text outside the JSON object."
)

# -- Helpers to compose the full system instruction -------------------------

SYSTEM_INSTRUCTION = "\n\n".join([
    ROLE,
    SEARCH_SITES,
    EVENTS_INSTRUCTION,
    JSON_SCHEMA,
    JSON_RULES,
    RECENCY_RULE,
])


def _build_json_rules(news_description: str, effective_domains: str) -> str:
    """Build the JSON rules block with the given news headline description and domains."""
    return (
        "Rules:\n"
        f"- news: 2-3 items max. Each headline should be {news_description}.\n"
        "- events: 0-2 items. Include earnings dates, ex-dividend dates, investor days, etc.\n"
        "- date: Always YYYY-MM-DD format.\n"
        f"- source_url: MUST be from {effective_domains} ONLY.\n"
        "- source_name: Human-readable site name.\n"
        "- If no news found, set news to an empty array [].\n"
        "- If no events found, set events to an empty array [].\n"
        "- Do NOT include any text outside the JSON object."
    )


def build_system_instruction(
    jar_jar: bool = False, domains: frozenset[str] | None = None,
    verbose: bool = False,
) -> str:
    """Compose the full system instruction, optionally with verbose or custom domains."""
    effective_domains = domains_str_from(domains) if domains is not None else domains_str()
    search_sites = (
        f"Search {effective_domains} "
        "for news about the given stock ticker."
    )
    news_description = (
        "a full paragraph summarising the article in detail" if (verbose or jar_jar)
        else "Bloomberg-terminal terse"
    )
    json_rules = _build_json_rules(news_description, effective_domains)
    parts = [ROLE, search_sites, EVENTS_INSTRUCTION, JSON_SCHEMA, json_rules, RECENCY_RULE]
    return "\n\n".join(parts)


def build_input_prompt(ticker: str, date: str, domains: frozenset[str] | None = None) -> str:
    """Build the user input prompt, optionally using custom domains."""
    effective_domains = domains_str_from(domains) if domains is not None else domains_str()
    return (
        f"Search for news about {ticker} stock from {date} on "
        f"{effective_domains}. "
        f"Only include articles published on {date} or within 1-2 days of it. "
        "Do NOT include old or outdated articles. "
        f"Also check for any upcoming events (earnings, dividends, etc.) for {ticker}."
    )

# -- User/input prompt templates -------------------------------------------

INPUT_WITH_DATE = (
    "Search for news about {ticker} stock from {date} on "
    f"{domains_str()}. "
    "Only include articles published on {date} or within 1-2 days of it. "
    "Do NOT include old or outdated articles. "
    "Also check for any upcoming events (earnings, dividends, etc.) for {ticker}."
)
