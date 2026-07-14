from app.infrastructure.ai.provider_registry import ProviderRegistry
from app.infrastructure.ai.adapters.ollama_adapter import OllamaAdapter


def build_registry() -> ProviderRegistry:
    """
    Membangun registry beserta seluruh provider
    yang tersedia.
    """

    registry = ProviderRegistry()

    registry.register(
        "ollama",
        OllamaAdapter()
    )

    return registry