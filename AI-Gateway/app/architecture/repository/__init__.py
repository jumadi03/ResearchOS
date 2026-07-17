"""Repository Management capability owned by the Architecture Engine."""

from .classifier import RepositoryClassifier
from .models import (
    RepositoryFileClassification,
    RepositoryFileRecord,
    RepositoryInventory,
)
from .scanner import RepositoryScanner
from .policy_models import (
    RepositoryLifecycle,
    RepositoryLifecyclePolicy,
    RepositoryNamingPolicy,
    RepositoryOwnershipPolicy,
    RepositoryPlacementPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyException,
)
from .policy_registry import (
    RepositoryPolicyConflict,
    RepositoryPolicyRegistry,
)
from .file_registry_models import (
    FileContinuityEvent,
    FileGovernanceState,
    RepositoryFileEntry,
    RepositoryFileRegistry,
)
from .file_registry_builder import RepositoryFileRegistryBuilder

__all__ = [
    "RepositoryClassifier",
    "RepositoryFileClassification",
    "RepositoryFileRecord",
    "RepositoryInventory",
    "RepositoryScanner",
    "RepositoryLifecycle",
    "RepositoryLifecyclePolicy",
    "RepositoryNamingPolicy",
    "RepositoryOwnershipPolicy",
    "RepositoryPlacementPolicy",
    "RepositoryPolicyBundle",
    "RepositoryPolicyConflict",
    "RepositoryPolicyException",
    "RepositoryPolicyRegistry",
    "FileContinuityEvent",
    "FileGovernanceState",
    "RepositoryFileEntry",
    "RepositoryFileRegistry",
    "RepositoryFileRegistryBuilder",
]
