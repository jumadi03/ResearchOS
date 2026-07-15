import pytest

from app.main import create_app
from app import settings


def test_application_factory_creates_isolated_state():
    first = create_app()
    second = create_app()

    assert first is not second
    assert first.state.metrics_registry is not second.state.metrics_registry
    assert first.state.knowledge_service is not second.state.knowledge_service
    assert first.state.architecture_service is not second.state.architecture_service


def test_runtime_configuration_rejects_partial_minio(monkeypatch):
    monkeypatch.setattr(settings, "MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr(settings, "MINIO_ACCESS_KEY", None)
    monkeypatch.setattr(settings, "MINIO_SECRET_KEY", None)

    with pytest.raises(RuntimeError, match="must be configured together"):
        settings.validate_runtime_configuration()


def test_runtime_configuration_rejects_invalid_limits(monkeypatch):
    monkeypatch.setattr(settings, "KNOWLEDGE_PROVIDER_MAX_ATTEMPTS", 0)

    with pytest.raises(RuntimeError, match="timeout and attempts"):
        settings.validate_runtime_configuration()
