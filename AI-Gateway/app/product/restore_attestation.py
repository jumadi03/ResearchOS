"""Canonical signing and verification contract for isolated restore evidence."""

from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


ALGORITHM = "ed25519"
REPORT_SCHEMA_VERSION = "1.0"
TRUST_SCHEMA_VERSION = "1.0"
REQUIRED_COMPONENTS = {
    "architecture",
    "configuration",
    "knowledge",
    "migration",
    "minio",
    "postgresql",
}
TARGET_IDENTIFIER = "researchos_restore_drill+researchos-restore-drill"
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class RestoreAttestationError(ValueError):
    """Raised when restore evidence is not authentic or semantically eligible."""


def _canonical_payload(report: dict[str, Any]) -> bytes:
    payload = {
        key: value
        for key, value in report.items()
        if key not in {"content_hash", "attestation"}
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def calculate_report_hash(report: dict[str, Any]) -> str:
    return sha256(_canonical_payload(report)).hexdigest()


def public_key_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return f"restore-ed25519-{sha256(raw).hexdigest()[:16]}"


def sign_report(report: dict[str, Any], private_key_pem: bytes) -> dict[str, Any]:
    if report.get("attestation") is not None:
        raise RestoreAttestationError("Report is already attested")
    expected_hash = calculate_report_hash(report)
    if report.get("content_hash") != expected_hash:
        raise RestoreAttestationError("Report content hash is invalid")
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RestoreAttestationError("Restore attestation key must be Ed25519")
    signature = private_key.sign(_canonical_payload(report))
    signed = dict(report)
    signed["attestation"] = {
        "algorithm": ALGORITHM,
        "key_id": public_key_id(private_key.public_key()),
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    return signed


def _validate_semantics(report: dict[str, Any]) -> None:
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise RestoreAttestationError("Unsupported restore report schema")
    if report.get("outcome") != "verified":
        raise RestoreAttestationError("Only verified restore reports are admissible")
    if report.get("target_kind") != "isolated":
        raise RestoreAttestationError("Restore target is not isolated")
    if report.get("target_identifier") != TARGET_IDENTIFIER:
        raise RestoreAttestationError("Restore target identity is not canonical")
    if report.get("restore_executed") is not True:
        raise RestoreAttestationError("Restore execution is not proven")
    if report.get("active_target_touched") is not False:
        raise RestoreAttestationError("Active target safety is not proven")
    if report.get("cleanup_verified") is not True:
        raise RestoreAttestationError("Isolated target cleanup is not proven")
    if report.get("ledger_written") is not False:
        raise RestoreAttestationError("Executor report cannot claim ledger admission")
    components = report.get("components")
    if (
        not isinstance(components, list)
        or len(components) != len(REQUIRED_COMPONENTS)
        or set(components) != REQUIRED_COMPONENTS
    ):
        raise RestoreAttestationError("Restore component set is incomplete")
    checks = report.get("checks")
    if not isinstance(checks, list):
        raise RestoreAttestationError("Restore checks are missing")
    checked = [
        item.get("component")
        for item in checks
        if isinstance(item, dict) and isinstance(item.get("component"), str)
    ]
    if len(checked) != len(REQUIRED_COMPONENTS) or set(checked) != REQUIRED_COMPONENTS:
        raise RestoreAttestationError("Component checks are incomplete or duplicated")
    if report.get("error") is not None:
        raise RestoreAttestationError("Verified report contains an error")
    for field in ("manifest_hash", "content_hash"):
        value = report.get(field)
        if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
            raise RestoreAttestationError(f"Invalid {field}")
    if calculate_report_hash(report) != report["content_hash"]:
        raise RestoreAttestationError("Restore report content hash mismatch")


def load_trust_registry(root: Path) -> dict[str, Ed25519PublicKey]:
    registry_path = root / "trusted-restore-keys.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RestoreAttestationError("Restore trust registry is unavailable") from exc
    if (
        not isinstance(registry, dict)
        or registry.get("schema_version") != TRUST_SCHEMA_VERSION
        or not isinstance(registry.get("keys"), list)
    ):
        raise RestoreAttestationError("Restore trust registry is invalid")
    trusted: dict[str, Ed25519PublicKey] = {}
    for item in registry["keys"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"key_id", "algorithm", "status", "public_key_file"}
            or item["algorithm"] != ALGORITHM
            or item["status"] not in {"active", "revoked"}
        ):
            raise RestoreAttestationError("Restore trust entry is invalid")
        filename = item["public_key_file"]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise RestoreAttestationError("Restore public-key path is unsafe")
        if item["status"] == "revoked":
            continue
        try:
            key = serialization.load_pem_public_key((root / filename).read_bytes())
        except (OSError, ValueError) as exc:
            raise RestoreAttestationError("Restore public key is unavailable") from exc
        if not isinstance(key, Ed25519PublicKey) or public_key_id(key) != item["key_id"]:
            raise RestoreAttestationError("Restore public-key identity mismatch")
        if item["key_id"] in trusted:
            raise RestoreAttestationError("Duplicate restore trust key")
        trusted[item["key_id"]] = key
    return trusted


def verify_signed_report(
    report: dict[str, Any],
    trust_root: Path,
) -> dict[str, Any]:
    _validate_semantics(report)
    attestation = report.get("attestation")
    if (
        not isinstance(attestation, dict)
        or set(attestation) != {"algorithm", "key_id", "signature"}
        or attestation.get("algorithm") != ALGORITHM
    ):
        raise RestoreAttestationError("Restore attestation is invalid")
    trusted = load_trust_registry(trust_root)
    key = trusted.get(attestation.get("key_id"))
    if key is None:
        raise RestoreAttestationError("Restore attestation key is not trusted")
    try:
        signature = base64.b64decode(attestation["signature"], validate=True)
        key.verify(signature, _canonical_payload(report))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise RestoreAttestationError("Restore attestation signature is invalid") from exc
    return report
