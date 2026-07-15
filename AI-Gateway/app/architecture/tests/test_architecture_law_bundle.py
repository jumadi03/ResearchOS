import json

import pytest

from app.architecture.models import (
    ArchitectureLaw,
    ArchitectureLawBundle,
    LawScope,
    LawSeverity,
)


def _law(law_id: str) -> ArchitectureLaw:
    return ArchitectureLaw(
        law_id=law_id,
        title=f"Law {law_id}",
        description="Test law",
        version="1.0.0",
        category="Dependency",
        severity=LawSeverity.ERROR,
        scope=LawScope(node_types=("Module",), path_patterns=("app/**",)),
        condition={"relation": "IMPORTS"},
    )


def test_bundle_identity_is_deterministic() -> None:
    first = ArchitectureLawBundle("", "1.0.0", (_law("B"), _law("A"))).finalized()
    second = ArchitectureLawBundle("", "1.0.0", (_law("A"), _law("B"))).finalized()

    assert first.content_hash == second.content_hash
    assert first.bundle_id == second.bundle_id
    assert first.to_json() == second.to_json()
    assert json.loads(first.to_json())["laws"][0]["law_id"] == "A"
    assert ArchitectureLawBundle.from_json(first.to_json()) == first


def test_bundle_load_rejects_tampered_content() -> None:
    bundle = ArchitectureLawBundle("", "1.0.0", (_law("A"),)).finalized()
    payload = json.loads(bundle.to_json())
    payload["laws"][0]["title"] = "Tampered"
    with pytest.raises(ValueError, match="content hash"):
        ArchitectureLawBundle.from_json(json.dumps(payload))


def test_bundle_rejects_duplicate_law_identifiers() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ArchitectureLawBundle("", "1.0.0", (_law("A"), _law("A")))


def test_law_rejects_invalid_effective_range() -> None:
    with pytest.raises(ValueError, match="effective_from"):
        ArchitectureLaw(
            "A",
            "Law A",
            "Test",
            "1.0.0",
            effective_from="2026-02-01",
            effective_until="2026-01-01",
        )
