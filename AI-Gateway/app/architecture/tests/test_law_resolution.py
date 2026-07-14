"""
Manual test for Law Resolution.
"""

from app.architecture.governance import (
    LawRegistry,
    LawResolution,
)


def main() -> None:
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    print("Registry   :", registry)
    print("Resolution :", resolution)
    print("Resolved   :", resolution.resolve_all())

    print()
    print("PASS")


if __name__ == "__main__":
    main()