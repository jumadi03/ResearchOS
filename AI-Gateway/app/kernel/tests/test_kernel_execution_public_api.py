"""
Manual test for Kernel Execution Public API.
"""

from app.kernel.execution import ExecutionContext


def main() -> None:
    print("ExecutionContext:", ExecutionContext)
    print()
    print("PASS")


if __name__ == "__main__":
    main()