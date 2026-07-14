from abc import ABC, abstractmethod

from app.infrastructure.ai.provider_profile import ProviderProfile


class AIProvider(ABC):
    """
    Interface dasar seluruh AI Provider.
    """

    @abstractmethod
    def execute(self, request):
        """
        Execute non-streaming request.
        """
        pass

    @abstractmethod
    def stream(self, request):
        """
        Execute streaming request.
        """
        pass

    @abstractmethod
    def health(self):
        """
        Return provider health information.
        """
        pass

    @abstractmethod
    def models(self):
        """
        Return available models.
        """
        pass

    @abstractmethod
    def profile(self) -> ProviderProfile:
        """
        Return immutable provider profile.

        The profile describes runtime metadata
        such as supported capabilities.
        """
        pass