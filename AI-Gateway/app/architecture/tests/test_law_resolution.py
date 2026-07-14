"""
Manual test for Law Resolution.
"""

from app.architecture.governance import (
    LawRegistry,
    LawResolution,
)


def test_contract() -> None:
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    print("Registry   :", registry)
    print("Resolution :", resolution)
    print("Resolved   :", resolution.resolve_all())

    print()
    print("PASS")


