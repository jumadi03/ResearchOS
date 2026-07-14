from .provider_profile import ProviderProfile


OLLAMA_PROFILE = ProviderProfile(
    #
    # Identity
    #
    name="ollama",
    vendor="Ollama",
    family="Local LLM",

    #
    # Runtime Capabilities
    #
    supports_thinking=True,
    supports_streaming=True,
    supports_tools=True,
    supports_embeddings=False,
    supports_vision=False,

    #
    # Future Runtime Features
    #
    supports_json=False,
    supports_multimodal=False,
    supports_audio_input=False,
    supports_audio_output=False,
    supports_image_generation=False,
)