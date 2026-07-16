"""Theory, gap, validation, and publication orchestration."""

from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from app.knowledge.gaps.detector import ResearchGapDetector
from app.knowledge.gaps.persistence import GapAnalysisStore
from app.knowledge.models import DiscoveryRun
from app.knowledge.modeling.admission import EvidenceAdmissionGate
from app.knowledge.publication.engine import PublicationEngine
from app.knowledge.publication.models import PublicationKind
from app.knowledge.publication.persistence import PublicationStore
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.calibration import (
    AlignmentCalibration, AlignmentCalibrationStore, CalibrationCase,
    CalibrationCaseStore, CalibrationReview,
)
from app.knowledge.theory.models import TheoryReviewState
from app.knowledge.theory.persistence import TheoryBundleStore
from app.knowledge.theory.quality import AlignmentQualityEvaluator
from app.knowledge.theory.translation import (
    TheoryTranslation, TheoryTranslationStore,
)
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
        self.evidence_admission_gate = EvidenceAdmissionGate()
        self.alignment_quality_evaluator = AlignmentQualityEvaluator()
        self.calibration_store = AlignmentCalibrationStore(
            output_root / "alignment-calibrations"
        )
        self.calibration_case_store = CalibrationCaseStore(
            output_root / "alignment-calibration-cases"
        )
        self.calibration_cases = {
            item.case_id: item for item in self.calibration_case_store.load_all()
        }
        self.translation_store = TheoryTranslationStore(
            output_root / "theory-translations"
        )
        self.translations = {
            item.translation_id: item for item in self.translation_store.load_all()
        }
        self.calibrations = list(self.calibration_store.load_all())
        approved_calibrations = [
            item for item in self.calibrations if item.status == "approved"
        ]
        if approved_calibrations:
            active = approved_calibrations[0]
            self.theory_builder.candidate_method = active.method
            self.theory_builder.candidate_threshold = active.proposed_threshold
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
        self.publication_packages = {
            item.manifest.publication_id: item
            for item in self.publication_store.load_all()
        }

    def build_theories(self, graph_ids: tuple[str, ...], *, generated_by: str):
        missing = [item for item in graph_ids if item not in self.graphs]
        if missing:
            raise KeyError(f"Unknown knowledge graph: {missing[0]}")
        if self.data_repository is None:
            raise ValueError(
                "Canonical repository is required for evidence admission"
            )
        graphs = tuple(self.graphs[item] for item in graph_ids)
        for graph in graphs:
            object_ids = tuple(sorted({
                node.provenance.object_id
                for node in graph.nodes if node.provenance is not None
            }))
            admissions = self.data_repository.resolve_evidence_admissions(
                object_ids
            )
            self.evidence_admission_gate.revalidate(graph, admissions)
        bundle = self.theory_builder.build(
            graphs,
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

    def alignment_candidate_metadata(self):
        return {
            "method": self.theory_builder.candidate_method,
            "threshold": self.theory_builder.candidate_threshold,
            "scoring": {
                "content_term_jaccard_weight": 0.85,
                "content_bigram_jaccard_weight": 0.15,
                "minimum_shared_content_terms": 2,
                "opposing_polarity_excluded": True,
            },
        }

    def theory_translation_source(self, bundle_id, theory_id):
        bundle = self._bundle(bundle_id)
        proposal = next((
            item for item in bundle.proposals if item.theory_id == theory_id
        ), None)
        if proposal is None:
            raise KeyError(f"Unknown theory proposal: {theory_id}")
        return {
            "bundle_id": bundle_id, "theory_id": theory_id,
            "statement": proposal.statement,
            "source_hash": TheoryTranslation.hash_source(proposal.statement),
        }

    def record_theory_translation(
        self, bundle_id, theory_id, *, translated_statement, provider,
        model, generated_by, generated_at,
    ):
        source = self.theory_translation_source(bundle_id, theory_id)
        translated = translated_statement.strip()
        if not translated:
            raise ValueError("Translated statement is required")
        identity = (
            f"{bundle_id}:{theory_id}:id:{source['source_hash']}"
        )
        item = TheoryTranslation(
            translation_id=f"theory-translation-{sha256(identity.encode()).hexdigest()[:24]}",
            bundle_id=bundle_id, theory_id=theory_id,
            source_language="original", target_language="id",
            source_statement=source["statement"],
            source_hash=source["source_hash"],
            translated_statement=translated,
            provider=provider, model=model, generated_by=generated_by,
            generated_at=generated_at,
        ).finalized()
        self.translations[item.translation_id] = item
        return item, self.translation_store.save(item)

    def theory_translations(self, bundle_id):
        bundle = self._bundle(bundle_id)
        by_theory = {}
        for item in self.translations.values():
            proposal = next((
                proposal for proposal in bundle.proposals
                if proposal.theory_id == item.theory_id
            ), None)
            if (
                item.bundle_id == bundle_id and proposal is not None
                and item.source_hash == TheoryTranslation.hash_source(proposal.statement)
            ):
                by_theory[item.theory_id] = item
        return tuple(
            asdict(by_theory[item.theory_id])
            for item in bundle.proposals if item.theory_id in by_theory
        )

    def review_theory_translation(
        self, translation_id, *, reviewer, rationale, reviewed_at,
        corrected_translation=None,
    ):
        item = self.translations.get(translation_id)
        if item is None:
            raise KeyError(f"Unknown theory translation: {translation_id}")
        if not rationale.strip():
            raise ValueError("Translation review rationale is required")
        source = self.theory_translation_source(item.bundle_id, item.theory_id)
        if source["source_hash"] != item.source_hash:
            raise ValueError("Translation source has changed and must be regenerated")
        translation = (
            corrected_translation.strip()
            if corrected_translation is not None else item.translated_statement
        )
        if not translation:
            raise ValueError("Reviewed translation is required")
        reviewed = replace(
            item, translated_statement=translation, status="reviewed",
            reviewer=reviewer, review_rationale=rationale.strip(),
            reviewed_at=reviewed_at, content_hash="",
        ).finalized()
        self.translations[translation_id] = reviewed
        return reviewed, self.translation_store.save(reviewed)

    def alignment_quality(self, bundle_id, *, threshold=None):
        bundle = self._bundle(bundle_id)
        simulated_threshold = (
            self.theory_builder.candidate_threshold
            if threshold is None else threshold
        )
        benchmark = self.alignment_quality_evaluator.benchmark(
            threshold=simulated_threshold
        )
        observations = [
            ("aligned", item.candidate_score)
            for item in bundle.alignments if item.candidate_method
        ] + [
            ("keep_separate", item.candidate_score)
            for item in bundle.alignment_decisions if item.candidate_method
        ] + [
            ("pending", item.lexical_overlap_score)
            for item in self.theory_builder.alignment_candidates(bundle)
        ]
        ranges = ((0.0, 0.19), (0.2, 0.39), (0.4, 0.59), (0.6, 0.79), (0.8, 1.0))
        distribution = []
        for lower, upper in ranges:
            counts = {"aligned": 0, "keep_separate": 0, "pending": 0}
            for outcome, score in observations:
                if score is not None and lower <= score <= upper:
                    counts[outcome] += 1
            distribution.append({
                "range": f"{lower:.2f}-{upper:.2f}", **counts,
            })
        aligned = sum(1 for outcome, _ in observations if outcome == "aligned")
        kept = sum(1 for outcome, _ in observations if outcome == "keep_separate")
        reviewed = aligned + kept
        historical = sum(
            1 for item in bundle.alignments if not item.candidate_method
        ) + sum(
            1 for item in bundle.alignment_decisions if not item.candidate_method
        )
        return {
            "bundle_id": bundle_id,
            "method": self.theory_builder.candidate_method,
            "production_threshold": self.theory_builder.candidate_threshold,
            "simulated_threshold": simulated_threshold,
            "simulation_only": True,
            "outcomes": {
                "reviewed": reviewed, "aligned": aligned,
                "keep_separate": kept,
                "pending": sum(1 for outcome, _ in observations if outcome == "pending"),
                "unscored_historical": historical,
                "alignment_acceptance_rate": round(aligned / reviewed, 4) if reviewed else None,
                "keep_separate_rate": round(kept / reviewed, 4) if reviewed else None,
            },
            "score_distribution": tuple(distribution),
            "benchmark": benchmark,
        }

    def alignment_calibration_summary(self):
        observations = self._calibration_observations()
        recommendation = self._recommended_threshold(observations)
        cases = tuple(self.calibration_cases.values())
        return {
            "method": self.theory_builder.candidate_method,
            "production_threshold": self.theory_builder.candidate_threshold,
            "minimum_reviewed_outcomes": 30,
            "reviewed_outcomes": len(observations),
            "eligible_to_propose": len(observations) >= 30,
            "recommendation": recommendation,
            "queue": {
                "total": len(cases),
                "awaiting_first_review": sum(
                    item.status == "awaiting_first_review" for item in cases
                ),
                "awaiting_second_review": sum(
                    item.status == "awaiting_second_review" for item in cases
                ),
                "disputed": sum(item.status == "disputed" for item in cases),
                "finalized": sum(item.status == "finalized" for item in cases),
                "agreement_rate": self._calibration_agreement_rate(cases),
                "by_stratum": tuple({
                    "stratum": stratum,
                    "count": sum(item.stratum == stratum for item in cases),
                    "finalized": sum(
                        item.stratum == stratum and item.status == "finalized"
                        for item in cases
                    ),
                } for stratum in ("0.00-0.19", "0.20-0.39", "0.40-0.59", "0.60-0.79", "0.80-1.00")),
            },
            "proposals": tuple(asdict(item) for item in self.calibrations),
        }

    def refresh_calibration_queue(self, *, created_at):
        existing = {
            (item.bundle_id, item.theory_ids)
            for item in self.calibration_cases.values()
        }
        available = {key: [] for key in (
            "0.00-0.19", "0.20-0.39", "0.40-0.59", "0.60-0.79", "0.80-1.00",
        )}
        for bundle in self.bundles.values():
            accepted = tuple(sorted(
                (item for item in bundle.proposals
                 if item.review_state is TheoryReviewState.ACCEPTED),
                key=lambda item: item.theory_id,
            ))
            for index, left in enumerate(accepted):
                for right in accepted[index + 1:]:
                    theory_ids = (left.theory_id, right.theory_id)
                    if (bundle.bundle_id, theory_ids) in existing:
                        continue
                    signals = self.theory_builder.candidate_signals(
                        left.statement, right.statement, threshold=0.0,
                    )
                    graph_ids = tuple(sorted({
                        evidence.graph_id
                        for proposal in (left, right)
                        for evidence in proposal.evidence
                    }))
                    if (
                        len(signals["shared_terms"]) < 2
                        or not signals["polarity_match"]
                        or len(graph_ids) < 2
                    ):
                        continue
                    score = signals["score"]
                    stratum = self._score_stratum(score)
                    available[stratum].append((
                        bundle, left, right, theory_ids, graph_ids, score,
                    ))
        created = []
        target_per_stratum = 6
        for stratum, candidates in available.items():
            current = sum(
                item.stratum == stratum for item in self.calibration_cases.values()
            )
            for bundle, left, right, theory_ids, graph_ids, score in sorted(
                candidates,
                key=lambda entry: sha256(
                    f"{entry[0].bundle_id}:{':'.join(entry[3])}".encode()
                ).hexdigest(),
            )[:max(0, target_per_stratum - current)]:
                identity = f"{bundle.bundle_id}:{':'.join(theory_ids)}:{self.theory_builder.candidate_method}"
                case = CalibrationCase(
                    case_id=f"calibration-case-{sha256(identity.encode()).hexdigest()[:24]}",
                    bundle_id=bundle.bundle_id, theory_ids=theory_ids,
                    statements=(left.statement, right.statement),
                    graph_ids=graph_ids,
                    evidence_by_theory=(
                        tuple(asdict(item) for item in left.evidence),
                        tuple(asdict(item) for item in right.evidence),
                    ),
                    method=self.theory_builder.candidate_method,
                    score=score, stratum=stratum, created_at=created_at,
                ).finalized()
                self.calibration_cases[case.case_id] = case
                self.calibration_case_store.save(case)
                created.append(case)
        return {
            "created": len(created),
            "queue": self.alignment_calibration_summary()["queue"],
        }

    def next_calibration_case(self, *, reviewer):
        eligible = tuple(sorted(
            (
                item for item in self.calibration_cases.values()
                if item.status in {"awaiting_first_review", "awaiting_second_review"}
                and reviewer not in {review.reviewer for review in item.reviews}
            ),
            key=lambda item: (
                item.status != "awaiting_second_review",
                len(item.reviews), item.created_at, item.case_id,
            ),
        ))
        return self._blind_calibration_case(eligible[0]) if eligible else None

    def review_calibration_case(
        self, case_id, *, reviewer, decision, rationale, reviewed_at,
    ):
        case = self._calibration_case(case_id)
        if case.status not in {"awaiting_first_review", "awaiting_second_review"}:
            raise ValueError("Calibration case is not awaiting an independent review")
        if reviewer in {item.reviewer for item in case.reviews}:
            raise ValueError("A reviewer cannot review the same calibration case twice")
        if decision not in {"aligned", "keep_separate"}:
            raise ValueError("Calibration decision must be aligned or keep_separate")
        if not rationale.strip():
            raise ValueError("Calibration review rationale is required")
        reviews = case.reviews + (
            CalibrationReview(
                reviewer, decision, rationale.strip(), reviewed_at,
            ),
        )
        if len(reviews) == 1:
            status, outcome, finalized_at = "awaiting_second_review", None, None
        elif reviews[0].decision == reviews[1].decision:
            status, outcome, finalized_at = "finalized", decision, reviewed_at
        else:
            status, outcome, finalized_at = "disputed", None, None
        reviewed = replace(
            case, reviews=reviews, status=status, final_outcome=outcome,
            finalized_at=finalized_at, content_hash="",
        ).finalized()
        self.calibration_cases[case_id] = reviewed
        return self._blind_calibration_case(reviewed), self.calibration_case_store.save(reviewed)

    def calibration_disputes(self, *, reviewer):
        return tuple(
            self._blind_calibration_case(item)
            for item in sorted(
                self.calibration_cases.values(),
                key=lambda entry: (entry.created_at, entry.case_id),
            )
            if item.status == "disputed"
            and reviewer not in {review.reviewer for review in item.reviews}
        )

    def adjudicate_calibration_case(
        self, case_id, *, reviewer, decision, rationale, reviewed_at,
    ):
        case = self._calibration_case(case_id)
        if case.status != "disputed":
            raise ValueError("Calibration case is not awaiting adjudication")
        if reviewer in {item.reviewer for item in case.reviews}:
            raise ValueError("Adjudication requires a third reviewer")
        if decision not in {"aligned", "keep_separate"}:
            raise ValueError("Calibration decision must be aligned or keep_separate")
        if not rationale.strip():
            raise ValueError("Adjudication rationale is required")
        reviews = case.reviews + (
            CalibrationReview(
                reviewer, decision, rationale.strip(), reviewed_at,
                role="adjudicator",
            ),
        )
        adjudicated = replace(
            case, reviews=reviews, status="finalized",
            final_outcome=decision, finalized_at=reviewed_at,
            content_hash="",
        ).finalized()
        self.calibration_cases[case_id] = adjudicated
        return self._blind_calibration_case(adjudicated), self.calibration_case_store.save(adjudicated)

    def propose_alignment_calibration(
        self, *, threshold, proposer, rationale, proposed_at,
    ):
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if not rationale.strip():
            raise ValueError("Calibration rationale is required")
        observations = self._calibration_observations()
        if len(observations) < 30:
            raise ValueError("Calibration requires at least 30 reviewed candidate outcomes")
        observed = self._threshold_metrics(observations, threshold)
        if observed["precision"] < 0.75 or observed["recall"] < 0.8:
            raise ValueError("Proposed threshold fails the observed reviewer-outcome floor")
        benchmark = self.alignment_quality_evaluator.benchmark(threshold=threshold)
        benchmark_metrics = benchmark["metrics"]
        if benchmark_metrics["precision"] < 0.75 or benchmark_metrics["recall"] < 1.0:
            raise ValueError("Proposed threshold fails the benchmark quality floor")
        sequence = len(self.calibrations) + 1
        identity = f"{threshold}:{proposer}:{proposed_at}:{sequence}"
        item = AlignmentCalibration(
            calibration_id=f"alignment-calibration-{sha256(identity.encode()).hexdigest()[:24]}",
            method=f"explainable-lexical-v2.{sequence}",
            version=f"2.{sequence}.0",
            current_threshold=self.theory_builder.candidate_threshold,
            proposed_threshold=threshold,
            reviewed_outcomes=len(observations),
            observed_precision=observed["precision"],
            observed_recall=observed["recall"],
            benchmark_precision=benchmark_metrics["precision"],
            benchmark_recall=benchmark_metrics["recall"],
            proposer=proposer, rationale=rationale.strip(),
            proposed_at=proposed_at,
            previous_version=self.theory_builder.candidate_method,
        ).finalized()
        self.calibrations.insert(0, item)
        return item, self.calibration_store.save(item)

    def approve_alignment_calibration(self, calibration_id, *, approver, approved_at):
        item = next((
            entry for entry in self.calibrations
            if entry.calibration_id == calibration_id
        ), None)
        if item is None:
            raise KeyError(f"Unknown alignment calibration: {calibration_id}")
        if item.status != "pending":
            raise ValueError("Calibration proposal is no longer pending")
        if item.proposer == approver:
            raise ValueError("Calibration approval requires a different reviewer")
        approved = replace(
            item, status="approved", approver=approver,
            approved_at=approved_at, content_hash="",
        ).finalized()
        self.calibrations = [
            approved if entry.calibration_id == calibration_id else entry
            for entry in self.calibrations
        ]
        self.theory_builder.candidate_method = approved.method
        self.theory_builder.candidate_threshold = approved.proposed_threshold
        return approved, self.calibration_store.save(approved)

    def rollback_alignment_calibration(
        self, *, approver, rationale, occurred_at,
    ):
        if not rationale.strip():
            raise ValueError("Rollback rationale is required")
        approved = [
            item for item in self.calibrations if item.status == "approved"
        ]
        if not approved:
            raise ValueError("No approved calibration is available to roll back")
        active = approved[0]
        if active.approver == approver:
            raise ValueError("Rollback requires a different reviewer")
        sequence = len(self.calibrations) + 1
        identity = f"rollback:{active.calibration_id}:{approver}:{occurred_at}"
        rollback = AlignmentCalibration(
            calibration_id=f"alignment-calibration-{sha256(identity.encode()).hexdigest()[:24]}",
            method=f"explainable-lexical-v2.{sequence}",
            version=f"2.{sequence}.0",
            current_threshold=active.proposed_threshold,
            proposed_threshold=active.current_threshold,
            reviewed_outcomes=active.reviewed_outcomes,
            observed_precision=active.observed_precision,
            observed_recall=active.observed_recall,
            benchmark_precision=active.benchmark_precision,
            benchmark_recall=active.benchmark_recall,
            proposer="system-rollback", rationale=rationale.strip(),
            proposed_at=occurred_at, status="approved", approver=approver,
            approved_at=occurred_at, previous_version=active.method,
        ).finalized()
        self.calibrations.insert(0, rollback)
        self.theory_builder.candidate_method = rollback.method
        self.theory_builder.candidate_threshold = rollback.proposed_threshold
        return rollback, self.calibration_store.save(rollback)

    def _calibration_observations(self):
        governed = tuple(
            (item.final_outcome == "aligned", item.score)
            for item in self.calibration_cases.values()
            if item.status == "finalized" and item.final_outcome is not None
        )
        return governed + tuple(
            (True, item.candidate_score)
            for bundle in self.bundles.values() for item in bundle.alignments
            if item.candidate_method and item.candidate_score is not None
        ) + tuple(
            (False, item.candidate_score)
            for bundle in self.bundles.values() for item in bundle.alignment_decisions
            if item.candidate_method and item.candidate_score is not None
        )

    @staticmethod
    def _score_stratum(score):
        if score < 0.2:
            return "0.00-0.19"
        if score < 0.4:
            return "0.20-0.39"
        if score < 0.6:
            return "0.40-0.59"
        if score < 0.8:
            return "0.60-0.79"
        return "0.80-1.00"

    @staticmethod
    def _calibration_agreement_rate(cases):
        double_reviewed = [
            item for item in cases if len(item.reviews) >= 2
        ]
        if not double_reviewed:
            return None
        agreements = sum(
            item.reviews[0].decision == item.reviews[1].decision
            for item in double_reviewed
        )
        return round(agreements / len(double_reviewed), 4)

    @staticmethod
    def _blind_calibration_case(case):
        return {
            "case_id": case.case_id, "bundle_id": case.bundle_id,
            "theory_ids": case.theory_ids, "statements": case.statements,
            "graph_ids": case.graph_ids,
            "evidence_by_theory": case.evidence_by_theory,
            "status": case.status, "review_count": len(case.reviews),
            "final_outcome": case.final_outcome,
            "created_at": case.created_at,
        }

    def _calibration_case(self, case_id):
        case = self.calibration_cases.get(case_id)
        if case is None:
            raise KeyError(f"Unknown calibration case: {case_id}")
        return case

    @staticmethod
    def _threshold_metrics(observations, threshold):
        true_positive = sum(expected and score >= threshold for expected, score in observations)
        false_positive = sum(not expected and score >= threshold for expected, score in observations)
        false_negative = sum(expected and score < threshold for expected, score in observations)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        return {"precision": round(precision, 4), "recall": round(recall, 4)}

    def _recommended_threshold(self, observations):
        if not observations:
            return None
        candidates = sorted({
            self.theory_builder.candidate_threshold,
            *(score for _, score in observations),
        })
        ranked = []
        for threshold in candidates:
            metrics = self._threshold_metrics(observations, threshold)
            precision, recall = metrics["precision"], metrics["recall"]
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            benchmark = self.alignment_quality_evaluator.benchmark(threshold=threshold)["metrics"]
            if benchmark["precision"] >= 0.75 and benchmark["recall"] >= 1.0:
                ranked.append((round(f1, 4), -abs(threshold - self.theory_builder.candidate_threshold), threshold, metrics))
        if not ranked:
            return None
        _, _, threshold, metrics = max(ranked)
        return {"threshold": threshold, **metrics}

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
                "candidate_method": event.candidate_method,
                "candidate_score": event.candidate_score,
                "candidate_threshold": event.candidate_threshold,
                "candidate_shared_terms": event.candidate_shared_terms,
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
                "candidate_method": event.candidate_method,
                "candidate_score": event.candidate_score,
                "candidate_threshold": event.candidate_threshold,
                "candidate_shared_terms": event.candidate_shared_terms,
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
        location = self.publication_store.save(package)
        self.publication_packages[package.manifest.publication_id] = package
        return package, location

    def publication_readiness(
        self, bundle_id, *, kind, validation_report_id=None,
    ):
        bundle = self._bundle(bundle_id)
        report = self._publication_report(bundle, validation_report_id)
        return self.publication_engine.readiness(
            bundle, report, PublicationKind(kind)
        )

    def preview_publication(
        self, bundle_id, *, kind, validation_report_id=None,
    ):
        bundle = self._bundle(bundle_id)
        report = self._publication_report(bundle, validation_report_id)
        return self.publication_engine.preview(
            bundle, report, PublicationKind(kind)
        )

    def publication_history(self, bundle_id):
        self._bundle(bundle_id)
        return tuple(sorted(
            (item for item in self.publication_packages.values()
             if item.manifest.theory_bundle_id == bundle_id),
            key=lambda item: (
                item.manifest.generated_at, item.manifest.publication_id,
            ), reverse=True,
        ))

    def publication_package(self, bundle_id, publication_id):
        self._bundle(bundle_id)
        package = self.publication_packages.get(publication_id)
        if package is None or package.manifest.theory_bundle_id != bundle_id:
            raise KeyError(f"Unknown publication package: {publication_id}")
        return package

    def _publication_report(self, bundle, report_id=None):
        if report_id:
            report = self.validation_reports.get(report_id)
            if report is None:
                raise KeyError(f"Unknown validation report: {report_id}")
            return report
        reports = sorted(
            (item for item in self.validation_reports.values()
             if item.theory_bundle_id == bundle.bundle_id
             and item.theory_bundle_hash == bundle.content_hash),
            key=lambda item: (item.assessed_at, item.report_id), reverse=True,
        )
        if not reports:
            raise ValueError("No active validation report for current theory bundle")
        return reports[0]

    def _bundle(self, bundle_id):
        bundle = self.bundles.get(bundle_id)
        if bundle is None:
            raise KeyError(f"Unknown theory bundle: {bundle_id}")
        return bundle
