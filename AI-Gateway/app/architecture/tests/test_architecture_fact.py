from app.architecture.models.architecture_artifact import (
    ArchitectureArtifact,
)

from app.architecture.models.architecture_fact import (
    ArchitectureFact,
)


def test_architecture_fact_contract() -> None:
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

    fact = ArchitectureFact(
        fact_id="FACT-0001",
        artifact=artifact,
        fact_name="Frozen",
        fact_value="True",
    )

    assert fact.artifact is artifact
    assert fact.fact_name == "Frozen"
