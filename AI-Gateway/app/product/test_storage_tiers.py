from datetime import date, datetime, timezone

from app.product.storage_tiers import read_storage_tier_status


class _Cursor:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query):
        assert "storage_tier_current" in query

    def fetchall(self):
        return [(
            "postgresql", "archived_local", "20260720T075150Z", "a" * 64,
            "hostinger-offsite:20260720T075150Z/postgresql", 
            datetime(2026, 7, 20, 8, tzinfo=timezone.utc),
            date(2026, 8, 19),
        )]


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return _Cursor()


def test_storage_tier_projection_is_read_only_and_never_authorizes_eviction(monkeypatch):
    monkeypatch.setattr("app.product.storage_tiers.psycopg.connect", lambda _url: _Connection())

    result = read_storage_tier_status("postgresql://example")

    assert result["status"] == "attested"
    assert result["counts"] == {"hot": 0, "archived_local": 1, "restore_required": 0}
    assert result["eviction_authorized"] is False
    assert result["items"][0]["content_sha256"] == "a" * 64
    assert result["items"][0]["retention_until"] == "2026-08-19"
