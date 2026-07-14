"""
Smoke Test + Contract Test
for Namespace Validator.
"""

from app.architecture.governance import (
    LawRegistry,
    LawResolution,
    NamespaceValidator,
)


def test_contract() -> None:
    #
    # Arrange
    #
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    validator = NamespaceValidator(
        resolution=resolution,
    )

    #
    # Act
    #
    result = validator.validate()

    #
    # Smoke Test
    #
    print("Registry   :", registry)
    print("Resolution :", resolution)
    print("Validator  :", validator)
    print("Result     :", result)

    #
    # Contract Test
    #
    assert (
        result.validation_id
        == "NAMESPACE-FOUNDATION"
    )

    assert (
        result.artifact_name
        == "NamespaceValidator"
    )

    assert result.violations == ()

    assert (
        result.metadata["resolved_laws"]
        == 0
    )

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


