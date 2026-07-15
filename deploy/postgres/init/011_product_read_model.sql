CREATE TABLE IF NOT EXISTS research_projects (
    project_id text PRIMARY KEY,
    name text NOT NULL,
    description text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_objects (
    project_id text NOT NULL REFERENCES research_projects(project_id),
    object_id uuid NOT NULL REFERENCES canonical_objects(object_id),
    added_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(project_id,object_id)
);
CREATE INDEX IF NOT EXISTS project_objects_object_idx ON project_objects(object_id);

INSERT INTO research_projects(project_id,name,description)
VALUES ('researchos-default','ResearchOS','Default workspace for canonical objects created before project assignment')
ON CONFLICT(project_id) DO NOTHING;

INSERT INTO project_objects(project_id,object_id)
SELECT 'researchos-default',object_id FROM canonical_objects
ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION assign_default_project() RETURNS trigger AS $$
BEGIN
    INSERT INTO project_objects(project_id,object_id)
    VALUES ('researchos-default',NEW.object_id)
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS canonical_objects_default_project ON canonical_objects;
CREATE TRIGGER canonical_objects_default_project
    AFTER INSERT ON canonical_objects
    FOR EACH ROW EXECUTE FUNCTION assign_default_project();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
('research_projects','postgres_table','Research Workspace','Canonical project workspace identity',true,'canonical',true,'Root product workspace'),
('project_objects','postgres_table','Research Workspace','Project-to-canonical-object membership',true,'canonical',true,'Enables project-scoped read models')
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,notes=excluded.notes,updated_at=now();
