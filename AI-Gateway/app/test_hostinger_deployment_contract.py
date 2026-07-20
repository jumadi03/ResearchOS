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
