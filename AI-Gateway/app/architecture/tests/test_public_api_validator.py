"""
Smoke Test + Contract Test
for Public API Validator.
"""

from app.architecture.governance import (
    LawRegistry,
    LawResolution,
    PublicAPIValidator,
)


def test_contract() -> None:
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
        == "PUBLIC-API"
    )

    assert (
        result.artifact_name
        == "PublicAPIValidator"
    )

    assert result.violations == ()

    assert result.status.value == "NOT_RUN"
    assert result.metadata["reason"] == "ARCHITECTURE_GRAPH_REQUIRED"

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


