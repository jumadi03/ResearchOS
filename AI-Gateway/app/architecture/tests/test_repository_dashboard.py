from dataclasses import replace
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.architecture.repository import (
    RepositoryDashboardProjector,
    RepositoryDashboardService,
    RepositoryDashboardSnapshot,
    RepositoryDashboardArtifactStore,
    RepositoryHealthCategory,
    RepositoryHealthEngine,
    RepositoryHealthOutcome,
)
from app.architecture.tests.test_repository_health import _inputs
from app.knowledge.authentication import KnowledgeAuthenticator
from app.router.administration import router as administration_router


def _snapshot(tmp_path: Path):
    registry, verification, graph = _inputs(tmp_path)
    health = RepositoryHealthEngine().assess(
        registry, verification, graph, as_of="2026-07-17",
    )
    return (
        RepositoryDashboardProjector().project(
            registry, verification, graph, health,
        ),
        registry,
        verification,
        graph,
        health,
    )


def test_dashboard_projects_provenance_bearing_inventory_and_health(
    tmp_path: Path,
) -> None:
    snapshot, registry, verification, graph, health = _snapshot(tmp_path)

    assert snapshot.verify()
    assert snapshot.status == "INCOMPLETE"
    assert snapshot.is_compliance_decision is False
    assert snapshot.registry_id == registry.registry_id
    assert snapshot.registry_hash == registry.content_hash
    assert snapshot.verification_report_id == verification.report_id
    assert snapshot.verification_report_hash == verification.content_hash
    assert snapshot.graph_id == graph.graph_id
    assert snapshot.graph_hash == graph.content_hash
    assert snapshot.health_report_id == health.report_id
    assert snapshot.health_report_hash == health.content_hash
    assert len(snapshot.files) == len(registry.entries)
    assert {item.path for item in snapshot.files} == {
        item.current_path for item in registry.entries
    }
    assert dict(snapshot.inventory_counts)["code"] == 4
    assert dict(snapshot.governance_counts)["assigned"] == 4
    unavailable = {
        item.category for item in snapshot.health
        if item.outcome is RepositoryHealthOutcome.NOT_EVALUATED
    }
    assert unavailable == {
        RepositoryHealthCategory.DEAD_FILE_ANALYSIS,
        RepositoryHealthCategory.STALENESS,
        RepositoryHealthCategory.EXECUTION_COVERAGE,
        RepositoryHealthCategory.DOCUMENTATION_COVERAGE,
    }


