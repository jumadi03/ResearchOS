from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.architecture.pipeline_service import ArchitecturePipelineService
from app.architecture.authentication import BearerTokenAuthenticator
from app.router.architecture import router
from app.observability import AuditTrail, CorrelationMiddleware, MetricsRegistry


def _client(tmp_path: Path, *, authenticated: bool = True) -> tuple[TestClient, Path]:
    project = tmp_path / "project"
    package = project / "sample"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text("class Service: pass\n", encoding="utf-8")
    output = tmp_path / "output"
    app = FastAPI()
    app.state.architecture_service = ArchitecturePipelineService(project, output)
    app.state.architecture_authenticator = BearerTokenAuthenticator(
        {
            "test-token": {
                "actor_id": "architect@example",
                "roles": [
                    "scanner", "law_admin", "reviewer", "approver",
                    "publisher", "auditor",
                ],
            },
            "reviewer-token": {
                "actor_id": "reviewer@example",
                "roles": ["reviewer"],
            },
        }
    )
    app.state.metrics_registry = MetricsRegistry()
    app.state.audit_trail = AuditTrail(output / "audit" / "events.jsonl")
    app.add_middleware(CorrelationMiddleware, metrics=app.state.metrics_registry)
    app.include_router(router)
    headers = {"Authorization": "Bearer test-token"} if authenticated else None
    return TestClient(app, headers=headers), output


