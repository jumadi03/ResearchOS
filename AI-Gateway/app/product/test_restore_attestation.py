from base64 import b64encode
from datetime import datetime, timezone
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from app.product.restore_attestation import (
    RestoreAttestationError,
    calculate_report_hash,
    public_key_id,
    sign_report,
    verify_signed_report,
)


NOW = datetime(2026, 7, 17, 13, 0, tzinfo=timezone.utc).isoformat()
COMPONENTS = [
    "architecture",
    "configuration",
    "knowledge",
    "migration",
    "minio",
    "postgresql",
]


def report_fixture() -> dict:
    report = {
        "schema_version": "1.0",
        "drill_id": "restore-drill:20260717T131208Z",
        "backup_stamp": "20260717T131208Z",
        "manifest_hash": "a" * 64,
        "target_kind": "isolated",
        "target_identifier": "researchos_restore_drill+researchos-restore-drill",
        "components": list(COMPONENTS),
        "outcome": "verified",
        "checks": [{"component": name, "verified": True} for name in COMPONENTS],
        "actor": "researchos-isolated-restore-drill",
        "started_at": NOW,
        "completed_at": NOW,
        "restore_executed": True,
        "active_target_touched": False,
        "cleanup_verified": True,
        "ledger_written": False,
        "error": None,
    }
    report["content_hash"] = calculate_report_hash(report)
    return report


def trust_fixture(tmp_path: Path, *, status: str = "active"):
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key_id = public_key_id(private.public_key())
    public_name = f"{key_id}.pem"
    (tmp_path / public_name).write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    (tmp_path / "trusted-restore-keys.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "keys": [
                    {
                        "key_id": key_id,
                        "algorithm": "ed25519",
                        "status": status,
                        "public_key_file": public_name,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return private_pem


def test_signed_complete_report_is_verified(tmp_path):
    private_pem = trust_fixture(tmp_path)
    signed = sign_report(report_fixture(), private_pem)

    assert verify_signed_report(signed, tmp_path) == signed


def test_tampered_report_is_rejected(tmp_path):
    private_pem = trust_fixture(tmp_path)
    signed = sign_report(report_fixture(), private_pem)
    signed["cleanup_verified"] = False

    with pytest.raises(RestoreAttestationError):
        verify_signed_report(signed, tmp_path)


def test_revoked_key_is_rejected(tmp_path):
    private_pem = trust_fixture(tmp_path, status="revoked")
    signed = sign_report(report_fixture(), private_pem)

    with pytest.raises(RestoreAttestationError, match="not trusted"):
        verify_signed_report(signed, tmp_path)


def test_partial_or_duplicate_components_are_rejected(tmp_path):
    private_pem = trust_fixture(tmp_path)
    report = report_fixture()
    report["components"][-1] = "minio"
    report["content_hash"] = calculate_report_hash(report)
    signed = sign_report(report, private_pem)

    with pytest.raises(RestoreAttestationError, match="component"):
        verify_signed_report(signed, tmp_path)


def test_forged_signature_is_rejected(tmp_path):
    private_pem = trust_fixture(tmp_path)
    signed = sign_report(report_fixture(), private_pem)
    signed["attestation"]["signature"] = b64encode(b"forged").decode()

    with pytest.raises(RestoreAttestationError, match="signature"):
        verify_signed_report(signed, tmp_path)
