from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "bootstrap_local.py"
SPEC = spec_from_file_location("researchos_bootstrap_local", SCRIPT)
assert SPEC and SPEC.loader
bootstrap = module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def _template() -> str:
    return (Path(__file__).resolve().parents[2] / "deploy" / "stack.env.example").read_text()


def test_generated_configuration_is_complete_and_synchronized() -> None:
    stack, local, monitor = bootstrap.generated_configuration(_template())
    bootstrap.validate_configuration(stack, local, monitor)
    stack_values = bootstrap.parse_env(stack)
    local_values = bootstrap.parse_env(local)
    knowledge = json.loads(stack_values["KNOWLEDGE_API_PRINCIPALS"])
    assert len(knowledge) == 4
    assert len(json.loads(stack_values["ARCHITECTURE_API_PRINCIPALS"])) == 1
    assert len(set(knowledge) | {monitor.strip()}) == 5
    assert all(
        len(local_values[f"RESEARCHOS_{name.upper()}_PASSWORD"]) >= 20
        for name, _, _ in bootstrap.ACCOUNT_DEFINITIONS
    )


def test_configuration_bootstrap_is_idempotent(tmp_path: Path) -> None:
    deploy = tmp_path / "deploy"
    (deploy / "monitoring").mkdir(parents=True)
    (deploy / "stack.env.example").write_text(_template(), encoding="utf-8")
    assert bootstrap.ensure_configuration(tmp_path) == "created"
    first = (deploy / "stack.env").read_bytes()
    assert bootstrap.ensure_configuration(tmp_path) == "reused"
    assert (deploy / "stack.env").read_bytes() == first


def test_partial_configuration_is_rejected(tmp_path: Path) -> None:
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "stack.env").write_text("partial", encoding="utf-8")
    try:
        bootstrap.ensure_configuration(tmp_path)
    except RuntimeError as error:
        assert "Partial local configuration" in str(error)
    else:
        raise AssertionError("Partial configuration must fail closed")


def test_missing_credentials_with_existing_volumes_is_rejected(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: "docker")
    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="researchos_postgres_data\n"),
    )
    try:
        bootstrap.refuse_orphaned_volumes(tmp_path)
    except RuntimeError as error:
        assert "volumes exist" in str(error)
    else:
        raise AssertionError("Orphaned volumes must fail closed")
