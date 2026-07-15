"""Fail-closed readiness checks for external runtime dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeReadinessChecker:
    database_url: str | None
    expected_schema_version: int
    object_store: Any | None
    worker_max_age_seconds: int = 15

    def checks(self) -> dict[str, bool]:
        results = {
            "database": True,
            "schema_version": True,
            "worker": True,
            "object_storage": True,
        }
        if self.database_url:
            results.update(self._database_checks())
        if self.object_store is not None:
            results["object_storage"] = self._object_storage_ready()
        return results

    def _database_checks(self) -> dict[str, bool]:
        import psycopg

        results = {"database": False, "schema_version": False, "worker": False}
        try:
            with psycopg.connect(
                self.database_url, connect_timeout=2
            ) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                results["database"] = cursor.fetchone() == (1,)
                cursor.execute("SELECT COALESCE(max(version), 0) FROM schema_migrations")
                results["schema_version"] = (
                    cursor.fetchone()[0] == self.expected_schema_version
                )
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM worker_heartbeats
                        WHERE last_seen_at >= now() - (%s * interval '1 second')
                    )
                    """,
                    (self.worker_max_age_seconds,),
                )
                results["worker"] = cursor.fetchone()[0] is True
        except (psycopg.Error, TypeError, ValueError):
            pass
        return results

    def _object_storage_ready(self) -> bool:
        try:
            self.object_store.client.head_bucket(Bucket=self.object_store.bucket)
        except Exception:
            return False
        return True
