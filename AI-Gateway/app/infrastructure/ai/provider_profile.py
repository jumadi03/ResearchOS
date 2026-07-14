from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    """
    Immutable metadata describing an AI provider.

    The profile represents runtime metadata used by
    routing, discovery, monitoring and diagnostics.

    It does not contain provider behavior.
    """

    #
    # Identity
    #

    name: str

    vendor: str = "Unknown"

    family: str = "Unknown"

    #
    # Runtime Capabilities
    #

    supports_thinking: bool = False

    supports_streaming: bool = False

    supports_tools: bool = False

    supports_embeddings: bool = False

    supports_vision: bool = False

    #
    # Future Runtime Features
    #

    supports_json: bool = False

    supports_multimodal: bool = False

    supports_audio_input: bool = False

    supports_audio_output: bool = False

    supports_image_generation: bool = False