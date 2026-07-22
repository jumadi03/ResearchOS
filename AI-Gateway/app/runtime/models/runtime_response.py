from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class RuntimeResponse:
    """
    Canonical Runtime Response.

    Seluruh AI Provider wajib
    mengembalikan tipe ini.
    """

    provider: str

    model: str

    text: str

    finish_reason: str | None = None

    input_tokens: int | None = None

    output_tokens: int | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    raw: Any = None

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
