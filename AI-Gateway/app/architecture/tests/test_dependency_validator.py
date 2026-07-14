"""
Smoke Test + Contract Test
for Dependency Validator.
"""

from app.architecture.governance import (
    DependencyValidator,
    LawRegistry,
    LawResolution,
)


def main() -> None:
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
    assert result.validation_id == "DEPENDENCY-FOUNDATION"
    assert result.artifact_name == "DependencyValidator"
    assert result.violations == ()
    assert result.metadata["resolved_laws"] == 0

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


if __name__ == "__main__":
    main()