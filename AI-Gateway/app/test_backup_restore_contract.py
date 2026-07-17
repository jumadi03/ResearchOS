from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/postgres/init/029_backup_restore_contracts.sql"
BACKUP = ROOT / "deploy/backup/backup.sh"
ADMIN = ROOT / "AI-Gateway/app/product/static/admin.js"


def test_restore_evidence_is_immutable_isolated_and_manifest_bound():
    contract = MIGRATION.read_text(encoding="utf-8")

    assert "target_kind = 'isolated'" in contract
    assert "backup_restore_verifications_immutable" in contract
    assert "reject_ledger_mutation()" in contract
    assert "FOREIGN KEY (backup_id, backup_set_hash)" in contract
    assert "REFERENCES backup_runs(backup_id, backup_set_hash)" in contract
    assert "jsonb_array_length(checks) > 0" in contract


def test_backup_producer_publishes_a_hash_bound_portable_manifest():
    script = BACKUP.read_text(encoding="utf-8")

    assert b"\r\n" not in BACKUP.read_bytes()
    assert 'manifest="/backups/backup-set-${stamp}.json"' in script
    assert '"schema_version": "1.0"' in script
    assert r'\"name\":\"postgresql\"' in script
    assert r'\"name\":\"minio\"' in script
    assert r'\"name\":\"knowledge\"' in script
    assert "backup_set_hash='$manifest_hash'" in script
    assert "integrity_verified=true" in script


def test_administration_ui_uses_restore_verified_recovery_semantics():
    script = ADMIN.read_text(encoding="utf-8")

    assert "ready=r.recovery_ready===true" in script
    assert "Portable backup-set integrity verified" in script
    assert "Isolated restore verified" in script
    assert "${r.ready?" not in script


def test_schema_version_29_is_consistent():
    settings = (ROOT / "AI-Gateway/app/settings.py").read_text(encoding="utf-8")
    environment = (ROOT / "deploy/stack.env.example").read_text(encoding="utf-8")
    healthcheck = (
        ROOT / "deploy/verify/canonical_storage_healthcheck.sql"
    ).read_text(encoding="utf-8")

    assert 'DATABASE_SCHEMA_VERSION", "29"' in settings
    assert "DATABASE_SCHEMA_VERSION=29" in environment
    assert "max(version),0) FROM schema_migrations) <> 29" in healthcheck
