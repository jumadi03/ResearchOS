"""PostgreSQL artifact lifecycle and publication persistence."""

from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.repositories.artifacts import ArtifactLifecycleEvent
from app.knowledge.repositories.models import StoredRepresentation


class PostgresArtifactRepositoryMixin:
    """Research artifact lifecycle and immutable publication behavior."""

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


