"""Theory, gap, validation, and publication orchestration."""

from dataclasses import asdict
from pathlib import Path

from app.knowledge.gaps.detector import ResearchGapDetector
from app.knowledge.gaps.persistence import GapAnalysisStore
from app.knowledge.models import DiscoveryRun
from app.knowledge.publication.engine import PublicationEngine
from app.knowledge.publication.models import PublicationKind
from app.knowledge.publication.persistence import PublicationStore
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.models import TheoryReviewState
from app.knowledge.theory.persistence import TheoryBundleStore
from app.knowledge.validation.engine import ValidationEngine
from app.knowledge.validation.models import RiskOfBias
from app.knowledge.validation.persistence import ValidationReportStore


class KnowledgeTheoryPipeline:
    def __init__(
        self, output_root: Path, graphs: dict, *, data_repository=None,
        object_store=None,
    ) -> None:
        self.graphs = graphs
        self.data_repository = data_repository
        self.object_store = object_store
        self.theory_builder = TheoryBuilder()
        self.theory_store = TheoryBundleStore(output_root / "theories")
        self.gap_detector = ResearchGapDetector()
        self.gap_store = GapAnalysisStore(output_root / "gaps")
        self.validation_engine = ValidationEngine()
        self.validation_store = ValidationReportStore(output_root / "validations")
        self.publication_engine = PublicationEngine()
        self.publication_store = PublicationStore(output_root / "publications")
        self.bundles = {
            item.bundle_id: item for item in self.theory_store.load_all()
        }
        self.validation_reports = {
            item.report_id: item for item in self.validation_store.load_all()
        }

    def build_theories(self, graph_ids: tuple[str, ...], *, generated_by: str):
        missing = [item for item in graph_ids if item not in self.graphs]
        if missing:
            raise KeyError(f"Unknown knowledge graph: {missing[0]}")
        bundle = self.theory_builder.build(
            tuple(self.graphs[item] for item in graph_ids),
            created_at=DiscoveryRun.timestamp(),
        )
        self.bundles[bundle.bundle_id] = bundle
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=bundle.bundle_id, project_id=bundle.bundle_id,
                artifact_type="theory_bundle", title="Scientific theory bundle",
                status="draft", metadata=asdict(bundle), actor_id=generated_by,
                occurred_at=bundle.created_at,
            )
        return bundle, self.theory_store.save(bundle)

    def review_theory(self, bundle_id, **options):
        bundle = self.bundles.get(bundle_id)
        if bundle is None:
            raise KeyError(f"Unknown theory bundle: {bundle_id}")
        decision = options.pop("decision")
        reviewed = self.theory_builder.review(
            bundle, decision=TheoryReviewState(decision), **options
        )
        self.bundles[bundle_id] = reviewed
        return reviewed, self.theory_store.save(reviewed)

    def align_theories(self, bundle_id, **options):
        bundle = self._bundle(bundle_id)
        aligned = self.theory_builder.align(bundle, **options)
        self.bundles[bundle_id] = aligned
        return aligned, self.theory_store.save(aligned)

    def alignment_candidates(self, bundle_id):
        return self.theory_builder.alignment_candidates(self._bundle(bundle_id))

    def keep_theories_separate(self, bundle_id, **options):
        bundle = self._bundle(bundle_id)
        decided = self.theory_builder.keep_separate(bundle, **options)
        self.bundles[bundle_id] = decided
        return decided, self.theory_store.save(decided)

    def alignment_history(self, bundle_id):
        bundle = self._bundle(bundle_id)
        proposals = {item.theory_id: item for item in bundle.proposals}
        entries = []
        for event in bundle.alignments:
            result = proposals.get(event.resulting_theory_id)
            entries.append({
                "decision_id": event.alignment_id,
                "decision": "aligned",
                "theory_ids": event.source_theory_ids,
                "resulting_theory_id": event.resulting_theory_id,
                "statements": (event.statement,),
                "reviewer": event.reviewer,
                "rationale": event.rationale,
                "occurred_at": event.occurred_at,
                "evidence_by_theory": (
                    tuple(asdict(item) for item in result.evidence) if result else (),
                ),
            })
        for event in bundle.alignment_decisions:
            sources = tuple(proposals.get(item) for item in event.theory_ids)
            entries.append({
                "decision_id": event.decision_id,
                "decision": event.decision,
                "theory_ids": event.theory_ids,
                "resulting_theory_id": None,
                "statements": tuple(
                    item.statement if item else "Historical source theory"
                    for item in sources
                ),
                "reviewer": event.reviewer,
                "rationale": event.rationale,
                "occurred_at": event.occurred_at,
                "evidence_by_theory": tuple(
                    tuple(asdict(evidence) for evidence in item.evidence)
                    if item else () for item in sources
                ),
            })
        all_reports = sorted(
            (item for item in self.validation_reports.values()
             if item.theory_bundle_id == bundle_id),
            key=lambda item: (item.assessed_at, item.report_id), reverse=True,
        )
        reports = tuple(
            item for item in all_reports
            if item.theory_bundle_hash == bundle.content_hash
        )
        invalidation_reason = None
        if not reports:
            invalidation_reason = (
                "theory_bundle_changed_after_reviewer_decision"
                if all_reports else "never_validated"
            )
        return {
            "bundle_id": bundle_id,
            "latest_validation": ({
                "report_id": reports[0].report_id,
                "status": reports[0].status.value,
                "assessed_at": reports[0].assessed_at,
            } if reports else None),
            "validation_state": {
                "active": bool(reports),
                "reason": invalidation_reason,
            },
            "active_theories": tuple({
                "theory_id": item.theory_id,
                "statement": item.statement,
                "review_state": item.review_state.value,
            } for item in bundle.proposals),
            "items": tuple(sorted(
                entries,
                key=lambda item: (item["occurred_at"], item["decision_id"]),
                reverse=True,
            )),
        }

    def list_theory_bundles(self):
        summaries = []
        for bundle in self.bundles.values():
            reports = sorted(
                (item for item in self.validation_reports.values()
                 if item.theory_bundle_id == bundle.bundle_id
                 and item.theory_bundle_hash == bundle.content_hash),
                key=lambda item: (item.assessed_at, item.report_id), reverse=True,
            )
            candidates = self.theory_builder.alignment_candidates(bundle)
            summaries.append({
                "bundle_id": bundle.bundle_id,
                "created_at": bundle.created_at,
                "graph_count": len(bundle.graph_ids),
                "theory_count": len(bundle.proposals),
                "accepted_count": sum(
                    item.review_state is TheoryReviewState.ACCEPTED
                    for item in bundle.proposals
                ),
                "pending_review_count": sum(
                    item.review_state is TheoryReviewState.PROPOSED
                    for item in bundle.proposals
                ),
                "alignment_count": len(bundle.alignments),
                "keep_separate_count": len(bundle.alignment_decisions),
                "candidate_count": len(candidates),
                "latest_validation": ({
                    "report_id": reports[0].report_id,
                    "status": reports[0].status.value,
                    "assessed_at": reports[0].assessed_at,
                } if reports else None),
                "schema_version": bundle.schema_version,
                "content_hash": bundle.content_hash,
            })
        return tuple(sorted(
            summaries, key=lambda item: (item["created_at"], item["bundle_id"]),
            reverse=True,
        ))

    def detect_research_gaps(self, bundle_id: str, *, generated_by: str):
        bundle = self._bundle(bundle_id)
        analysis = self.gap_detector.analyze(
            bundle, created_at=DiscoveryRun.timestamp()
        )
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=analysis.analysis_id, project_id=bundle_id,
                artifact_type="gap_analysis", title="Research gap analysis",
                status="draft", metadata=asdict(analysis), actor_id=generated_by,
                occurred_at=analysis.created_at,
            )
        return analysis, self.gap_store.save(analysis)

    def validate_theories(self, bundle_id, **options):
        bundle = self._bundle(bundle_id)
        risk = options.pop("risk_of_bias_by_theory")
        trigger = options.get("triggered_by_decision_id")
        if trigger:
            decision_ids = {
                item.alignment_id for item in bundle.alignments
            } | {
                item.decision_id for item in bundle.alignment_decisions
            }
            if trigger not in decision_ids:
                raise ValueError("Validation trigger is not a decision in this bundle")
        report = self.validation_engine.validate(
            bundle,
            bias_by_theory={key: RiskOfBias(value) for key, value in risk.items()},
            **options,
        )
        self.validation_reports[report.report_id] = report
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=report.report_id, project_id=bundle_id,
                artifact_type="validation_report", title="Theory validation report",
                status="validated", metadata=asdict(report),
                actor_id=options["reviewer"], occurred_at=report.assessed_at,
            )
        return report, self.validation_store.save(report)

    def validation_history(self, bundle_id):
        bundle = self._bundle(bundle_id)
        reports = sorted(
            (item for item in self.validation_reports.values()
             if item.theory_bundle_id == bundle_id),
            key=lambda item: (item.assessed_at, item.report_id), reverse=True,
        )
        return tuple({
            **asdict(item),
            "active_for_current_bundle": item.theory_bundle_hash == bundle.content_hash,
        } for item in reports)

    def publish(self, bundle_id, *, validation_report_id, kind, generated_at, generated_by):
        bundle = self._bundle(bundle_id)
        report = self.validation_reports.get(validation_report_id)
        if report is None:
            raise KeyError(f"Unknown validation report: {validation_report_id}")
        package = self.publication_engine.publish(
            bundle, report, kind=PublicationKind(kind), generated_at=generated_at,
            generated_by=generated_by,
        )
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=package.manifest.publication_id, project_id=bundle_id,
                artifact_type="publication_package",
                title=package.manifest.kind.value.replace("_", " ").title(),
                status="published", metadata=asdict(package), actor_id=generated_by,
                occurred_at=generated_at,
            )
        if self.object_store is not None:
            if self.data_repository is None:
                raise RuntimeError("Publication object storage requires canonical repository")
            markdown = package.markdown.encode("utf-8")
            storage_uri = self.object_store.put_bytes(
                markdown, media_type="text/markdown",
                checksum_sha256=package.manifest.markdown_hash,
                extension="md", namespace="publications",
            )
            self.data_repository.persist_publication_representation(
                package.manifest.publication_id, storage_uri=storage_uri,
                media_type="text/markdown",
                checksum_sha256=package.manifest.markdown_hash,
                file_size=len(markdown), representation_type="markdown",
                edition_type="canonical", published_at=generated_at,
            )
        return package, self.publication_store.save(package)

    def _bundle(self, bundle_id):
        bundle = self.bundles.get(bundle_id)
        if bundle is None:
            raise KeyError(f"Unknown theory bundle: {bundle_id}")
        return bundle
