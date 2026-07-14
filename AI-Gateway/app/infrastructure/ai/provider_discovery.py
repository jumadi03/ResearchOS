from app.infrastructure.ai.provider_registry import ProviderRegistry


class ProviderDiscovery:
    """
    Provider Discovery Service.

    Provides a unified API for retrieving
    provider metadata from registered providers.

    This service does not execute inference.
    It only exposes discovery operations.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
    ):
        self._registry = registry

    def profile(
        self,
        provider_name: str,
    ):
        """
        Return provider profile.
        """

        provider = self._registry.get(
            provider_name
        )

        return provider.profile()

    def models(
        self,
        provider_name: str,
    ):
        """
        Return provider models.
        """

        provider = self._registry.get(
            provider_name
        )

        return provider.models()

    def health(
        self,
        provider_name: str,
    ):
        """
        Return provider health.
        """

        provider = self._registry.get(
            provider_name
        )

        return provider.health()