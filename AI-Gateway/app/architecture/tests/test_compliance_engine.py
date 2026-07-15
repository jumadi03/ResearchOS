"""
Smoke Test + Contract Test
for Compliance Engine.
"""

from app.architecture.governance import (
    ComplianceEngine,
    DependencyValidator,
    LawRegistry,
    LawResolution,
    NamespaceValidator,
    ValidatorRegistry,
)
from app.architecture.models import ValidationStatus


def test_contract() -> None:
    #
    # Arrange
    #
    registry = LawRegistry()

    resolution = LawResolution(
        registry=registry,
    )

    namespace_validator = NamespaceValidator(
        resolution=resolution,
    )

    dependency_validator = DependencyValidator(
        resolution=resolution,
    )

    validator_registry = ValidatorRegistry(
        validators=(
            namespace_validator,
            dependency_validator,
        ),
    )

    engine = ComplianceEngine(
        registry=validator_registry,
    )

    #
    # Act
    #
    report = engine.validate()

    results = report.validation_results

    #
    # Smoke Test
    #
    print("Engine           :", engine)
    print("Registry         :", validator_registry)
    print("Validator Count  :", engine.validator_count())
    print("Results          :", results)

    #
    # Contract Test
    #
    assert engine.validator_count() == 2

    assert len(results) == 2

    # Foundation validators are deliberately inconclusive. An empty list of
    # violations must not be interpreted as a compliant architecture.
    assert report.status == "INCOMPLETE"
    assert report.is_compliant is False
    assert results[0].status is ValidationStatus.NOT_IMPLEMENTED
    assert results[1].status is ValidationStatus.NOT_RUN

    assert (
        results[0].validation_id
        == "NAMESPACE-FOUNDATION"
    )

    assert (
        results[1].validation_id
        == "DEPENDENCY"
    )

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


