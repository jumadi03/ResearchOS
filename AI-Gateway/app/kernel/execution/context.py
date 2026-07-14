"""
ResearchOS Kernel Contract.

Canonical Execution Context Protocol.

Defines the minimal contract implemented
by every execution context.

Contains no implementation.
"""

from typing import Any
from typing import Protocol


class ExecutionContext(
    Protocol,
):
    """
    Canonical Execution Context.

    Holds execution state during
    capability processing.
    """

    @property
    def metadata(
        self,
    ) -> dict[str, Any]:
        ...