DROP TRIGGER IF EXISTS scientific_representations_immutable ON scientific_representations;
CREATE TRIGGER scientific_representations_immutable
    BEFORE UPDATE OR DELETE ON scientific_representations
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS publication_representations_immutable ON publication_representations;
CREATE TRIGGER publication_representations_immutable
    BEFORE UPDATE OR DELETE ON publication_representations
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
