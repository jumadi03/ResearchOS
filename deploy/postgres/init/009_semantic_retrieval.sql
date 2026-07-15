ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS content_hash text;
UPDATE research_artifacts
SET content_hash=encode(digest(convert_to(metadata::text,'UTF8'),'sha256'),'hex')
WHERE content_hash IS NULL;
ALTER TABLE research_artifacts ALTER COLUMN content_hash SET NOT NULL;
CREATE INDEX IF NOT EXISTS research_artifacts_semantic_eligibility_idx
    ON research_artifacts(status,content_hash);
