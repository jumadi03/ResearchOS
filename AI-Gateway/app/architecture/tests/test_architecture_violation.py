from app.architecture.models.architecture_fact import (
    ArchitectureFact,
)

from app.architecture.models.architecture_violation import (
    ArchitectureViolation,
)

from app.architecture.models.architecture_law import (
    ArchitectureLaw,
)


law = ArchitectureLaw(
    law_id="ALA-001",
    title="Immutable Domain Model",
    description=(
        "All canonical domain models "
        "must be immutable."
    ),
    version="1.0",
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
    law=law,
    fact=fact,
    message="Domain Model must be immutable.",
)


print(violation)