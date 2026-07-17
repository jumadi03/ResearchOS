from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/postgres/init/030_signed_restore_evidence_admission.sql"
ADMISSION = ROOT / "deploy/restore/admit_restore_report.py"
BOOTSTRAP = ROOT / "deploy/restore/bootstrap_attestation_key.py"
COMPOSE = ROOT / "deploy/compose.yaml"
SPEC = spec_from_file_location("researchos_restore_admission", ADMISSION)
assert SPEC and SPEC.loader
admission = module_from_spec(SPEC)
SPEC.loader.exec_module(admission)
BOOTSTRAP_SPEC = spec_from_file_location(
    "researchos_restore_key_bootstrap",
    BOOTSTRAP,
)
assert BOOTSTRAP_SPEC and BOOTSTRAP_SPEC.loader
bootstrap = module_from_spec(BOOTSTRAP_SPEC)
BOOTSTRAP_SPEC.loader.exec_module(bootstrap)


def test_database_guard_requires_complete_attested_verified_evidence():
    contract = MIGRATION.read_text(encoding="utf-8")

    assert "backup_restore_verifications_admission_guard" in contract
    assert "six unique canonical components" in contract
    assert "researchos_restore_drill+researchos-restore-drill" in contract
    assert "NEW.report->'cleanup_verified' <> 'true'::jsonb" in contract
    assert "NEW.report->'active_target_touched' <> 'false'::jsonb" in contract
    assert "NEW.report->>'manifest_hash' <> NEW.backup_set_hash" in contract
    assert "admit_backup_restore_verification" in contract


def test_admission_runtime_has_public_trust_and_no_private_key():
    compose = COMPOSE.read_text(encoding="utf-8")

    assert 'profiles: ["restore-admission"]' in compose
    assert "./restore/trust:/restore-trust:ro" in compose
    admission_block = compose.split("  restore-admission:", 1)[1].split(
        "\n  postgres-exporter:", 1
    )[0]
    assert "private/" not in admission_block
    assert "restore-attestation-private" not in admission_block
    assert "worker" not in admission_block


def test_api_projection_receives_only_public_trust():
    compose = COMPOSE.read_text(encoding="utf-8")
    api_block = compose.split("  api:", 1)[1].split("\n  worker:", 1)[0]

    assert "RESTORE_TRUST_ROOT: /restore-trust" in api_block
    assert "./restore/trust:/restore-trust:ro" in api_block
    assert "private/" not in api_block


def test_key_rotation_preserves_existing_trust_entries(tmp_path, monkeypatch):
    trust_root = tmp_path / "trust"
    first_private = tmp_path / "private" / "restore-v1.pem"
    second_private = tmp_path / "private" / "restore-v2.pem"
    for private_path in (first_private, second_private):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                str(BOOTSTRAP),
                "--private-key",
                str(private_path),
                "--trust-root",
                str(trust_root),
            ],
        )
        assert bootstrap.main() == 0

    registry = json.loads(
        (trust_root / "trusted-restore-keys.json").read_text(encoding="utf-8")
    )
    assert len(registry["keys"]) == 2
    assert len({entry["key_id"] for entry in registry["keys"]}) == 2
    assert all(entry["status"] == "active" for entry in registry["keys"])
