CREATE TABLE publication_relationships (
    relationship_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_key text NOT NULL UNIQUE,
    source_artifact_id uuid NOT NULL REFERENCES research_artifacts(artifact_id),
    target_artifact_id uuid REFERENCES research_artifacts(artifact_id),
    relation_type text NOT NULL CHECK(
        relation_type IN ('corrects','supersedes','retracts')
    ),
    actor_id text NOT NULL CHECK(length(btrim(actor_id)) > 0),
    rationale text NOT NULL CHECK(length(btrim(rationale)) > 0),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id),
    content_hash text NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
    CHECK(
        (relation_type = 'retracts' AND target_artifact_id IS NULL)
        OR
        (relation_type IN ('corrects','supersedes')
         AND target_artifact_id IS NOT NULL
         AND source_artifact_id <> target_artifact_id)
    )
);

CREATE INDEX publication_relationships_source_idx
    ON publication_relationships(source_artifact_id, occurred_at);
CREATE INDEX publication_relationships_target_idx
    ON publication_relationships(target_artifact_id, occurred_at)
    WHERE target_artifact_id IS NOT NULL;

CREATE TRIGGER publication_relationships_immutable
    BEFORE UPDATE OR DELETE ON publication_relationships
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'publication_relationships','postgres_table','Publication Repository',
    'Immutable correction, supersession, and retraction relationships',
    true,'immutable_ledger',true,
    'Published packages remain immutable; relationships project current use'
);
