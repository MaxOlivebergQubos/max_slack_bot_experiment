from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a natural-language response for the given prompt.

        Args:
            prompt: The user query or enriched prompt to send to the LLM.

        Returns:
            A natural-language string response.
        """
