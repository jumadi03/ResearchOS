from app.architecture.models.architecture_fact import (
    ArchitectureFact,
)

from app.architecture.models.architecture_artifact import (
    ArchitectureArtifact,
)

from app.architecture.models.architecture_law import (
    ArchitectureLaw,
)

from app.architecture.models.architecture_violation import (
    ArchitectureViolation,
)

from app.architecture.models.architecture_validation_result import (
    ArchitectureValidationResult,
)

def test_architecture_validation_result_contract() -> None:
    artifact = ArchitectureArtifact(
        artifact_id="ART-0001",
        name="ScientificTheory",
        artifact_type="DomainModel",
        module="app.modeling.models.scientific_theory",
        source="class ScientificTheory: ...",
    )
    fact = ArchitectureFact(
        fact_id="FACT-0001",
        artifact=artifact,
        fact_name="Frozen",
        fact_value="False",
    )
    law = ArchitectureLaw(
        law_id="ALA-001",
        title="Immutable Domain Model",
        description="Canonical domain models must be immutable.",
        version="1.0",
    )
    violation = ArchitectureViolation(
        violation_id="VIO-0001",
        law=law,
        fact=fact,
        message="Domain Model must be immutable.",
    )
    result = ArchitectureValidationResult(
        validation_id="VAL-0001",
        artifact_name="ScientificTheory",
        violations=(violation,),
    )

    assert result.artifact_name == "ScientificTheory"
    assert result.violations == (violation,)
