from app.infrastructure.ai.interfaces import AIProvider
from app.infrastructure.ai.transport.ollama_transport import OllamaTransport
from app.infrastructure.ai.provider_profiles import OLLAMA_PROFILE
from app.runtime.models.runtime_response import RuntimeResponse


class OllamaAdapter(AIProvider):
    """
    Adapter yang menerjemahkan transport
    menjadi Canonical RuntimeResponse.
    """

    PROVIDER_NAME = "ollama"

    def __init__(self):

        self.transport = OllamaTransport()

    def execute(
        self,
        request,
    ):

        result = self.transport.generate(
            request.prompt,
            options=request.metadata.get("generation_options"),
            think=request.metadata.get("think"),
        )

        return RuntimeResponse(
            provider=self.PROVIDER_NAME,
            model=result["model"],
            text=result["response"],
            raw=result,
        )

    def stream(
        self,
        request,
    ):

        return self.transport.generate_stream(
            request.prompt,
            options=request.metadata.get("generation_options"),
            think=request.metadata.get("think"),
        )

    def health(self):

        return True

    def models(self):

        return [
            self.transport.model,
        ]

    def profile(self):

        return OLLAMA_PROFILE
