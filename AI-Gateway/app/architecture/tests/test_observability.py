import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.architecture.authentication import BearerTokenAuthenticator
from app.architecture.pipeline_service import ArchitecturePipelineService
from app.logger import JSONFormatter, correlation_id_context
from app.observability import (
    AuditTrail,
    CorrelationMiddleware,
    MetricsRegistry,
    router,
)


def _operations_client(tmp_path: Path, *, configured: bool = True) -> TestClient:
    project = tmp_path / "project"
    project.mkdir(parents=True)
    output = tmp_path / "output"
    app = FastAPI()
    app.state.architecture_service = ArchitecturePipelineService(project, output)
    config = {
        "auditor-token": {
            "actor_id": "auditor@example",
            "roles": ["auditor"],
        }
    } if configured else {}
    app.state.architecture_authenticator = BearerTokenAuthenticator(config)
    app.state.metrics_registry = MetricsRegistry()
    app.state.audit_trail = AuditTrail(output / "audit" / "events.jsonl")
    app.add_middleware(CorrelationMiddleware, metrics=app.state.metrics_registry)
    app.include_router(router)
    return TestClient(app)


def test_health_and_correlation_id_propagation(tmp_path: Path) -> None:
    client = _operations_client(tmp_path)
    valid = client.get("/health", headers={"X-Correlation-ID": "request-123"})
    assert valid.status_code == 200
    assert valid.headers["x-correlation-id"] == "request-123"

    invalid = client.get("/health", headers={"X-Correlation-ID": "bad value"})
    assert invalid.status_code == 200
    assert invalid.headers["x-correlation-id"] != "bad value"
    assert len(invalid.headers["x-correlation-id"]) == 32


def test_readiness_fails_closed_without_authentication_config(tmp_path: Path) -> None:
    ready = _operations_client(tmp_path / "ready").get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    unavailable = _operations_client(
        tmp_path / "not-ready", configured=False
    ).get("/ready")
    assert unavailable.status_code == 503
    assert unavailable.json()["checks"]["authentication_configured"] is False


def test_metrics_require_auditor_and_expose_request_measurements(
    tmp_path: Path,
) -> None:
    client = _operations_client(tmp_path)
    client.get("/health")
    denied = client.get("/metrics")
    assert denied.status_code == 401

    metrics = client.get(
        "/metrics", headers={"Authorization": "Bearer auditor-token"}
    )
    assert metrics.status_code == 200
    assert "researchos_http_requests_total" in metrics.text
    assert "researchos_http_request_duration_seconds_count" in metrics.text


def test_audit_trail_and_json_formatter_include_correlation(tmp_path: Path) -> None:
    trail = AuditTrail(tmp_path / "audit" / "events.jsonl")
    token = correlation_id_context.set("correlation-1")
    try:
        event = trail.record(
            "security_test",
            actor="auditor@example",
            outcome="succeeded",
        )
        record = logging.LogRecord(
            "ResearchOS", logging.INFO, "", 0, "event", (), None
        )
        record.event = "structured_test"
        record.fields = {"run_id": "run:1"}
        structured = json.loads(JSONFormatter().format(record))
    finally:
        correlation_id_context.reset(token)

    persisted = json.loads(
        (tmp_path / "audit" / "events.jsonl").read_text(encoding="utf-8")
    )
    assert event == persisted
    assert persisted["correlation_id"] == "correlation-1"
    assert structured["correlation_id"] == "correlation-1"
    assert structured["run_id"] == "run:1"
