"""PostgreSQL evidence review and knowledge-graph persistence."""

from dataclasses import asdict
from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.extraction.models import (
    DocumentCoordinates, ExtractedScientificObject,
    EpistemicClassification, EvidenceAdmission, EvidenceReviewAssessment,
    EvidenceReviewEvent, ExtractionManifest, ExtractionReviewState,
    ScientificObjectType,
)
from app.knowledge.intake.models import KnowledgeIntakeManifest
from app.knowledge.modeling.models import ScientificKnowledgeGraph
from app.knowledge.models import LiteratureRecord


class PostgresEvidenceRepositoryMixin:
    """Canonical evidence and assertional graph behavior."""

    def persist_evidence(
        self, record: LiteratureRecord | None, manifest: ExtractionManifest,
        *, source_extraction_id: str | None = None,
    ) -> tuple[str, ...]:
        if manifest.schema_version != "1.1" or not manifest.verify():
            raise ValueError("Canonical extraction manifest integrity verification failed")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if source_extraction_id is not None:
                    cursor.execute("""
                        SELECT document_id,representation_id
                        FROM extraction_manifests
                        WHERE extraction_key=%s AND document_content_hash=%s
                    """, (
                        source_extraction_id,
                        manifest.document_content_hash,
                    ))
                else:
                    if record is None:
                        raise ValueError(
                            "Literature record or source extraction is required"
                        )
                    cursor.execute("""
                        SELECT c.object_id, r.representation_id
                        FROM canonical_objects c
                        JOIN scientific_representations r
                          ON r.object_id=c.object_id
                        WHERE c.stable_key=%s AND r.checksum_sha256=%s
                        ORDER BY r.document_version DESC LIMIT 1
                    """, (
                        self._stable_key(record),
                        manifest.document_content_hash,
                    ))
                source = cursor.fetchone()
                if source is None:
                    raise KeyError(f"Canonical representation missing for extraction: {manifest.extraction_id}")
                document_id, representation_id = source
                cursor.execute("""
                    SELECT screening_decision_id FROM screening_decisions
                    WHERE decision_key=%s AND decision_hash=%s
                      AND status='eligible'
                      AND source_document_id=%s
                      AND document_content_hash=%s
                      AND inspection_manifest_hash=%s
                """, (
                    manifest.screening_decision_id,
                    manifest.screening_decision_hash,
                    manifest.document_id,
                    manifest.document_content_hash,
                    manifest.inspection_manifest_hash,
                ))
                screening = cursor.fetchone()
                if screening is None:
                    raise ValueError(
                        "Canonical eligible screening decision is required "
                        "for evidence persistence"
                    )
                cursor.execute("""
                    INSERT INTO extraction_manifests(
                        extraction_key,document_id,representation_id,
                        screening_decision_id,source_document_id,
                        document_content_hash,inspection_manifest_hash,
                        parser_name,parser_version,configuration_hash,
                        object_count,created_at,manifest_hash
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(extraction_key) DO NOTHING
                    RETURNING extraction_manifest_id
                """, (
                    manifest.extraction_id, document_id, representation_id,
                    screening[0], manifest.document_id,
                    manifest.document_content_hash,
                    manifest.inspection_manifest_hash,
                    manifest.parser_name, manifest.parser_version,
                    manifest.configuration_hash, len(manifest.objects),
                    manifest.created_at, manifest.manifest_hash,
                ))
                inserted_manifest = cursor.fetchone()
                if inserted_manifest:
                    extraction_manifest_id = inserted_manifest[0]
                else:
                    cursor.execute("""
                        SELECT extraction_manifest_id,manifest_hash
                        FROM extraction_manifests WHERE extraction_key=%s
                    """, (manifest.extraction_id,))
                    extraction_manifest_id, existing_hash = cursor.fetchone()
                    if existing_hash != manifest.manifest_hash:
                        raise RuntimeError("Extraction manifest integrity conflict")
                evidence_ids = []
                review_status = {
                    ExtractionReviewState.PROVISIONAL: "pending",
                    ExtractionReviewState.ACCEPTED: "accepted",
                    ExtractionReviewState.REJECTED: "rejected",
                }
                for ordinal, item in enumerate(manifest.objects):
                    cursor.execute("""
                        INSERT INTO canonical_objects(object_type,stable_key,lifecycle_status)
                        VALUES ('evidence',%s,'draft')
                        ON CONFLICT(stable_key) DO UPDATE SET updated_at=now()
                        RETURNING object_id
                    """, (f"evidence:{item.object_id}",))
                    evidence_id = cursor.fetchone()[0]
                    cursor.execute("""
                        SELECT content_hash, document_id, representation_id,
                               extraction_manifest_id,page_text_hash,
                               extraction_rule,extraction_ordinal
                        FROM evidence_objects WHERE evidence_id=%s
                    """, (evidence_id,))
                    existing = cursor.fetchone()
                    if existing is not None:
                        if existing[:3] != (
                            item.coordinates.quote_hash,
                            document_id, representation_id,
                        ):
                            raise RuntimeError(f"Evidence integrity conflict: {item.object_id}")
                        if existing[3] not in (None, extraction_manifest_id):
                            raise RuntimeError(
                                f"Evidence extraction provenance conflict: {item.object_id}"
                            )
                        if (
                            existing[4] not in (None, item.coordinates.page_text_hash)
                            or existing[5] not in (None, item.extraction_rule)
                            or existing[6] not in (None, ordinal)
                        ):
                            raise RuntimeError(
                                f"Evidence intake provenance conflict: {item.object_id}"
                            )
                        if (
                            existing[3] is None
                            or existing[4] is None
                            or existing[5] is None
                            or existing[6] is None
                        ):
                            cursor.execute("""
                                UPDATE evidence_objects
                                SET extraction_manifest_id=%s,
                                    page_text_hash=%s,extraction_rule=%s,
                                    extraction_ordinal=%s
                                WHERE evidence_id=%s
                            """, (
                                extraction_manifest_id,
                                item.coordinates.page_text_hash,
                                item.extraction_rule, ordinal, evidence_id,
                            ))
                        evidence_ids.append(str(evidence_id))
                        continue
                    cursor.execute("""
                        INSERT INTO evidence_objects(
                            evidence_id, document_id, representation_id, evidence_type,
                            statement, page, character_start, character_end,
                            section,paragraph,table_id,figure_id,
                            extraction_method, extraction_confidence,
                            human_review_status, content_hash,extraction_manifest_id,
                            page_text_hash,extraction_rule,extraction_ordinal
                        ) VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s
                        )
                    """, (
                        evidence_id, document_id, representation_id,
                        item.object_type.value, item.content, item.coordinates.page,
                        item.coordinates.start_char, item.coordinates.end_char,
                        item.coordinates.section, item.coordinates.paragraph,
                        item.coordinates.table_id, item.coordinates.figure_id,
                        f"{item.extraction_method}@{item.parser_version}", item.confidence,
                        review_status[item.review_state], item.coordinates.quote_hash,
                        extraction_manifest_id, item.coordinates.page_text_hash,
                        item.extraction_rule, ordinal,
                    ))
                    evidence_ids.append(str(evidence_id))
                return tuple(evidence_ids)

    def load_extraction_manifest(self, extraction_id: str) -> ExtractionManifest:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT x.source_document_id,x.document_content_hash,x.created_at,
                           x.parser_name,x.parser_version,x.inspection_manifest_hash,
                           s.decision_key,s.decision_hash,x.configuration_hash,
                           x.manifest_hash
                    FROM extraction_manifests x
                    JOIN screening_decisions s
                      ON s.screening_decision_id=x.screening_decision_id
                    WHERE x.extraction_key=%s
                """, (extraction_id,))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown canonical extraction: {extraction_id}")
                cursor.execute("""
                    SELECT c.stable_key,e.evidence_type,e.statement,e.page,
                           e.character_start,e.character_end,e.content_hash,
                           e.section,e.paragraph,e.table_id,e.figure_id,
                           e.extraction_confidence,e.extraction_method,
                           e.page_text_hash,e.extraction_rule
                    FROM extraction_manifests x
                    JOIN evidence_objects e
                      ON e.extraction_manifest_id=x.extraction_manifest_id
                    JOIN canonical_objects c ON c.object_id=e.evidence_id
                    WHERE x.extraction_key=%s
                    ORDER BY e.extraction_ordinal
                """, (extraction_id,))
                evidence_rows = cursor.fetchall()
        objects = []
        for item in evidence_rows:
            method = item[12]
            extraction_method, separator, parser_version = method.rpartition("@")
            if not separator:
                extraction_method, parser_version = method, row[4]
            if not item[13] or not item[14]:
                raise ValueError(
                    "Canonical extraction lacks SCAN-001L intake provenance: "
                    f"{item[0]}"
                )
            objects.append(ExtractedScientificObject(
                item[0].removeprefix("evidence:"),
                ScientificObjectType(item[1]), item[2],
                DocumentCoordinates(
                    item[3], item[4], item[5], item[6], item[7], item[8],
                    item[9], item[10], item[13],
                ),
                item[11], ExtractionReviewState.PROVISIONAL,
                extraction_method, parser_version, item[2], item[14],
            ))
        manifest = ExtractionManifest(
            extraction_id, row[0], row[1],
            row[2].isoformat().replace("+00:00", "Z"),
            row[3], row[4], tuple(objects), "1.1", row[5], row[6], row[7],
            row[8], row[9],
        )
        if not manifest.verify():
            raise ValueError("Canonical extraction manifest integrity verification failed")
        return manifest

    def review_evidence(
        self, evidence_object_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str, assessment: EvidenceReviewAssessment,
    ) -> EvidenceReviewEvent:
        review_state = ExtractionReviewState(decision)
        if review_state is ExtractionReviewState.PROVISIONAL:
            raise ValueError("Evidence review decision must be accepted or rejected")
        if not reviewer.strip() or not rationale.strip():
            raise ValueError("Reviewer and rationale are required")
        if not assessment.verify():
            raise ValueError("Evidence review assessment is incomplete")
        if (
            review_state is ExtractionReviewState.ACCEPTED
            and not assessment.permits_acceptance()
        ):
            raise ValueError("Accepted evidence requires every review criterion to pass")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT e.evidence_id, e.human_review_status,e.content_hash,
                           x.manifest_hash
                    FROM canonical_objects c
                    JOIN evidence_objects e ON e.evidence_id=c.object_id
                    JOIN extraction_manifests x
                      ON x.extraction_manifest_id=e.extraction_manifest_id
                    WHERE c.stable_key=%s
                    FOR UPDATE
                """, (f"evidence:{evidence_object_id}",))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown canonical evidence: {evidence_object_id}")
                evidence_id, previous_state, statement_hash, manifest_hash = row
                if (
                    assessment.reviewed_statement_hash != statement_hash
                    or assessment.extraction_manifest_hash != manifest_hash
                ):
                    raise ValueError("Evidence changed after the review context was opened")
                payload = {
                    "evidence_object_id": evidence_object_id,
                    "previous_state": previous_state,
                    "decision": review_state.value,
                    "reviewer": reviewer.strip(),
                    "rationale": rationale.strip(),
                    "occurred_at": occurred_at,
                    "assessment": asdict(assessment),
                    "assessment_hash": assessment.digest(),
                }
                event_identity = {
                    key: value for key, value in payload.items() if key != "previous_state"
                }
                event_hash = sha256(canonical_json(event_identity).encode()).hexdigest()
                cursor.execute("""
                    INSERT INTO provenance_events(
                        execution_id, source_object_id, output_object_id,
                        human_reviewer, event_type, event_payload, occurred_at, event_hash
                    ) VALUES (%s,%s,%s,%s,'evidence_review',%s,%s,%s)
                    ON CONFLICT(event_hash) DO NOTHING
                    RETURNING provenance_id
                """, (
                    f"evidence-review:{event_hash}", evidence_id, evidence_id,
                    reviewer.strip(), json.dumps(payload), occurred_at, event_hash,
                ))
                provenance = cursor.fetchone()
                if provenance is None:
                    cursor.execute(
                        "SELECT provenance_id FROM provenance_events WHERE event_hash=%s",
                        (event_hash,),
                    )
                    provenance_id = cursor.fetchone()[0]
                else:
                    provenance_id = provenance[0]
                cursor.execute("""
                    INSERT INTO evidence_review_events(
                        evidence_id, from_status, decision, reviewer_id,
                        rationale, occurred_at, provenance_id,assessment,
                        assessment_hash,reviewed_statement_hash,
                        extraction_manifest_hash
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(provenance_id) DO NOTHING
                    RETURNING review_id
                """, (
                    evidence_id, previous_state, review_state.value, reviewer.strip(),
                    rationale.strip(), occurred_at, provenance_id,
                    json.dumps(asdict(assessment)), assessment.digest(),
                    assessment.reviewed_statement_hash,
                    assessment.extraction_manifest_hash,
                ))
                review = cursor.fetchone()
                if review is None:
                    cursor.execute(
                        "SELECT review_id, from_status FROM evidence_review_events WHERE provenance_id=%s",
                        (provenance_id,),
                    )
                    review_id, recorded_previous = cursor.fetchone()
                    previous_state = recorded_previous
                else:
                    review_id = review[0]
                cursor.execute(
                    "UPDATE evidence_objects SET human_review_status=%s WHERE evidence_id=%s",
                    (review_state.value, evidence_id),
                )
                if review_state is ExtractionReviewState.REJECTED:
                    cursor.execute("""
                        UPDATE knowledge_edges SET review_status='rejected'
                        WHERE provenance_id IN (
                            SELECT provenance_id FROM provenance_events
                            WHERE source_object_id=%s
                              AND event_type='knowledge_edge_assertion'
                        )
                    """, (evidence_id,))
        return EvidenceReviewEvent(
            str(review_id), evidence_object_id, review_state, reviewer.strip(),
            rationale.strip(), occurred_at, str(provenance_id), previous_state,
            assessment, assessment.digest(),
        )

    def resolve_evidence_admissions(
        self, evidence_object_ids: tuple[str, ...],
    ) -> tuple[EvidenceAdmission, ...]:
        status_map = {
            "pending": ExtractionReviewState.PROVISIONAL,
            "accepted": ExtractionReviewState.ACCEPTED,
            "rejected": ExtractionReviewState.REJECTED,
        }
        admissions = []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for object_id in evidence_object_ids:
                    cursor.execute("""
                        SELECT p.projected_status,
                               v.review_id, v.decision, v.reviewer_id,
                               v.rationale, v.occurred_at, v.provenance_id,
                               v.from_status,v.assessment,v.assessment_hash
                        FROM canonical_objects c
                        JOIN evidence_objects e ON e.evidence_id=c.object_id
                        JOIN evidence_current_review_projection p
                          ON p.evidence_id=e.evidence_id
                        LEFT JOIN LATERAL (
                            SELECT review_id, decision, reviewer_id, rationale,
                                   occurred_at, provenance_id, from_status,
                                   assessment,assessment_hash
                            FROM evidence_review_events
                            WHERE evidence_id=e.evidence_id
                              AND assessment IS NOT NULL
                              AND assessment_hash IS NOT NULL
                              AND reviewed_statement_hash=e.content_hash
                              AND extraction_manifest_hash=(
                                  SELECT manifest_hash FROM extraction_manifests
                                  WHERE extraction_manifest_id=e.extraction_manifest_id
                              )
                            ORDER BY occurred_at DESC,created_at DESC,review_id DESC
                            LIMIT 1
                        ) v ON true
                        WHERE c.stable_key=%s
                    """, (f"evidence:{object_id}",))
                    row = cursor.fetchone()
                    if row is None:
                        admissions.append(EvidenceAdmission(object_id, None, None))
                        continue
                    status = status_map.get(row[0])
                    event = None
                    if row[1] is not None:
                        raw = row[8] or {}
                        assessment = EvidenceReviewAssessment(
                            bool(raw.get("citation_fidelity")),
                            bool(raw.get("context_preserved")),
                            bool(raw.get("relevant")),
                            float(raw.get("confidence_assessment", 0)),
                            EpistemicClassification(
                                raw.get("epistemic_classification", "unclear")
                            ),
                            raw.get("reviewed_statement_hash", ""),
                            raw.get("extraction_manifest_hash", ""),
                        )
                        event = EvidenceReviewEvent(
                            str(row[1]), object_id,
                            ExtractionReviewState(row[2]), row[3], row[4],
                            row[5].isoformat().replace("+00:00", "Z"),
                            str(row[6]), row[7], assessment, row[9] or "",
                        )
                    admissions.append(EvidenceAdmission(object_id, status, event))
        return tuple(admissions)

    def persist_graph(
        self, graph: ScientificKnowledgeGraph, *, occurred_at: str,
        intake: KnowledgeIntakeManifest | None = None,
    ) -> tuple[str, ...]:
        graph.validate_evidence_admission()
        if not graph.verify():
            raise ValueError("Scientific Knowledge Graph integrity verification failed")
        if any(not edge.assertion for edge in graph.edges):
            raise ValueError("Canonical graph edges must be explicit assertions")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                evidence_nodes = [node for node in graph.nodes if node.provenance is not None]
                if not evidence_nodes:
                    raise ValueError("Canonical graph requires reviewed evidence nodes")
                object_by_domain_node = {}
                reviewer_by_evidence = {}
                document_ids = set()
                for node in evidence_nodes:
                    cursor.execute("""
                        SELECT e.evidence_id, e.document_id, e.evidence_type,
                               e.statement, e.content_hash, p.projected_status,
                               v.review_id, v.decision, v.reviewer_id,
                               v.rationale, v.occurred_at, v.provenance_id,
                               v.from_status,v.assessment,v.assessment_hash,
                               v.reviewed_statement_hash,
                               v.extraction_manifest_hash
                        FROM canonical_objects c
                        JOIN evidence_objects e ON e.evidence_id=c.object_id
                        JOIN evidence_current_review_projection p
                          ON p.evidence_id=e.evidence_id
                        LEFT JOIN LATERAL (
                            SELECT review_id, decision, reviewer_id, rationale,
                                   occurred_at, provenance_id, from_status,
                                   assessment,assessment_hash,
                                   reviewed_statement_hash,
                                   extraction_manifest_hash
                            FROM evidence_review_events
                            WHERE evidence_id=e.evidence_id
                              AND assessment IS NOT NULL
                              AND assessment_hash IS NOT NULL
                              AND reviewed_statement_hash=e.content_hash
                              AND extraction_manifest_hash=(
                                  SELECT manifest_hash FROM extraction_manifests
                                  WHERE extraction_manifest_id=e.extraction_manifest_id
                              )
                            ORDER BY occurred_at DESC,created_at DESC,review_id DESC
                            LIMIT 1
                        ) v ON true
                        WHERE c.stable_key=%s
                        FOR UPDATE OF e
                    """, (f"evidence:{node.provenance.object_id}",))
                    row = cursor.fetchone()
                    if row is None:
                        raise KeyError(f"Canonical evidence missing: {node.provenance.object_id}")
                    (
                        evidence_id, document_id, evidence_type, statement,
                        content_hash, status, review_id, decision, reviewer,
                        rationale, reviewed_at, review_provenance_id,
                        previous_state,review_assessment,assessment_hash,
                        reviewed_statement_hash,review_manifest_hash,
                    ) = row
                    if status != "accepted" or decision != "accepted" or reviewer is None:
                        raise ValueError(f"Evidence is not accepted: {node.provenance.object_id}")
                    event = node.provenance.review_event
                    if (
                        event is None
                        or event.review_id != str(review_id)
                        or event.decision is not ExtractionReviewState.ACCEPTED
                        or event.reviewer != reviewer
                        or event.rationale != rationale
                        or event.occurred_at
                        != reviewed_at.isoformat().replace("+00:00", "Z")
                        or event.provenance_id != str(review_provenance_id)
                        or event.previous_state != previous_state
                        or event.assessment is None
                        or asdict(event.assessment) != review_assessment
                        or event.assessment_hash != assessment_hash
                        or event.assessment.digest() != assessment_hash
                        or event.assessment.reviewed_statement_hash
                        != reviewed_statement_hash
                        or event.assessment.extraction_manifest_hash
                        != review_manifest_hash
                        or reviewed_statement_hash != content_hash
                    ):
                        raise ValueError(
                            "Evidence review provenance is incomplete: "
                            f"{node.provenance.object_id}"
                        )
                    if evidence_type != node.node_type.value or statement != node.label:
                        raise ValueError(f"Graph node does not match canonical evidence: {node.node_id}")
                    if content_hash != node.provenance.quote_hash:
                        raise ValueError(f"Graph provenance hash mismatch: {node.node_id}")
                    object_by_domain_node[node.node_id] = evidence_id
                    reviewer_by_evidence[node.provenance.object_id] = (
                        reviewer, str(review_provenance_id),
                    )
                    document_ids.add(document_id)
                if len(document_ids) != 1:
                    raise ValueError("A persisted graph must reference one canonical document")
                document_node = next(
                    (node for node in graph.nodes if node.provenance is None), None,
                )
                if document_node is None:
                    raise ValueError("Canonical graph document node is missing")
                object_by_domain_node[document_node.node_id] = next(iter(document_ids))

                db_node_by_domain = {}
                for node in graph.nodes:
                    object_id = object_by_domain_node.get(node.node_id)
                    if object_id is None:
                        raise ValueError(f"Graph node has no canonical object: {node.node_id}")
                    cursor.execute("""
                        INSERT INTO knowledge_nodes(object_id,node_type)
                        VALUES (%s,%s)
                        ON CONFLICT(object_id) DO NOTHING
                        RETURNING node_id
                    """, (object_id, node.node_type.value))
                    inserted = cursor.fetchone()
                    if inserted is None:
                        cursor.execute(
                            "SELECT node_id,node_type FROM knowledge_nodes WHERE object_id=%s",
                            (object_id,),
                        )
                        node_id, node_type = cursor.fetchone()
                        if node_type != node.node_type.value:
                            raise RuntimeError(f"Knowledge node type conflict: {node.node_id}")
                    else:
                        node_id = inserted[0]
                    db_node_by_domain[node.node_id] = node_id

                edge_ids = []
                for edge in graph.edges:
                    evidence_id = object_by_domain_node.get(f"node:{edge.provenance.object_id}")
                    if evidence_id is None:
                        raise ValueError(f"Edge provenance evidence is missing: {edge.edge_id}")
                    payload = {
                        "graph_id": graph.graph_id, "edge_id": edge.edge_id,
                        "source_id": edge.source_id, "target_id": edge.target_id,
                        "relationship_type": edge.edge_type.value,
                        "evidence_object_id": edge.provenance.object_id,
                        "evidence_review_provenance_id": reviewer_by_evidence[
                            edge.provenance.object_id
                        ][1],
                        "quote_hash": edge.provenance.quote_hash,
                    }
                    event_hash = sha256(canonical_json(payload).encode()).hexdigest()
                    cursor.execute("""
                        INSERT INTO provenance_events(
                            execution_id, source_object_id, output_object_id,
                            human_reviewer, event_type, event_payload, occurred_at, event_hash
                        ) VALUES (%s,%s,%s,%s,'knowledge_edge_assertion',%s,%s,%s)
                        ON CONFLICT(event_hash) DO NOTHING
                        RETURNING provenance_id
                    """, (
                        graph.graph_id, evidence_id,
                        object_by_domain_node[edge.target_id],
                        reviewer_by_evidence[edge.provenance.object_id][0],
                        json.dumps(payload), occurred_at, event_hash,
                    ))
                    provenance = cursor.fetchone()
                    if provenance is None:
                        cursor.execute(
                            "SELECT provenance_id FROM provenance_events WHERE event_hash=%s",
                            (event_hash,),
                        )
                        provenance_id = cursor.fetchone()[0]
                    else:
                        provenance_id = provenance[0]
                    cursor.execute("""
                        INSERT INTO knowledge_edges(
                            source_node_id,target_node_id,relationship_type,
                            provenance_id,confidence,review_status
                        ) VALUES (%s,%s,%s,%s,%s,'accepted')
                        ON CONFLICT(source_node_id,target_node_id,relationship_type,provenance_id)
                        DO NOTHING
                        RETURNING edge_id
                    """, (
                        db_node_by_domain[edge.source_id], db_node_by_domain[edge.target_id],
                        edge.edge_type.value, provenance_id, edge.provenance.confidence,
                    ))
                    persisted = cursor.fetchone()
                    if persisted is None:
                        cursor.execute("""
                            SELECT edge_id,confidence,review_status FROM knowledge_edges
                            WHERE source_node_id=%s AND target_node_id=%s
                              AND relationship_type=%s AND provenance_id=%s
                        """, (
                            db_node_by_domain[edge.source_id], db_node_by_domain[edge.target_id],
                            edge.edge_type.value, provenance_id,
                        ))
                        edge_id, confidence, review_status = cursor.fetchone()
                        if confidence != edge.provenance.confidence or review_status != "accepted":
                            raise RuntimeError(f"Knowledge edge integrity conflict: {edge.edge_id}")
                    else:
                        edge_id = persisted[0]
                    edge_ids.append(str(edge_id))
                if intake is not None:
                    if (
                        not intake.verify()
                        or intake.graph_id != graph.graph_id
                        or intake.graph_content_hash != graph.content_hash
                    ):
                        raise ValueError("Knowledge intake manifest integrity verification failed")
                    payload = asdict(intake)
                    event_hash = sha256(canonical_json(payload).encode()).hexdigest()
                    cursor.execute("""
                        INSERT INTO provenance_events(
                            execution_id,human_reviewer,event_type,event_payload,
                            occurred_at,event_hash
                        ) VALUES (%s,%s,'knowledge_intake',%s,%s,%s)
                        ON CONFLICT(event_hash) DO NOTHING
                        RETURNING provenance_id
                    """, (
                        intake.intake_id, intake.actor_id, json.dumps(payload),
                        intake.occurred_at, event_hash,
                    ))
                    provenance = cursor.fetchone()
                    if provenance is None:
                        cursor.execute(
                            "SELECT provenance_id FROM provenance_events WHERE event_hash=%s",
                            (event_hash,),
                        )
                        provenance_id = cursor.fetchone()[0]
                    else:
                        provenance_id = provenance[0]
                    cursor.execute("""
                        INSERT INTO knowledge_intake_manifests(
                            intake_key,extraction_key,extraction_manifest_hash,
                            graph_key,graph_content_hash,requested_evidence_ids,
                            admitted_evidence_ids,decisions,actor_id,occurred_at,
                            provenance_id,content_hash,schema_version
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT(intake_key) DO NOTHING
                        RETURNING intake_manifest_id
                    """, (
                        intake.intake_id, intake.extraction_id,
                        intake.extraction_manifest_hash, intake.graph_id,
                        intake.graph_content_hash,
                        list(intake.requested_evidence_object_ids),
                        list(intake.admitted_evidence_object_ids),
                        json.dumps([asdict(item) for item in intake.decisions]),
                        intake.actor_id, intake.occurred_at, provenance_id,
                        intake.content_hash, intake.schema_version,
                    ))
                    if cursor.fetchone() is None:
                        cursor.execute("""
                            SELECT content_hash,provenance_id
                            FROM knowledge_intake_manifests WHERE intake_key=%s
                        """, (intake.intake_id,))
                        existing_hash, existing_provenance = cursor.fetchone()
                        if (
                            existing_hash != intake.content_hash
                            or existing_provenance != provenance_id
                        ):
                            raise RuntimeError("Knowledge intake integrity conflict")
                return tuple(edge_ids)
