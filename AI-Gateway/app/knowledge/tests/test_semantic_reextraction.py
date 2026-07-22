from hashlib import sha256

import pytest

from app.knowledge.extraction.models import (
    DocumentCoordinates, ExtractedScientificObject, ExtractionManifest,
    ExtractionReviewState, ScientificObjectType,
)
from app.knowledge.extraction.semantic_reextraction import (
    SemanticReextractionEngine,
)


def parent_manifest(text: str) -> ExtractionManifest:
    quote_hash = sha256(text.encode()).hexdigest()
    source = ExtractedScientificObject(
        "source-result", ScientificObjectType.RESULT, text,
        DocumentCoordinates(
            4, 100, 100 + len(text), quote_hash,
            section="Results", page_text_hash="a" * 64,
        ),
        0.9, ExtractionReviewState.PROVISIONAL,
        "source-parser", "1.2.0", text, "bounded_heading_section",
    )
    return ExtractionManifest(
        "parent-extraction", "document-1", "b" * 64,
        "2026-07-19T00:00:00Z", "source-parser", "1.2.0",
        (source,), "1.1", "c" * 64, "screening-1",
        "d" * 64, "e" * 64,
    ).finalized()


def test_semantic_reextraction_is_deterministic_verbatim_and_provisional():
    text = (
        "The final sample comprised 425 qualitative researchers and the "
        "majority were women (n = 324, 76%). "
        "Attitudes toward data sharing were measured on a seven-point "
        "Likert scale. "
        "The number of identified drivers does not indicate their importance "
        "and further research is needed."
    )
    parent = parent_manifest(text)
    engine = SemanticReextractionEngine()

    first = engine.extract(
        parent, ("source-result",), created_at="2026-07-19T01:00:00Z",
    )
    second = engine.extract(
        parent, ("source-result",), created_at="2026-07-19T01:00:00Z",
    )

    assert first == second and first.verify()
    assert {
        item.object_type for item in first.objects
    } == {
        ScientificObjectType.POPULATION,
        ScientificObjectType.VARIABLE,
        ScientificObjectType.MEASUREMENT,
        ScientificObjectType.LIMITATION,
    }
    for item in first.objects:
        assert item.review_state is ExtractionReviewState.PROVISIONAL
        assert item.content in text
        local_start = item.coordinates.start_char - 100
        assert text[local_start:local_start + len(item.content)] == item.content
        assert item.coordinates.quote_hash == sha256(
            item.content.encode()
        ).hexdigest()
        assert item.extraction_rule.endswith("derived_from:source-result")


def test_semantic_reextraction_fails_closed_without_reviewable_markers():
    parent = parent_manifest(
        "The analysis was completed according to the documented protocol."
    )
    with pytest.raises(ValueError, match="no reviewable candidates"):
        SemanticReextractionEngine().extract(
            parent, ("source-result",),
            created_at="2026-07-19T01:00:00Z",
        )
