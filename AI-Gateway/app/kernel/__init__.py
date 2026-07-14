"""
ResearchOS Kernel

The Kernel is the foundational namespace of ResearchOS.

Design Principles
-----------------
- Namespace Root
- Kernel First
- Stable Package APIs
- Evolutionary Refactoring

Public contracts are exposed through their
respective subpackages, for example:

    from app.kernel.contracts import Capability
    from app.kernel.contracts import Transformer
    from app.kernel.execution import ExecutionContext

The root package intentionally does not re-export
domain symbols.
"""

__all__: tuple[str, ...] = ()