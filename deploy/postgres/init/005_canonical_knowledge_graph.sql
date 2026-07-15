ALTER TABLE knowledge_edges
    DROP CONSTRAINT IF EXISTS knowledge_edges_relationship_type_check;
ALTER TABLE knowledge_edges
    ADD CONSTRAINT knowledge_edges_relationship_type_check CHECK (relationship_type IN
        ('contains','cites','supports','contradicts','extends','replicates','uses_method',
         'measures','has_limitation','derived_from','part_of'));
