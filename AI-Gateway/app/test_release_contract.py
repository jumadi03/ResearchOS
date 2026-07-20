from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "build_release.py"
SPEC = spec_from_file_location("researchos_build_release", SCRIPT)
assert SPEC and SPEC.loader
release = module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def test_release_version_is_synchronized() -> None:
    assert release.declared_version() == "0.5.0-rc.5"


def test_release_dependencies_are_exactly_pinned() -> None:
    for requirement in release.project_metadata()["dependencies"]:
        assert "==" in requirement
        assert not any(operator in requirement for operator in (">=", "<=", "~=", "!="))


def test_canonical_ui_lock_distinguishes_saved_and_deployed_source() -> None:
    lock = release.canonical_ui_lock()

    assert len(lock["commit_sha"]) == 40
    assert lock["deployment_url"].startswith("https://")
    assert lock["sites_version_number"] > 0
    assert lock["deployment_status"] == "saved_not_deployed"
    assert lock["deployed_sites_version_number"] < lock["sites_version_number"]
    assert lock["tests_passed"] > 0


def test_canonical_ui_lock_rejects_missing_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class IncompleteLock:
        @staticmethod
        def read_text(*, encoding: str) -> str:
            assert encoding == "utf-8"
            return json.dumps({"schema_version": "1.0"})

    monkeypatch.setattr(release, "CANONICAL_UI_LOCK", IncompleteLock())

    with pytest.raises(RuntimeError, match="missing fields"):
        release.canonical_ui_lock()
