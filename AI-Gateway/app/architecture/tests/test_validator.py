"""
Manual test for Validator Framework.
"""

from app.architecture.governance import (
    LawRegistry,
    LawResolution,
    Validator,
)


def test_contract() -> None:
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    validator = Validator(
        resolution=resolution,
    )

    print("Registry   :", registry)
    print("Resolution :", resolution)
    print("Validator  :", validator)

    print()

    try:
        validator.validate()

    except NotImplementedError as exc:
        print(exc)

    print()
    print("PASS")


