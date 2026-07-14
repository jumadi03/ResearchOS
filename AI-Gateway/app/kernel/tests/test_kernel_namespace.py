"""
Manual test for Kernel Namespace Principle.
"""

import app.kernel
from app.kernel.contracts import Capability
from app.kernel.contracts import Transformer
from app.kernel.execution import ExecutionContext


def main() -> None:
    print("Kernel Namespace :", app.kernel.__name__)
    print("Capability       :", Capability)
    print("Transformer      :", Transformer)
    print("ExecutionContext :", ExecutionContext)

    print()
    print("PASS")


if __name__ == "__main__":
    main()