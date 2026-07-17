ALTER TABLE backup_restore_verifications
    ADD COLUMN IF NOT EXISTS report jsonb,
    ADD COLUMN IF NOT EXISTS attestation_algorithm text,
    ADD COLUMN IF NOT EXISTS attestation_key_id text,
    ADD COLUMN IF NOT EXISTS attestation_signature text;

CREATE OR REPLACE FUNCTION validate_restore_verification_admission()
RETURNS trigger AS $$
DECLARE
    component_count integer;
    report_component_count integer;
    backup_is_eligible boolean;
BEGIN
    IF NEW.outcome <> 'verified' THEN
        RETURN NEW;
    END IF;

    SELECT count(DISTINCT value)
    INTO component_count
    FROM unnest(NEW.components) AS value;
    IF cardinality(NEW.components) <> 6
       OR component_count <> 6
       OR NOT NEW.components @> ARRAY[
           'postgresql', 'minio', 'knowledge', 'architecture',
           'configuration', 'migration'
       ]::text[] THEN
        RAISE EXCEPTION 'verified restore evidence requires six unique canonical components';
    END IF;

    IF NEW.target_identifier <> 'researchos_restore_drill+researchos-restore-drill'
       OR NEW.report IS NULL
       OR jsonb_typeof(NEW.report) <> 'object'
       OR NEW.attestation_algorithm <> 'ed25519'
       OR length(trim(NEW.attestation_key_id)) = 0
       OR length(trim(NEW.attestation_signature)) = 0 THEN
        RAISE EXCEPTION 'verified restore evidence lacks canonical attestation';
    END IF;

    SELECT count(DISTINCT value)
    INTO report_component_count
    FROM jsonb_array_elements_text(NEW.report->'components') AS value;
    IF jsonb_array_length(NEW.report->'components') <> 6
       OR report_component_count <> 6
       OR NEW.report->>'schema_version' <> '1.0'
       OR NEW.report->>'outcome' <> NEW.outcome
       OR NEW.report->>'target_kind' <> NEW.target_kind
       OR NEW.report->>'target_identifier' <> NEW.target_identifier
       OR NEW.report->>'manifest_hash' <> NEW.backup_set_hash
       OR NEW.report->>'content_hash' <> NEW.content_hash
       OR NEW.report->'checks' <> NEW.checks
       OR (NEW.report->>'actor') <> NEW.actor
       OR (NEW.report->>'started_at')::timestamptz <> NEW.started_at
       OR (NEW.report->>'completed_at')::timestamptz <> NEW.completed_at
       OR NEW.report->'restore_executed' <> 'true'::jsonb
       OR NEW.report->'active_target_touched' <> 'false'::jsonb
       OR NEW.report->'cleanup_verified' <> 'true'::jsonb
       OR NEW.report->'ledger_written' <> 'false'::jsonb
       OR NEW.report->'error' <> 'null'::jsonb
       OR NEW.report->'attestation'->>'algorithm' <> NEW.attestation_algorithm
       OR NEW.report->'attestation'->>'key_id' <> NEW.attestation_key_id
       OR NEW.report->'attestation'->>'signature' <> NEW.attestation_signature THEN
        RAISE EXCEPTION 'verified restore evidence report does not match ledger projection';
    END IF;

    SELECT status = 'completed'
           AND integrity_verified
           AND database_verified
           AND minio_verified
           AND knowledge_verified
    INTO backup_is_eligible
    FROM backup_runs
    WHERE backup_id = NEW.backup_id
      AND backup_set_hash = NEW.backup_set_hash;
    IF backup_is_eligible IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'verified restore evidence references an ineligible backup';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS backup_restore_verifications_admission_guard
    ON backup_restore_verifications;
CREATE TRIGGER backup_restore_verifications_admission_guard
BEFORE INSERT ON backup_restore_verifications
FOR EACH ROW EXECUTE FUNCTION validate_restore_verification_admission();

CREATE OR REPLACE FUNCTION admit_backup_restore_verification(p_report jsonb)
RETURNS uuid AS $$
DECLARE
    existing_id uuid;
    matched_backup_id uuid;
    result_id uuid;
BEGIN
    SELECT verification_id INTO existing_id
    FROM backup_restore_verifications
    WHERE content_hash = p_report->>'content_hash';
    IF existing_id IS NOT NULL THEN
        RETURN existing_id;
    END IF;

    SELECT backup_id INTO matched_backup_id
    FROM backup_runs
    WHERE backup_stamp = p_report->>'backup_stamp'
      AND backup_set_hash = p_report->>'manifest_hash'
      AND status = 'completed'
      AND integrity_verified
      AND database_verified
      AND minio_verified
      AND knowledge_verified;
    IF matched_backup_id IS NULL THEN
        RAISE EXCEPTION 'restore report does not match an eligible canonical backup';
    END IF;

    INSERT INTO backup_restore_verifications(
        backup_id, backup_set_hash, target_kind, target_identifier, components,
        outcome, checks, actor, started_at, completed_at, content_hash,
        report, attestation_algorithm, attestation_key_id, attestation_signature
    ) VALUES (
        matched_backup_id,
        p_report->>'manifest_hash',
        p_report->>'target_kind',
        p_report->>'target_identifier',
        ARRAY(SELECT jsonb_array_elements_text(p_report->'components')),
        p_report->>'outcome',
        p_report->'checks',
        p_report->>'actor',
        (p_report->>'started_at')::timestamptz,
        (p_report->>'completed_at')::timestamptz,
        p_report->>'content_hash',
        p_report,
        p_report->'attestation'->>'algorithm',
        p_report->'attestation'->>'key_id',
        p_report->'attestation'->>'signature'
    )
    RETURNING verification_id INTO result_id;
    RETURN result_id;
END;
$$ LANGUAGE plpgsql;

UPDATE storage_contract_registry SET
    responsibility='Append-only signed evidence admitted from isolated restore verification',
    notes='Verified readiness requires complete signed report admission and live trust revalidation',
    updated_at=now()
WHERE resource_name='backup_restore_verifications';
