"""
ResearchOS Kernel Contract.

Canonical Capability Lifecycle Contract.

Defines the minimal lifecycle implemented
by every ResearchOS capability.

Contains no implementation.
"""

from typing import Protocol
from typing import TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Capability(
    Protocol[
        InputT,
        OutputT,
    ]
):
    """
    Canonical Capability Contract.

    A capability receives one canonical
    input and produces one canonical
    output.

    Internal execution is intentionally
    unspecified.
    """

    def execute(
        self,
        value: InputT,
    ) -> OutputT:
        ...