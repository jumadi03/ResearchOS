"""
Smoke Test + Contract Test
for Validation Report.
"""

from app.architecture.models import (
    ValidationReport,
)


def test_contract() -> None:
    #
    # Arrange
    #
    report = ValidationReport()

    #
    # Smoke Test
    #
    print("Report             :", report)
    print(
        "Validation Results :",
        report.validation_results,
    )
    print(
        "Metadata           :",
        report.metadata,
    )

    #
    # Contract Test
    #
    assert report.validation_results == ()

    assert report.metadata is None

    print()
    print("CONTRACT TEST : PASS")
    print("PASS")


