from app.architecture.models.architecture_fact import (
    ArchitectureFact,
)

from app.architecture.models.architecture_violation import (
    ArchitectureViolation,
)

from app.architecture.models.architecture_validation_result import (
    ArchitectureValidationResult,
)

fact = ArchitectureFact(
    fact_id="FACT-0001",
    artifact_name="ScientificTheory",
    artifact_type="DomainModel",
    fact_name="Frozen",
    fact_value="False",
)

violation = ArchitectureViolation(
    violation_id="VIO-0001",
    law_id="ALA-001",
    fact=fact,
    message="Domain Model must be immutable.",
)

result = ArchitectureValidationResult(
    validation_id="VAL-0001",
    artifact_name="ScientificTheory",
    violations=(
        violation,
    ),
)

print(result)