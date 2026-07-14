"""
Manual test for Kernel Contracts Public API.
"""

from app.kernel.contracts import Capability
from app.kernel.contracts import Transformer


def main() -> None:
    print("Capability :", Capability)
    print("Transformer:", Transformer)

    print()
    print("PASS")


if __name__ == "__main__":
    main()