import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "deploy" / "production-registry.json"
RELEASE_PATH = ROOT / "deploy" / "production-release.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_git_commit_exists(commit: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"release manifest references unknown commit {commit}"


def test_production_registry_has_one_canonical_public_target() -> None:
    registry = _load(REGISTRY_PATH)

    assert registry["schema_version"] == 1
    assert registry["environment"] == "production"
    assert registry["public_ui"]["canonical_url"] == "https://researchos.click/"
    assert registry["public_api"]["canonical_url"] == "https://api.researchos.click"
    assert registry["public_api"]["health_url"] == "https://api.researchos.click/health"
    assert registry["infrastructure"]["host"] == "srv1534304"
    assert registry["infrastructure"]["public_ip"] == "76.13.20.211"

    for section, key in (
        ("public_ui", "canonical_url"),
        ("public_api", "canonical_url"),
        ("public_api", "health_url"),
    ):
        parsed = urlparse(registry[section][key])
        assert parsed.scheme == "https"
        assert parsed.hostname


def test_release_manifest_binds_backend_ui_and_schema() -> None:
    registry = _load(REGISTRY_PATH)
    release = _load(RELEASE_PATH)

    assert registry["release_manifest"] == "deploy/production-release.json"
    assert release["schema_version"] == 1
    assert release["environment"] == "production"
    assert release["acceptance_state"] == "accepted"
    assert len(release["backend"]["commit"]) == 40
    assert len(release["ui"]["commit"]) == 40
    _assert_git_commit_exists(release["backend"]["commit"])
    assert release["database"]["schema_version"] == 42
    assert release["production_mutation_verified"] is True
    assert all((ROOT / evidence).is_file() for evidence in release["acceptance_evidence"])


def test_live_operational_configuration_matches_release_manifest() -> None:
    release = _load(RELEASE_PATH)
    settings = (ROOT / "AI-Gateway" / "app" / "settings.py").read_text(
        encoding="utf-8"
    )
    compose = (ROOT / "deploy" / "compose.hostinger.yaml").read_text(
        encoding="utf-8"
    )
    deployed_commit = (
        ROOT / "deploy" / "local-runtime" / "PRODUCTION_DEPLOYED_COMMIT"
    ).read_text(encoding="utf-8").strip()

    schema = release["database"]["schema_version"]
    assert f'os.getenv("DATABASE_SCHEMA_VERSION", "{schema}")' in settings
    assert f'EXPECTED_SCHEMA_VERSION: "{schema}"' in compose
    assert deployed_commit == release["backend"]["commit"]
