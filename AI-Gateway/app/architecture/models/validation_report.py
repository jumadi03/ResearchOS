"""
ResearchOS Architecture Domain Model.

Canonical Validation Report.

Represents the complete result of an
architecture validation execution.

Contains no business logic.
"""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from typing import Any

from app.architecture.models.architecture_validation_result import (
    ArchitectureValidationResult,
)
from app.architecture.models.validation_status import ValidationStatus
from app.architecture.models.architecture_violation import ArchitectureViolation
from app.architecture.schema import COMPLIANCE_SCHEMA


@dataclass(
    frozen=True,
    slots=True,
)
class ValidationReport:
    """
    Canonical Validation Report.

    Aggregate root for an architecture
    validation execution.
    """

    validation_results: tuple[
        ArchitectureValidationResult,
        ...
    ] = ()

    metadata: dict[str, Any] | None = None
    schema_version: str = "1.0"

    @property
    def is_compliant(self) -> bool:
        """Return true only when every validator produced a conclusive result."""
        if not self.validation_results:
            return False

        accepted = {
            ValidationStatus.PASS,
            ValidationStatus.NOT_APPLICABLE,
        }
        return all(result.status in accepted for result in self.validation_results)

    @property
    def status(self) -> str:
        """Return a fail-safe aggregate status for the report."""
        statuses = {result.status for result in self.validation_results}
        if not statuses or statuses & {
            ValidationStatus.NOT_IMPLEMENTED,
            ValidationStatus.NOT_RUN,
            ValidationStatus.ERROR,
        }:
            return "INCOMPLETE"
        if ValidationStatus.FAIL in statuses:
            return "FAIL"
        return "PASS"

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the complete report deterministically for audit storage."""
        payload = {"status": self.status, "is_compliant": self.is_compliant, **asdict(self)}
        if self.schema_version == "0.9":
            payload.pop("schema_version")
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def calculate_content_hash(self) -> str:
        """Return the canonical SHA-256 compliance report hash."""
        return sha256(self.to_json(indent=None).encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, value: str) -> "ValidationReport":
        """Rehydrate a report and verify its derived aggregate fields."""
        payload = json.loads(value)
        schema_version = payload.get("schema_version", "0.9")
        COMPLIANCE_SCHEMA.require_readable(schema_version)
        report = cls(
            validation_results=tuple(
                ArchitectureValidationResult(
                    validation_id=item["validation_id"],
                    artifact_name=item["artifact_name"],
                    violations=tuple(
                        ArchitectureViolation.from_dict(violation)
                        for violation in item.get("violations", [])
                    ),
                    metadata=item.get("metadata", {}),
                    status=ValidationStatus(item.get("status", "NOT_RUN")),
                )
                for item in payload.get("validation_results", [])
            ),
            metadata=payload.get("metadata"),
            schema_version=schema_version,
        )
        if payload.get("status") != report.status:
            raise ValueError("Persisted compliance aggregate status is invalid")
        if payload.get("is_compliant") is not report.is_compliant:
            raise ValueError("Persisted compliance flag is invalid")
        return report

    def upgraded(self) -> "ValidationReport":
        """Return a current-schema copy; historical input remains unchanged."""
        return replace(self, schema_version=COMPLIANCE_SCHEMA.current)
