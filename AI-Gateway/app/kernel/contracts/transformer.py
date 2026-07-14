"""
ResearchOS Kernel Contract.

Canonical Transformer Protocol.

Defines the minimal contract implemented
by all capability transformers.

Contains no implementation.
"""

from typing import Protocol
from typing import TypeVar


InputT = TypeVar("InputT")

OutputT = TypeVar("OutputT")


class Transformer(
    Protocol[
        InputT,
        OutputT,
    ]
):
    """
    Canonical Transformer Contract.

    Every transformer in ResearchOS
    implements exactly one public
    transform() method.
    """

    def transform(
        self,
        value: InputT,
    ) -> OutputT:
        ...