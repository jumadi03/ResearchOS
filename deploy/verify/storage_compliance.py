"""DATA-002L cross-store storage contract compliance scan."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import boto3
import psycopg


REQUIRED_RESOURCES = {
    "canonical_objects", "scientific_sources", "scientific_documents",
    "document_source_references", "metadata_observations",
    "scientific_representations", "source_inspections", "screening_decisions",
    "citation_traversal_runs", "citation_traversal_edges",
    "citation_traversal_candidates", "citation_traversal_failures",
    "scientific_source_watches", "scientific_source_watch_state",
    "scientific_monitoring_runs", "scientific_changes",
    "scientific_change_acknowledgements",
    "scientific_impact_review_resolutions",
    "scientific_follow_up_case_targets",
    "scientific_source_watch_transitions",
    "extraction_manifests", "knowledge_intake_manifests",
    "scientific_identifiers", "identity_resolution_events",
    "evidence_objects", "evidence_review_events",
    "provenance_events", "knowledge_nodes", "knowledge_edges",
    "research_artifacts", "artifact_lifecycle_events",
    "publication_representations", "publication_relationships",
    "embedding_index", "background_jobs",
    "researchos-documents", "researchos-backups", "knowledge_data",
    "backup_runs", "backup_restore_verifications",
}


def scalar(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchone()[0]


def main() -> None:
    findings = []
    with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT resource_name FROM storage_contract_registry")
            registered = {row[0] for row in cursor.fetchall()}
            missing_contracts = REQUIRED_RESOURCES - registered
            if missing_contracts:
                findings.append(f"missing storage contracts: {sorted(missing_contracts)}")
            if scalar(cursor, "SELECT count(*) FROM storage_contract_compliance WHERE NOT resource_present"):
                findings.append("registered PostgreSQL resource is missing")
            checks = {
                "orphan documents": "SELECT count(*) FROM scientific_documents d LEFT JOIN canonical_objects c ON c.object_id=d.document_id WHERE c.object_id IS NULL",
                "orphan representations": "SELECT count(*) FROM scientific_representations r LEFT JOIN canonical_objects c ON c.object_id=r.object_id WHERE c.object_id IS NULL",
                "orphan evidence": "SELECT count(*) FROM evidence_objects e LEFT JOIN scientific_representations r ON r.representation_id=e.representation_id WHERE r.representation_id IS NULL",
                "intakes without provenance": "SELECT count(*) FROM knowledge_intake_manifests i LEFT JOIN provenance_events p ON p.provenance_id=i.provenance_id WHERE p.provenance_id IS NULL",
                "edges without provenance": "SELECT count(*) FROM knowledge_edges e LEFT JOIN provenance_events p ON p.provenance_id=e.provenance_id WHERE p.provenance_id IS NULL",
                "artifact events without provenance": "SELECT count(*) FROM artifact_lifecycle_events e LEFT JOIN provenance_events p ON p.provenance_id=e.provenance_id WHERE p.provenance_id IS NULL",
                "publication editions without representation": "SELECT count(*) FROM publication_representations p LEFT JOIN scientific_representations r ON r.representation_id=p.representation_id WHERE r.representation_id IS NULL",
                "publication relationships without provenance": "SELECT count(*) FROM publication_relationships r LEFT JOIN provenance_events p ON p.provenance_id=r.provenance_id WHERE p.provenance_id IS NULL",
                "impact resolutions without provenance": "SELECT count(*) FROM scientific_impact_review_resolutions r LEFT JOIN provenance_events p ON p.provenance_id=r.provenance_id WHERE p.provenance_id IS NULL",
                "follow-up targets without provenance": "SELECT count(*) FROM scientific_follow_up_case_targets t LEFT JOIN provenance_events p ON p.provenance_id=t.provenance_id WHERE p.provenance_id IS NULL",
                "invalid canonical hashes": "SELECT count(*) FROM scientific_representations WHERE length(checksum_sha256)<>64",
                "invalid semantic dimensions": "SELECT count(*) FROM embedding_index WHERE dimensions<>1536",
            }
            for label, sql in checks.items():
                count = scalar(cursor, sql)
                if count:
                    findings.append(f"{label}: {count}")
            required_triggers = {
                "provenance_events_immutable", "evidence_review_events_immutable",
                "artifact_lifecycle_events_immutable",
                "scientific_representations_immutable",
                "source_inspections_immutable",
                "screening_decisions_immutable",
                "extraction_manifests_immutable",
                "knowledge_intake_manifests_immutable",
                "citation_traversal_runs_immutable",
                "citation_traversal_edges_immutable",
                "citation_traversal_candidates_immutable",
                "citation_traversal_failures_immutable",
                "scientific_source_watches_immutable",
                "scientific_monitoring_runs_immutable",
                "scientific_changes_immutable",
                "scientific_change_acknowledgements_immutable",
                "scientific_source_watch_transitions_immutable",
                "backup_restore_verifications_immutable",
                "identity_resolution_events_immutable",
                "publication_representations_immutable",
                "publication_relationships_immutable",
                "scientific_impact_review_resolutions_immutable",
                "scientific_follow_up_case_targets_immutable",
            }
            cursor.execute("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")
            missing_triggers = required_triggers - {row[0] for row in cursor.fetchall()}
            if missing_triggers:
                findings.append(f"missing immutable triggers: {sorted(missing_triggers)}")
            cursor.execute("SELECT indexname FROM pg_indexes WHERE tablename='embedding_index'")
            if "embedding_hnsw_cosine_idx" not in {row[0] for row in cursor.fetchall()}:
                findings.append("HNSW cosine index is missing")
            cursor.execute("""
                SELECT storage_uri,file_size,checksum_sha256,media_type
                FROM scientific_representations
            """)
            representations = cursor.fetchall()

    client = boto3.client(
        "s3", endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )
    for bucket in ("researchos-documents", "researchos-backups"):
        try:
            client.head_bucket(Bucket=bucket)
        except Exception as exc:
            findings.append(f"bucket unavailable {bucket}: {type(exc).__name__}")
    for uri, size, checksum, media_type in representations:
        parsed = urlparse(uri)
        if parsed.scheme != "s3":
            findings.append(f"non-S3 canonical representation: {uri}")
            continue
        try:
            head = client.head_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))
        except Exception as exc:
            findings.append(f"missing representation object {uri}: {type(exc).__name__}")
            continue
        if head["ContentLength"] != size or head.get("Metadata", {}).get("sha256") != checksum:
            findings.append(f"representation integrity metadata mismatch: {uri}")
        if head.get("ContentType") != media_type:
            findings.append(f"representation media type mismatch: {uri}")
    if findings:
        raise AssertionError("; ".join(findings))
    print(
        f"storage compliance: passed ({len(registered)} contracts, "
        f"{len(representations)} representations verified)"
    )


if __name__ == "__main__":
    main()
