"""Provider-source normalization before PostgreSQL persistence."""

from app.knowledge.repositories.postgres import (
    normalized_source_license, source_access_status,
)


def test_crossref_license_object_is_normalized_to_text() -> None:
    raw = {
        "license": [
            {
                "start": {"date-parts": [[2025, 3, 26]]},
                "content-version": "vor",
                "URL": "https://creativecommons.org/licenses/by/4.0/",
            },
        ],
    }
    license_value = normalized_source_license(raw)

    assert license_value == "https://creativecommons.org/licenses/by/4.0/"
    assert source_access_status(raw, license_value) == "open"


def test_source_access_remains_unknown_without_explicit_open_signal() -> None:
    raw = {"license": [{"URL": "https://publisher.example/terms"}]}
    license_value = normalized_source_license(raw)

    assert license_value == "https://publisher.example/terms"
    assert source_access_status(raw, license_value) == "unknown"


def test_openalex_and_semantic_scholar_open_signals_are_supported() -> None:
    assert source_access_status({"open_access": {"is_oa": True}}, None) == "open"
    assert source_access_status({"openAccessPdf": {"url": "https://example.test/p.pdf"}}, None) == "open"
