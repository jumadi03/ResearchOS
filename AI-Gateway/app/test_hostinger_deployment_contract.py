from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Scripts" / "bootstrap_hostinger.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = spec_from_file_location("researchos_bootstrap_hostinger", SCRIPT)
assert SPEC and SPEC.loader
bootstrap = module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def test_hostinger_configuration_is_secret_and_hostname_bound() -> None:
    template = (ROOT / "deploy" / "stack.hostinger.env.example").read_text(
        encoding="utf-8"
    )
    hostname = "researchos-api.example.test"
    generated = bootstrap.generated_configuration(template, hostname)

    bootstrap.validate_configuration(generated, hostname)
    assert "replace-with" not in generated
    assert f"RESEARCHOS_API_HOSTNAME={hostname}" in generated


def test_hostinger_compose_uses_existing_tls_proxy_without_public_data_ports() -> None:
    compose = (ROOT / "deploy" / "compose.hostinger.yaml").read_text(
        encoding="utf-8"
    )

    assert "name: n8n_default" in compose
    assert "traefik.http.routers.researchos-api.tls.certresolver" in compose
    assert "Host(`${RESEARCHOS_API_HOSTNAME}`)" in compose
    assert 'ports: ["127.0.0.1:5432:5432"]' not in compose
    assert 'ports: ["127.0.0.1:9000:9000"' not in compose


def test_hostinger_stack_schedules_verified_backups_and_internal_monitoring() -> None:
    compose = (ROOT / "deploy" / "compose.hostinger.yaml").read_text(
        encoding="utf-8"
    )
    monitor = (
        ROOT / "deploy" / "monitor" / "hostinger_healthcheck.py"
    ).read_text(encoding="utf-8")

    assert "BACKUP_INTERVAL_SECONDS: ${BACKUP_INTERVAL_SECONDS:-86400}" in compose
    assert "BACKUP_RETENTION_DAYS: ${BACKUP_RETENTION_DAYS:-14}" in compose
    assert "backup_data:/backups" in compose
    assert "stack.hostinger.env:/source" not in compose
    assert "./compose.hostinger.yaml:/source/configuration/compose.yaml:ro" in compose
    assert (
        "./stack.hostinger.env.example:/source/configuration/stack.env.example:ro"
        in compose
    )
    assert "operations_state:/state" in compose
    assert "hostinger_healthcheck.py" in compose
    assert "EXPECTED_SCHEMA_VERSION: \"41\"" in compose
    assert 'cursor.execute("SELECT COUNT(*) FROM canonical_objects")' in monitor
    assert "maximum_age" in monitor


def test_offsite_backup_pull_is_manifest_bound_and_secret_excluding() -> None:
    script = (
        ROOT / "Scripts" / "pull_hostinger_backup.ps1"
    ).read_text(encoding="utf-8")

    assert "Get-FileHash" in script
    assert "ConvertFrom-Json" in script
    assert "component.sha256" in script
    assert "Assert-SafeChildPath" in script
    assert "stack.hostinger.env" not in script
    assert "offsite-backup=passed" in script

    override = (
        ROOT / "deploy" / "restore" / "compose.offsite-restore-drill.yaml"
    ).read_text(encoding="utf-8")
    assert "RESTORE_BACKUP_DIR" in override
    assert ":/backups:ro" in override
