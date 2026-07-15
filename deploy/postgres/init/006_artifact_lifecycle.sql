ALTER TABLE artifact_lifecycle_events
    DROP CONSTRAINT IF EXISTS artifact_lifecycle_events_provenance_key;
ALTER TABLE artifact_lifecycle_events
    ADD CONSTRAINT artifact_lifecycle_events_provenance_key UNIQUE(provenance_id);

DROP TRIGGER IF EXISTS artifact_lifecycle_events_immutable ON artifact_lifecycle_events;
CREATE TRIGGER artifact_lifecycle_events_immutable
    BEFORE UPDATE OR DELETE ON artifact_lifecycle_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
