from app.architecture.models.architecture_law import (
    ArchitectureLaw,
)

def test_architecture_law_contract() -> None:
    law = ArchitectureLaw(
        law_id="ALA-001",
        title="Immutable Domain Model",
        description=(
            "All canonical domain models "
            "must be immutable."
        ),
        version="1.0",
    )

    assert law.law_id == "ALA-001"
    assert law.version == "1.0"
