from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "deploy" / "compose.yaml").read_text(encoding="utf-8")
SCRIPT = (ROOT / "Scripts" / "archive_database_locally.ps1").read_text(
    encoding="utf-8"
)
INACTIVE = (ROOT / "Scripts" / "archive_inactive_data.ps1").read_text(
    encoding="utf-8"
)
RESTORE = (ROOT / "Scripts" / "restore_inactive_data.ps1").read_text(
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


def test_inactive_archive_is_immutable_content_addressed_and_bounded() -> None:
    assert "local_inactive_archive_items" in SCRIPT
    assert "local_inactive_archive_restores" in SCRIPT
    assert "BEFORE UPDATE OR DELETE" in SCRIPT
    assert "content_sha256" in INACTIVE
    assert "Get-FileHash" in INACTIVE
    assert "100 MiB safety limit" in INACTIVE
    assert "active_source = $false" in INACTIVE


def test_legacy_github_refs_are_bundled_without_becoming_active() -> None:
    assert "refs/remotes/legacy-github/" in INACTIVE
    assert "git bundle create" in INACTIVE
    assert "git bundle verify" in INACTIVE
    assert "legacy_github_bundle" in INACTIVE


def test_inactive_restore_never_overwrites_and_verifies_checksum() -> None:
    assert "destination already exists" in RESTORE
    assert "FromBase64String" in RESTORE
    assert "Restored inactive archive checksum mismatch" in RESTORE
    assert '"archive_remains_inactive":true' in RESTORE
