"""LLM provider selection. Add new providers here."""
import config
from llm.base import LLMError, LLMProvider


def get_provider(name: str) -> LLMProvider:
    if name == "mock":
        from llm.mock_provider import MockProvider
        return MockProvider()
    if name == "cmsai":
        from llm.cmsai_provider import CmsaiProvider
        return CmsaiProvider(config.CMSAI_URL, config.CMSAI_MAX_TOKENS, config.CMSAI_TIMEOUT)
    if name == "ollama":
        from llm.ollama_provider import OllamaProvider
        return OllamaProvider(config.OLLAMA_HOST, config.OLLAMA_MODEL,
                              config.OLLAMA_NUM_CTX, config.OLLAMA_TIMEOUT)
    raise ValueError(f"Unknown LLM_PROVIDER '{name}'. Use mock, cmsai, or ollama.")


__all__ = ["get_provider", "LLMError", "LLMProvider"]
