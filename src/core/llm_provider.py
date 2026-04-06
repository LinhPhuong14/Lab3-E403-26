from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generator

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Supports OpenAI, Gemini, and Local models.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Produce a non-streaming completion.
        Returns:
            Dict containing:
            - content: The response text
            - usage: { 'prompt_tokens', 'completion_tokens' }
            - latency_ms: Response time
        """
        pass

    @abstractmethod
    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """Produce a streaming completion."""
        pass


def create_llm_provider(provider_name: str = "openai", model_name: str = "gpt-4o") -> "LLMProvider":
    normalized = (provider_name or "openai").strip().lower()
    if normalized != "openai":
        raise ValueError(f"Unsupported provider '{provider_name}'. Only 'openai' is supported.")

    from src.core.openai_provider import OpenAIProvider

    return OpenAIProvider(model_name=model_name)
