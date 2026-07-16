"""Regression tests for canonical PostgreSQL artifact metadata comparison."""

from hashlib import sha256

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.repositories.postgres_artifacts import artifact_integrity_matches


def test_artifact_integrity_accepts_json_normalized_nested_tuples() -> None:
    metadata = {
        "graph_ids": ("graph-1",),
        "proposals": (
            {
                "theory_id": "theory-1",
                "evidence": ({"edge_id": "edge-1", "confidence": 0.7},),
            },
        ),
    }
    stored_metadata = {
        "graph_ids": ["graph-1"],
        "proposals": [
            {
                "theory_id": "theory-1",
                "evidence": [{"edge_id": "edge-1", "confidence": 0.7}],
            },
        ],
    }
    metadata_hash = sha256(canonical_json(metadata).encode()).hexdigest()

    assert artifact_integrity_matches(
        ("project-1", "theory_bundle", "Theory", stored_metadata, metadata_hash),
        project_id="project-1", artifact_type="theory_bundle", title="Theory",
        metadata=metadata, metadata_hash=metadata_hash,
    )


def test_artifact_integrity_still_rejects_changed_metadata() -> None:
    metadata = {"graph_ids": ("graph-1",)}
    metadata_hash = sha256(canonical_json(metadata).encode()).hexdigest()

    assert not artifact_integrity_matches(
        ("project-1", "theory_bundle", "Theory", {"graph_ids": ["graph-2"]}, metadata_hash),
        project_id="project-1", artifact_type="theory_bundle", title="Theory",
        metadata=metadata, metadata_hash=metadata_hash,
    )
