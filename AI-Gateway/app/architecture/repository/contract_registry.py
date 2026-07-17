"""Read-only resolution for the advisory public-contract registry."""

from .contract_registry_models import (
    PublicContractEntry,
    PublicContractLifecycle,
    PublicContractRegistryManifest,
)


class PublicContractRegistry:
    def __init__(self, manifest: PublicContractRegistryManifest) -> None:
        if not manifest.verify():
            raise ValueError("Public contract registry integrity verification failed")
        self.manifest = manifest
        self._by_id = {item.contract_id: item for item in manifest.entries}
        self._by_surface = {item.public_surface: item for item in manifest.entries}

    def get(self, contract_id: str) -> PublicContractEntry | None:
        return self._by_id.get(contract_id)

    def resolve_surface(self, public_surface: str) -> PublicContractEntry | None:
        return self._by_surface.get(public_surface)

    def by_lifecycle(
        self, lifecycle: PublicContractLifecycle,
    ) -> tuple[PublicContractEntry, ...]:
        return tuple(
            item for item in self.manifest.entries
            if item.lifecycle is lifecycle
        )
