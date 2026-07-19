"""Deterministic semantic annotation candidates from accepted passages."""

from hashlib import sha256
import re

from app.knowledge.extraction.models import (
    DocumentCoordinates, ExtractedScientificObject, ExtractionManifest,
    ExtractionReviewState, ScientificObjectType,
)


class SemanticReextractionEngine:
    parser_name = "researchos-semantic-annotation-parser"
    parser_version = "1.0.0"
    _rules = (
        (
            ScientificObjectType.POPULATION,
            re.compile(
                r"(?i)\b(sample|respondents?|participants?|researchers?|"
                r"interviewees?|assessors?)\b"
            ),
            "population_lexical_candidate",
            0.72,
        ),
        (
            ScientificObjectType.VARIABLE,
            re.compile(
                r"(?i)\b(factors?|drivers?|inhibitors?|attitudes?|motivations?|"
                r"conditions?|trust|effort|skills?|performance|experience)\b"
            ),
            "construct_lexical_candidate",
            0.68,
        ),
        (
            ScientificObjectType.MEASUREMENT,
            re.compile(
                r"(?i)(?:\bn\s*=\s*\d+|\b\d+(?:\.\d+)?%|\blikert\b|"
                r"\bscale\b|\brate\b|\bmajority\b|\bnumber\b)"
            ),
            "measurement_marker_candidate",
            0.74,
        ),
        (
            ScientificObjectType.LIMITATION,
            re.compile(
                r"(?i)\b(does not indicate|further research|limitation|"
                r"limited|only a few|excluded|missing data|did not)\b"
            ),
            "limitation_lexical_candidate",
            0.66,
        ),
    )

    def extract(
        self, parent: ExtractionManifest,
        accepted_object_ids: tuple[str, ...], *, created_at: str,
    ) -> ExtractionManifest:
        selected = set(accepted_object_ids)
        if not selected:
            raise ValueError(
                "Semantic re-extraction requires accepted source evidence"
            )
        parent_by_id = {item.object_id: item for item in parent.objects}
        unknown = sorted(selected - set(parent_by_id))
        if unknown:
            raise ValueError(
                f"Semantic re-extraction source is unknown: {unknown[0]}"
            )
        candidates = {}
        for object_id in sorted(selected):
            source = parent_by_id[object_id]
            for match in re.finditer(
                r"(?s)(?:^|(?<=[.!?])\s+)([^.!?]{40,1200}[.!?])",
                source.content,
            ):
                raw = match.group(1)
                leading = len(raw) - len(raw.lstrip())
                content = raw.strip()
                local_start = match.start(1) + leading
                start = source.coordinates.start_char + local_start
                end = start + len(content)
                for kind, pattern, rule, confidence in self._rules:
                    if not pattern.search(content):
                        continue
                    quote_hash = sha256(content.encode("utf-8")).hexdigest()
                    identity = (
                        f"{parent.extraction_id}:{object_id}:{kind.value}:"
                        f"{start}:{end}:{quote_hash}:{self.parser_version}"
                    )
                    candidate = ExtractedScientificObject(
                        f"object-{sha256(identity.encode()).hexdigest()[:24]}",
                        kind, content,
                        DocumentCoordinates(
                            source.coordinates.page, start, end, quote_hash,
                            section=source.coordinates.section,
                            paragraph=source.coordinates.paragraph,
                            page_text_hash=source.coordinates.page_text_hash,
                        ),
                        confidence, ExtractionReviewState.PROVISIONAL,
                        self.parser_name, self.parser_version,
                        verbatim_text=content, extraction_rule=(
                            f"{rule}:derived_from:{object_id}"
                        ),
                    )
                    candidates[candidate.object_id] = candidate
        configuration_hash = sha256((
            self.parser_name + ":" + self.parser_version + ":"
            + ",".join(item[0].value for item in self._rules)
        ).encode()).hexdigest()
        selection = ",".join(sorted(selected))
        identity = (
            f"{parent.extraction_id}:{parent.manifest_hash}:{selection}:"
            f"{self.parser_version}"
        )
        manifest = ExtractionManifest(
            f"extraction-{sha256(identity.encode()).hexdigest()[:24]}",
            parent.document_id, parent.document_content_hash, created_at,
            self.parser_name, self.parser_version,
            tuple(sorted(candidates.values(), key=lambda item: item.object_id)),
            "1.1", parent.inspection_manifest_hash,
            parent.screening_decision_id, parent.screening_decision_hash,
            configuration_hash,
        ).finalized()
        if not manifest.objects:
            raise ValueError(
                "Semantic re-extraction produced no reviewable candidates"
            )
        return manifest
