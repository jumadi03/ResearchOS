from dataclasses import dataclass
from typing import Any


@dataclass
class CanonicalResponse:
    """
    Canonical Response Model
    yang digunakan oleh seluruh Runtime.
    """

    provider: str
    model: str
    text: str

    raw: Any