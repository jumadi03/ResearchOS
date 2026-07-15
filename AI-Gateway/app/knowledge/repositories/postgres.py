"""Transactional PostgreSQL implementation for DATA-002A/B."""

from __future__ import annotations

from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.ingestion.models import AcquisitionResult, AcquisitionStatus
from app.knowledge.models import DiscoveryRun, LiteratureRecord, SourceRecord
from app.knowledge.retrieval.models import MetadataRun
from app.knowledge.repositories.models import StoredRepresentation
from app.knowledge.extraction.models import (
    EvidenceReviewEvent, ExtractionManifest, ExtractionReviewState,
)
from app.knowledge.modeling.models import ScientificKnowledgeGraph
from app.knowledge.repositories.artifacts import ArtifactLifecycleEvent
from app.knowledge.repositories.read_models import ObjectPage, ObjectSummary, ProjectSummary
from app.knowledge.repositories.postgres_semantic import PostgresSemanticRepositoryMixin


class _PostgresRepositoryCore:
    _LIFECYCLE_TRANSITIONS = {
        "planned": "draft", "draft": "review", "review": "validated",
        "validated": "ratified", "ratified": "published",
        "published": "deprecated", "deprecated": "archived",
    }
    _LIFECYCLE_STATES = frozenset((*_LIFECYCLE_TRANSITIONS, "archived"))
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("database_url is required")
        self.database_url = database_url

    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url)

    @staticmethod
    def _stable_key(record: LiteratureRecord) -> str:
        return f"doi:{record.doi}" if record.doi else f"literature:{record.record_id}"

    def persist_discovery(self, run: DiscoveryRun) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for record in run.records:
                    document_id = self._upsert_document(cursor, record)
                    for source in record.source_records:
                        source_id = self._upsert_source(cursor, record, source)
                        cursor.execute("""
                            INSERT INTO document_source_references(
                                document_id, source_id, match_method, match_confidence
                            ) VALUES (%s,%s,%s,%s)
                            ON CONFLICT(document_id,source_id) DO NOTHING
                        """, (
                            document_id, source_id,
                            "exact_doi" if record.doi else record.match_kind.value,
                            1.0 if record.doi else 0.8 if record.possible_matches else 1.0,
                        ))
                        cursor.execute("""
                            INSERT INTO metadata_observations(
                                document_id, source_id, metadata, observed_at, content_hash
                            ) VALUES (%s,%s,%s,%s,%s)
                            ON CONFLICT(document_id,source_id,content_hash) DO NOTHING
                        """, (
                            document_id, source_id, json.dumps(source.raw),
                            source.retrieved_at, source.response_hash,
                        ))

    def _upsert_document(self, cursor, record: LiteratureRecord):
        stable_key = self._stable_key(record)
        cursor.execute("""
            INSERT INTO canonical_objects(object_type,stable_key,lifecycle_status)
            VALUES ('scientific_document',%s,'draft')
            ON CONFLICT(stable_key) DO UPDATE SET updated_at=now()
            RETURNING object_id
        """, (stable_key,))
        document_id = cursor.fetchone()[0]
        payload = {
            "title": record.title, "abstract": record.abstract,
            "authors": record.authors, "year": record.year,
            "venue": record.venue, "work_type": record.work_type,
        }
        metadata_hash = sha256(canonical_json(payload).encode()).hexdigest()
        cursor.execute("""
            INSERT INTO scientific_documents(
                document_id,canonical_doi,title,abstract,authors,journal,
                publication_date,document_type,metadata_hash
            ) VALUES (%s,%s,%s,%s,%s,%s,
                CASE WHEN %s IS NULL THEN NULL ELSE make_date(%s,1,1) END,%s,%s)
            ON CONFLICT(document_id) DO UPDATE SET
                title=excluded.title, abstract=excluded.abstract,
                authors=excluded.authors, journal=excluded.journal,
                publication_date=excluded.publication_date,
                document_type=excluded.document_type,
                metadata_version=CASE WHEN scientific_documents.metadata_hash<>excluded.metadata_hash
                    THEN scientific_documents.metadata_version+1 ELSE scientific_documents.metadata_version END,
                metadata_hash=excluded.metadata_hash
        """, (
            document_id, record.doi, record.title, record.abstract,
            json.dumps(record.authors), record.venue, record.year, record.year,
            record.work_type, metadata_hash,
        ))
        return document_id

    @staticmethod
    def _upsert_source(cursor, record: LiteratureRecord, source: SourceRecord):
        raw = source.raw
        url = raw.get("URL") or raw.get("url") or raw.get("id")
        source_type = str(raw.get("type") or raw.get("publicationTypes") or "scholarly_work")
        cursor.execute("""
            INSERT INTO scientific_sources(
                provider,source_type,external_id,doi,url,title,authors,
                publication_year,retrieved_at,license,access_status,response_hash
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(provider,external_id,response_hash) DO UPDATE SET
                retrieved_at=excluded.retrieved_at
            RETURNING source_id
        """, (
            source.provider, source_type, source.source_id, record.doi, url,
            record.title, json.dumps(record.authors), record.year,
            source.retrieved_at, raw.get("license"),
            "open" if (raw.get("open_access") or {}).get("is_oa") else "unknown",
            source.response_hash,
        ))
        return cursor.fetchone()[0]

    def persist_metadata(self, run: MetadataRun) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for record in run.records:
                    cursor.execute("""
                        SELECT object_id FROM canonical_objects
                        WHERE stable_key=%s OR stable_key=%s
                        ORDER BY stable_key LIKE 'doi:%%' DESC LIMIT 1
                    """, (
                        f"literature:{record.record_id}",
                        next((f"doi:{value}" for key, value in record.identifiers if key == "doi"), ""),
                    ))
                    row = cursor.fetchone()
                    if row is None:
                        raise KeyError(f"Canonical document missing for record: {record.record_id}")
                    document_id = row[0]
                    cursor.execute("""
                        UPDATE scientific_documents SET
                            citation_count=%s,
                            keywords=%s,
                            metadata_version=CASE
                                WHEN citation_count IS DISTINCT FROM %s
                                  OR keywords IS DISTINCT FROM %s::jsonb
                                THEN metadata_version+1
                                ELSE metadata_version
                            END
                        WHERE document_id=%s
                    """, (
                        record.citation_count, json.dumps(record.concepts),
                        record.citation_count, json.dumps(record.concepts), document_id,
                    ))
                    for observation in record.observations:
                        cursor.execute("""
                            SELECT source_id FROM scientific_sources
                            WHERE provider=%s AND external_id=%s AND response_hash=%s
                        """, (
                            observation.provider, observation.source_id,
                            observation.response_hash,
                        ))
                        source = cursor.fetchone()
                        if source is None:
                            raise KeyError(
                                f"Source missing for metadata observation: {observation.source_id}"
                            )
                        content_hash = sha256(canonical_json(observation.values).encode()).hexdigest()
                        cursor.execute("""
                            INSERT INTO metadata_observations(
                                document_id,source_id,metadata,observed_at,content_hash
                            ) VALUES (%s,%s,%s,%s,%s)
                            ON CONFLICT(document_id,source_id,content_hash) DO NOTHING
                        """, (
                            document_id, source[0], json.dumps(observation.values),
                            run.created_at, content_hash,
                        ))

    def persist_representation(
        self, record: LiteratureRecord, result: AcquisitionResult, storage_uri: str,
    ) -> tuple[str, int]:
        if result.status is not AcquisitionStatus.ACQUIRED:
            raise ValueError("Only acquired content can create a representation")
        if not result.content_hash or result.byte_size is None or not result.media_type:
            raise ValueError("Acquired representation integrity metadata is incomplete")
        representation_type = {
            "application/pdf": "pdf",
            "text/html": "html",
            "application/xml": "xml",
            "application/json": "json",
        }.get(result.media_type)
        if representation_type is None:
            raise ValueError(f"Unsupported representation media type: {result.media_type}")

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT object_id FROM canonical_objects WHERE stable_key=%s
                """, (self._stable_key(record),))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(
                        f"Canonical source missing for representation: {result.record_id}"
                    )
                document_id = row[0]
                cursor.execute("""
                    SELECT 1
                    FROM scientific_sources s
                    JOIN document_source_references r ON r.source_id=s.source_id
                    WHERE r.document_id=%s AND s.provider=%s AND s.response_hash=%s
                """, (
                    document_id, result.source_provider, result.source_response_hash,
                ))
                if cursor.fetchone() is None:
                    raise ValueError("Representation provenance does not match canonical document")
                cursor.execute(
                    "SELECT object_id FROM canonical_objects WHERE object_id=%s FOR UPDATE",
                    (document_id,),
                )
                cursor.execute("""
                    SELECT representation_id, document_version
                    FROM scientific_representations
                    WHERE object_id=%s AND representation_type=%s AND checksum_sha256=%s
                """, (document_id, representation_type, result.content_hash))
                existing = cursor.fetchone()
                if existing is not None:
                    return str(existing[0]), existing[1]
                cursor.execute("""
                    SELECT COALESCE(max(document_version),0)+1
                    FROM scientific_representations
                    WHERE object_id=%s AND representation_type=%s
                """, (document_id, representation_type))
                version = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO scientific_representations(
                        object_id, representation_type, storage_uri, media_type,
                        checksum_sha256, file_size, document_version, source_url,
                        retrieval_method, retrieved_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'https_download',%s)
                    RETURNING representation_id
                """, (
                    document_id, representation_type, storage_uri, result.media_type,
                    result.content_hash, result.byte_size, version, result.source_url,
                    result.acquired_at,
                ))
                representation_id = cursor.fetchone()[0]
                cursor.execute(
                    "UPDATE scientific_documents SET license=COALESCE(%s,license) WHERE document_id=%s",
                    (result.license, document_id),
                )
                return str(representation_id), version

    def get_representation(
        self, record: LiteratureRecord, checksum_sha256: str,
    ) -> StoredRepresentation:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT r.representation_id, r.object_id, r.representation_type,
                           r.storage_uri, r.media_type, r.checksum_sha256,
                           r.file_size, r.document_version
                    FROM scientific_representations r
                    JOIN canonical_objects c ON c.object_id=r.object_id
                    WHERE c.stable_key=%s AND r.checksum_sha256=%s
                    ORDER BY r.document_version DESC
                    LIMIT 1
                """, (self._stable_key(record), checksum_sha256))
                row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Representation missing for record: {record.record_id}")
        return StoredRepresentation(
            representation_id=str(row[0]), object_id=str(row[1]),
            representation_type=row[2], storage_uri=row[3], media_type=row[4],
            checksum_sha256=row[5], file_size=row[6], document_version=row[7],
        )

    def persist_evidence(
        self, record: LiteratureRecord, manifest: ExtractionManifest,
    ) -> tuple[str, ...]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.object_id, r.representation_id
                    FROM canonical_objects c
                    JOIN scientific_representations r ON r.object_id=c.object_id
                    WHERE c.stable_key=%s AND r.checksum_sha256=%s
                    ORDER BY r.document_version DESC LIMIT 1
                """, (self._stable_key(record), manifest.document_content_hash))
                source = cursor.fetchone()
                if source is None:
                    raise KeyError(f"Canonical representation missing for extraction: {manifest.extraction_id}")
                document_id, representation_id = source
                evidence_ids = []
                review_status = {
                    ExtractionReviewState.PROVISIONAL: "pending",
                    ExtractionReviewState.ACCEPTED: "accepted",
                    ExtractionReviewState.REJECTED: "rejected",
                }
                for item in manifest.objects:
                    cursor.execute("""
                        INSERT INTO canonical_objects(object_type,stable_key,lifecycle_status)
                        VALUES ('evidence',%s,'draft')
                        ON CONFLICT(stable_key) DO UPDATE SET updated_at=now()
                        RETURNING object_id
                    """, (f"evidence:{item.object_id}",))
                    evidence_id = cursor.fetchone()[0]
                    cursor.execute("""
                        SELECT content_hash, document_id, representation_id
                        FROM evidence_objects WHERE evidence_id=%s
                    """, (evidence_id,))
                    existing = cursor.fetchone()
                    if existing is not None:
                        if existing != (item.coordinates.quote_hash, document_id, representation_id):
                            raise RuntimeError(f"Evidence integrity conflict: {item.object_id}")
                        evidence_ids.append(str(evidence_id))
                        continue
                    cursor.execute("""
                        INSERT INTO evidence_objects(
                            evidence_id, document_id, representation_id, evidence_type,
                            statement, page, character_start, character_end,
                            extraction_method, extraction_confidence,
                            human_review_status, content_hash
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        evidence_id, document_id, representation_id,
                        item.object_type.value, item.content, item.coordinates.page,
                        item.coordinates.start_char, item.coordinates.end_char,
                        f"{item.extraction_method}@{item.parser_version}", item.confidence,
                        review_status[item.review_state], item.coordinates.quote_hash,
                    ))
                    evidence_ids.append(str(evidence_id))
                return tuple(evidence_ids)

    def review_evidence(
        self, evidence_object_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str,
    ) -> EvidenceReviewEvent:
        review_state = ExtractionReviewState(decision)
        if review_state is ExtractionReviewState.PROVISIONAL:
            raise ValueError("Evidence review decision must be accepted or rejected")
        if not reviewer.strip() or not rationale.strip():
            raise ValueError("Reviewer and rationale are required")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT e.evidence_id, e.human_review_status
                    FROM canonical_objects c
                    JOIN evidence_objects e ON e.evidence_id=c.object_id
                    WHERE c.stable_key=%s
                    FOR UPDATE
                """, (f"evidence:{evidence_object_id}",))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown canonical evidence: {evidence_object_id}")
                evidence_id, previous_state = row
                payload = {
                    "evidence_object_id": evidence_object_id,
                    "previous_state": previous_state,
                    "decision": review_state.value,
                    "reviewer": reviewer.strip(),
                    "rationale": rationale.strip(),
                    "occurred_at": occurred_at,
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
                        rationale, occurred_at, provenance_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(provenance_id) DO NOTHING
                    RETURNING review_id
                """, (
                    evidence_id, previous_state, review_state.value, reviewer.strip(),
                    rationale.strip(), occurred_at, provenance_id,
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
        )

    def persist_graph(
        self, graph: ScientificKnowledgeGraph, *, occurred_at: str,
    ) -> tuple[str, ...]:
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
                               e.statement, e.content_hash, e.human_review_status,
                               v.reviewer_id, v.provenance_id
                        FROM canonical_objects c
                        JOIN evidence_objects e ON e.evidence_id=c.object_id
                        LEFT JOIN LATERAL (
                            SELECT reviewer_id, provenance_id FROM evidence_review_events
                            WHERE evidence_id=e.evidence_id AND decision='accepted'
                            ORDER BY occurred_at DESC, created_at DESC LIMIT 1
                        ) v ON true
                        WHERE c.stable_key=%s
                        FOR UPDATE OF e
                    """, (f"evidence:{node.provenance.object_id}",))
                    row = cursor.fetchone()
                    if row is None:
                        raise KeyError(f"Canonical evidence missing: {node.provenance.object_id}")
                    evidence_id, document_id, evidence_type, statement, content_hash, status, reviewer, review_provenance_id = row
                    if status != "accepted" or reviewer is None:
                        raise ValueError(f"Evidence is not accepted: {node.provenance.object_id}")
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
                return tuple(edge_ids)

    def persist_artifact(
        self, *, artifact_id: str, project_id: str, artifact_type: str,
        title: str, status: str, metadata: dict, actor_id: str,
        occurred_at: str,
    ) -> ArtifactLifecycleEvent:
        if status not in self._LIFECYCLE_STATES:
            raise ValueError(f"Invalid artifact lifecycle status: {status}")
        if not all(value.strip() for value in (artifact_id, project_id, artifact_type, title, actor_id)):
            raise ValueError("Artifact identity, project, type, title, and actor are required")
        stable_key = f"artifact:{artifact_id}"
        metadata_hash = sha256(canonical_json(metadata).encode()).hexdigest()
        payload = {
            "artifact_id": artifact_id, "artifact_type": artifact_type,
            "project_id": project_id, "title": title, "status": status,
            "actor_id": actor_id, "occurred_at": occurred_at,
            "metadata_hash": metadata_hash,
        }
        event_hash = sha256(canonical_json(payload).encode()).hexdigest()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO canonical_objects(object_type,stable_key,lifecycle_status)
                    VALUES ('research_artifact',%s,%s)
                    ON CONFLICT(stable_key) DO NOTHING
                    RETURNING object_id
                """, (stable_key, status))
                inserted = cursor.fetchone()
                if inserted is None:
                    cursor.execute(
                        "SELECT object_id FROM canonical_objects WHERE stable_key=%s FOR UPDATE",
                        (stable_key,),
                    )
                    canonical_id = cursor.fetchone()[0]
                else:
                    canonical_id = inserted[0]
                cursor.execute("""
                    INSERT INTO provenance_events(
                        execution_id,output_object_id,agent_id,event_type,
                        event_payload,occurred_at,event_hash
                    ) VALUES (%s,%s,%s,'artifact_created',%s,%s,%s)
                    ON CONFLICT(event_hash) DO NOTHING RETURNING provenance_id
                """, (
                    f"artifact-create:{artifact_id}", canonical_id, actor_id,
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
                    INSERT INTO research_artifacts(
                        artifact_id,project_id,artifact_type,title,status,provenance_id,
                        metadata,content_hash
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(artifact_id) DO NOTHING
                """, (
                    canonical_id, project_id, artifact_type, title, status,
                    provenance_id, json.dumps(metadata), metadata_hash,
                ))
                cursor.execute("""
                    SELECT project_id,artifact_type,title,metadata,content_hash
                    FROM research_artifacts WHERE artifact_id=%s
                """, (canonical_id,))
                existing = cursor.fetchone()
                if existing != (project_id, artifact_type, title, metadata, metadata_hash):
                    raise RuntimeError(f"Artifact integrity conflict: {artifact_id}")
                cursor.execute("""
                    INSERT INTO artifact_lifecycle_events(
                        artifact_id,from_status,to_status,actor_id,rationale,
                        occurred_at,provenance_id
                    ) VALUES (%s,NULL,%s,%s,'Artifact created',%s,%s)
                    ON CONFLICT(provenance_id) DO NOTHING
                    RETURNING lifecycle_event_id
                """, (canonical_id, status, actor_id, occurred_at, provenance_id))
                lifecycle = cursor.fetchone()
                if lifecycle is None:
                    cursor.execute("""
                        SELECT lifecycle_event_id FROM artifact_lifecycle_events
                        WHERE provenance_id=%s
                    """, (provenance_id,))
                    lifecycle_id = cursor.fetchone()[0]
                else:
                    lifecycle_id = lifecycle[0]
        return ArtifactLifecycleEvent(
            str(lifecycle_id), artifact_id, None, status, actor_id,
            "Artifact created", occurred_at, str(provenance_id),
        )

    def transition_artifact(
        self, artifact_id: str, *, to_status: str, actor_id: str,
        rationale: str, occurred_at: str,
    ) -> ArtifactLifecycleEvent:
        if to_status not in self._LIFECYCLE_STATES:
            raise ValueError(f"Invalid artifact lifecycle status: {to_status}")
        if not actor_id.strip() or not rationale.strip():
            raise ValueError("Artifact transition actor and rationale are required")
        identity = {
            "artifact_id": artifact_id, "to_status": to_status,
            "actor_id": actor_id.strip(), "rationale": rationale.strip(),
            "occurred_at": occurred_at,
        }
        event_hash = sha256(canonical_json(identity).encode()).hexdigest()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.provenance_id,l.lifecycle_event_id,l.from_status
                    FROM provenance_events p
                    JOIN artifact_lifecycle_events l ON l.provenance_id=p.provenance_id
                    WHERE p.event_hash=%s
                """, (event_hash,))
                repeated = cursor.fetchone()
                if repeated is not None:
                    provenance_id, lifecycle_id, from_status = repeated
                    return ArtifactLifecycleEvent(
                        str(lifecycle_id), artifact_id, from_status, to_status,
                        actor_id.strip(), rationale.strip(), occurred_at, str(provenance_id),
                    )
                cursor.execute("""
                    SELECT c.object_id,r.status
                    FROM canonical_objects c
                    JOIN research_artifacts r ON r.artifact_id=c.object_id
                    WHERE c.stable_key=%s FOR UPDATE OF c,r
                """, (f"artifact:{artifact_id}",))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown canonical artifact: {artifact_id}")
                canonical_id, from_status = row
                expected = self._LIFECYCLE_TRANSITIONS.get(from_status)
                if expected != to_status:
                    raise ValueError(
                        f"Invalid artifact transition: {from_status} -> {to_status}; expected {expected}"
                    )
                payload = {**identity, "from_status": from_status}
                cursor.execute("""
                    INSERT INTO provenance_events(
                        execution_id,source_object_id,output_object_id,human_reviewer,
                        event_type,event_payload,occurred_at,event_hash
                    ) VALUES (%s,%s,%s,%s,'artifact_lifecycle_transition',%s,%s,%s)
                    RETURNING provenance_id
                """, (
                    f"artifact-transition:{event_hash}", canonical_id, canonical_id,
                    actor_id.strip(), json.dumps(payload), occurred_at, event_hash,
                ))
                provenance_id = cursor.fetchone()[0]
                cursor.execute("""
                    INSERT INTO artifact_lifecycle_events(
                        artifact_id,from_status,to_status,actor_id,rationale,
                        occurred_at,provenance_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    RETURNING lifecycle_event_id
                """, (
                    canonical_id, from_status, to_status, actor_id.strip(),
                    rationale.strip(), occurred_at, provenance_id,
                ))
                lifecycle_id = cursor.fetchone()[0]
                cursor.execute(
                    "UPDATE research_artifacts SET status=%s WHERE artifact_id=%s",
                    (to_status, canonical_id),
                )
                cursor.execute("""
                    UPDATE canonical_objects
                    SET lifecycle_status=%s,current_version=current_version+1,updated_at=now()
                    WHERE object_id=%s
                """, (to_status, canonical_id))
        return ArtifactLifecycleEvent(
            str(lifecycle_id), artifact_id, from_status, to_status,
            actor_id.strip(), rationale.strip(), occurred_at, str(provenance_id),
        )

    def persist_publication_representation(
        self, publication_id: str, *, storage_uri: str, media_type: str,
        checksum_sha256: str, file_size: int, representation_type: str,
        edition_type: str, published_at: str,
    ) -> StoredRepresentation:
        if representation_type not in {"markdown", "pdf", "docx", "html", "json", "csv", "rdf"}:
            raise ValueError(f"Unsupported publication representation: {representation_type}")
        if file_size < 1 or not checksum_sha256 or not edition_type.strip():
            raise ValueError("Publication representation integrity and edition are required")
        publication_hash = sha256(canonical_json({
            "publication_id": publication_id, "edition_type": edition_type.strip(),
            "representation_type": representation_type, "checksum_sha256": checksum_sha256,
        }).encode()).hexdigest()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.object_id,r.artifact_type,r.status
                    FROM canonical_objects c
                    JOIN research_artifacts r ON r.artifact_id=c.object_id
                    WHERE c.stable_key=%s FOR UPDATE OF c,r
                """, (f"artifact:{publication_id}",))
                artifact = cursor.fetchone()
                if artifact is None:
                    raise KeyError(f"Unknown publication artifact: {publication_id}")
                artifact_id, artifact_type, status = artifact
                if artifact_type != "publication_package" or status != "published":
                    raise ValueError("Publication representation requires a published package artifact")
                cursor.execute("""
                    SELECT representation_id,document_version,storage_uri,media_type,file_size
                    FROM scientific_representations
                    WHERE object_id=%s AND representation_type=%s AND checksum_sha256=%s
                """, (artifact_id, representation_type, checksum_sha256))
                existing = cursor.fetchone()
                if existing is None:
                    cursor.execute("""
                        SELECT COALESCE(max(document_version),0)+1
                        FROM scientific_representations
                        WHERE object_id=%s AND representation_type=%s
                    """, (artifact_id, representation_type))
                    version = cursor.fetchone()[0]
                    cursor.execute("""
                        INSERT INTO scientific_representations(
                            object_id,representation_type,storage_uri,media_type,
                            checksum_sha256,file_size,document_version,
                            retrieval_method,retrieved_at
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,'researchos_publication',%s)
                        RETURNING representation_id
                    """, (
                        artifact_id, representation_type, storage_uri, media_type,
                        checksum_sha256, file_size, version, published_at,
                    ))
                    representation_id = cursor.fetchone()[0]
                else:
                    representation_id, version, recorded_uri, recorded_media, recorded_size = existing
                    if (recorded_uri, recorded_media, recorded_size) != (storage_uri, media_type, file_size):
                        raise RuntimeError("Publication representation integrity conflict")
                cursor.execute("""
                    INSERT INTO publication_representations(
                        artifact_id,representation_id,edition_type,published_at,publication_hash
                    ) VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT(publication_hash) DO NOTHING
                    RETURNING publication_id
                """, (
                    artifact_id, representation_id, edition_type.strip(),
                    published_at, publication_hash,
                ))
                linked = cursor.fetchone()
                if linked is None:
                    cursor.execute("""
                        SELECT artifact_id,representation_id,edition_type
                        FROM publication_representations WHERE publication_hash=%s
                    """, (publication_hash,))
                    recorded = cursor.fetchone()
                    if recorded != (artifact_id, representation_id, edition_type.strip()):
                        raise RuntimeError("Publication edition integrity conflict")
        return StoredRepresentation(
            str(representation_id), str(artifact_id), representation_type,
            storage_uri, media_type, checksum_sha256, file_size, version,
        )

    def enqueue_semantic_index(
        self, *, object_type: str, object_id: str, model: str,
        embedding: tuple[float, ...], metadata: dict,
    ) -> SemanticIndexJob:
        if object_type not in {"evidence", "artifact"}:
            raise ValueError("Semantic object type must be evidence or artifact")
        if len(embedding) != 1536:
            raise ValueError("Embedding must contain 1536 dimensions")
        if not object_id.strip() or not model.strip():
            raise ValueError("Semantic object identity and model are required")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if object_type == "evidence":
                    cursor.execute("""
                        SELECT c.object_id,e.content_hash,e.human_review_status
                        FROM canonical_objects c
                        JOIN evidence_objects e ON e.evidence_id=c.object_id
                        WHERE c.stable_key=%s
                    """, (f"evidence:{object_id}",))
                    source = cursor.fetchone()
                    if source is None:
                        raise KeyError(f"Unknown canonical evidence: {object_id}")
                    canonical_id, content_hash, status = source
                    if status != "accepted":
                        raise ValueError(f"Evidence is not accepted: {object_id}")
                else:
                    cursor.execute("""
                        SELECT c.object_id,r.content_hash,r.status
                        FROM canonical_objects c
                        JOIN research_artifacts r ON r.artifact_id=c.object_id
                        WHERE c.stable_key=%s
                    """, (f"artifact:{object_id}",))
                    source = cursor.fetchone()
                    if source is None:
                        raise KeyError(f"Unknown canonical artifact: {object_id}")
                    canonical_id, content_hash, status = source
                    if status not in {"validated", "ratified", "published"}:
                        raise ValueError(f"Artifact is not eligible for indexing: {object_id}")
                deduplication_key = sha256(canonical_json({
                    "canonical_object_id": str(canonical_id),
                    "content_hash": content_hash, "model": model.strip(),
                }).encode()).hexdigest()
                payload = {
                    "object_type": object_type, "object_id": object_id,
                    "model": model.strip(), "embedding": embedding,
                    "metadata": metadata, "canonical_object_id": str(canonical_id),
                    "content_hash": content_hash,
                }
                cursor.execute("""
                    INSERT INTO background_jobs(job_type,payload,deduplication_key)
                    VALUES ('index_embedding',%s,%s)
                    ON CONFLICT(deduplication_key)
                    WHERE deduplication_key IS NOT NULL DO NOTHING
                    RETURNING job_id,status
                """, (json.dumps(payload), deduplication_key))
                job = cursor.fetchone()
                if job is None:
                    cursor.execute("""
                        SELECT job_id,status FROM background_jobs
                        WHERE deduplication_key=%s
                    """, (deduplication_key,))
                    job = cursor.fetchone()
        return SemanticIndexJob(
            str(job[0]), object_type, object_id, str(canonical_id), content_hash,
            model.strip(), len(embedding), job[1],
        )

    def semantic_search(
        self, *, model: str, query_embedding: tuple[float, ...], limit: int,
        object_types: tuple[str, ...],
    ) -> tuple[SemanticSearchHit, ...]:
        if len(query_embedding) != 1536:
            raise ValueError("Query embedding must contain 1536 dimensions")
        normalized_types = tuple(dict.fromkeys(object_types))
        if not normalized_types or any(item not in {"evidence", "artifact"} for item in normalized_types):
            raise ValueError("Semantic search object types must be evidence or artifact")
        if not 1 <= limit <= 100 or not model.strip():
            raise ValueError("Semantic search requires a model and limit from 1 to 100")
        vector = "[" + ",".join(str(float(value)) for value in query_embedding) + "]"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT i.canonical_object_id,c.stable_key,i.object_type,i.object_id,
                           i.content_hash,i.model,
                           1-(i.embedding <=> %s::vector) AS similarity,
                           i.metadata,
                           COALESCE(er.provenance_id,al.provenance_id,a.provenance_id),
                           COALESCE(er.reviewer_id,al.actor_id)
                    FROM embedding_index i
                    JOIN canonical_objects c ON c.object_id=i.canonical_object_id
                    LEFT JOIN evidence_objects e ON e.evidence_id=i.canonical_object_id
                    LEFT JOIN research_artifacts a ON a.artifact_id=i.canonical_object_id
                    LEFT JOIN LATERAL (
                        SELECT provenance_id,reviewer_id
                        FROM evidence_review_events
                        WHERE evidence_id=e.evidence_id AND decision='accepted'
                        ORDER BY occurred_at DESC,created_at DESC LIMIT 1
                    ) er ON i.object_type='evidence'
                    LEFT JOIN LATERAL (
                        SELECT provenance_id,actor_id
                        FROM artifact_lifecycle_events
                        WHERE artifact_id=a.artifact_id
                        ORDER BY occurred_at DESC LIMIT 1
                    ) al ON i.object_type='artifact'
                    WHERE i.model=%s AND i.object_type=ANY(%s)
                      AND (
                        (i.object_type='evidence' AND e.human_review_status='accepted'
                         AND e.content_hash=i.content_hash)
                        OR
                        (i.object_type='artifact'
                         AND a.status IN ('validated','ratified','published')
                         AND a.content_hash=i.content_hash)
                      )
                    ORDER BY i.embedding <=> %s::vector, i.embedding_id
                    LIMIT %s
                """, (vector, model.strip(), list(normalized_types), vector, limit))
                rows = cursor.fetchall()
        return tuple(SemanticSearchHit(
            canonical_object_id=str(row[0]), stable_key=row[1],
            object_type=row[2], object_id=row[3], content_hash=row[4],
            model=row[5], similarity=float(row[6]), metadata=row[7],
            provenance_id=str(row[8]) if row[8] else None,
            attributed_actor=row[9],
        ) for row in rows)

    def list_projects(self) -> tuple[ProjectSummary, ...]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.project_id,p.name,p.description,p.status,count(po.object_id)
                    FROM research_projects p
                    LEFT JOIN project_objects po ON po.project_id=p.project_id
                    GROUP BY p.project_id ORDER BY p.name,p.project_id
                """)
                rows = cursor.fetchall()
        return tuple(ProjectSummary(*row) for row in rows)

    def list_objects(
        self, project_id: str, *, limit: int, cursor: str | None,
        query: str | None, object_types: tuple[str, ...],
    ) -> ObjectPage:
        if not 1 <= limit <= 100:
            raise ValueError("Object page limit must be from 1 to 100")
        clauses = ["po.project_id=%s"]
        values = [project_id]
        if cursor:
            clauses.append("c.stable_key>%s")
            values.append(cursor)
        if query:
            clauses.append("lower(COALESCE(d.title,a.title,e.statement,c.stable_key)) LIKE %s")
            values.append(f"%{query.strip().lower()}%")
        if object_types:
            clauses.append("c.object_type=ANY(%s)")
            values.append(list(object_types))
        values.append(limit + 1)
        with self._connect() as connection:
            with connection.cursor() as db_cursor:
                db_cursor.execute(f"""
                    SELECT c.object_id,c.stable_key,c.object_type,c.lifecycle_status,
                           c.current_version,
                           COALESCE(d.title,a.title,e.statement,c.stable_key) AS title,
                           c.updated_at
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    LEFT JOIN scientific_documents d ON d.document_id=c.object_id
                    LEFT JOIN research_artifacts a ON a.artifact_id=c.object_id
                    LEFT JOIN evidence_objects e ON e.evidence_id=c.object_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY c.stable_key LIMIT %s
                """, values)
                rows = db_cursor.fetchall()
        page_rows = rows[:limit]
        items = tuple(ObjectSummary(
            str(row[0]), row[1], row[2], row[3], row[4], row[5], row[6].isoformat(),
        ) for row in page_rows)
        next_cursor = page_rows[-1][1] if len(rows) > limit else None
        return ObjectPage(items, next_cursor)

    def get_object_read_model(self, object_ref: str, project_id: str) -> dict:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.object_id,c.stable_key,c.object_type,c.lifecycle_status,
                           c.current_version,c.classification,c.created_at,c.updated_at,
                           COALESCE(d.title,a.title,e.statement,c.stable_key),
                           d.canonical_doi,d.authors,d.journal,d.publication_date,
                           e.evidence_type,e.page,e.character_start,e.character_end,
                           e.human_review_status,e.extraction_confidence,
                           a.artifact_type,a.status,a.metadata,a.content_hash
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    LEFT JOIN scientific_documents d ON d.document_id=c.object_id
                    LEFT JOIN evidence_objects e ON e.evidence_id=c.object_id
                    LEFT JOIN research_artifacts a ON a.artifact_id=c.object_id
                    WHERE po.project_id=%s
                      AND (c.object_id::text=%s OR c.stable_key=%s)
                """, (project_id, object_ref, object_ref))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown project object: {object_ref}")
                object_id = row[0]
                cursor.execute("""
                    SELECT representation_id,representation_type,storage_uri,media_type,
                           checksum_sha256,file_size,document_version,created_at
                    FROM scientific_representations WHERE object_id=%s
                    ORDER BY representation_type,document_version DESC
                """, (object_id,))
                representations = [{
                    "representation_id": str(item[0]), "type": item[1],
                    "storage_uri": item[2], "media_type": item[3],
                    "checksum_sha256": item[4], "file_size": item[5],
                    "version": item[6], "created_at": item[7].isoformat(),
                } for item in cursor.fetchall()]
                cursor.execute("""
                    SELECT ks.stable_key,kt.stable_key,ke.relationship_type,
                           ke.confidence,ke.review_status,ke.provenance_id,ke.created_at
                    FROM knowledge_edges ke
                    JOIN knowledge_nodes ns ON ns.node_id=ke.source_node_id
                    JOIN canonical_objects ks ON ks.object_id=ns.object_id
                    JOIN knowledge_nodes nt ON nt.node_id=ke.target_node_id
                    JOIN canonical_objects kt ON kt.object_id=nt.object_id
                    WHERE ns.object_id=%s OR nt.object_id=%s
                    ORDER BY ke.created_at DESC LIMIT 100
                """, (object_id, object_id))
                relationships = [{
                    "source": item[0], "target": item[1], "type": item[2],
                    "confidence": item[3], "review_status": item[4],
                    "provenance_id": str(item[5]), "created_at": item[6].isoformat(),
                } for item in cursor.fetchall()]
                cursor.execute("""
                    SELECT provenance_id,event_type,event_payload,occurred_at,
                           COALESCE(human_reviewer,agent_id,provider_id)
                    FROM provenance_events
                    WHERE source_object_id=%s OR output_object_id=%s
                    ORDER BY occurred_at DESC,provenance_id DESC LIMIT 100
                """, (object_id, object_id))
                timeline = [{
                    "provenance_id": str(item[0]), "event_type": item[1],
                    "payload": item[2], "occurred_at": item[3].isoformat(),
                    "actor": item[4],
                } for item in cursor.fetchall()]
        return {
            "identity": {
                "object_id": str(row[0]), "stable_key": row[1], "object_type": row[2],
                "lifecycle_status": row[3], "current_version": row[4],
                "classification": row[5], "created_at": row[6].isoformat(),
                "updated_at": row[7].isoformat(),
                "deep_link": f"/knowledge/projects/{project_id}/objects/{row[0]}",
            },
            "summary": {"title": row[8]},
            "document": ({
                "doi": row[9], "authors": row[10], "journal": row[11],
                "publication_date": row[12].isoformat() if row[12] else None,
            } if row[9] is not None or row[10] is not None else None),
            "evidence": ({
                "type": row[13], "page": row[14], "character_start": row[15],
                "character_end": row[16], "review_status": row[17],
                "confidence": row[18],
            } if row[13] is not None else None),
            "artifact": ({
                "type": row[19], "status": row[20], "metadata": row[21],
                "content_hash": row[22],
            } if row[19] is not None else None),
            "representations": representations,
            "relationships": relationships,
            "timeline": timeline,
            "project_id": project_id,
        }

    def get_work_queue(self, project_id: str) -> dict:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.object_id,c.stable_key,e.statement,e.evidence_type,
                           e.extraction_confidence,c.updated_at
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    JOIN evidence_objects e ON e.evidence_id=c.object_id
                    WHERE po.project_id=%s AND e.human_review_status='pending'
                    ORDER BY c.updated_at DESC LIMIT 100
                """, (project_id,))
                reviews = [{
                    "object_id": str(row[0]), "stable_key": row[1], "title": row[2],
                    "evidence_type": row[3], "confidence": row[4],
                    "updated_at": row[5].isoformat(),
                } for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT c.object_id,c.stable_key,a.title,a.artifact_type,a.status,
                           CASE a.status WHEN 'draft' THEN 'validated'
                             WHEN 'validated' THEN 'ratified'
                             WHEN 'ratified' THEN 'published' END,c.updated_at
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    JOIN research_artifacts a ON a.artifact_id=c.object_id
                    WHERE po.project_id=%s AND a.status IN ('draft','validated','ratified')
                    ORDER BY c.updated_at DESC LIMIT 100
                """, (project_id,))
                transitions = [{
                    "object_id": str(row[0]), "stable_key": row[1], "title": row[2],
                    "artifact_type": row[3], "status": row[4], "next_status": row[5],
                    "updated_at": row[6].isoformat(),
                } for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT job_id,status,payload->>'object_type',payload->>'object_id',
                           payload->>'model',attempts,error,created_at,
                           COALESCE(completed_at,started_at,created_at)
                    FROM background_jobs WHERE job_type='index_embedding'
                    ORDER BY created_at DESC LIMIT 100
                """)
                jobs = [{
                    "job_id": str(row[0]), "status": row[1], "object_type": row[2],
                    "object_id": row[3], "model": row[4], "attempts": row[5],
                    "last_error": row[6], "created_at": row[7].isoformat(),
                    "updated_at": row[8].isoformat(),
                } for row in cursor.fetchall()]
        return {
            "project_id": project_id, "pending_reviews": reviews,
            "pending_transitions": transitions, "index_jobs": jobs,
            "counts": {
                "pending_reviews": len(reviews),
                "pending_transitions": len(transitions),
                "index_jobs": len(jobs),
                "failed_jobs": sum(job["status"] == "failed" for job in jobs),
            },
        }

    def get_project_graph(
        self, project_id: str, *, limit: int, relationship_types: tuple[str, ...],
        review_status: str | None, min_confidence: float,
    ) -> dict:
        if not 1 <= limit <= 300:
            raise ValueError("Graph edge limit must be from 1 to 300")
        if not 0 <= min_confidence <= 1:
            raise ValueError("Graph minimum confidence must be from 0 to 1")
        if review_status not in {None, "provisional", "accepted", "rejected"}:
            raise ValueError("Invalid graph review status")
        clauses = ["ps.project_id=%s", "pt.project_id=%s", "COALESCE(ke.confidence,0)>=%s"]
        values = [project_id, project_id, min_confidence]
        if relationship_types:
            clauses.append("ke.relationship_type=ANY(%s)")
            values.append(list(dict.fromkeys(relationship_types)))
        if review_status:
            clauses.append("ke.review_status=%s")
            values.append(review_status)
        values.append(limit)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT ke.edge_id,cs.object_id,cs.stable_key,cs.object_type,
                           COALESCE(ds.title,ars.title,es.statement,cs.stable_key),
                           ct.object_id,ct.stable_key,ct.object_type,
                           COALESCE(dt.title,art.title,et.statement,ct.stable_key),
                           ke.relationship_type,ke.confidence,ke.review_status,
                           ke.provenance_id
                    FROM knowledge_edges ke
                    JOIN knowledge_nodes ns ON ns.node_id=ke.source_node_id
                    JOIN canonical_objects cs ON cs.object_id=ns.object_id
                    JOIN project_objects ps ON ps.object_id=cs.object_id
                    JOIN knowledge_nodes nt ON nt.node_id=ke.target_node_id
                    JOIN canonical_objects ct ON ct.object_id=nt.object_id
                    JOIN project_objects pt ON pt.object_id=ct.object_id
                    LEFT JOIN scientific_documents ds ON ds.document_id=cs.object_id
                    LEFT JOIN research_artifacts ars ON ars.artifact_id=cs.object_id
                    LEFT JOIN evidence_objects es ON es.evidence_id=cs.object_id
                    LEFT JOIN scientific_documents dt ON dt.document_id=ct.object_id
                    LEFT JOIN research_artifacts art ON art.artifact_id=ct.object_id
                    LEFT JOIN evidence_objects et ON et.evidence_id=ct.object_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY ke.created_at DESC,ke.edge_id LIMIT %s
                """, values)
                rows = cursor.fetchall()
                cursor.execute("""
                    SELECT DISTINCT relationship_type FROM knowledge_edges
                    ORDER BY relationship_type
                """)
                available_types = [row[0] for row in cursor.fetchall()]
        nodes = {}
        edges = []
        for row in rows:
            nodes[str(row[1])] = {"object_id": str(row[1]), "stable_key": row[2], "object_type": row[3], "title": row[4]}
            nodes[str(row[5])] = {"object_id": str(row[5]), "stable_key": row[6], "object_type": row[7], "title": row[8]}
            edges.append({
                "edge_id": str(row[0]), "source": str(row[1]), "target": str(row[5]),
                "relationship_type": row[9], "confidence": row[10],
                "review_status": row[11], "provenance_id": str(row[12]),
            })
        return {"project_id": project_id, "nodes": list(nodes.values()), "edges": edges,
                "available_relationship_types": available_types,
                "truncated": len(edges) == limit}


class PostgresScientificDataRepository(
    PostgresSemanticRepositoryMixin,
    _PostgresRepositoryCore,
):
    """Compatibility façade composed from bounded PostgreSQL repositories."""
