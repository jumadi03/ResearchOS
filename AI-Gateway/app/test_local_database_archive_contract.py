from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "deploy" / "compose.yaml").read_text(encoding="utf-8")
SCRIPT = (ROOT / "Scripts" / "archive_database_locally.ps1").read_text(
    encoding="utf-8"
)


def test_local_archive_database_is_separate_and_persistent() -> None:
    assert "archive-postgres:" in COMPOSE
    assert 'profiles: ["local-archive"]' in COMPOSE
    assert 'ports: ["127.0.0.1:5433:5432"]' in COMPOSE
    assert "postgres_archive_data:/var/lib/postgresql/data" in COMPOSE
    assert "postgres_archive_data:" in COMPOSE


def test_local_archive_requires_verified_postgresql_dump() -> None:
    assert "exactly one PostgreSQL component" in SCRIPT
    assert "Get-FileHash" in SCRIPT
    assert "PostgreSQL dump checksum mismatch" in SCRIPT
    assert "pg_restore" in SCRIPT
    assert "schema_migrations" in SCRIPT
    assert "canonical_objects" in SCRIPT
    assert "read_back_verified" in SCRIPT


def test_local_archive_preserves_generations_and_fails_closed() -> None:
    assert "researchos_archive_$(" in SCRIPT
    assert "local_archive_generations" in SCRIPT
    assert "reject_local_archive_mutation" in SCRIPT
    assert "AS $function$" in SCRIPT
    assert "AS `$function`$" not in SCRIPT
    assert "BEFORE UPDATE OR DELETE" in SCRIPT
    assert "Existing archive catalog hash conflicts" in SCRIPT
    assert "dropdb" in SCRIPT
    assert "local-database-archive=passed" in SCRIPT
