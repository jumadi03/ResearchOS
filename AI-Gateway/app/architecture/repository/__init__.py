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
from .verification_models import (
    RepositoryPolicyDomain,
    RepositoryPolicyEvaluation,
    RepositoryVerificationMode,
    RepositoryVerificationOutcome,
    RepositoryVerificationReport,
)
from .placement_naming_verifier import RepositoryPlacementNamingVerifier
from .traceability_graph_builder import RepositoryTraceabilityGraphBuilder
from .health_models import (
    RepositoryHealthCategory,
    RepositoryHealthCheck,
    RepositoryHealthOutcome,
    RepositoryHealthReport,
)
from .health_engine import RepositoryHealthEngine
from .dashboard_models import (
    RepositoryDashboardFile,
    RepositoryDashboardHealth,
    RepositoryDashboardSnapshot,
)
from .dashboard_projector import RepositoryDashboardProjector
from .dashboard_service import RepositoryDashboardService, RepositoryDashboardSource
from .dashboard_store import RepositoryDashboardArtifactStore
from .evolution_models import (
    RepositoryEvolutionDecision,
    RepositoryEvolutionPlan,
    RepositoryEvolutionPreflight,
    RepositoryMove,
    RepositoryPreflightCheck,
    RepositoryPreflightOutcome,
)
from .evolution_planner import RepositoryEvolutionPlanner
from .evolution_preflight import RepositoryEvolutionPreflightEngine
from .evolution_dry_run_models import (
    RepositoryDryRunDirection,
    RepositoryDryRunStep,
    RepositoryEvolutionDryRun,
)
from .evolution_dry_run import RepositoryEvolutionDryRunEngine
from .evolution_execution_models import (
    RepositoryEvolutionExecution,
    RepositoryExecutionAction,
    RepositoryExecutionEvent,
    RepositoryExecutionOutcome,
    RepositoryExecutionStatus,
)
from .evolution_executor import (
    NoOverwriteFileMover,
    RepositoryEvolutionExecutor,
    RepositoryFileMover,
)
from .evolution_post_verification import (
    RepositoryEvolutionPostVerification,
    RepositoryEvolutionPostVerifier,
    RepositoryPostVerificationCheck,
    RepositoryPostVerificationOutcome,
)
from .evolution_recovery import (
    RepositoryEvolutionRecovery,
    RepositoryEvolutionRecoveryPlanner,
    RepositoryRecoveryDecision,
    RepositoryRecoveryExecution,
    RepositoryRecoveryExecutionStatus,
)
from .evolution_recovery_executor import RepositoryEvolutionRecoveryExecutor
from .evolution_post_recovery import (
    RepositoryEvolutionPostRecoveryVerifier,
    RepositoryPostRecoveryCheck,
    RepositoryPostRecoveryOutcome,
    RepositoryPostRecoveryVerification,
)

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
    "RepositoryPlacementNamingVerifier",
    "RepositoryPolicyDomain",
    "RepositoryPolicyEvaluation",
    "RepositoryVerificationMode",
    "RepositoryVerificationOutcome",
    "RepositoryVerificationReport",
    "RepositoryTraceabilityGraphBuilder",
    "RepositoryHealthCategory",
    "RepositoryHealthCheck",
    "RepositoryHealthEngine",
    "RepositoryHealthOutcome",
    "RepositoryHealthReport",
    "RepositoryDashboardFile",
    "RepositoryDashboardHealth",
    "RepositoryDashboardArtifactStore",
    "RepositoryDashboardProjector",
    "RepositoryDashboardService",
    "RepositoryDashboardSnapshot",
    "RepositoryDashboardSource",
    "RepositoryEvolutionDecision",
    "RepositoryEvolutionPlan",
    "RepositoryEvolutionPlanner",
    "RepositoryEvolutionPreflight",
    "RepositoryEvolutionPreflightEngine",
    "RepositoryMove",
    "RepositoryPreflightCheck",
    "RepositoryPreflightOutcome",
    "RepositoryDryRunDirection",
    "RepositoryDryRunStep",
    "RepositoryEvolutionDryRun",
    "RepositoryEvolutionDryRunEngine",
    "RepositoryEvolutionExecution",
    "RepositoryEvolutionExecutor",
    "RepositoryExecutionAction",
    "RepositoryExecutionEvent",
    "RepositoryExecutionOutcome",
    "RepositoryExecutionStatus",
    "RepositoryFileMover",
    "NoOverwriteFileMover",
    "RepositoryEvolutionPostVerification",
    "RepositoryEvolutionPostVerifier",
    "RepositoryPostVerificationCheck",
    "RepositoryPostVerificationOutcome",
    "RepositoryEvolutionRecovery",
    "RepositoryEvolutionRecoveryPlanner",
    "RepositoryRecoveryDecision",
    "RepositoryRecoveryExecution",
    "RepositoryRecoveryExecutionStatus",
    "RepositoryEvolutionRecoveryExecutor",
    "RepositoryEvolutionPostRecoveryVerifier",
    "RepositoryPostRecoveryCheck",
    "RepositoryPostRecoveryOutcome",
    "RepositoryPostRecoveryVerification",
]
