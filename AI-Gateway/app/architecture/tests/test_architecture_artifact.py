from app.architecture.models.architecture_artifact import (
    ArchitectureArtifact,
)

def test_architecture_artifact_contract() -> None:
    artifact = ArchitectureArtifact(
        artifact_id="ART-0001",
        name="ScientificTheory",
        artifact_type="DomainModel",
        module=(
            "app.modeling.models."
            "scientific_theory"
        ),
        source="class ScientificTheory: ...",
    )

    assert artifact.artifact_id == "ART-0001"
    assert artifact.source == "class ScientificTheory: ..."
