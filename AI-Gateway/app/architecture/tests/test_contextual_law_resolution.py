from app.architecture.governance import LawRegistry, LawResolution
from app.architecture.models import (
    ArchitectureLaw,
    ArchitectureLawBundle,
    LawScope,
    ResolutionContext,
)


def _law(
    law_id: str,
    *,
    category: str = "Dependency",
    enabled: bool = True,
    effective_from: str | None = None,
) -> ArchitectureLaw:
    return ArchitectureLaw(
        law_id,
        law_id,
        "Test law",
        "1.0.0",
        category=category,
        scope=LawScope(node_types=("Module",), path_patterns=("app/kernel/**",)),
        enabled=enabled,
        effective_from=effective_from,
    )


def test_context_resolution_is_scoped_and_auditable() -> None:
    bundle = ArchitectureLawBundle(
        "",
        "2026.1",
        (
            _law("APPLIES"),
            _law("DISABLED", enabled=False),
            _law("FUTURE", effective_from="2027-01-01"),
            _law("OTHER-CATEGORY", category="PublicAPI"),
        ),
    ).finalized()
    resolution = LawResolution(LawRegistry.from_bundle(bundle))

    result = resolution.resolve_context(
        ResolutionContext(
            category="Dependency",
            node_type="Module",
            source_path="app/kernel/contracts/transformer.py",
            as_of="2026-07-15",
        )
    )

    assert tuple(law.law_id for law in result.applicable_laws) == ("APPLIES",)
    assert result.bundle_id == bundle.bundle_id
    assert result.bundle_hash == bundle.content_hash
    reasons = {item.law_id: item.reason for item in result.trace}
    assert reasons == {
        "APPLIES": "APPLICABLE",
        "DISABLED": "DISABLED",
        "FUTURE": "NOT_YET_EFFECTIVE",
        "OTHER-CATEGORY": "CATEGORY_MISMATCH",
    }


def test_legacy_metadata_category_remains_supported() -> None:
    law = ArchitectureLaw(
        "LEGACY",
        "Legacy",
        "Legacy category",
        "1.0",
        metadata={"category": "PublicAPI"},
    )
    registry = LawRegistry((law,))
    assert registry.get_by_category("PublicAPI") == (law,)
