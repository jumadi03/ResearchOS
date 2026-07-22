from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "verify_local_continuity.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = spec_from_file_location("researchos_local_continuity", SCRIPT)
assert SPEC and SPEC.loader
continuity = module_from_spec(SPEC)
SPEC.loader.exec_module(continuity)


def test_probe_is_secret_free_and_checks_persistent_services() -> None:
    assert "pg_control_system()" in continuity.PROBE_SOURCE
    assert "workspace_users" in continuity.PROBE_SOURCE
    assert "put_object" in continuity.PROBE_SOURCE
    assert "get_object" in continuity.PROBE_SOURCE
    assert "delete_object" in continuity.PROBE_SOURCE
    assert "payload" not in {
        "postgres_system_identifier",
        "schema_version",
        "workspace_user_count",
        "workspace_user_hash",
        "object_sentinel_sha256",
    }


def test_continuity_mismatch_fails_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(continuity.bootstrap_local, "require_local_configuration", lambda _root: None)
    monkeypatch.setattr(continuity.bootstrap_local, "show_status", lambda _root: None)
    monkeypatch.setattr(continuity.bootstrap_local, "verify_runtime", lambda: {})
    monkeypatch.setattr(continuity.bootstrap_local, "compose", lambda *_args, **_kwargs: None)
    snapshots = iter(({"schema_version": 41}, {"schema_version": 40}))
    monkeypatch.setattr(continuity, "probe", lambda *_args, **_kwargs: next(snapshots))

    try:
        continuity.verify(tmp_path, tmp_path / "report.json")
    except RuntimeError as error:
        assert "identity changed" in str(error)
    else:
        raise AssertionError("A changed persistence identity must fail closed")
