# max_slack_bot_experiment

A modular Slack bot that searches trusted financial news sites for stock ticker
news. Mention a ticker in any message after `!gaston` and the bot replies
in-thread with a terse, headline-style summary and links to the source articles.

The bot uses **OpenAI's Responses API** with the built-in `web_search` tool, so
a single API call performs both the web search and the summarization. No
separate search API key is needed.

**Example usage:**
```
!gaston AAPL is going crazy, can you check for news?
```

**Example reply:**
```
📈 *AAPL — News Summary*

• iPhone 16 sales beat expectations in Q1, revenue up 8% YoY
• Apple announces $100B buyback program, largest in history
• Analysts upgrade price target to $210 amid strong services growth

*Sources:*
• <https://reuters.com/...|Apple Q1 earnings beat...>
• <https://finance.yahoo.com/...|Apple announces buyback...>
• <https://investing.com/...|Analysts upgrade Apple...>
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
│   ├── models.py                   # NewsResult + Source dataclasses
│   └── openai_provider.py          # OpenAIProvider — Responses API with web_search tool
├── parsing/
│   ├── base.py                     # BaseMessageParser (abstract, generic)
│   ├── ticker_parser.py            # TickerMessageParser — extracts ticker from !gaston message
│   └── regex_parser.py             # RegexMessageParser — generic !gaston parser (kept for compatibility)
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
  (a model that supports web search, e.g. `gpt-4o-search-preview`, is required)

---

## 1 — Create and configure the Slack App

1. Go to <https://api.slack.com/apps> and click **Create New App → From scratch**.
2. Give it a name (e.g. `gaston`) and pick your workspace.
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
7. Invite the bot to any channel: `/invite @gaston`.

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
| `OPENAI_MODEL` | Model name (default: `gpt-4o-search-preview`) — must support the `web_search` tool |
| `BOT_TRIGGER` | Trigger prefix (default: `!gaston`) |
| `SLACK_LOG_CHANNEL` | *(Optional)* Channel **ID** to post debug traces to (e.g. `C1234567890`). Must be a channel ID, not a name. Leave empty to disable. |

---

## 4 — Run the bot

```bash
python bot.py
```

You should see `⚡️ Bolt app is running!` in the terminal.
Now post `!gaston TSLA what is happening?` in any channel where the bot is invited.

---

## 5 — Swapping out providers

Every component implements a simple abstract interface.

### Changing which sites are searched

The trusted sites are configured directly in the LLM prompt inside
`llm/openai_provider.py`. Edit the `_INSTRUCTIONS` constant to add or remove
sites. Because the model's built-in `web_search` tool handles retrieval, no
separate search provider is needed.

### Replacing OpenAI with another LLM

```python
# my_anthropic_provider.py
from llm.base import BaseLLMProvider
from llm.models import NewsResult, Source

class AnthropicProvider(BaseLLMProvider):
    async def search_and_summarize(self, ticker: str) -> NewsResult:
        # Call your provider, extract summary and sources
        ...
        return NewsResult(summary=summary, sources=sources)
```

Then in `bot.py` change one line:

```python
# from llm.openai_provider import OpenAIProvider
from my_anthropic_provider import AnthropicProvider
llm = AnthropicProvider()
```

The same pattern works for parsing and formatting.
