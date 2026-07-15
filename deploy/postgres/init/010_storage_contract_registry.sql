CREATE TABLE IF NOT EXISTS storage_contract_registry (
    resource_name text PRIMARY KEY,
    resource_kind text NOT NULL CHECK (resource_kind IN
        ('postgres_table','minio_bucket','filesystem_snapshot','derived_index','job_queue')),
    owner_component text NOT NULL,
    responsibility text NOT NULL,
    source_of_truth boolean NOT NULL,
    lifecycle_class text NOT NULL CHECK (lifecycle_class IN
        ('canonical','immutable_ledger','representation','derived','operational_staging','retired')),
    active boolean NOT NULL,
    notes text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
('canonical_objects','postgres_table','Scientific Data Repository','Stable identity, lifecycle, and version',true,'canonical',true,'Root identity for canonical scientific objects'),
('scientific_sources','postgres_table','Source Registry','Provider-specific immutable source observations',true,'canonical',true,'Provider identity is retained without becoming canonical identity'),
('scientific_documents','postgres_table','Document Repository','Canonical scientific document metadata',true,'canonical',true,'One row per canonical document'),
('document_source_references','postgres_table','Source Registry','Auditable source-to-document match decisions',true,'canonical',true,'Match method and confidence retained'),
('metadata_observations','postgres_table','Metadata Repository','Immutable raw and normalized metadata observations',true,'canonical',true,'Content-hash idempotent observations'),
('scientific_representations','postgres_table','Representation Repository','Immutable representation identity and integrity metadata',true,'representation',true,'Bytes reside in MinIO'),
('evidence_objects','postgres_table','Evidence Repository','Canonical extracted scientific evidence',true,'canonical',true,'Exact document and representation coordinates'),
('evidence_review_events','postgres_table','Evidence Review Workflow','Append-only attributed evidence decisions',true,'immutable_ledger',true,'Current state is materialized on evidence_objects'),
('provenance_events','postgres_table','Provenance Ledger','Append-only execution and decision provenance',true,'immutable_ledger',true,'Never update or delete'),
('knowledge_nodes','postgres_table','Knowledge Graph Repository','Canonical graph node adjacency',true,'canonical',true,'Backed by canonical objects'),
('knowledge_edges','postgres_table','Knowledge Graph Repository','Provenance-required graph assertions',true,'canonical',true,'Review status reflects current supporting evidence'),
('research_artifacts','postgres_table','Artifact Repository','Canonical research outputs and current lifecycle',true,'canonical',true,'Domain metadata retained with content hash'),
('artifact_lifecycle_events','postgres_table','Artifact Lifecycle Repository','Append-only artifact state transitions',true,'immutable_ledger',true,'Actor and rationale are mandatory'),
('publication_representations','postgres_table','Publication Repository','Immutable publication editions',true,'representation',true,'Links artifact identity to immutable representation'),
('embedding_index','derived_index','Semantic Retrieval','Rebuildable pgvector similarity index',false,'derived',true,'Never a source of scientific truth'),
('background_jobs','job_queue','Background Workers','Operational asynchronous job coordination',false,'operational_staging',true,'May be retained for rebuild and audit diagnostics'),
('normalized_metadata','postgres_table','Background Workers','Legacy normalization staging output',false,'operational_staging',true,'Still written by normalize_metadata worker jobs'),
('document_registry','postgres_table','Legacy Data Layer','Superseded database document staging table',false,'retired',false,'Active document registry is filesystem-backed; preserve table for migration audit only'),
('researchos-documents','minio_bucket','Representation Repository','Content-addressed document and publication bytes',true,'representation',true,'Integrity metadata mirrored in PostgreSQL'),
('researchos-backups','minio_bucket','Backup Process','Backup object namespace',false,'operational_staging',true,'Operational backup destination'),
('knowledge_data','filesystem_snapshot','Scientific Knowledge Service','Portable run manifests and compatibility extraction registry',false,'operational_staging',true,'Compatibility fallback; not canonical when database/object storage are configured')
ON CONFLICT(resource_name) DO UPDATE SET
    resource_kind=excluded.resource_kind,
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();

COMMENT ON TABLE document_registry IS 'RETIRED: superseded PostgreSQL staging table. Active compatibility registry is filesystem-backed; canonical representations are in scientific_representations + MinIO.';
COMMENT ON TABLE normalized_metadata IS 'ACTIVE OPERATIONAL STAGING: worker normalization output only; canonical metadata is scientific_documents + metadata_observations.';
COMMENT ON TABLE embedding_index IS 'DERIVED AND REBUILDABLE: semantic retrieval index; never canonical scientific truth.';

CREATE OR REPLACE VIEW storage_contract_compliance AS
SELECT r.resource_name,r.owner_component,r.lifecycle_class,r.active,
       CASE
         WHEN r.resource_kind IN ('postgres_table','derived_index','job_queue')
           THEN to_regclass(r.resource_name) IS NOT NULL
         ELSE true
       END AS resource_present,
       r.source_of_truth,r.notes
FROM storage_contract_registry r;
