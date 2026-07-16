"""Transactional PostgreSQL implementation for DATA-002A/B."""

from __future__ import annotations

from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.ingestion.models import AcquisitionResult, AcquisitionStatus
from app.knowledge.models import DiscoveryRun, LiteratureRecord, SourceRecord
from app.knowledge.retrieval.models import MetadataRun
from app.knowledge.repositories.models import StoredRepresentation
from app.knowledge.repositories.postgres_semantic import PostgresSemanticRepositoryMixin
from app.knowledge.repositories.postgres_read_model import PostgresReadModelRepositoryMixin
from app.knowledge.repositories.postgres_evidence import PostgresEvidenceRepositoryMixin
from app.knowledge.repositories.postgres_artifacts import PostgresArtifactRepositoryMixin


def normalized_source_license(raw: dict) -> str | None:
    value = raw.get("license")
    if isinstance(value, str):
        return value.strip() or None
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, dict):
            candidate = item.get("URL") or item.get("url")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def source_access_status(raw: dict, license_value: str | None) -> str:
    if isinstance(raw.get("open_access"), dict) and raw["open_access"].get("is_oa") is True:
        return "open"
    if raw.get("openAccessPdf"):
        return "open"
    if license_value and "creativecommons.org/" in license_value.lower():
        return "open"
    return "unknown"


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
        run.validate_query_plan()
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
        license_value = normalized_source_license(raw)
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
            source.retrieved_at, license_value,
            source_access_status(raw, license_value),
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


class PostgresScientificDataRepository(
    PostgresSemanticRepositoryMixin,
    PostgresReadModelRepositoryMixin,
    PostgresEvidenceRepositoryMixin,
    PostgresArtifactRepositoryMixin,
    _PostgresRepositoryCore,
):
    """Compatibility façade composed from bounded PostgreSQL repositories."""
