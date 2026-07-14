from app.architecture.models.architecture_inventory import (
    ArchitectureInventory,
)

def test_architecture_inventory_contract() -> None:
    inventory = ArchitectureInventory(
        inventory_id="ARCH-INV-0001",
        project_name="ResearchOS",
        subsystems=(
            "Runtime",
            "Architecture",
        ),
        engines=(
            "Runtime Engine",
            "Architecture Engine",
        ),
        capabilities=(
            "Discovery",
            "Modeling",
        ),
    )

    assert inventory.project_name == "ResearchOS"
    assert inventory.capabilities == (
        "Discovery",
        "Modeling",
    )
