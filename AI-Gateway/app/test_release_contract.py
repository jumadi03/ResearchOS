from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "Scripts" / "build_release.py"
SPEC = spec_from_file_location("researchos_build_release", SCRIPT)
assert SPEC and SPEC.loader
release = module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def test_release_version_is_synchronized() -> None:
    assert release.declared_version() == "0.5.0-rc.1"


def test_release_dependencies_are_exactly_pinned() -> None:
    for requirement in release.project_metadata()["dependencies"]:
        assert "==" in requirement
        assert not any(operator in requirement for operator in (">=", "<=", "~=", "!="))
