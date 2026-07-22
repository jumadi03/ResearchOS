"""DATA-002I immutable publication representation acceptance check."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import os

from app.knowledge.publication.models import (
    PublicationRelationship,
    PublicationRelationType,
)
from app.knowledge.repositories.minio import MinioScientificObjectStore
from app.knowledge.repositories.postgres import PostgresScientificDataRepository


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    store = MinioScientificObjectStore(
        endpoint=os.environ["MINIO_ENDPOINT"], access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        bucket=os.getenv("MINIO_DOCUMENT_BUCKET", "researchos-documents"),
    )
    now = datetime.now(timezone.utc)
    occurred_at = now.isoformat().replace("+00:00", "Z")
    suffix = now.strftime("%Y%m%dT%H%M%S%f")
    publication_id = f"publication-representation-healthcheck-{suffix}"
    prior_publication_id = f"publication-prior-healthcheck-{suffix}"
    withdrawn_publication_id = f"publication-withdrawn-healthcheck-{suffix}"
    for artifact_id, title in (
        (prior_publication_id, "Prior publication relationship healthcheck"),
        (withdrawn_publication_id, "Withdrawn publication relationship healthcheck"),
    ):
        repository.persist_artifact(
            artifact_id=artifact_id, project_id=f"publication-project-{suffix}",
            artifact_type="publication_package", title=title,
            status="published", metadata={"healthcheck": True},
            actor_id="publisher@researchos.local", occurred_at=occurred_at,
        )
    repository.persist_artifact(
        artifact_id=publication_id, project_id=f"publication-project-{suffix}",
        artifact_type="publication_package", title="Publication representation healthcheck",
        status="published", metadata={"healthcheck": True},
        actor_id="publisher@researchos.local", occurred_at=occurred_at,
    )
    editions = (
        ("canonical", f"# Canonical publication {suffix}\n".encode()),
        ("revised", f"# Revised publication {suffix}\n\nIntegrity verified.\n".encode()),
    )
    stored = []
    for edition_type, content in editions:
        checksum = sha256(content).hexdigest()
        uri = store.put_bytes(
            content, media_type="text/markdown", checksum_sha256=checksum,
            extension="md", namespace="publications",
        )
        representation = repository.persist_publication_representation(
            publication_id, storage_uri=uri, media_type="text/markdown",
            checksum_sha256=checksum, file_size=len(content),
            representation_type="markdown", edition_type=edition_type,
            published_at=occurred_at,
        )
        repeated = repository.persist_publication_representation(
            publication_id, storage_uri=uri, media_type="text/markdown",
            checksum_sha256=checksum, file_size=len(content),
            representation_type="markdown", edition_type=edition_type,
            published_at=occurred_at,
        )
        assert repeated == representation
        assert store.read_verified(representation) == content
        stored.append(representation)
    assert [item.document_version for item in stored] == [1, 2]

    correction = PublicationRelationship(
        f"publication-correction-healthcheck-{suffix}",
        publication_id, PublicationRelationType.CORRECTS,
        prior_publication_id, "publisher@researchos.local",
        "Data-backed acceptance confirms an immutable correction relationship.",
        occurred_at,
    ).finalized()
    retraction = PublicationRelationship(
        f"publication-retraction-healthcheck-{suffix}",
        withdrawn_publication_id, PublicationRelationType.RETRACTS,
        None, "publisher@researchos.local",
        "Data-backed acceptance confirms an immutable retraction relationship.",
        occurred_at,
    ).finalized()
    repository.record_publication_relationship(correction)
    repository.record_publication_relationship(correction)
    repository.record_publication_relationship(retraction)

    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.edition_type,r.document_version,r.media_type,r.checksum_sha256,
                       p.publication_hash
                FROM canonical_objects c
                JOIN publication_representations p ON p.artifact_id=c.object_id
                JOIN scientific_representations r ON r.representation_id=p.representation_id
                WHERE c.stable_key=%s ORDER BY r.document_version
            """, (f"artifact:{publication_id}",))
            rows = cursor.fetchall()
            cursor.execute("""
                SELECT p.relationship_key,p.relation_type,p.content_hash,
                       v.event_type
                FROM publication_relationships p
                JOIN provenance_events v ON v.provenance_id=p.provenance_id
                WHERE p.relationship_key IN (%s,%s)
                ORDER BY p.relationship_key
            """, (correction.relationship_id, retraction.relationship_id))
            relationships = cursor.fetchall()
    assert len(rows) == 2, rows
    assert [row[0] for row in rows] == ["canonical", "revised"]
    assert all(row[2] == "text/markdown" and len(row[3]) == 64 and len(row[4]) == 64 for row in rows)
    assert len(relationships) == 2, relationships
    assert {row[1] for row in relationships} == {"corrects", "retracts"}
    assert all(len(row[2]) == 64 and row[3] == "publication_relationship"
               for row in relationships)
    try:
        with repository._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE publication_representations SET edition_type='mutated' WHERE representation_id=%s",
                    (stored[0].representation_id,),
                )
    except Exception as exc:
        assert "append-only" in str(exc)
    else:
        raise AssertionError("Publication edition mutation was not rejected")
    try:
        with repository._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM publication_relationships WHERE relationship_key=%s",
                    (correction.relationship_id,),
                )
    except Exception as exc:
        assert "append-only" in str(exc)
    else:
        raise AssertionError("Publication relationship deletion was not rejected")
    print("canonical publication and relationship healthcheck: passed")


if __name__ == "__main__":
    main()
