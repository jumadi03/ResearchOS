from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SSH_HARDENING = ROOT / "deploy/security/00-researchos-hardening.conf"


def test_hostinger_ssh_is_key_only_non_root_and_allowlisted() -> None:
    configuration = SSH_HARDENING.read_text(encoding="utf-8")

    assert "PubkeyAuthentication yes" in configuration
    assert "PasswordAuthentication no" in configuration
    assert "KbdInteractiveAuthentication no" in configuration
    assert "PermitRootLogin no" in configuration
    assert "MaxAuthTries 3" in configuration
    assert "AllowUsers ubuntu" in configuration
    assert "PermitRootLogin yes" not in configuration
