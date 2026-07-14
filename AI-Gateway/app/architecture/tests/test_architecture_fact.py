from app.architecture.models.architecture_artifact import (
    ArchitectureArtifact,
)

from app.architecture.models.architecture_fact import (
    ArchitectureFact,
)


artifact = ArchitectureArtifact(
    artifact_id="ART-0001",
    name="ScientificTheory",
    artifact_type="DomainModel",
    module=(
        "app.modeling.models."
        "scientific_theory"
    ),
)

fact = ArchitectureFact(
    fact_id="FACT-0001",
    artifact=artifact,
    fact_name="Frozen",
    fact_value="True",
)

print(fact)