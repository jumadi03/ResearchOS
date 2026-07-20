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


def test_hostinger_compose_owns_tls_proxy_without_public_data_ports() -> None:
    compose = (ROOT / "deploy" / "compose.hostinger.yaml").read_text(
        encoding="utf-8"
    )

    assert "name: n8n_default" in compose
    assert "traefik@sha256:279606d45ac2a96f" in compose
    assert "traefik_data:/letsencrypt" in compose
    assert "/var/run/docker.sock:/var/run/docker.sock:ro" in compose
    assert "external: true" in compose
    assert "- 80:80" in compose
    assert "- 443:443" in compose
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
    assert "MaximumBackupAgeHours" in script
    assert '[string]$RemoteUser = "ubuntu"' in script
    assert '"sudo", "docker", "cp"' in script
    assert "root@" not in script

    override = (
        ROOT / "deploy" / "restore" / "compose.offsite-restore-drill.yaml"
    ).read_text(encoding="utf-8")
    assert "RESTORE_BACKUP_DIR" in override
    assert ":/backups:ro" in override


def test_local_monitor_produces_durable_alerts_without_secrets() -> None:
    script = (
        ROOT / "Scripts" / "monitor_hostinger_backup.ps1"
    ).read_text(encoding="utf-8")

    assert "researchos-monitor-1" in script
    assert "MaximumMonitorAgeMinutes" in script
    assert "alerts" in script
    assert "latest.json" in script
    assert "msg.exe" in script
    assert "hostinger-backup-monitor=passed" in script
    assert "stack.hostinger.env" not in script
    assert '[string]$RemoteUser = "ubuntu"' in script
    assert "sudo docker exec" in script
    assert "root@" not in script
