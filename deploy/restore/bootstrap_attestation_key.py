"""Create a local Ed25519 restore-attestation key and extend public trust."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "AI-Gateway"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.product.restore_attestation import (
    ALGORITHM,
    TRUST_SCHEMA_VERSION,
    RestoreAttestationError,
    load_trust_registry,
    public_key_id,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--private-key",
        type=Path,
        default=REPOSITORY_ROOT
        / "deploy"
        / "restore"
        / "private"
        / "restore-attestation-v1.pem",
    )
    parser.add_argument(
        "--trust-root",
        type=Path,
        default=REPOSITORY_ROOT / "deploy" / "restore" / "trust",
    )
    args = parser.parse_args()
    if args.private_key.exists():
        raise SystemExit("Private key already exists; rotation must use a new key path")
    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    args.trust_root.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    descriptor = os.open(
        args.private_key,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(private_pem)

    key_id = public_key_id(private_key.public_key())
    public_filename = f"{key_id}.pem"
    public_path = args.trust_root / public_filename
    if public_path.exists():
        args.private_key.unlink(missing_ok=True)
        raise SystemExit("Derived public key already exists")
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    registry_path = args.trust_root / "trusted-restore-keys.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            load_trust_registry(args.trust_root)
        except (OSError, json.JSONDecodeError, RestoreAttestationError) as exc:
            public_path.unlink(missing_ok=True)
            args.private_key.unlink(missing_ok=True)
            raise SystemExit(f"Existing trust registry is invalid: {exc}") from exc
    else:
        registry = {"schema_version": TRUST_SCHEMA_VERSION, "keys": []}
    registry["keys"].append(
        {
            "key_id": key_id,
            "algorithm": ALGORITHM,
            "status": "active",
            "public_key_file": public_filename,
        }
    )
    registry_path.write_text(
        json.dumps(registry, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(key_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
