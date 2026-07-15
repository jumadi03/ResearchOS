"""Reversible exact and possible-match detection."""

from __future__ import annotations

from dataclasses import replace
from difflib import SequenceMatcher
import re
import unicodedata

from app.knowledge.models import LiteratureRecord, MatchKind


def _title_key(value: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_title.lower()).strip()


def deduplicate(
    records: tuple[LiteratureRecord, ...], *, possible_threshold: float = 0.92
) -> tuple[LiteratureRecord, ...]:
    """Merge DOI-identical records and flag, but never merge, fuzzy matches."""
    exact: dict[str, LiteratureRecord] = {}
    unique: list[LiteratureRecord] = []
    for record in records:
        if not record.doi:
            unique.append(record)
            continue
        existing = exact.get(record.doi)
        if existing is None:
            exact[record.doi] = record
            continue
        exact[record.doi] = replace(
            existing,
            authors=existing.authors or record.authors,
            year=existing.year or record.year,
            abstract=existing.abstract or record.abstract,
            venue=existing.venue or record.venue,
            work_type=existing.work_type or record.work_type,
            source_records=tuple(sorted(existing.source_records + record.source_records, key=lambda s: s.provider)),
            match_kind=MatchKind.EXACT,
        )
    output = list(exact.values()) + unique
    possible: dict[str, set[str]] = {record.record_id: set() for record in output}
    for index, left in enumerate(output):
        for right in output[index + 1 :]:
            if left.doi and right.doi:
                continue
            similarity = SequenceMatcher(None, _title_key(left.title), _title_key(right.title)).ratio()
            same_year = left.year is None or right.year is None or left.year == right.year
            if similarity >= possible_threshold and same_year:
                possible[left.record_id].add(right.record_id)
                possible[right.record_id].add(left.record_id)
    result = []
    for record in output:
        matches = tuple(sorted(possible[record.record_id]))
        if matches and record.match_kind is MatchKind.UNIQUE:
            record = replace(record, match_kind=MatchKind.POSSIBLE, possible_matches=matches)
        result.append(record)
    return tuple(sorted(result, key=lambda r: (r.title.casefold(), r.record_id)))
