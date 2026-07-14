"""
Manual test for Kernel Namespace Principle.
"""

import app.kernel
from app.kernel.contracts import Capability
from app.kernel.contracts import Transformer
from app.kernel.execution import ExecutionContext


def test_contract() -> None:
    print("Kernel Namespace :", app.kernel.__name__)
    print("Capability       :", Capability)
    print("Transformer      :", Transformer)
    print("ExecutionContext :", ExecutionContext)

    print()
    print("PASS")


