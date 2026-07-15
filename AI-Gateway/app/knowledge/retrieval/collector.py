"""Deterministic metadata and citation extraction from discovery provenance."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256

from app.knowledge.models import DiscoveryRun
from app.knowledge.retrieval.models import (
    CitationEdge, EnrichedMetadata, LifecycleSignal, MetadataConflict,
    MetadataObservation, MetadataRun,
)


def _provider_values(provider: str, raw: dict) -> tuple[dict, tuple[str, ...]]:
    if provider == "openalex":
        concepts = tuple(item.get("display_name") for item in raw.get("concepts", ()) if item.get("display_name"))
        values = {
            "citation_count": raw.get("cited_by_count"),
            "open_access": (raw.get("open_access") or {}).get("is_oa"),
            "lifecycle": "retracted" if raw.get("is_retracted") else "active",
            "concepts": concepts,
        }
        return values, tuple(raw.get("referenced_works", ()))
    if provider == "semantic_scholar":
        refs = tuple(item.get("paperId") for item in raw.get("references", ()) if item.get("paperId"))
        values = {
            "citation_count": raw.get("citationCount"),
            "open_access": (raw.get("openAccessPdf") is not None) if "openAccessPdf" in raw else None,
            "lifecycle": "active",
            "concepts": tuple(raw.get("fieldsOfStudy") or ()),
        }
        return values, refs
    if provider == "crossref":
        refs = tuple(item.get("DOI") for item in raw.get("reference", ()) if item.get("DOI"))
        relation = raw.get("relation") or {}
        lifecycle = "corrected" if any(key in relation for key in ("is-corrected-by", "is-updated-by")) else "active"
        return {"citation_count": raw.get("is-referenced-by-count"), "open_access": None, "lifecycle": lifecycle, "concepts": tuple(raw.get("subject") or ())}, refs
    raise ValueError(f"Unsupported provider: {provider}")


class MetadataCollector:
    def collect(self, run: DiscoveryRun, *, created_at: str) -> MetadataRun:
        enriched = []
        edges = []
        for record in run.records:
            observations = []
            field_values = defaultdict(list)
            identifiers = {"doi": record.doi} if record.doi else {}
            for source in record.source_records:
                values, references = _provider_values(source.provider, source.raw)
                observations.append(MetadataObservation(record.record_id, source.provider, source.source_id, source.response_hash, values))
                identifiers[source.provider] = source.source_id
                for field, value in values.items():
                    if value is not None:
                        field_values[field].append((source.provider, value))
                edges.extend(CitationEdge(record.record_id, str(ref), source.provider, source.response_hash) for ref in references)
            conflicts = []
            for field, values in field_values.items():
                rendered = {(str(value)) for _, value in values}
                if len(rendered) > 1:
                    conflicts.append(MetadataConflict(record.record_id, field, tuple(sorted((provider, str(value)) for provider, value in values))))
            concepts = sorted({item for _, value in field_values["concepts"] for item in value})
            counts = [value for _, value in field_values["citation_count"] if isinstance(value, int)]
            oa = [value for _, value in field_values["open_access"] if isinstance(value, bool)]
            states = {value for _, value in field_values["lifecycle"]}
            lifecycle = LifecycleSignal.RETRACTED if "retracted" in states else LifecycleSignal.CORRECTED if "corrected" in states else LifecycleSignal.ACTIVE if states else LifecycleSignal.UNKNOWN
            enriched.append(EnrichedMetadata(record.record_id, tuple(sorted((k, v) for k, v in identifiers.items() if v)), tuple(concepts), max(counts) if counts else None, any(oa) if oa else None, lifecycle, tuple(observations), tuple(sorted(conflicts, key=lambda c: c.field))))
        identity = f"{run.run_id}:{created_at}:1.0"
        return MetadataRun(f"metadata-{sha256(identity.encode()).hexdigest()[:24]}", run.run_id, created_at, tuple(enriched), tuple(sorted(edges, key=lambda e: (e.citing_record_id, e.cited_identifier, e.provider))))
