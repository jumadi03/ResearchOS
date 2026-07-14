from typing import Any

from pydantic import BaseModel, Field


class RuntimeRequest(BaseModel):
    """
    Canonical Runtime Input Model.

    Every Runtime execution begins with RuntimeRequest.
    This model is the canonical input domain model shared
    across all Runtime layers.

    Domain Model only.
    No business logic.
    """

    prompt: str = Field(
        ...,
        description="User prompt to execute."
    )

    model: str | None = Field(
        default=None,
        description="Preferred model if explicitly requested."
    )

    stream: bool = Field(
        default=False,
        description="Whether streaming response is requested."
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional runtime metadata."
    )