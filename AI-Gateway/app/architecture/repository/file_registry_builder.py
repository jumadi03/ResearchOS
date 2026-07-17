"""Build revision-bound file registries from FMA inventory and policy inputs."""

from __future__ import annotations

from hashlib import sha256
import json

from .file_registry_models import (
    FileContinuityEvent,
    FileGovernanceState,
    RepositoryFileEntry,
    RepositoryFileRegistry,
)
from .models import RepositoryFileRecord, RepositoryInventory
from .policy_registry import RepositoryPolicyRegistry


class RepositoryFileRegistryBuilder:
    @staticmethod
    def _initial_file_id(project_name: str, item: RepositoryFileRecord) -> str:
        payload = json.dumps(
            {
                "project_name": project_name,
                "first_path": item.path,
                "first_content_hash": item.sha256,
            },
            separators=(",", ":"), sort_keys=True,
        )
        return f"file:{sha256(payload.encode('utf-8')).hexdigest()[:24]}"

    @staticmethod
    def _validate_inputs(
        inventory: RepositoryInventory,
        policies: RepositoryPolicyRegistry,
        previous: RepositoryFileRegistry | None,
    ) -> None:
        if not inventory.verify():
            raise ValueError("Repository inventory integrity verification failed")
        if not policies.bundle.verify():
            raise ValueError("Repository policy integrity verification failed")
        if inventory.project_name != policies.bundle.project_name:
            raise ValueError("Inventory and policy project do not match")
        if previous is not None:
            if not previous.verify():
                raise ValueError("Previous file registry integrity verification failed")
            if previous.project_name != inventory.project_name:
                raise ValueError("Previous registry project does not match inventory")
            if previous.source_revision == inventory.source_revision:
                raise ValueError("Registry evolution requires a new source revision")

    @staticmethod
    def _validate_continuity(
        inventory: RepositoryInventory,
        previous: RepositoryFileRegistry | None,
        claims: tuple[FileContinuityEvent, ...],
    ) -> dict[str, FileContinuityEvent]:
        if claims and previous is None:
            raise ValueError("Continuity claims require a previous registry")
        if previous is None:
            return {}
        old_by_id = {item.file_id: item for item in previous.entries}
        old_paths = {item.current_path for item in previous.entries}
        current_by_path = {item.path: item for item in inventory.files}
        current_paths = set(current_by_path)
        claimed_ids: set[str] = set()
        claimed_targets: set[str] = set()
        existing_events = {item.event_id for item in previous.continuity_events}
        result = {}
        for claim in claims:
            if not claim.verify():
                raise ValueError("File continuity claim integrity verification failed")
            old = old_by_id.get(claim.file_id)
            current = current_by_path.get(claim.to_path)
            if old is None or current is None:
                raise ValueError("File continuity claim references an unknown file")
            if (
                old.current_path != claim.from_path
                or old.content_hash != claim.from_hash
                or current.sha256 != claim.to_hash
                or previous.source_revision != claim.from_revision
                or inventory.source_revision != claim.to_revision
            ):
                raise ValueError("File continuity claim provenance does not match")
            if claim.from_path in current_paths:
                raise ValueError("Continuity source path still exists")
            if claim.to_path in old_paths:
                raise ValueError(
                    "Continuity target path already has an established identity"
                )
            if (
                claim.file_id in claimed_ids
                or claim.to_path in claimed_targets
                or claim.event_id in existing_events
            ):
                raise ValueError("File continuity claim is duplicated or reused")
            claimed_ids.add(claim.file_id)
            claimed_targets.add(claim.to_path)
            result[claim.to_path] = claim
        return result

    def build(
        self,
        inventory: RepositoryInventory,
        policies: RepositoryPolicyRegistry,
        *,
        previous: RepositoryFileRegistry | None = None,
        continuity_claims: tuple[FileContinuityEvent, ...] = (),
    ) -> RepositoryFileRegistry:
        self._validate_inputs(inventory, policies, previous)
        claims = self._validate_continuity(
            inventory, previous, continuity_claims,
        )
        old_by_path = (
            {item.current_path: item for item in previous.entries}
            if previous else {}
        )
        old_by_id = (
            {item.file_id: item for item in previous.entries}
            if previous else {}
        )
        entries = []
        for item in inventory.files:
            old = old_by_path.get(item.path)
            claim = claims.get(item.path)
            if old is not None:
                file_id = old.file_id
                first_seen = old.first_seen_revision
                previous_paths = old.previous_paths
            elif claim is not None:
                old = old_by_id[claim.file_id]
                file_id = old.file_id
                first_seen = old.first_seen_revision
                previous_paths = tuple(dict.fromkeys(
                    (*old.previous_paths, old.current_path)
                ))
            else:
                file_id = self._initial_file_id(inventory.project_name, item)
                first_seen = inventory.source_revision
                previous_paths = ()

            applicable = policies.resolve(item.path)
            policy_ids = tuple(sorted(
                policy.policy_id for policy in applicable
            ))
            ownership = policies.resolve_ownership(item.path)
            lifecycle = policies.resolve_lifecycle(item.path)
            exceptions = policies.resolve_exceptions(item.path, policy_ids)
            has_owner = ownership is not None
            governance = (
                FileGovernanceState.ASSIGNED
                if has_owner and lifecycle is not None
                else FileGovernanceState.PARTIAL
                if has_owner or lifecycle is not None
                else FileGovernanceState.UNASSIGNED
            )
            entries.append(RepositoryFileEntry(
                file_id=file_id,
                current_path=item.path,
                content_hash=item.sha256,
                classification=item.classification,
                size=item.size,
                extension=item.extension,
                first_seen_revision=first_seen,
                previous_paths=previous_paths,
                owner=ownership.owner if ownership else None,
                subsystem=ownership.subsystem if ownership else None,
                engine=ownership.engine if ownership else None,
                capability=ownership.capability if ownership else None,
                lifecycle=lifecycle.lifecycle if lifecycle else None,
                policy_ids=policy_ids,
                exception_ids=tuple(
                    sorted(exception.exception_id for exception in exceptions)
                ),
                governance_state=governance,
            ))
        current_file_ids = {item.file_id for item in entries}
        events = tuple(
            event for event in (
                (previous.continuity_events if previous else ())
                + continuity_claims
            )
            if event.file_id in current_file_ids
        )
        registry = RepositoryFileRegistry(
            registry_id="",
            project_name=inventory.project_name,
            source_revision=inventory.source_revision,
            inventory_id=inventory.inventory_id,
            inventory_hash=inventory.content_hash,
            policy_bundle_id=policies.bundle.bundle_id,
            policy_bundle_hash=policies.bundle.content_hash,
            entries=tuple(entries),
            continuity_events=tuple(events),
        ).finalized()
        if not registry.verify():
            raise ValueError("Repository file registry integrity verification failed")
        return registry