def test_dashboard_is_deterministic_round_trippable_and_tamper_evident(
    tmp_path: Path,
) -> None:
    first, registry, verification, graph, health = _snapshot(tmp_path)
    second = RepositoryDashboardProjector().project(
        registry, verification, graph, health,
    )

    assert first == second
    assert RepositoryDashboardSnapshot.from_json(first.to_json()) == first
    assert not replace(first, registry_hash="0" * 64).verify()
    payload = json.loads(first.to_json())
    payload["status"] = "OBSERVED"
    with pytest.raises(ValueError, match="invalid"):
        RepositoryDashboardSnapshot.from_json(json.dumps(payload))
    payload = json.loads(first.to_json())
    payload["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="future"):
        RepositoryDashboardSnapshot.from_json(json.dumps(payload))


def test_dashboard_rejects_mixed_revision_and_provenance_bypass(
    tmp_path: Path,
) -> None:
    _, registry, verification, graph, health = _snapshot(tmp_path)
    projector = RepositoryDashboardProjector()

    stale_health = replace(
        health, source_revision="r2", report_id="", content_hash="",
    ).finalized()
    with pytest.raises(ValueError, match="revision mismatch"):
        projector.project(registry, verification, graph, stale_health)

    wrong_registry = replace(
        registry, registry_id="file-registry:ResearchOS:wrong",
    )
    with pytest.raises(ValueError, match="valid file registry"):
        projector.project(wrong_registry, verification, graph, health)

    stale_graph = replace(
        graph, source_revision="r2", graph_id="", content_hash="",
    ).finalized()
    with pytest.raises(ValueError, match="revision mismatch"):
        projector.project(registry, verification, stale_graph, health)


def test_dashboard_service_cannot_bypass_projection_validation(
    tmp_path: Path,
) -> None:
    _, registry, verification, graph, health = _snapshot(tmp_path)

    class Source:
        def __init__(self, artifacts):
            self.artifacts = artifacts

        def load(self):
            return self.artifacts

    service = RepositoryDashboardService(
        Source((registry, verification, graph, health))
    )
    assert service.snapshot().verify()

    invalid = replace(health, content_hash="0" * 64)
    bypass = RepositoryDashboardService(
        Source((registry, verification, graph, invalid))
    )
    with pytest.raises(ValueError, match="valid health report"):
        bypass.snapshot()


def test_dashboard_store_publishes_and_rehydrates_complete_immutable_bundle(
    tmp_path: Path,
) -> None:
    expected, registry, verification, graph, health = _snapshot(
        tmp_path / "source"
    )
    root = tmp_path / "published"
    store = RepositoryDashboardArtifactStore(
        root, expected_revision="r1",
    )

    assert store.publish(registry, verification, graph, health) == expected
    assert store.publish(registry, verification, graph, health) == expected
    restarted = RepositoryDashboardArtifactStore(
        root, expected_revision="r1",
    )
    assert restarted.snapshot() == expected
    assert RepositoryDashboardService(restarted).snapshot() == expected
    release = root / "releases" / expected.content_hash
    assert sorted(path.name for path in release.iterdir()) == [
        "architecture-graph.json",
        "dashboard-snapshot.json",
        "file-registry.json",
        "health-report.json",
        "verification-report.json",
    ]


def test_dashboard_store_rejects_tamper_stale_pointer_and_partial_release(
    tmp_path: Path,
) -> None:
    expected, registry, verification, graph, health = _snapshot(
        tmp_path / "source"
    )
    root = tmp_path / "published"
    store = RepositoryDashboardArtifactStore(root)
    store.publish(registry, verification, graph, health)
    release = root / "releases" / expected.content_hash

    (release / "health-report.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete or invalid"):
        store.snapshot()

    root2 = tmp_path / "pointer"
    valid = RepositoryDashboardArtifactStore(root2)
    valid.publish(registry, verification, graph, health)
    pointer = json.loads((root2 / "active.json").read_text(encoding="utf-8"))
    pointer["source_revision"] = "r2"
    (root2 / "active.json").write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(ValueError, match="pointer is invalid"):
        valid.snapshot()

    stale = RepositoryDashboardArtifactStore(
        root2, expected_revision="r2",
    )
    valid.publish(registry, verification, graph, health)
    with pytest.raises(ValueError, match="revision is stale"):
        stale.snapshot()

    abandoned = root2 / "releases" / ".tmp-dashboard-abandoned"
    abandoned.mkdir()
    recovered = RepositoryDashboardArtifactStore(root2)
    assert abandoned in recovered.recovered_temporary_entries
    assert not abandoned.exists()


def _admin_client(service, role: str = "admin") -> TestClient:
    app = FastAPI()
    app.state.knowledge_authenticator = KnowledgeAuthenticator({
        "token": {"actor_id": role, "roles": [role]},
    })
    app.state.workspace_sessions = None
    app.state.repository_dashboard_service = service
    app.include_router(administration_router)
    return TestClient(app)


def test_dashboard_api_is_admin_only_read_only_and_fail_closed(
    tmp_path: Path,
) -> None:
    expected, registry, verification, graph, health = _snapshot(
        tmp_path / "source"
    )

    class Source:
        def load(self):
            return registry, verification, graph, health

    service = RepositoryDashboardService(Source())
    response = _admin_client(service).get(
        "/admin/repository-dashboard",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 200
    assert response.json()["snapshot_id"] == expected.snapshot_id
    assert response.json()["is_compliance_decision"] is False

    denied = _admin_client(service, "auditor").get(
        "/admin/repository-dashboard",
        headers={"Authorization": "Bearer token"},
    )
    assert denied.status_code == 403

    unauthenticated = _admin_client(service).get(
        "/admin/repository-dashboard",
    )
    assert unauthenticated.status_code == 401

    class Missing:
        def load(self):
            raise ValueError("active pointer is unavailable")

    unavailable = _admin_client(
        RepositoryDashboardService(Missing())
    ).get(
        "/admin/repository-dashboard",
        headers={"Authorization": "Bearer token"},
    )
    assert unavailable.status_code == 503
    assert "unavailable" in unavailable.json()["detail"]


def test_dashboard_ui_is_bilingual_provenance_bearing_and_fail_closed() -> None:
    static = Path(__file__).resolve().parents[2] / "product" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "admin.js").read_text(encoding="utf-8")
    catalog = (static / "i18n.js").read_text(encoding="utf-8")
    styles = (static / "admin.css").read_text(encoding="utf-8")

    assert 'id="repositoryDashboard"' in html
    assert 'id="repositoryDashboardStatus"' in html
    assert "api('/admin/repository-dashboard')" in script
    assert "snapshot.inventory_counts" in script
    assert "snapshot.health" in script
    assert "snapshot.snapshot_id" in script
    assert "snapshot.registry_id" in script
    assert "snapshot.verification_report_id" in script
    assert "snapshot.graph_id" in script
    assert "snapshot.health_report_id" in script
    assert "No missing or invalid snapshot is interpreted as passing." in script
    assert '"Repository Dashboard":"Dasbor Repositori"' in catalog
    assert '"Not evaluated":"Belum dievaluasi"' in catalog
    assert (
        '"No tracked generated or temporary files were detected.":'
        '"Tidak ditemukan berkas yang dihasilkan atau sementara dalam pelacakan."'
    ) in catalog
    assert ".repository-health-item.repository-not_evaluated" in styles

    root = Path(__file__).resolve().parents[4]
    compose = (root / "deploy" / "compose.yaml").read_text(encoding="utf-8")
    example = (root / "deploy" / "stack.env.example").read_text(encoding="utf-8")
    assert "REPOSITORY_DASHBOARD_ROOT: /data/architecture/repository-dashboard" in compose
    assert "architecture_data:/data/architecture" in compose
    assert "REPOSITORY_DASHBOARD_EXPECTED_REVISION=" in example


def test_dashboard_has_no_runtime_storage_compliance_or_filesystem_dependency() -> None:
    capability = Path(__file__).parents[1] / "repository"
    source = "\n".join(
        (capability / name).read_text(encoding="utf-8")
        for name in (
            "dashboard_models.py", "dashboard_projector.py",
            "dashboard_service.py",
        )
    )
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3", "ComplianceEngine", "ArchitectureViolation",
        "from pathlib import Path", "open(", "read_text(", "write_text(",
    )
    assert not any(item in source for item in forbidden)
