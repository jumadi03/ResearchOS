"""PostgreSQL project and object read-model queries."""

from app.knowledge.repositories.read_models import ObjectPage, ObjectSummary, ProjectSummary


class PostgresReadModelRepositoryMixin:
    """Read-only product projections composed into the PostgreSQL façade."""

    def list_projects(self) -> tuple[ProjectSummary, ...]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.project_id,p.name,p.description,p.status,count(po.object_id)
                    FROM research_projects p
                    LEFT JOIN project_objects po ON po.project_id=p.project_id
                    GROUP BY p.project_id ORDER BY p.name,p.project_id
                """)
                rows = cursor.fetchall()
        return tuple(ProjectSummary(*row) for row in rows)

    def list_objects(
        self, project_id: str, *, limit: int, cursor: str | None,
        query: str | None, object_types: tuple[str, ...],
    ) -> ObjectPage:
        if not 1 <= limit <= 100:
            raise ValueError("Object page limit must be from 1 to 100")
        clauses = ["po.project_id=%s"]
        values = [project_id]
        if cursor:
            clauses.append("c.stable_key>%s")
            values.append(cursor)
        if query:
            clauses.append("lower(COALESCE(d.title,a.title,e.statement,c.stable_key)) LIKE %s")
            values.append(f"%{query.strip().lower()}%")
        if object_types:
            clauses.append("c.object_type=ANY(%s)")
            values.append(list(object_types))
        values.append(limit + 1)
        with self._connect() as connection:
            with connection.cursor() as db_cursor:
                db_cursor.execute(f"""
                    SELECT c.object_id,c.stable_key,c.object_type,c.lifecycle_status,
                           c.current_version,
                           COALESCE(d.title,a.title,e.statement,c.stable_key) AS title,
                           c.updated_at
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    LEFT JOIN scientific_documents d ON d.document_id=c.object_id
                    LEFT JOIN research_artifacts a ON a.artifact_id=c.object_id
                    LEFT JOIN evidence_objects e ON e.evidence_id=c.object_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY c.stable_key LIMIT %s
                """, values)
                rows = db_cursor.fetchall()
        page_rows = rows[:limit]
        items = tuple(ObjectSummary(
            str(row[0]), row[1], row[2], row[3], row[4], row[5], row[6].isoformat(),
        ) for row in page_rows)
        next_cursor = page_rows[-1][1] if len(rows) > limit else None
        return ObjectPage(items, next_cursor)

    def get_object_read_model(self, object_ref: str, project_id: str) -> dict:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.object_id,c.stable_key,c.object_type,c.lifecycle_status,
                           c.current_version,c.classification,c.created_at,c.updated_at,
                           COALESCE(d.title,a.title,e.statement,c.stable_key),
                           d.canonical_doi,d.authors,d.journal,d.publication_date,
                           e.evidence_type,e.page,e.character_start,e.character_end,
                           e.human_review_status,e.extraction_confidence,
                           a.artifact_type,a.status,a.metadata,a.content_hash
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    LEFT JOIN scientific_documents d ON d.document_id=c.object_id
                    LEFT JOIN evidence_objects e ON e.evidence_id=c.object_id
                    LEFT JOIN research_artifacts a ON a.artifact_id=c.object_id
                    WHERE po.project_id=%s
                      AND (c.object_id::text=%s OR c.stable_key=%s)
                """, (project_id, object_ref, object_ref))
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(f"Unknown project object: {object_ref}")
                object_id = row[0]
                cursor.execute("""
                    SELECT representation_id,representation_type,storage_uri,media_type,
                           checksum_sha256,file_size,document_version,created_at
                    FROM scientific_representations WHERE object_id=%s
                    ORDER BY representation_type,document_version DESC
                """, (object_id,))
                representations = [{
                    "representation_id": str(item[0]), "type": item[1],
                    "storage_uri": item[2], "media_type": item[3],
                    "checksum_sha256": item[4], "file_size": item[5],
                    "version": item[6], "created_at": item[7].isoformat(),
                } for item in cursor.fetchall()]
                cursor.execute("""
                    SELECT ks.stable_key,kt.stable_key,ke.relationship_type,
                           ke.confidence,ke.review_status,ke.provenance_id,ke.created_at
                    FROM knowledge_edges ke
                    JOIN knowledge_nodes ns ON ns.node_id=ke.source_node_id
                    JOIN canonical_objects ks ON ks.object_id=ns.object_id
                    JOIN knowledge_nodes nt ON nt.node_id=ke.target_node_id
                    JOIN canonical_objects kt ON kt.object_id=nt.object_id
                    WHERE ns.object_id=%s OR nt.object_id=%s
                    ORDER BY ke.created_at DESC LIMIT 100
                """, (object_id, object_id))
                relationships = [{
                    "source": item[0], "target": item[1], "type": item[2],
                    "confidence": item[3], "review_status": item[4],
                    "provenance_id": str(item[5]), "created_at": item[6].isoformat(),
                } for item in cursor.fetchall()]
                cursor.execute("""
                    SELECT provenance_id,event_type,event_payload,occurred_at,
                           COALESCE(human_reviewer,agent_id,provider_id)
                    FROM provenance_events
                    WHERE source_object_id=%s OR output_object_id=%s
                    ORDER BY occurred_at DESC,provenance_id DESC LIMIT 100
                """, (object_id, object_id))
                timeline = [{
                    "provenance_id": str(item[0]), "event_type": item[1],
                    "payload": item[2], "occurred_at": item[3].isoformat(),
                    "actor": item[4],
                } for item in cursor.fetchall()]
        return {
            "identity": {
                "object_id": str(row[0]), "stable_key": row[1], "object_type": row[2],
                "lifecycle_status": row[3], "current_version": row[4],
                "classification": row[5], "created_at": row[6].isoformat(),
                "updated_at": row[7].isoformat(),
                "deep_link": f"/knowledge/projects/{project_id}/objects/{row[0]}",
            },
            "summary": {"title": row[8]},
            "document": ({
                "doi": row[9], "authors": row[10], "journal": row[11],
                "publication_date": row[12].isoformat() if row[12] else None,
            } if row[9] is not None or row[10] is not None else None),
            "evidence": ({
                "type": row[13], "page": row[14], "character_start": row[15],
                "character_end": row[16], "review_status": row[17],
                "confidence": row[18],
            } if row[13] is not None else None),
            "artifact": ({
                "type": row[19], "status": row[20], "metadata": row[21],
                "content_hash": row[22],
            } if row[19] is not None else None),
            "representations": representations,
            "relationships": relationships,
            "timeline": timeline,
            "project_id": project_id,
        }

    def get_work_queue(self, project_id: str) -> dict:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.object_id,c.stable_key,e.statement,e.evidence_type,
                           e.extraction_confidence,c.updated_at,e.page,e.section,
                           e.character_start,e.character_end,e.content_hash,
                           x.manifest_hash,d.title,d.canonical_doi
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    JOIN evidence_objects e ON e.evidence_id=c.object_id
                    JOIN extraction_manifests x
                      ON x.extraction_manifest_id=e.extraction_manifest_id
                    JOIN scientific_documents d ON d.document_id=e.document_id
                    WHERE po.project_id=%s AND e.human_review_status='pending'
                    ORDER BY c.updated_at DESC LIMIT 100
                """, (project_id,))
                reviews = [{
                    "object_id": str(row[0]), "stable_key": row[1], "title": row[2],
                    "evidence_type": row[3], "confidence": row[4],
                    "updated_at": row[5].isoformat(),
                    "coordinates": {
                        "page": row[6], "section": row[7],
                        "character_start": row[8], "character_end": row[9],
                    },
                    "reviewed_statement_hash": row[10],
                    "extraction_manifest_hash": row[11],
                    "source_document": {"title": row[12], "doi": row[13]},
                    "required_assessments": (
                        "citation_fidelity", "context_preserved", "relevance",
                        "confidence", "epistemic_classification",
                    ),
                } for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT c.object_id,c.stable_key,a.title,a.artifact_type,a.status,
                           CASE a.status WHEN 'draft' THEN 'validated'
                             WHEN 'validated' THEN 'ratified'
                             WHEN 'ratified' THEN 'published' END,c.updated_at
                    FROM project_objects po
                    JOIN canonical_objects c ON c.object_id=po.object_id
                    JOIN research_artifacts a ON a.artifact_id=c.object_id
                    WHERE po.project_id=%s AND a.status IN ('draft','validated','ratified')
                    ORDER BY c.updated_at DESC LIMIT 100
                """, (project_id,))
                transitions = [{
                    "object_id": str(row[0]), "stable_key": row[1], "title": row[2],
                    "artifact_type": row[3], "status": row[4], "next_status": row[5],
                    "updated_at": row[6].isoformat(),
                } for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT job_id,status,payload->>'object_type',payload->>'object_id',
                           payload->>'model',attempts,error,created_at,
                           COALESCE(completed_at,started_at,created_at)
                    FROM background_jobs WHERE job_type='index_embedding'
                    ORDER BY created_at DESC LIMIT 100
                """)
                jobs = [{
                    "job_id": str(row[0]), "status": row[1], "object_type": row[2],
                    "object_id": row[3], "model": row[4], "attempts": row[5],
                    "last_error": row[6], "created_at": row[7].isoformat(),
                    "updated_at": row[8].isoformat(),
                } for row in cursor.fetchall()]
        return {
            "project_id": project_id, "pending_reviews": reviews,
            "pending_transitions": transitions, "index_jobs": jobs,
            "counts": {
                "pending_reviews": len(reviews),
                "pending_transitions": len(transitions),
                "index_jobs": len(jobs),
                "failed_jobs": sum(
                    job["status"] in {"failed", "dead_letter"} for job in jobs
                ),
                "dead_letter_jobs": sum(
                    job["status"] == "dead_letter" for job in jobs
                ),
            },
        }

    def get_project_graph(
        self, project_id: str, *, limit: int, relationship_types: tuple[str, ...],
        review_status: str | None, min_confidence: float,
    ) -> dict:
        if not 1 <= limit <= 300:
            raise ValueError("Graph edge limit must be from 1 to 300")
        if not 0 <= min_confidence <= 1:
            raise ValueError("Graph minimum confidence must be from 0 to 1")
        if review_status not in {None, "provisional", "accepted", "rejected"}:
            raise ValueError("Invalid graph review status")
        clauses = ["ps.project_id=%s", "pt.project_id=%s", "COALESCE(ke.confidence,0)>=%s"]
        values = [project_id, project_id, min_confidence]
        if relationship_types:
            clauses.append("ke.relationship_type=ANY(%s)")
            values.append(list(dict.fromkeys(relationship_types)))
        if review_status:
            clauses.append("ke.review_status=%s")
            values.append(review_status)
        values.append(limit)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT ke.edge_id,cs.object_id,cs.stable_key,cs.object_type,
                           COALESCE(ds.title,ars.title,es.statement,cs.stable_key),
                           ct.object_id,ct.stable_key,ct.object_type,
                           COALESCE(dt.title,art.title,et.statement,ct.stable_key),
                           ke.relationship_type,ke.confidence,ke.review_status,
                           ke.provenance_id
                    FROM knowledge_edges ke
                    JOIN knowledge_nodes ns ON ns.node_id=ke.source_node_id
                    JOIN canonical_objects cs ON cs.object_id=ns.object_id
                    JOIN project_objects ps ON ps.object_id=cs.object_id
                    JOIN knowledge_nodes nt ON nt.node_id=ke.target_node_id
                    JOIN canonical_objects ct ON ct.object_id=nt.object_id
                    JOIN project_objects pt ON pt.object_id=ct.object_id
                    LEFT JOIN scientific_documents ds ON ds.document_id=cs.object_id
                    LEFT JOIN research_artifacts ars ON ars.artifact_id=cs.object_id
                    LEFT JOIN evidence_objects es ON es.evidence_id=cs.object_id
                    LEFT JOIN scientific_documents dt ON dt.document_id=ct.object_id
                    LEFT JOIN research_artifacts art ON art.artifact_id=ct.object_id
                    LEFT JOIN evidence_objects et ON et.evidence_id=ct.object_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY ke.created_at DESC,ke.edge_id LIMIT %s
                """, values)
                rows = cursor.fetchall()
                cursor.execute("""
                    SELECT DISTINCT relationship_type FROM knowledge_edges
                    ORDER BY relationship_type
                """)
                available_types = [row[0] for row in cursor.fetchall()]
        nodes = {}
        edges = []
        for row in rows:
            nodes[str(row[1])] = {"object_id": str(row[1]), "stable_key": row[2], "object_type": row[3], "title": row[4]}
            nodes[str(row[5])] = {"object_id": str(row[5]), "stable_key": row[6], "object_type": row[7], "title": row[8]}
            edges.append({
                "edge_id": str(row[0]), "source": str(row[1]), "target": str(row[5]),
                "relationship_type": row[9], "confidence": row[10],
                "review_status": row[11], "provenance_id": str(row[12]),
            })
        return {"project_id": project_id, "nodes": list(nodes.values()), "edges": edges,
                "available_relationship_types": available_types,
                "truncated": len(edges) == limit}
