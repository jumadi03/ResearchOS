"""Application service orchestrating the ResearchOS architecture workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
from threading import RLock
from uuid import uuid4

from .graph_builder import ArchitectureGraphBuilder
from .governance import (
    ARCGenerator, ARCPublisher, ComplianceEngine, DependencyValidator,
    LawRegistry, LawResolution, PublicAPIValidator, ReviewEngine,
    ValidatorRegistry,
)
from .models import (
    ARCPackage, ArchitectureGraph, ArchitectureLawBundle, ReviewDecisionType,
    ReviewSession, ValidationReport,
)
from .persistence import (
    InterProcessFileLock,
    atomic_write,
    remove_internal_temporary_entries,
)


@dataclass(frozen=True, slots=True)
class ArchitecturePipelineRun:
    run_id: str
    graph: ArchitectureGraph
    law_bundle: ArchitectureLawBundle | None = None
    compliance_report: ValidationReport | None = None
    review: ReviewSession | None = None
    arc_package: ARCPackage | None = None


@dataclass(frozen=True, slots=True)
class PipelineArtifactStore:
    """Persist stage snapshots beneath a server-controlled output root."""

    root: Path

    @staticmethod
    def _safe(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", value)

    def run_directory(self, run_id: str) -> Path:
        return self.root / "runs" / self._safe(run_id)

    def _lock(self) -> InterProcessFileLock:
        return InterProcessFileLock(self.root / ".pipeline.lock")

    def recover(self) -> tuple[Path, ...]:
        with self._lock():
            return remove_internal_temporary_entries(self.root)

    def write_text(self, run_id: str, name: str, content: str) -> Path:
        target = self.run_directory(run_id) / name
        with self._lock():
            atomic_write(target, content)
        return target

    def write_arc(self, run_id: str, package: ARCPackage) -> Path:
        directory = self.run_directory(run_id) / "arc" / self._safe(
            package.manifest.arc_id
        )
        with self._lock():
            if directory.exists():
                raise FileExistsError(
                    f"Released ARC directories are immutable: {directory}"
                )
            directory.parent.mkdir(parents=True, exist_ok=True)
            staging = directory.parent / f".tmp-arc-{uuid4().hex}"
            try:
                package.write_to(staging)
                restored = ARCPackage.from_directory(staging)
                if restored.manifest.arc_id != package.manifest.arc_id:
                    raise ValueError("Staged ARC identity changed before commit")
                os.replace(staging, directory)
            finally:
                if staging.exists():
                    remove_internal_temporary_entries(staging.parent)
        return directory


class ArchitecturePipelineService:
    """Thread-safe coordinator for staged architecture governance runs."""

    def __init__(self, project_root: Path, output_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.store = PipelineArtifactStore(output_root.resolve())
        self._runs: dict[str, ArchitecturePipelineRun] = {}
        self._lock = RLock()
        self.rehydration_errors: dict[str, tuple[str, ...]] = {}
        self.recovered_temporary_entries = self.store.recover()
        self.rehydrate()

    def rehydrate(self) -> int:
        """Rebuild the active run index from verified persisted snapshots."""
        runs_root = self.store.root / "runs"
        if not runs_root.exists():
            return 0
        loaded = 0
        for directory in sorted(path for path in runs_root.iterdir() if path.is_dir()):
            errors: list[str] = []
            try:
                graph = ArchitectureGraph.from_json(
                    (directory / "architecture-graph.json").read_text(encoding="utf-8")
                )
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self.rehydration_errors[directory.name] = (f"graph:{exc}",)
                continue

            run_id = f"run:{graph.content_hash[:16]}"
            run = ArchitecturePipelineRun(run_id=run_id, graph=graph)

            laws_path = directory / "laws.json"
            if laws_path.exists():
                try:
                    run = replace(
                        run,
                        law_bundle=ArchitectureLawBundle.from_json(
                            laws_path.read_text(encoding="utf-8")
                        ),
                    )
                except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"laws:{exc}")

            report_path = directory / "compliance-report.json"
            if run.law_bundle and report_path.exists():
                try:
                    report = ValidationReport.from_json(
                        report_path.read_text(encoding="utf-8")
                    )
                    metadata = report.metadata or {}
                    if metadata.get("graph_id") != graph.graph_id or metadata.get(
                        "graph_hash"
                    ) != graph.content_hash:
                        raise ValueError("graph provenance mismatch")
                    run = replace(run, compliance_report=report)
                except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"compliance:{exc}")

            review_path = directory / "review.json"
            if run.compliance_report and review_path.exists():
                try:
                    review = ReviewSession.from_json(
                        review_path.read_text(encoding="utf-8")
                    )
                    if review.graph_id != graph.graph_id or review.graph_hash != graph.content_hash:
                        raise ValueError("graph provenance mismatch")
                    report_findings = {
                        violation.violation_id
                        for result in run.compliance_report.validation_results
                        for violation in result.violations
                    }
                    if {item.finding_id for item in review.findings} != report_findings:
                        raise ValueError("review findings mismatch")
                    run = replace(run, review=review)
                except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"review:{exc}")

            location_path = directory / "arc-location.json"
            if run.law_bundle and run.compliance_report and run.review:
                arc_root = directory / "arc"
                candidates = sorted(
                    (
                        path for path in arc_root.iterdir()
                        if path.is_dir() and not path.name.startswith(".tmp-")
                    ),
                    key=lambda path: path.name,
                ) if arc_root.exists() else []
                if location_path.exists():
                    try:
                        location = json.loads(location_path.read_text(encoding="utf-8"))
                        directory_name = location["directory_name"]
                        if directory_name != self.store._safe(directory_name):
                            raise ValueError("unsafe ARC directory name")
                        preferred = arc_root / directory_name
                        candidates = [preferred, *(item for item in candidates if item != preferred)]
                    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(f"arc-location:{exc}")

                valid_packages: list[ARCPackage] = []
                for candidate in candidates:
                    try:
                        package = ARCPackage.from_directory(candidate)
                        manifest = package.manifest
                        if (
                            manifest.graph_hash != graph.content_hash
                            or manifest.law_bundle_hash != run.law_bundle.content_hash
                            or manifest.compliance_hash
                            != run.compliance_report.calculate_content_hash()
                            or manifest.review_hash != run.review.calculate_content_hash()
                        ):
                            raise ValueError("ARC provenance mismatch")
                        valid_packages.append(package)
                    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                        errors.append(f"arc:{candidate.name}:{exc}")
                if valid_packages:
                    run = replace(
                        run,
                        arc_package=max(
                            valid_packages,
                            key=lambda item: (
                                item.manifest.generated_at,
                                item.manifest.arc_id,
                            ),
                        ),
                    )

            self._save(run)
            loaded += 1
            if errors:
                self.rehydration_errors[run_id] = tuple(errors)
        return loaded

    def get(self, run_id: str) -> ArchitecturePipelineRun:
        with self._lock:
            try:
                return self._runs[run_id]
            except KeyError as exc:
                raise KeyError(f"Unknown architecture run: {run_id}") from exc

    def _save(self, run: ArchitecturePipelineRun) -> ArchitecturePipelineRun:
        with self._lock:
            self._runs[run.run_id] = run
        return run

    def scan(self, *, project_name: str, source_revision: str) -> ArchitecturePipelineRun:
        graph = ArchitectureGraphBuilder(
            self.project_root, project_name, source_revision
        ).build()
        run = self._save(
            ArchitecturePipelineRun(
                run_id=f"run:{graph.content_hash[:16]}",
                graph=graph,
            )
        )
        self.store.write_text(run.run_id, "architecture-graph.json", graph.to_json())
        return run

    def register_laws(
        self, run_id: str, bundle: ArchitectureLawBundle
    ) -> ArchitecturePipelineRun:
        bundle = bundle if bundle.content_hash else bundle.finalized()
        current = self.get(run_id)
        updated = self._save(
            replace(
                current, law_bundle=bundle, compliance_report=None,
                review=None, arc_package=None,
            )
        )
        self.store.write_text(run_id, "laws.json", bundle.to_json())
        return updated

    def run_compliance(self, run_id: str, *, as_of: str) -> ArchitecturePipelineRun:
        current = self.get(run_id)
        if current.law_bundle is None:
            raise ValueError("A law bundle must be registered before compliance")
        resolution = LawResolution(LawRegistry.from_bundle(current.law_bundle))
        report = ComplianceEngine(
            ValidatorRegistry(
                (DependencyValidator(resolution), PublicAPIValidator(resolution))
            )
        ).validate(current.graph, as_of=as_of)
        updated = self._save(
            replace(current, compliance_report=report, review=None, arc_package=None)
        )
        self.store.write_text(run_id, "compliance-report.json", report.to_json())
        return updated

    def open_review(
        self, run_id: str, *, reviewer: str, opened_at: str
    ) -> ArchitecturePipelineRun:
        current = self.get(run_id)
        if current.compliance_report is None:
            raise ValueError("Compliance must run before review")
        review = ReviewEngine().open(
            current.compliance_report, reviewer=reviewer, opened_at=opened_at
        )
        updated = self._save(replace(current, review=review, arc_package=None))
        self.store.write_text(run_id, "review.json", review.to_json())
        return updated

    def decide(
        self, run_id: str, *, finding_id: str,
        decision_type: ReviewDecisionType, rationale: str, reviewer: str,
        decided_at: str, expires_at: str | None = None,
    ) -> ArchitecturePipelineRun:
        current = self.get(run_id)
        if current.review is None:
            raise ValueError("A review must be opened before recording decisions")
        review = ReviewEngine().decide(
            current.review, finding_id=finding_id, decision_type=decision_type,
            rationale=rationale, reviewer=reviewer, decided_at=decided_at,
            expires_at=expires_at,
        )
        updated = self._save(replace(current, review=review, arc_package=None))
        self.store.write_text(run_id, "review.json", review.to_json())
        return updated

    def finalize_review(
        self, run_id: str, *, actor: str, occurred_at: str, as_of: str
    ) -> ArchitecturePipelineRun:
        current = self.get(run_id)
        if current.review is None:
            raise ValueError("A review must be opened before finalization")
        review = ReviewEngine().mark_stale(
            current.review, current_graph_hash=current.graph.content_hash,
            actor=actor, occurred_at=occurred_at,
        )
        if review.status.value != "STALE":
            review = ReviewEngine().finalize(
                review, actor=actor, occurred_at=occurred_at, as_of=as_of
            )
        updated = self._save(replace(current, review=review, arc_package=None))
        self.store.write_text(run_id, "review.json", review.to_json())
        return updated

    def generate_arc(
        self, run_id: str, *, generated_at: str, publish: bool,
        actor: str = "system",
    ) -> ArchitecturePipelineRun:
        current = self.get(run_id)
        if not current.law_bundle or not current.compliance_report or not current.review:
            raise ValueError("Law, compliance, and review stages must be complete")
        package = ARCGenerator().generate(
            graph=current.graph, law_bundle=current.law_bundle,
            compliance_report=current.compliance_report, review=current.review,
            generated_at=generated_at, generated_by=actor,
        )
        if publish:
            package = ARCPublisher().publish(package)
        directory = self.store.write_arc(run_id, package)
        updated = self._save(replace(current, arc_package=package))
        self.store.write_text(
            run_id, "arc-location.json",
            json.dumps(
                {
                    "arc_id": package.manifest.arc_id,
                    "directory_name": directory.name,
                },
                indent=2, sort_keys=True,
            ),
        )
        return updated
