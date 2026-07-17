"""
ResearchOS Architecture.

Canonical public namespace for the
Architecture subsystem.
"""

from .models import (
    ArchitectureArtifact,
    ArchitectureFact,
    ArchitectureInventory,
    ArchitectureLaw,
    ArchitectureValidationResult,
    ArchitectureViolation,
    ValidationReport,
)

from .scanner import ArchitectureScanner
from .parser import ArchitectureParser
from .symbol_extractor import SymbolExtractor
from .graph_builder import ArchitectureGraphBuilder
from .import_extractor import ImportExtractor
from .class_extractor import ClassExtractor
from .visitor import ArchitectureVisitor
from .node_collector import NodeCollector
from .repository import (
    RepositoryClassifier,
    RepositoryFileClassification,
    RepositoryFileRecord,
    RepositoryInventory,
    RepositoryScanner,
    RepositoryLifecycle,
    RepositoryLifecyclePolicy,
    RepositoryNamingPolicy,
    RepositoryOwnershipPolicy,
    RepositoryPlacementPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyConflict,
    RepositoryPolicyException,
    RepositoryPolicyRegistry,
    FileContinuityEvent,
    FileGovernanceState,
    RepositoryFileEntry,
    RepositoryFileRegistry,
    RepositoryFileRegistryBuilder,
    RepositoryPlacementNamingVerifier,
    RepositoryPolicyDomain,
    RepositoryPolicyEvaluation,
    RepositoryVerificationMode,
    RepositoryVerificationOutcome,
    RepositoryVerificationReport,
    RepositoryTraceabilityGraphBuilder,
)


__all__ = [
    "ArchitectureArtifact",
    "ArchitectureFact",
    "ArchitectureInventory",
    "ArchitectureLaw",
    "ArchitectureValidationResult",
    "ArchitectureViolation",
    "ValidationReport",
    "ArchitectureScanner",
    "ArchitectureParser",
    "SymbolExtractor",
    "ArchitectureGraphBuilder",
    "ImportExtractor",
    "ClassExtractor",
    "ArchitectureVisitor",
    "NodeCollector",
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
    "RepositoryPlacementNamingVerifier",
    "RepositoryPolicyDomain",
    "RepositoryPolicyEvaluation",
    "RepositoryVerificationMode",
    "RepositoryVerificationOutcome",
    "RepositoryVerificationReport",
    "RepositoryTraceabilityGraphBuilder",
]
