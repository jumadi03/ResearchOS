"""
Contract test for Validator Registry.
"""

from app.architecture.governance import (
    ValidatorRegistry,
)


def test_contract() -> None:
    registry = ValidatorRegistry()

    print("Registry :", registry)
    print("Validators :", registry.get_all())
    print("Count :", registry.count())

    #
    # Contract Assertions
    #

    assert registry.get_all() == ()

    assert registry.count() == 0

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


