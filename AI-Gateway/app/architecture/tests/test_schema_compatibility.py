from dataclasses import replace
from hashlib import sha256
import json

import pytest

from app.architecture.governance import ReviewEngine
from app.architecture.models import (
    ARCManifest,
    ArchitectureGraph,
    ArchitectureLawBundle,
    ArchitectureValidationResult,
    ValidationReport,
    ValidationStatus,
)
from app.architecture.schema import (
    COMPLIANCE_MIGRATIONS,
    GRAPH_SCHEMA,
    SchemaVersion,
    SchemaVersionError,
)


def _report() -> ValidationReport:
    return ValidationReport(
        (
            ArchitectureValidationResult(
                "DEPENDENCY", "graph:sample:abc", status=ValidationStatus.PASS
            ),
        ),
        {"graph_id": "graph:sample:abc", "graph_hash": "abc"},
    )


def test_schema_version_parser_and_future_rejection() -> None:
    assert str(SchemaVersion.parse("1.2")) == "1.2"
    with pytest.raises(SchemaVersionError, match="Invalid"):
        SchemaVersion.parse("1")
    with pytest.raises(SchemaVersionError, match="future"):
        GRAPH_SCHEMA.require_readable("2.0")


def test_graph_and_law_bundle_reject_unknown_schema_before_content_use() -> None:
    graph_payload = json.loads(ArchitectureGraph("", "sample").finalized().to_json())
    graph_payload["schema_version"] = "2.0"
    with pytest.raises(SchemaVersionError, match="future"):
        ArchitectureGraph.from_json(json.dumps(graph_payload))

    bundle_payload = json.loads(ArchitectureLawBundle("", "1.0").finalized().to_json())
    bundle_payload["schema_version"] = "7.0"
    with pytest.raises(SchemaVersionError, match="future"):
        ArchitectureLawBundle.from_json(json.dumps(bundle_payload))


def test_legacy_compliance_loads_without_silent_upgrade() -> None:
    payload = json.loads(_report().to_json())
    payload.pop("schema_version")
    legacy = ValidationReport.from_json(json.dumps(payload))
    assert legacy.schema_version == "0.9"
    upgraded = legacy.upgraded()
    assert upgraded.schema_version == "1.0"
    assert '"schema_version": "1.0"' in upgraded.to_json()


def test_legacy_review_hash_is_preserved_until_explicit_upgrade() -> None:
    report = _report()
    review = ReviewEngine().open(
        report,
        reviewer="reviewer",
        opened_at="2026-07-15T08:00:00Z",
    )
    payload = json.loads(review.to_json())
    payload.pop("schema_version")
    canonical = dict(payload)
    canonical.pop("content_hash")
    payload["content_hash"] = sha256(
        json.dumps(
            canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    ).hexdigest()

    legacy = review.from_json(json.dumps(payload))
    assert legacy.schema_version == "0.9"
    assert legacy.calculate_content_hash() == payload["content_hash"]
    upgraded = legacy.upgraded()
    assert upgraded.schema_version == "1.0"
    assert upgraded.calculate_content_hash() != legacy.calculate_content_hash()


def test_arc_1_0_verifies_and_upgrades_to_new_identity() -> None:
    legacy = ARCManifest(
        arc_id="",
        project_name="sample",
        generated_at="2026-07-15T10:00:00Z",
        graph_id="graph:sample:abc",
        graph_hash="abc",
        source_revision="revision-1",
        law_bundle_id="law-bundle:1.0:abc",
        law_bundle_hash="law-hash",
        compliance_hash="compliance-hash",
        review_id="review:abc",
        review_hash="review-hash",
        schema_version="1.0",
    ).finalized()
    restored = ARCManifest.from_json(legacy.to_json())
    assert restored.schema_version == "1.0"
    assert restored.arc_id == legacy.arc_id

    upgraded = restored.upgraded(generated_by="publisher@example")
    assert upgraded.schema_version == "1.1"
    assert upgraded.generated_by == "publisher@example"
    assert upgraded.arc_id != legacy.arc_id


def test_migration_registry_is_explicit_and_non_mutating() -> None:
    source = {"status": "PASS"}
    migrated = COMPLIANCE_MIGRATIONS.migrate(source, source_version="0.9")
    assert source == {"status": "PASS"}
    assert migrated["schema_version"] == "1.0"
