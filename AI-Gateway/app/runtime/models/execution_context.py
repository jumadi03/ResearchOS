from pydantic import BaseModel, Field

from app.runtime.models.runtime_request import RuntimeRequest


class ExecutionContext(BaseModel):
    """
    Canonical Runtime Execution Context.

    ExecutionContext represents the runtime
    state carried throughout the Runtime
    Pipeline.

    Sprint-001Q (Stage 1)

    Initially, the execution context contains
    only the canonical RuntimeRequest.

    Additional runtime state will be introduced
    incrementally following the Evolutionary
    Domain Modeling (EDM) principle.

    Domain Model only.
    No business logic.
    """

    request: RuntimeRequest = Field(
        ...,
        description="Canonical Runtime Input Model."
    )