def test_complete_api_workflow_persists_published_arc(tmp_path: Path) -> None:
    client, output = _client(tmp_path)

    scan = client.post(
        "/architecture/runs",
        json={"project_name": "sample", "source_revision": "revision-1"},
    )
    assert scan.status_code == 201
    run_id = scan.json()["run_id"]
    assert scan.json()["graph"]["nodes"] >= 3

    laws = client.put(
        f"/architecture/runs/{run_id}/laws",
        json={"version": "1.0.0", "laws": []},
    )
    assert laws.status_code == 200
    assert laws.json()["law_bundle"]["laws"] == 0

    compliance = client.post(
        f"/architecture/runs/{run_id}/compliance",
        json={"as_of": "2026-07-15"},
    )
    assert compliance.status_code == 200
    assert compliance.json()["compliance"]["status"] == "PASS"

    review = client.post(
        f"/architecture/runs/{run_id}/review",
        json={"opened_at": "2026-07-15T08:00:00Z"},
    )
    assert review.status_code == 201
    assert review.json()["review"]["status"] == "OPEN"

    finalized = client.post(
        f"/architecture/runs/{run_id}/review/finalize",
        json={
            "occurred_at": "2026-07-15T09:00:00Z",
            "as_of": "2026-07-15",
        },
    )
    assert finalized.status_code == 200
    assert finalized.json()["review"]["status"] == "APPROVED"

    arc = client.post(
        f"/architecture/runs/{run_id}/arc",
        json={
            "generated_at": "2026-07-15T10:00:00Z",
            "publish": True,
        },
    )
    assert arc.status_code == 201
    assert arc.json()["arc"]["verified"] is True
    assert arc.headers["x-correlation-id"]
    assert "report.html" in arc.json()["arc"]["artifacts"]
    assert "report.pdf" in arc.json()["arc"]["artifacts"]

    run_directory = next((output / "runs").iterdir())
    assert (run_directory / "architecture-graph.json").exists()
    assert (run_directory / "laws.json").exists()
    assert (run_directory / "compliance-report.json").exists()
    assert (run_directory / "review.json").exists()
    assert next((run_directory / "arc").rglob("report.pdf")).read_bytes().startswith(
        b"%PDF-"
    )
    service = client.app.state.architecture_service
    assert service.get(run_id).review.opened_by == "architect@example"
    assert service.get(run_id).arc_package.manifest.generated_by == (
        "architect@example"
    )
    audit_events = [
        __import__("json").loads(line)
        for line in (output / "audit" / "events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    publication_outcomes = [
        item["outcome"]
        for item in audit_events
        if item["event_type"] == "arc_publication"
    ]
    assert publication_outcomes == ["attempted", "succeeded"]

    restarted = ArchitecturePipelineService(service.project_root, output)
    restored = restarted.get(run_id)
    assert restored.law_bundle is not None
    assert restored.compliance_report is not None
    assert restored.review is not None
    assert restored.review.status.value == "APPROVED"
    assert restored.arc_package is not None
    assert restored.arc_package.verify() is True

    # A crash after the immutable ARC directory commit but before updating the
    # location pointer is recoverable by verified directory discovery.
    (run_directory / "arc-location.json").unlink()
    recovered_without_pointer = ArchitecturePipelineService(
        service.project_root, output
    ).get(run_id)
    assert recovered_without_pointer.arc_package is not None
    assert recovered_without_pointer.arc_package.verify() is True

    repeated = client.post(
        f"/architecture/runs/{run_id}/arc",
        json={
            "generated_at": "2026-07-15T10:00:00Z",
            "publish": True,
        },
    )
    assert repeated.status_code == 409
    assert "immutable" in repeated.json()["detail"]
    final_audit = [
        __import__("json").loads(line)
        for line in (output / "audit" / "events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert [
        item["outcome"]
        for item in final_audit
        if item["event_type"] == "arc_publication"
    ][-2:] == ["attempted", "failed"]


def test_api_enforces_stage_order_and_maps_unknown_run(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    scan = client.post(
        "/architecture/runs",
        json={"project_name": "sample", "source_revision": "revision-1"},
    )
    run_id = scan.json()["run_id"]

    compliance = client.post(
        f"/architecture/runs/{run_id}/compliance",
        json={"as_of": "2026-07-15"},
    )
    assert compliance.status_code == 422
    assert "law bundle" in compliance.json()["detail"]

    missing = client.get("/architecture/runs/run:missing")
    assert missing.status_code == 404


def test_api_does_not_accept_client_filesystem_root(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    response = client.post(
        "/architecture/runs",
        json={
            "project_name": "sample",
            "source_revision": "revision-1",
            "root": "C:/sensitive",
        },
    )
    assert response.status_code == 422


def test_api_fails_closed_without_valid_bearer_token(tmp_path: Path) -> None:
    client, output = _client(tmp_path, authenticated=False)
    missing = client.post(
        "/architecture/runs",
        json={"project_name": "sample", "source_revision": "revision-1"},
    )
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.headers["x-correlation-id"]

    invalid = client.post(
        "/architecture/runs",
        headers={"Authorization": "Bearer invalid"},
        json={"project_name": "sample", "source_revision": "revision-1"},
    )
    assert invalid.status_code == 401
    events = [
        __import__("json").loads(line)
        for line in (output / "audit" / "events.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert [item["event_type"] for item in events] == [
        "architecture_authentication",
        "architecture_authentication",
    ]
    assert all(item["outcome"] == "denied" for item in events)


def test_valid_principal_without_required_role_gets_forbidden(tmp_path: Path) -> None:
    client, _ = _client(tmp_path, authenticated=False)
    response = client.post(
        "/architecture/runs",
        headers={"Authorization": "Bearer reviewer-token"},
        json={"project_name": "sample", "source_revision": "revision-1"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Role required: scanner"


def test_principal_configuration_rejects_legacy_or_unknown_roles() -> None:
    import pytest

    with pytest.raises(ValueError, match="must be an object"):
        BearerTokenAuthenticator({"token": "actor@example"})
    with pytest.raises(ValueError):
        BearerTokenAuthenticator(
            {"token": {"actor_id": "actor@example", "roles": ["superuser"]}}
        )


def test_openapi_declares_http_bearer_security(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    schema = client.app.openapi()
    schemes = schema["components"]["securitySchemes"]
    assert schemes["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/architecture/runs"]["post"]["security"] == [
        {"HTTPBearer": []}
    ]


def test_rehydration_discards_tampered_review_but_keeps_valid_stages(
    tmp_path: Path,
) -> None:
    client, output = _client(tmp_path)
    run_id = client.post(
        "/architecture/runs",
        json={"project_name": "sample", "source_revision": "revision-1"},
    ).json()["run_id"]
    client.put(
        f"/architecture/runs/{run_id}/laws",
        json={"version": "1.0.0", "laws": []},
    )
    client.post(
        f"/architecture/runs/{run_id}/compliance",
        json={"as_of": "2026-07-15"},
    )
    client.post(
        f"/architecture/runs/{run_id}/review",
        json={"opened_at": "2026-07-15T08:00:00Z"},
    )

    run_directory = next((output / "runs").iterdir())
    review_path = run_directory / "review.json"
    review_path.write_text(
        review_path.read_text(encoding="utf-8").replace(
            '"status": "OPEN"', '"status": "APPROVED"'
        ),
        encoding="utf-8",
    )
    service = client.app.state.architecture_service
    restarted = ArchitecturePipelineService(service.project_root, output)
    restored = restarted.get(run_id)
    assert restored.compliance_report is not None
    assert restored.review is None
    assert any(
        item.startswith("review:")
        for item in restarted.rehydration_errors[run_id]
    )
