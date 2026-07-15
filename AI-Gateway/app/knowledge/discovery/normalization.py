"""Provider normalization with field-level source preservation."""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from app.knowledge.models import LiteratureRecord, MatchKind, SourceRecord


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip().lower()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi or None


def _inverted_abstract(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    words = sorted(((position, word) for word, positions in index.items() for position in positions))
    return " ".join(word for _, word in words)


def normalize(
    provider: str, raw: dict[str, Any], retrieved_at: str,
    *, response_hash: str | None = None,
) -> LiteratureRecord:
    if provider == "openalex":
        source_id = str(raw.get("id") or raw.get("doi") or raw.get("title"))
        authors = tuple(
            item.get("author", {}).get("display_name", "").strip()
            for item in raw.get("authorships", ())
            if item.get("author", {}).get("display_name")
        )
        doi = normalize_doi(raw.get("doi"))
        abstract = _inverted_abstract(raw.get("abstract_inverted_index"))
        venue = (raw.get("primary_location") or {}).get("source") or {}
        venue = venue.get("display_name")
        work_type = raw.get("type")
    elif provider == "crossref":
        source_id = str(raw.get("DOI") or raw.get("URL") or (raw.get("title") or [""])[0])
        authors = tuple(
            " ".join(part for part in (a.get("given"), a.get("family")) if part).strip()
            for a in raw.get("author", ())
        )
        doi = normalize_doi(raw.get("DOI"))
        abstract = raw.get("abstract")
        venue = (raw.get("container-title") or [None])[0]
        work_type = raw.get("type")
    elif provider == "semantic_scholar":
        source_id = str(raw.get("paperId") or raw.get("title"))
        authors = tuple(a.get("name", "").strip() for a in raw.get("authors", ()) if a.get("name"))
        doi = normalize_doi((raw.get("externalIds") or {}).get("DOI"))
        abstract = raw.get("abstract")
        venue = raw.get("venue")
        types = raw.get("publicationTypes") or ()
        work_type = types[0] if types else None
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    title_value = raw.get("title") or ""
    title = title_value[0] if isinstance(title_value, list) else title_value
    year = raw.get("publication_year") if provider == "openalex" else raw.get("year")
    if provider == "crossref":
        parts = ((raw.get("published") or raw.get("issued") or {}).get("date-parts") or [[]])[0]
        year = parts[0] if parts else None
    source = SourceRecord(provider, source_id, retrieved_at, response_hash or content_hash(raw), raw)
    identity = doi or f"{provider}:{source_id}"
    return LiteratureRecord(
        record_id=sha256(identity.encode("utf-8")).hexdigest()[:24],
        title=str(title).strip(), authors=authors, year=year, doi=doi,
        abstract=abstract, venue=venue, work_type=work_type, source_records=(source,),
        match_kind=MatchKind.UNIQUE,
    )
