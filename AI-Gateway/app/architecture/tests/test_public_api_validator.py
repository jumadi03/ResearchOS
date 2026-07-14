"""
Smoke Test + Contract Test
for Public API Validator.
"""

from app.architecture.governance import (
    LawRegistry,
    LawResolution,
    PublicAPIValidator,
)


def main() -> None:
    #
    # Arrange
    #
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    validator = PublicAPIValidator(
        resolution=resolution,
    )

    #
    # Act
    #
    result = validator.validate()

    #
    # Smoke Test
    #
    print("Registry  :", registry)
    print("Resolution:", resolution)
    print("Validator :", validator)
    print("Result    :", result)

    #
    # Contract Test
    #
    assert (
        result.validation_id
        == "PUBLIC-API-FOUNDATION"
    )

    assert (
        result.artifact_name
        == "PublicAPIValidator"
    )

    assert result.violations == ()

    assert (
        result.metadata["resolved_laws"]
        == 0
    )

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


if __name__ == "__main__":
    main()