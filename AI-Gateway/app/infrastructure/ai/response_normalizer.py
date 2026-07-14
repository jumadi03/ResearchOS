from app.runtime.models.runtime_response import RuntimeResponse


class ResponseNormalizer:
    """
    Menghasilkan Canonical RuntimeResponse.

    Pada Sprint-001M normalizer bertugas
    memastikan seluruh provider
    mengembalikan RuntimeResponse.

    Ke depan di sinilah akan dilakukan
    normalisasi OpenAI, Gemini,
    Anthropic, Ollama, dsb.
    """

    def normalize(
        self,
        provider_name: str,
        response: RuntimeResponse,
    ) -> RuntimeResponse:

        # --------------------------------------------------
        # Jika provider sudah menghasilkan RuntimeResponse
        # cukup pastikan nama provider konsisten.
        # --------------------------------------------------

        response.provider = provider_name

        return response