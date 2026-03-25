# max_slack_bot_experiment

A modular Slack bot that scans trusted financial news sites for stock ticker
news. Mention a ticker in any message after `!maxbot` and the bot replies
in-thread with a terse, headline-style summary and links to the source articles.

**Example usage:**
```
!maxbot AAPL is going crazy, can you check for news?
```

**Example reply:**
```
📈 *AAPL — News Summary*

• iPhone 16 sales beat expectations in Q1, revenue up 8% YoY
• Apple announces $100B buyback program, largest in history
• Analysts upgrade price target to $210 amid strong services growth

*Sources:*
• <https://reuters.com/...|Reuters: Apple Q1 earnings beat...>
• <https://finance.yahoo.com/...|Yahoo Finance: Apple announces buyback...>
• <https://investing.com/...|Investing.com: Analysts upgrade Apple...>
```

---

## Architecture

```
max_slack_bot_experiment/
├── bot.py                          # Main entrypoint — wires providers, starts Socket Mode
├── requirements.txt
├── .env.example                    # Template for all required env vars
├── .gitignore
├── README.md
├── llm/
│   ├── base.py                     # BaseLLMProvider (abstract)
│   └── openai_provider.py          # OpenAIProvider — GPT-4, financial news prompt
├── search/
│   ├── base.py                     # BaseSearchProvider + SearchResult dataclass
│   ├── news_search_provider.py     # NewsSearchProvider — Bing scoped to trusted sites
│   └── bing_provider.py            # BingSearchProvider — generic Bing (kept for compatibility)
├── parsing/
│   ├── base.py                     # BaseMessageParser (abstract, generic)
│   ├── ticker_parser.py            # TickerMessageParser — extracts ticker from !maxbot message
│   └── regex_parser.py             # RegexMessageParser — generic !maxbot parser (kept for compatibility)
└── formatting/
    ├── base.py                     # BaseFormatter (abstract)
    └── slack_formatter.py          # SlackFormatter — 📈 stock-news Slack output
```

Every layer has an abstract base class so you can swap out any component
without touching the rest of the code.

---

## Prerequisites

- Python 3.10 or newer
- A **Slack workspace** where you can create apps
- An **OpenAI API key** — <https://platform.openai.com/api-keys>
- A **Bing Search API key** — <https://www.microsoft.com/en-us/bing/apis/bing-web-search-api>

---

## 1 — Create and configure the Slack App

1. Go to <https://api.slack.com/apps> and click **Create New App → From scratch**.
2. Give it a name (e.g. `maxbot`) and pick your workspace.
3. In the left sidebar open **Socket Mode** and toggle it **on**.
   - Generate an **App-Level Token** with the `connections:write` scope.
   - Copy the token (starts with `xapp-`).
4. In the left sidebar open **OAuth & Permissions** and add these **Bot Token Scopes**:
   - `chat:write`
   - `channels:history`
   - `groups:history`
   - `im:history`
5. In the left sidebar open **Event Subscriptions**, toggle **on**, then under
   *Subscribe to bot events* add `message.channels`, `message.groups`, and `message.im`.
6. Click **Install to Workspace** and copy the **Bot User OAuth Token** (starts with `xoxb-`).
7. Invite the bot to any channel: `/invite @maxbot`.

---

## 2 — Clone and install

```bash
git clone https://github.com/MaxOliveberg/max_slack_bot_experiment.git
cd max_slack_bot_experiment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the values:

| Variable | Description |
|---|---|
| `SLACK_BOT_TOKEN` | Bot token from step 1.6 (`xoxb-…`) |
| `SLACK_APP_TOKEN` | App-level token from step 1.3 (`xapp-…`) |
| `OPENAI_API_KEY` | Your OpenAI secret key |
| `OPENAI_MODEL` | Model name (default: `gpt-4`) |
| `BING_API_KEY` | Bing Search API key — used to query Reuters, Yahoo Finance, and Investing.com |
| `BOT_TRIGGER` | Trigger prefix (default: `!maxbot`) |

---

## 4 — Run the bot

```bash
python bot.py
```

You should see `⚡️ Bolt app is running!` in the terminal.
Now post `!maxbot TSLA what is happening?` in any channel where the bot is invited.

---

## 5 — Swapping out providers

Every component implements a simple abstract interface.

### Adding a new news source

Edit `search/news_search_provider.py` and pass a custom `sites` list:

```python
searcher = NewsSearchProvider(
    sites=["reuters.com", "finance.yahoo.com", "investing.com", "bloomberg.com"]
)
```

The `_SOURCE_LABELS` dict in that file controls the friendly display name shown
in the Slack message. Add an entry there for any new domain.

### Replacing OpenAI with another LLM

```python
# my_anthropic_provider.py
from llm.base import BaseLLMProvider
from search.base import SearchResult
import anthropic

class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        self._client = anthropic.AsyncAnthropic()

    async def generate(self, prompt: str) -> str:
        msg = await self._client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    async def summarize_news(self, ticker: str, search_results: list[SearchResult]) -> str:
        snippets = "\n".join(f"- [{r.source}] {r.title}: {r.snippet}" for r in search_results)
        prompt = f"Ticker: {ticker}\n\nRecent news snippets:\n{snippets}\n\nSummarize in 2-3 bullet points."
        return await self.generate(prompt)
```

Then in `bot.py` change one line:

```python
# from llm.openai_provider import OpenAIProvider
from my_anthropic_provider import AnthropicProvider
llm = AnthropicProvider()
```

The same pattern works for search, parsing, and formatting.
