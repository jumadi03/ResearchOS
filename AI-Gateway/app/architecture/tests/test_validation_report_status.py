from app.architecture.models import (
    ArchitectureValidationResult,
    ValidationReport,
    ValidationStatus,
)


def _result(status: ValidationStatus) -> ArchitectureValidationResult:
    return ArchitectureValidationResult(
        validation_id=f"TEST-{status}",
        artifact_name="test-artifact",
        status=status,
    )


def test_empty_report_is_incomplete_and_not_compliant() -> None:
    report = ValidationReport()
    assert report.status == "INCOMPLETE"
    assert report.is_compliant is False


def test_not_implemented_result_is_not_compliant() -> None:
    report = ValidationReport(
        validation_results=(_result(ValidationStatus.NOT_IMPLEMENTED),)
    )
    assert report.status == "INCOMPLETE"
    assert report.is_compliant is False


def test_all_conclusive_success_results_are_compliant() -> None:
    report = ValidationReport(
        validation_results=(
            _result(ValidationStatus.PASS),
            _result(ValidationStatus.NOT_APPLICABLE),
        )
    )
    assert report.status == "PASS"
    assert report.is_compliant is True
