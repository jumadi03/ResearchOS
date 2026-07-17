"""Canonical reviewed-evidence admission into scientific modeling."""

from app.knowledge.extraction.models import (
    EvidenceAdmission, EvidenceReviewEvent, ExtractionManifest,
    ExtractionReviewState,
)
from app.knowledge.modeling.models import ScientificKnowledgeGraph


class EvidenceAdmissionGate:
    def admit(
        self,
        manifest: ExtractionManifest,
        admissions: tuple[EvidenceAdmission, ...] | None,
    ) -> dict[str, EvidenceReviewEvent]:
        if admissions is None:
            raise ValueError(
                "Canonical repository is required for evidence admission"
            )
        by_id = {
            admission.evidence_object_id: admission for admission in admissions
        }
        accepted = {}
        for item in manifest.objects:
            admission = by_id.get(item.object_id)
            if admission is None or admission.review_state is None:
                raise ValueError(
                    f"Evidence review status is missing: {item.object_id}"
                )
            if admission.review_state is not ExtractionReviewState.ACCEPTED:
                raise ValueError(
                    f"Evidence is not accepted: {item.object_id} "
                    f"(status={admission.review_state.value})"
                )
            event = admission.review_event
            if not self._complete_event(item.object_id, event):
                raise ValueError(
                    f"Evidence review provenance is incomplete: {item.object_id}"
                )
            accepted[item.object_id] = event
        return accepted

    def revalidate(
        self,
        graph: ScientificKnowledgeGraph,
        admissions: tuple[EvidenceAdmission, ...] | None,
    ) -> None:
        if admissions is None:
            raise ValueError(
                "Canonical repository is required for evidence admission"
            )
        graph.validate_evidence_admission()
        by_id = {
            admission.evidence_object_id: admission for admission in admissions
        }
        provenances = {
            node.provenance.object_id: node.provenance
            for node in graph.nodes if node.provenance is not None
        }
        for object_id, provenance in provenances.items():
            admission = by_id.get(object_id)
            if admission is None or admission.review_state is None:
                raise ValueError(f"Evidence review status is missing: {object_id}")
            if admission.review_state is ExtractionReviewState.REJECTED:
                raise ValueError(
                    f"Knowledge graph contains rejected evidence: {object_id}"
                )
            if admission.review_state is not ExtractionReviewState.ACCEPTED:
                raise ValueError(
                    f"Evidence is not accepted: {object_id} "
                    f"(status={admission.review_state.value})"
                )
            if not self._complete_event(object_id, admission.review_event):
                raise ValueError(
                    f"Evidence review provenance is incomplete: {object_id}"
                )
            if (
                provenance.review_event is None
                or provenance.review_event.provenance_id
                != admission.review_event.provenance_id
            ):
                raise ValueError(
                    f"Evidence review provenance is stale: {object_id}"
                )

    @staticmethod
    def _complete_event(
        object_id: str, event: EvidenceReviewEvent | None,
    ) -> bool:
        return bool(
            event is not None
            and event.evidence_object_id == object_id
            and event.decision is ExtractionReviewState.ACCEPTED
            and event.review_id.strip()
            and event.reviewer.strip()
            and event.rationale.strip()
            and event.occurred_at.strip()
            and event.provenance_id.strip()
            and event.previous_state.strip()
            and event.assessment is not None
            and event.assessment.permits_acceptance()
            and event.assessment_hash == event.assessment.digest()
        )
