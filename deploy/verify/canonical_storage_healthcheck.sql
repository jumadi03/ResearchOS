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
    'citation_traversal_runs','citation_traversal_edges',
    'citation_traversal_candidates','citation_traversal_failures',
    'extraction_manifests','knowledge_intake_manifests',
    'scientific_identifiers','identity_resolution_events',
    'evidence_objects','provenance_events',
    'knowledge_nodes','knowledge_edges','research_artifacts',
    'artifact_lifecycle_events','publication_representations',
    'backup_restore_verifications'
);

DO $$
BEGIN
    IF (SELECT COALESCE(max(version),0) FROM schema_migrations) <> 29 THEN
        RAISE EXCEPTION 'database schema version does not match application';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM storage_contract_registry
        WHERE resource_name='backup_runs'
          AND lifecycle_class='operational_staging'
          AND responsibility LIKE 'Mutable backup construction%'
    ) THEN
        RAISE EXCEPTION 'backup_runs authority classification is stale';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname='backup_restore_verifications_immutable'
          AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 'restore verification immutability is missing';
    END IF;
END;
$$;

DO $$
DECLARE
    test_backup_id uuid;
    test_verification_id uuid;
    set_hash text := repeat('a', 64);
BEGIN
    BEGIN
        INSERT INTO backup_runs(
            backup_stamp,status,database_path,minio_path,knowledge_path,
            database_verified,minio_verified,knowledge_verified,
            backup_set_id,backup_set_hash,manifest_path,integrity_verified,
            completed_at
        ) VALUES (
            'health-restore-contract','completed','database','minio','knowledge',
            true,true,true,'health-backup-set',set_hash,'manifest',true,now()
        ) RETURNING backup_id INTO test_backup_id;

        INSERT INTO backup_restore_verifications(
            backup_id,backup_set_hash,target_kind,target_identifier,components,
            outcome,checks,actor,started_at,completed_at,content_hash
        ) VALUES (
            test_backup_id,set_hash,'isolated','health-isolated-target',
            ARRAY['postgresql','minio','knowledge'],'verified',
            '[{"check":"contract","outcome":"passed"}]'::jsonb,
            'healthcheck',now(),now(),repeat('b', 64)
        ) RETURNING verification_id INTO test_verification_id;

        BEGIN
            UPDATE backup_restore_verifications
            SET outcome='failed' WHERE verification_id=test_verification_id;
            RAISE EXCEPTION 'restore evidence mutation was not rejected';
        EXCEPTION
            WHEN raise_exception THEN
                IF SQLERRM <> 'provenance ledger is append-only' THEN
                    RAISE;
                END IF;
        END;

        BEGIN
            INSERT INTO backup_restore_verifications(
                backup_id,backup_set_hash,target_kind,target_identifier,
                components,outcome,checks,actor,started_at,completed_at,content_hash
            ) VALUES (
                test_backup_id,repeat('c', 64),'isolated','mismatched-set',
                ARRAY['postgresql'],'failed',
                '[{"check":"binding","outcome":"failed"}]'::jsonb,
                'healthcheck',now(),now(),repeat('d', 64)
            );
            RAISE EXCEPTION 'mismatched backup set hash was not rejected';
        EXCEPTION
            WHEN foreign_key_violation THEN NULL;
        END;

        RAISE EXCEPTION 'restore contract healthcheck rollback';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'restore contract healthcheck rollback' THEN
                RAISE;
            END IF;
    END;
END;
$$;
