"""Transactional PostgreSQL implementation for DATA-002A/B."""

from __future__ import annotations

from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.ingestion.models import AcquisitionResult, AcquisitionStatus
from app.knowledge.models import DiscoveryRun, LiteratureRecord, SourceRecord
from app.knowledge.retrieval.models import MetadataRun
from app.knowledge.repositories.models import StoredRepresentation
from app.knowledge.repositories.artifacts import ArtifactLifecycleEvent
from app.knowledge.repositories.postgres_semantic import PostgresSemanticRepositoryMixin
from app.knowledge.repositories.postgres_read_model import PostgresReadModelRepositoryMixin
from app.knowledge.repositories.postgres_evidence import PostgresEvidenceRepositoryMixin


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


class PostgresScientificDataRepository(
    PostgresSemanticRepositoryMixin,
    PostgresReadModelRepositoryMixin,
    PostgresEvidenceRepositoryMixin,
    _PostgresRepositoryCore,
):
    """Compatibility façade composed from bounded PostgreSQL repositories."""
