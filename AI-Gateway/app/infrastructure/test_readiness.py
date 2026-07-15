import sys
from types import SimpleNamespace

from app.infrastructure.readiness import RuntimeReadinessChecker


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, *_args):
        return None

    def fetchone(self):
        return next(self.rows)


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return FakeCursor(self.rows)


def test_runtime_readiness_checks_database_schema_worker_and_storage(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(
            connect=lambda *_args, **_kwargs: FakeConnection([(1,), (16,), (True,)]),
            Error=RuntimeError,
        ),
    )
    storage = SimpleNamespace(
        bucket="documents",
        client=SimpleNamespace(head_bucket=lambda **_kwargs: None),
    )

    checks = RuntimeReadinessChecker(
        "postgresql://database", 16, storage
    ).checks()

    assert checks == {
        "database": True,
        "schema_version": True,
        "worker": True,
        "object_storage": True,
    }


def test_runtime_readiness_fails_closed_on_dependency_errors(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=unavailable, Error=RuntimeError),
    )
    storage = SimpleNamespace(
        bucket="documents",
        client=SimpleNamespace(head_bucket=unavailable),
    )

    checks = RuntimeReadinessChecker(
        "postgresql://database", 16, storage
    ).checks()

    assert checks == {
        "database": False,
        "schema_version": False,
        "worker": False,
        "object_storage": False,
    }
