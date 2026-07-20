from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/postgres/init/029_backup_restore_contracts.sql"
BACKUP = ROOT / "deploy/backup/backup.sh"
COMPOSE = ROOT / "deploy/compose.yaml"
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
    assert r'\"name\":\"architecture\"' in script
    assert r'\"name\":\"configuration\"' in script
    assert r'\"name\":\"migration\"' in script
    assert "snapshot_tree()" in script
    assert "write_tree_manifest()" in script
    assert "! -path './.researchos-tree-manifest.txt'" in script
    assert 'write_tree_manifest "$destination" "$copied"' in script
    assert 'cmp --silent "$before" "$copied"' in script
    assert 'cmp --silent "$before" "$after"' in script
    assert "Symbolic links are prohibited" in script
    assert "Filesystem did not reach a stable snapshot after 3 attempts" in script
    assert "backup_set_hash='$manifest_hash'" in script
    assert "integrity_verified=true" in script


def test_backup_mounts_only_explicit_non_secret_recovery_sources():
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "architecture_data:/source/architecture:ro" in compose
    assert "./compose.yaml:/source/configuration/compose.yaml:ro" in compose
    assert "./stack.env.example:/source/configuration/stack.env.example:ro" in compose
    assert "recovery-coverage-v1.json:/source/configuration/recovery-coverage-v1.json:ro" in compose
    assert "./migrate/migrate.sh:/source/migration/migrate.sh:ro" in compose
    assert "./postgres/init:/source/migration/sql:ro" in compose
    assert "./stack.env:/source" not in compose
    assert "local-access.env:/source" not in compose


def test_administration_ui_uses_restore_verified_recovery_semantics():
    script = ADMIN.read_text(encoding="utf-8")

    assert "ready=r.recovery_ready===true" in script
    assert "Portable backup-set integrity verified" in script
    assert "Isolated restore verified" in script
    assert "r.restore_fresh" in script
    assert "Restore evidence is fresh" in script
    assert "${r.ready?" not in script


def test_schema_version_42_is_consistent():
    settings = (ROOT / "AI-Gateway/app/settings.py").read_text(encoding="utf-8")
    environment = (ROOT / "deploy/stack.env.example").read_text(encoding="utf-8")
    healthcheck = (
        ROOT / "deploy/verify/canonical_storage_healthcheck.sql"
    ).read_text(encoding="utf-8")

    assert 'DATABASE_SCHEMA_VERSION", "42"' in settings
    assert "DATABASE_SCHEMA_VERSION=42" in environment
    assert "max(version),0) FROM schema_migrations) <> 42" in healthcheck
    assert "evidence_current_review_projection" in healthcheck
    assert "projection coverage is incomplete" in healthcheck


def test_migration_checksums_are_line_ending_stable():
    runner = (ROOT / "deploy/migrate/migrate.sh").read_text(encoding="utf-8")

    assert runner.count("tr -d '\\r' < \"$file\" | sha256sum") == 2


def test_historical_checksum_drift_is_narrowly_allowlisted():
    runner = (ROOT / "deploy/migrate/migrate.sh").read_text(encoding="utf-8")

    assert "checksum_compatibility_admitted" in runner
    assert "29:08fb62ef" in runner
    assert "30:ab136fe9" in runner
    assert "31:42260436" in runner
    assert "32:6f5d8c46" in runner
    assert '*) return 1 ;;' in runner
