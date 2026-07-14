"""
ResearchOS Public API Validator.

Architecture Law:

ALA-API-001

Every package exposing canonical
contracts must provide a package-level
public namespace.
"""

from dataclasses import dataclass

from .law_resolution import LawResolution
from .validator import Validator

from ..models import (
    ArchitectureValidationResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PublicAPIValidator(Validator):
    """
    Foundation implementation for
    ALA-API-001.

    Filesystem inspection will be
    introduced in a later sprint.
    """

    resolution: LawResolution

    def validate(
        self,
    ) -> ArchitectureValidationResult:
        """
        Validate ALA-API-001.

        Foundation implementation.
        """

        laws = self.resolution.resolve(
            category="PublicAPI",
        )

        print(
            f"Resolved {len(laws)} applicable law(s)."
        )

        return ArchitectureValidationResult(
            validation_id="PUBLIC-API-FOUNDATION",
            artifact_name="PublicAPIValidator",
            metadata={
                "resolved_laws": len(laws),
            },
        )