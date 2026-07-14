"""
ResearchOS Kernel Execution.

Stable execution contracts exposed by the
ResearchOS Kernel.

Capabilities must import execution contracts
only through this package.
"""

from .context import ExecutionContext

__all__ = (
    "ExecutionContext",
)