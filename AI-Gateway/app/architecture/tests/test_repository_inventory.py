from dataclasses import replace
from pathlib import Path

import pytest

from app.architecture.repository import (
    RepositoryClassifier,
    RepositoryFileClassification as Classification,
    RepositoryInventory,
    RepositoryScanner,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    (
        ("AI-Gateway/app/main.py", Classification.CODE),
        ("AI-Gateway/app/tests/test_main.py", Classification.TEST),
        ("README.md", Classification.DOCUMENT),
        (".github/workflows/ci.yml", Classification.CONFIGURATION),
        ("deploy/postgres/init/001.sql", Classification.SCRIPT),
        ("Scripts/release/publish.ps1", Classification.SCRIPT),
        ("data/results.csv", Classification.DATASET),
        ("Documents/diagram.png", Classification.ARTIFACT),
        ("dist/package.whl", Classification.GENERATED),
        ("workspace/debug.txt", Classification.TEMPORARY),
        ("unclassified.binary", Classification.UNKNOWN),
    ),
)
def test_repository_classifier_is_explicit_and_context_aware(
    path: str, expected: Classification,
) -> None:
    classification, reason = RepositoryClassifier().classify(path)
    assert classification is expected
    assert reason


def fixture_repository(root: Path) -> tuple[str, ...]:
    files = {
        "AI-Gateway/app/main.py": b"VALUE = 1\n",
        "AI-Gateway/app/tests/test_main.py": b"def test_value(): pass\n",
        "Documents/GUIDE.md": b"# Guide\n",
        ".github/workflows/ci.yml": b"name: CI\n",
        "deploy/postgres/init/001.sql": b"SELECT 1;\n",
        "assets/result.csv": b"value\n1\n",
        "mystery.bin": b"\x00\x01",
    }
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return tuple(files)


def test_repository_inventory_is_revision_bound_and_deterministic(
    tmp_path: Path,
) -> None:
    paths = fixture_repository(tmp_path)
    scanner = RepositoryScanner(tmp_path)
    first = scanner.scan(
        paths, project_name="ResearchOS", source_revision="revision-1",
    )
    reordered = scanner.scan(
        reversed(paths), project_name="ResearchOS", source_revision="revision-1",
    )

    assert first == reordered
    assert first.verify()
    assert tuple(item.path for item in first.files) == tuple(sorted(paths))
    assert dict(first.classification_counts)["unknown"] == 1
    assert RepositoryInventory.from_json(first.to_json()) == first

    target = tmp_path / paths[0]
    target.write_bytes(b"VALUE = 2\n")
    changed = scanner.scan(
        paths, project_name="ResearchOS", source_revision="revision-2",
    )
    assert changed.inventory_id != first.inventory_id
    assert changed.content_hash != first.content_hash


def test_repository_inventory_rejects_unsafe_or_ambiguous_inputs(
    tmp_path: Path,
) -> None:
    paths = fixture_repository(tmp_path)
    scanner = RepositoryScanner(tmp_path)
    with pytest.raises(ValueError, match="cannot be empty"):
        scanner.scan((), project_name="ResearchOS", source_revision="revision-1")
    with pytest.raises(ValueError, match="Duplicate"):
        scanner.scan(
            (paths[0], paths[0]),
            project_name="ResearchOS", source_revision="revision-1",
        )
    with pytest.raises(ValueError, match="Unsafe"):
        scanner.scan(
            ("../outside.py",),
            project_name="ResearchOS", source_revision="revision-1",
        )
    with pytest.raises(ValueError, match="required"):
        scanner.scan(paths, project_name="ResearchOS", source_revision="")


def test_repository_inventory_rejects_tampering(tmp_path: Path) -> None:
    inventory = RepositoryScanner(tmp_path).scan(
        fixture_repository(tmp_path),
        project_name="ResearchOS", source_revision="revision-1",
    )
    assert not replace(inventory, source_revision="revision-2").verify()
    payload = inventory.to_json().replace("GUIDE.md", "GUIDE-CHANGED.md")
    with pytest.raises(ValueError, match="invalid"):
        RepositoryInventory.from_json(payload)


def test_repository_scanner_rejects_symbolic_links(tmp_path: Path) -> None:
    source = tmp_path / "source.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("Symbolic links are not available on this platform")
    with pytest.raises(ValueError, match="Symbolic links"):
        RepositoryScanner(tmp_path).scan(
            ("linked.py",),
            project_name="ResearchOS", source_revision="revision-1",
        )


def test_repository_capability_has_no_runtime_or_scientific_dependencies() -> None:
    capability = Path(__file__).parents[1] / "repository"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in capability.glob("*.py")
    )
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3",
    )
    assert not any(item in source for item in forbidden)
