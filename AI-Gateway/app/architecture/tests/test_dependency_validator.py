"""
Smoke Test + Contract Test
for Dependency Validator.
"""

from app.architecture.governance import (
    DependencyValidator,
    LawRegistry,
    LawResolution,
)


def test_contract() -> None:
    #
    # Arrange
    #
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    validator = DependencyValidator(
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
    assert result.validation_id == "DEPENDENCY"
    assert result.artifact_name == "DependencyValidator"
    assert result.violations == ()
    assert result.status.value == "NOT_RUN"
    assert result.metadata["reason"] == "ARCHITECTURE_GRAPH_REQUIRED"

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


