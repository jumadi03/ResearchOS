from app.architecture.models.architecture_artifact import (
    ArchitectureArtifact,
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

print(artifact)