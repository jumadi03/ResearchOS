"""Immutable factual source-inspection contracts."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json


@dataclass(frozen=True, slots=True)
class HeadingObservation:
    page: int
    start_char: int
    end_char: int
    text: str
    text_hash: str


@dataclass(frozen=True, slots=True)
class PageInspection:
    page: int
    character_count: int
    text_hash: str
    has_extractable_text: bool
    headings: tuple[HeadingObservation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headings", tuple(self.headings))


@dataclass(frozen=True, slots=True)
class SourceInspection:
    inspection_id: str
    document_id: str
    document_content_hash: str
    raw_capture_manifest_hash: str
    inspected_at: str
    inspector_name: str
    inspector_version: str
    media_type: str
    pdf_version: str
    encrypted: bool
    page_count: int
    document_metadata: tuple[tuple[str, str], ...]
    pages: tuple[PageInspection, ...]
    diagnostics: tuple[str, ...]
    complete: bool
    manifest_hash: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "document_metadata",
            tuple(sorted(tuple(item) for item in self.document_metadata)),
        )
        object.__setattr__(self, "pages", tuple(self.pages))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))

    def expected_manifest_hash(self) -> str:
        payload = asdict(self)
        payload["manifest_hash"] = ""
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()

    def finalized(self) -> "SourceInspection":
        from dataclasses import replace
        return replace(self, manifest_hash=self.expected_manifest_hash())

    def verify(self) -> bool:
        return bool(
            self.manifest_hash
            and self.manifest_hash == self.expected_manifest_hash()
            and self.page_count == len(self.pages)
            and all(page.page == index for index, page in enumerate(self.pages, 1))
            and all(
                heading.page == page.page
                and heading.text_hash
                == sha256(heading.text.encode("utf-8")).hexdigest()
                for page in self.pages for heading in page.headings
            )
        )
