import os

from openai import AsyncOpenAI

from llm.base import BaseLLMProvider

_SYSTEM_PROMPT = (
    "You are a helpful assistant. You will provide a clear, concise answer to the "
    "user's question. Your answer will be accompanied by relevant web search results, "
    "so focus on giving context and explanation rather than listing links yourself."
)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider backed by the OpenAI API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4")

    async def generate(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""
