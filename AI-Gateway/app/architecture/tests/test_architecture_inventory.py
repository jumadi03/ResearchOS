from app.architecture.models.architecture_inventory import (
    ArchitectureInventory,
)

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

print(inventory)