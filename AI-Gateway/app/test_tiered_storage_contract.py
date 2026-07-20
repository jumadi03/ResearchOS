from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/postgres/init/042_tiered_storage_catalog.sql"
SYNC = ROOT / "Scripts/register_local_backup_attestation.ps1"


def test_tier_catalog_is_append_only_and_fail_closed():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "storage_tier_attestations_immutable" in sql
    assert "reject_ledger_mutation()" in sql
    assert "'hot','archived_local','restore_required'" in sql
    assert "storage_tier_current" in sql
    assert "no eviction is authorized" in sql


def test_local_archive_attestation_requires_checksum_verification():
    script = SYNC.read_text(encoding="utf-8")

    assert "Get-FileHash" in script
    assert "Local checksum mismatch" in script
    assert "'archived_local'" in script
    assert "'hot'" in script
    assert "ON CONFLICT" in script
    assert "restore_required" not in script
