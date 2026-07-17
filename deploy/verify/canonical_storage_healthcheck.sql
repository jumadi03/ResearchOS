DO $$
DECLARE
    object_uuid uuid;
    event_uuid uuid;
BEGIN
    INSERT INTO canonical_objects(object_type, stable_key, lifecycle_status)
    VALUES ('health_check', 'health:provenance-object', 'draft')
    ON CONFLICT(stable_key) DO UPDATE SET updated_at=now()
    RETURNING object_id INTO object_uuid;

    INSERT INTO provenance_events(
        execution_id, output_object_id, event_type, occurred_at, event_hash
    ) VALUES (
        'health-execution', object_uuid, 'health_check', now(),
        encode(digest('health-provenance-event', 'sha256'), 'hex')
    ) ON CONFLICT(event_hash) DO NOTHING
    RETURNING provenance_id INTO event_uuid;
    IF event_uuid IS NULL THEN
        SELECT provenance_id INTO event_uuid FROM provenance_events
        WHERE event_hash=encode(digest('health-provenance-event', 'sha256'), 'hex');
    END IF;

    BEGIN
        UPDATE provenance_events SET event_type='mutated' WHERE provenance_id=event_uuid;
        RAISE EXCEPTION 'append-only trigger did not reject mutation';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'provenance ledger is append-only' THEN
                RAISE;
            END IF;
    END;
END;
$$;

SELECT 'canonical-tables=' || count(*)
FROM pg_tables
WHERE schemaname='public' AND tablename IN (
    'canonical_objects','scientific_sources','scientific_documents',
    'document_source_references','metadata_observations',
    'scientific_representations','source_inspections','screening_decisions',
    'extraction_manifests',
    'scientific_identifiers','identity_resolution_events',
    'evidence_objects','provenance_events',
    'knowledge_nodes','knowledge_edges','research_artifacts',
    'artifact_lifecycle_events','publication_representations'
);

DO $$
BEGIN
    IF (SELECT COALESCE(max(version),0) FROM schema_migrations) <> 22 THEN
        RAISE EXCEPTION 'database schema version does not match application';
    END IF;
END;
$$;
