"""Deterministic, fail-safe Repository Health assessment."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from app.architecture.models import ArchitectureGraph

from .file_registry_models import (
    FileGovernanceState,
    RepositoryFileEntry,
    RepositoryFileRegistry,
)
from .health_models import (
    RepositoryHealthCategory,
    RepositoryHealthCheck,
    RepositoryHealthOutcome,
    RepositoryHealthReport,
)
from .models import RepositoryFileClassification
from .verification_models import (
    RepositoryVerificationOutcome,
    RepositoryVerificationReport,
)


@dataclass(frozen=True, slots=True)
class RepositoryHealthEngine:
    @staticmethod
    def _validate_inputs(
        registry: RepositoryFileRegistry,
        verification: RepositoryVerificationReport,
        graph: ArchitectureGraph,
    ) -> None:
        if not registry.verify():
            raise ValueError("Repository file registry integrity verification failed")
        if not verification.verify():
            raise ValueError(
                "Repository verification report integrity verification failed"
            )
        if not graph.verify():
            raise ValueError("Architecture Graph integrity verification failed")
        if (
            len({
                registry.project_name,
                verification.project_name,
                graph.project_name,
            }) != 1
            or registry.source_revision != verification.source_revision
            or registry.source_revision != graph.source_revision
            or verification.registry_id != registry.registry_id
            or verification.registry_hash != registry.content_hash
        ):
            raise ValueError("Repository health input provenance does not match")
        nodes = {item.node_id: item for item in graph.nodes}
        project = nodes.get(f"project:{registry.project_name}")
        trace = (
            project.metadata.get("repository_traceability", {})
            if project else {}
        )
        if (
            trace.get("registry_id") != registry.registry_id
            or trace.get("registry_hash") != registry.content_hash
            or trace.get("verification_report_id") != verification.report_id
            or trace.get("verification_report_hash") != verification.content_hash
        ):
            raise ValueError("Architecture Graph traceability provenance is stale")
        registry_ids = {item.file_id for item in registry.entries}
        graph_file_ids = {
            item.node_id for item in graph.nodes if item.node_type == "File"
        }
        if graph_file_ids != registry_ids:
            raise ValueError("Architecture Graph file identities are incomplete")
        for entry in registry.entries:
            node = nodes[entry.file_id]
            if (
                node.source_path != entry.current_path
                or node.metadata.get("content_hash") != entry.content_hash
            ):
                raise ValueError("Architecture Graph file provenance is stale")
        entries_by_id = {item.file_id: item for item in registry.entries}
        for evaluation in verification.evaluations:
            entry = entries_by_id.get(evaluation.file_id)
            if (
                entry is None
                or evaluation.path != entry.current_path
                or evaluation.content_hash != entry.content_hash
            ):
                raise ValueError(
                    "Repository evaluation file provenance is stale"
                )
        graph_evaluations = {
            item.node_id: item for item in graph.nodes
            if item.node_type == "RepositoryEvaluation"
        }
        if set(graph_evaluations) != {
            item.evaluation_id for item in verification.evaluations
        }:
            raise ValueError(
                "Architecture Graph evaluation identities are incomplete"
            )
        for evaluation in verification.evaluations:
            node = graph_evaluations[evaluation.evaluation_id]
            if (
                node.source_path != evaluation.path
                or node.metadata.get("evidence_hash")
                != evaluation.evidence_hash
            ):
                raise ValueError(
                    "Architecture Graph evaluation provenance is stale"
                )

    @staticmethod
    def _check(
        category: RepositoryHealthCategory,
        outcome: RepositoryHealthOutcome,
        summary: str,
        entries: tuple[RepositoryFileEntry, ...] = (),
        *,
        evidence_ids: tuple[str, ...] = (),
        details: dict[str, object] | None = None,
    ) -> RepositoryHealthCheck:
        return RepositoryHealthCheck(
            "", category, outcome, summary,
            tuple(item.file_id for item in entries),
            tuple(item.current_path for item in entries),
            evidence_ids, details or {},
        ).finalized()

    def assess(
        self,
        registry: RepositoryFileRegistry,
        verification: RepositoryVerificationReport,
        graph: ArchitectureGraph,
        *,
        as_of: str,
    ) -> RepositoryHealthReport:
        self._validate_inputs(registry, verification, graph)
        checks = []

        leakage = tuple(
            item for item in registry.entries
            if item.classification in {
                RepositoryFileClassification.GENERATED,
                RepositoryFileClassification.TEMPORARY,
            }
        )
        checks.append(self._check(
            RepositoryHealthCategory.CANONICAL_LEAKAGE,
            RepositoryHealthOutcome.FINDING
            if leakage else RepositoryHealthOutcome.OBSERVED,
            "Tracked generated or temporary files were detected."
            if leakage else "No tracked generated or temporary files were detected.",
            leakage,
        ))

        unknown = tuple(
            item for item in registry.entries
            if item.classification is RepositoryFileClassification.UNKNOWN
        )
        checks.append(self._check(
            RepositoryHealthCategory.UNKNOWN_CLASSIFICATION,
            RepositoryHealthOutcome.FINDING
            if unknown else RepositoryHealthOutcome.OBSERVED,
            "Files with unknown classification were detected."
            if unknown else "Every tracked file has an explicit classification.",
            unknown,
        ))

        governance = tuple(
            item for item in registry.entries
            if item.governance_state is not FileGovernanceState.ASSIGNED
        )
        checks.append(self._check(
            RepositoryHealthCategory.GOVERNANCE_COVERAGE,
            RepositoryHealthOutcome.FINDING
            if governance else RepositoryHealthOutcome.OBSERVED,
            "Files with partial or unassigned governance were detected."
            if governance else "Every tracked file has complete governance.",
            governance,
            details={"state_counts": dict(registry.governance_counts)},
        ))

        entries_by_id = {item.file_id: item for item in registry.entries}
        policy_findings = tuple(
            item for item in verification.evaluations
            if item.outcome is RepositoryVerificationOutcome.FINDING
        )
        finding_entries = tuple(
            entries_by_id[item.file_id] for item in policy_findings
        )
        checks.append(self._check(
            RepositoryHealthCategory.POLICY_FINDINGS,
            RepositoryHealthOutcome.FINDING
            if policy_findings else RepositoryHealthOutcome.OBSERVED,
            "Repository policy findings remain unresolved."
            if policy_findings else "No repository policy findings were detected.",
            finding_entries,
            evidence_ids=tuple(item.evaluation_id for item in policy_findings),
        ))

        uncovered = tuple(
            item for item in verification.evaluations
            if item.outcome is RepositoryVerificationOutcome.NOT_EVALUATED
        )
        uncovered_entries = tuple(entries_by_id[item.file_id] for item in uncovered)
        checks.append(self._check(
            RepositoryHealthCategory.POLICY_COVERAGE,
            RepositoryHealthOutcome.FINDING
            if uncovered else RepositoryHealthOutcome.OBSERVED,
            "Files outside placement or naming policy coverage were detected."
            if uncovered else "Placement and naming policy coverage is complete.",
            uncovered_entries,
            evidence_ids=tuple(item.evaluation_id for item in uncovered),
            details={
                "domain_counts": dict(Counter(
                    item.domain.value for item in uncovered
                )),
            },
        ))

        excepted = tuple(
            item for item in verification.evaluations
            if item.outcome is RepositoryVerificationOutcome.EXCEPTED
        )
        excepted_entries = tuple(entries_by_id[item.file_id] for item in excepted)
        checks.append(self._check(
            RepositoryHealthCategory.POLICY_EXCEPTIONS,
            RepositoryHealthOutcome.ADVISORY
            if excepted else RepositoryHealthOutcome.OBSERVED,
            "Active repository policy exceptions require review."
            if excepted else "No active repository policy exception was used.",
            excepted_entries,
            evidence_ids=tuple(item.evaluation_id for item in excepted),
        ))

        by_hash: dict[str, list[RepositoryFileEntry]] = defaultdict(list)
        for entry in registry.entries:
            if entry.size > 0:
                by_hash[entry.content_hash].append(entry)
        duplicate_groups = tuple(
            tuple(group) for group in by_hash.values() if len(group) > 1
        )
        duplicate_entries = tuple(
            item for group in duplicate_groups for item in group
        )
        checks.append(self._check(
            RepositoryHealthCategory.NON_EMPTY_EXACT_DUPLICATION,
            RepositoryHealthOutcome.ADVISORY
            if duplicate_groups else RepositoryHealthOutcome.OBSERVED,
            "Non-empty files with byte-identical content were observed."
            if duplicate_groups else "No non-empty exact content duplicates were observed.",
            duplicate_entries,
            details={
                "groups": [
                    {
                        "content_hash": group[0].content_hash,
                        "file_ids": [item.file_id for item in group],
                        "paths": [item.current_path for item in group],
                    }
                    for group in duplicate_groups
                ],
                "interpretation": (
                    "Exact content equality does not authorize deletion."
                ),
            },
        ))

        capability_counts: dict[str, Counter[str]] = defaultdict(Counter)
        capability_entries: dict[str, list[RepositoryFileEntry]] = defaultdict(list)
        for entry in registry.entries:
            if entry.capability:
                capability_counts[entry.capability][
                    entry.classification.value
                ] += 1
                capability_entries[entry.capability].append(entry)
        missing_test_capabilities = tuple(sorted(
            capability for capability, counts in capability_counts.items()
            if counts[RepositoryFileClassification.CODE.value] > 0
            and counts[RepositoryFileClassification.TEST.value] == 0
        ))
        test_presence_entries = tuple(
            item
            for capability in missing_test_capabilities
            for item in capability_entries[capability]
            if item.classification is RepositoryFileClassification.CODE
        )
        checks.append(self._check(
            RepositoryHealthCategory.CAPABILITY_TEST_PRESENCE,
            RepositoryHealthOutcome.ADVISORY
            if missing_test_capabilities else RepositoryHealthOutcome.OBSERVED,
            "Capabilities with code but no colocated owned test files were observed."
            if missing_test_capabilities
            else "Every capability with code owns at least one test file.",
            test_presence_entries,
            details={
                "capabilities": list(missing_test_capabilities),
                "interpretation": (
                    "Structural presence is not execution or branch coverage."
                ),
            },
        ))

        unavailable = {
            RepositoryHealthCategory.DEAD_FILE_ANALYSIS: (
                "Canonical runtime usage and entrypoint evidence is unavailable."
            ),
            RepositoryHealthCategory.STALENESS: (
                "Canonical last-review timestamps and maximum-age policy are unavailable."
            ),
            RepositoryHealthCategory.EXECUTION_COVERAGE: (
                "A revision-bound execution and branch coverage artifact is unavailable."
            ),
            RepositoryHealthCategory.DOCUMENTATION_COVERAGE: (
                "Explicit document-to-capability relationships are unavailable."
            ),
        }
        for category, reason in unavailable.items():
            checks.append(self._check(
                category,
                RepositoryHealthOutcome.NOT_EVALUATED,
                f"{category.value} was not evaluated.",
                details={"reason": reason},
            ))

        report = RepositoryHealthReport(
            "", registry.project_name, registry.source_revision,
            registry.registry_id, registry.content_hash,
            verification.report_id, verification.content_hash,
            graph.graph_id, graph.content_hash, as_of, tuple(checks),
        ).finalized()
        if not report.verify():
            raise ValueError("Repository health report integrity verification failed")
        return report
