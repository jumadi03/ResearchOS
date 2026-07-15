CREATE TABLE IF NOT EXISTS canonical_objects (
    object_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type text NOT NULL,
    stable_key text NOT NULL UNIQUE,
    lifecycle_status text NOT NULL DEFAULT 'draft' CHECK (lifecycle_status IN
        ('planned','draft','review','validated','ratified','published','deprecated','archived')),
    current_version integer NOT NULL DEFAULT 1 CHECK (current_version > 0),
    classification text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scientific_sources (
    source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    source_type text NOT NULL,
    external_id text NOT NULL,
    doi text,
    url text,
    title text,
    authors jsonb NOT NULL DEFAULT '[]',
    publication_year integer,
    retrieved_at timestamptz NOT NULL,
    license text,
    access_status text NOT NULL DEFAULT 'unknown' CHECK (access_status IN
        ('open','restricted','unknown')),
    response_hash text NOT NULL,
    UNIQUE(provider, external_id, response_hash)
);
CREATE INDEX IF NOT EXISTS scientific_sources_doi_idx
    ON scientific_sources (lower(doi)) WHERE doi IS NOT NULL;

CREATE TABLE IF NOT EXISTS scientific_documents (
    document_id uuid PRIMARY KEY REFERENCES canonical_objects(object_id),
    canonical_doi text,
    title text NOT NULL,
    abstract text,
    authors jsonb NOT NULL DEFAULT '[]',
    institutions jsonb NOT NULL DEFAULT '[]',
    journal text,
    keywords jsonb NOT NULL DEFAULT '[]',
    publication_date date,
    language text,
    document_type text,
    citation_count integer,
    license text,
    metadata_version integer NOT NULL DEFAULT 1,
    metadata_hash text NOT NULL,
    UNIQUE (canonical_doi)
);

CREATE TABLE IF NOT EXISTS document_source_references (
    document_id uuid NOT NULL REFERENCES scientific_documents(document_id),
    source_id uuid NOT NULL REFERENCES scientific_sources(source_id),
    match_method text NOT NULL,
    match_confidence double precision NOT NULL CHECK (match_confidence BETWEEN 0 AND 1),
    linked_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(document_id, source_id)
);

CREATE TABLE IF NOT EXISTS metadata_observations (
    observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES scientific_documents(document_id),
    source_id uuid NOT NULL REFERENCES scientific_sources(source_id),
    metadata jsonb NOT NULL,
    observed_at timestamptz NOT NULL,
    content_hash text NOT NULL,
    UNIQUE(document_id, source_id, content_hash)
);

CREATE TABLE IF NOT EXISTS scientific_representations (
    representation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id uuid NOT NULL REFERENCES canonical_objects(object_id),
    representation_type text NOT NULL CHECK (representation_type IN
        ('pdf','html','xml','json','supplementary','dataset','markdown','docx','csv','rdf')),
    storage_uri text NOT NULL,
    media_type text NOT NULL,
    checksum_sha256 text NOT NULL,
    file_size bigint NOT NULL CHECK (file_size >= 0),
    document_version integer NOT NULL CHECK (document_version > 0),
    source_url text,
    retrieval_method text,
    retrieved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(object_id, representation_type, checksum_sha256)
);

CREATE TABLE IF NOT EXISTS evidence_objects (
    evidence_id uuid PRIMARY KEY REFERENCES canonical_objects(object_id),
    document_id uuid NOT NULL REFERENCES scientific_documents(document_id),
    representation_id uuid NOT NULL REFERENCES scientific_representations(representation_id),
    evidence_type text NOT NULL CHECK (evidence_type IN
        ('claim','evidence','method','variable','population','dataset','result','limitation','conclusion')),
    statement text NOT NULL,
    page integer,
    section text,
    paragraph integer,
    character_start integer,
    character_end integer,
    table_id text,
    figure_id text,
    extraction_method text NOT NULL,
    extraction_confidence double precision CHECK (extraction_confidence BETWEEN 0 AND 1),
    human_review_status text NOT NULL DEFAULT 'pending' CHECK (human_review_status IN
        ('pending','accepted','rejected')),
    content_hash text NOT NULL
);

CREATE TABLE IF NOT EXISTS provenance_events (
    provenance_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id text NOT NULL,
    workflow_id text,
    task_id text,
    context_snapshot_id text,
    source_object_id uuid REFERENCES canonical_objects(object_id),
    output_object_id uuid REFERENCES canonical_objects(object_id),
    agent_id text,
    provider_id text,
    model_id text,
    configuration_id text,
    human_reviewer text,
    event_type text NOT NULL,
    event_payload jsonb NOT NULL DEFAULT '{}',
    occurred_at timestamptz NOT NULL,
    event_hash text NOT NULL UNIQUE
);

CREATE OR REPLACE FUNCTION reject_ledger_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'provenance ledger is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS provenance_events_immutable ON provenance_events;
CREATE TRIGGER provenance_events_immutable
    BEFORE UPDATE OR DELETE ON provenance_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

CREATE TABLE IF NOT EXISTS knowledge_nodes (
    node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id uuid NOT NULL UNIQUE REFERENCES canonical_objects(object_id),
    node_type text NOT NULL,
    ontology_term text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_edges (
    edge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id uuid NOT NULL REFERENCES knowledge_nodes(node_id),
    target_node_id uuid NOT NULL REFERENCES knowledge_nodes(node_id),
    relationship_type text NOT NULL CHECK (relationship_type IN
        ('cites','supports','contradicts','extends','replicates','uses_method',
         'measures','has_limitation','derived_from','part_of')),
    provenance_id uuid NOT NULL REFERENCES provenance_events(provenance_id),
    confidence double precision CHECK (confidence BETWEEN 0 AND 1),
    review_status text NOT NULL DEFAULT 'provisional' CHECK (review_status IN
        ('provisional','accepted','rejected')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(source_node_id, target_node_id, relationship_type, provenance_id)
);
CREATE INDEX IF NOT EXISTS knowledge_edges_source_idx ON knowledge_edges(source_node_id, relationship_type);
CREATE INDEX IF NOT EXISTS knowledge_edges_target_idx ON knowledge_edges(target_node_id, relationship_type);

CREATE TABLE IF NOT EXISTS research_artifacts (
    artifact_id uuid PRIMARY KEY REFERENCES canonical_objects(object_id),
    project_id text NOT NULL,
    artifact_type text NOT NULL,
    title text NOT NULL,
    status text NOT NULL,
    provenance_id uuid REFERENCES provenance_events(provenance_id),
    metadata jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS artifact_lifecycle_events (
    lifecycle_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id uuid NOT NULL REFERENCES research_artifacts(artifact_id),
    from_status text,
    to_status text NOT NULL,
    actor_id text NOT NULL,
    rationale text NOT NULL,
    occurred_at timestamptz NOT NULL,
    provenance_id uuid REFERENCES provenance_events(provenance_id)
);

CREATE TABLE IF NOT EXISTS publication_representations (
    publication_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id uuid NOT NULL REFERENCES research_artifacts(artifact_id),
    representation_id uuid NOT NULL UNIQUE REFERENCES scientific_representations(representation_id),
    edition_type text NOT NULL,
    published_at timestamptz,
    publication_hash text NOT NULL UNIQUE
);

ALTER TABLE embedding_index ADD COLUMN IF NOT EXISTS canonical_object_id uuid;
ALTER TABLE embedding_index ADD COLUMN IF NOT EXISTS content_hash text;
ALTER TABLE embedding_index DROP CONSTRAINT IF EXISTS embedding_index_canonical_object_fk;
ALTER TABLE embedding_index ADD CONSTRAINT embedding_index_canonical_object_fk
    FOREIGN KEY (canonical_object_id) REFERENCES canonical_objects(object_id);
ALTER TABLE embedding_index ALTER COLUMN canonical_object_id SET NOT NULL;
ALTER TABLE embedding_index ALTER COLUMN content_hash SET NOT NULL;
CREATE INDEX IF NOT EXISTS embedding_index_canonical_object_idx
    ON embedding_index(canonical_object_id, model);

COMMENT ON TABLE document_registry IS 'Operational filesystem registry; canonical identity lives in canonical_objects/scientific_documents/scientific_representations.';
COMMENT ON TABLE normalized_metadata IS 'Operational worker staging; canonical metadata lives in scientific_documents and metadata_observations.';
COMMENT ON TABLE embedding_index IS 'Derived semantic search index; never a canonical source of scientific truth.';
