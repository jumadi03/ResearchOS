"""Immutable, content-addressed discovery snapshots."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.discovery.providers import ProviderPage
from app.knowledge.models import (
    DiscoveryContract,
    DiscoveryRun,
    LiteratureRecord,
    MatchKind,
    ProviderEnumeration,
    ProviderFailure,
    QueryConcept,
    QueryFamily,
    ScientificQuestion,
    SearchPlan,
    SourceDefinition,
    SourceQuery,
    SourceRecord,
)


def serialize_run(run: DiscoveryRun) -> bytes:
    return json.dumps(
        asdict(run), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def deserialize_run(payload: bytes) -> DiscoveryRun:
    """Reconstruct and revalidate one immutable discovery snapshot."""
    data = json.loads(payload)
    question = ScientificQuestion(**data["question"])
    contract = DiscoveryContract(**{
        **data["discovery_contract"],
        **{
            name: tuple(data["discovery_contract"][name])
            for name in (
                "source_categories", "inclusion_rules", "exclusion_rules",
                "languages", "document_types", "evidence_types",
                "stopping_conditions",
            )
        },
    })
    concepts = tuple(QueryConcept(**{
        **item,
        "synonyms": tuple(item["synonyms"]),
        "disciplines": tuple(item["disciplines"]),
    }) for item in data["search_plan"]["concepts"])
    families = tuple(QueryFamily(**{
        **item,
        "concept_ids": tuple(item["concept_ids"]),
        "terms": tuple(item["terms"]),
    }) for item in data["search_plan"]["query_families"])
    source_queries = tuple(
        SourceQuery(**item) for item in data["search_plan"]["source_queries"]
    )
    plan = SearchPlan(**{
        **data["search_plan"],
        "providers": tuple(data["search_plan"]["providers"]),
        "concepts": concepts,
        "query_families": families,
        "source_queries": source_queries,
    })
    definitions = tuple(SourceDefinition(**{
        **item,
        "disciplines": tuple(item["disciplines"]),
        "content_types": tuple(item["content_types"]),
    }) for item in data["source_definitions"])
    records = tuple(LiteratureRecord(**{
        **item,
        "authors": tuple(item["authors"]),
        "source_records": tuple(
            SourceRecord(**source) for source in item["source_records"]
        ),
        "match_kind": MatchKind(item["match_kind"]),
        "possible_matches": tuple(item["possible_matches"]),
    }) for item in data["records"])
    return DiscoveryRun(
        run_id=data["run_id"],
        question=question,
        discovery_contract=contract,
        source_definitions=definitions,
        search_plan=plan,
        started_at=data["started_at"],
        enumerations=tuple(
            ProviderEnumeration(**item) for item in data["enumerations"]
        ),
        records=records,
        failures=tuple(ProviderFailure(**item) for item in data["failures"]),
        schema_version=data["schema_version"],
    )


class DiscoverySnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.unsupported_snapshot_count = 0

    def save(self, run: DiscoveryRun) -> Path:
        run.validate_query_plan()
        payload = serialize_run(run)
        digest = sha256(payload).hexdigest()
        path = self.root / run.run_id / f"discovery-{digest}.json"
        if path.exists():
            if path.read_bytes() != payload:
                raise RuntimeError("Discovery snapshot integrity conflict")
            return path
        atomic_write(path, payload)
        return path

    def load_all(self) -> tuple[DiscoveryRun, ...]:
        """Load the newest integrity-valid snapshot for every recorded run."""
        runs = []
        self.unsupported_snapshot_count = 0
        if not self.root.exists():
            return ()
        for run_root in sorted(path for path in self.root.iterdir() if path.is_dir()):
            snapshots = sorted(run_root.glob("discovery-*.json"))
            if not snapshots:
                continue
            payload = snapshots[-1].read_bytes()
            expected = snapshots[-1].stem.removeprefix("discovery-")
            if sha256(payload).hexdigest() != expected:
                raise RuntimeError(
                    f"Discovery snapshot integrity conflict: {run_root.name}"
                )
            shape = json.loads(payload)
            if not {
                "discovery_contract", "source_definitions", "enumerations",
            }.issubset(shape):
                # Pre-contract snapshots remain immutable historical evidence,
                # but cannot be reopened as governed workflow cases.
                self.unsupported_snapshot_count += 1
                continue
            run = deserialize_run(payload)
            if run.run_id != run_root.name:
                raise RuntimeError(
                    f"Discovery snapshot identity conflict: {run_root.name}"
                )
            runs.append(run)
        return tuple(runs)


class RawPageStore:
    """Persist immutable provider pages before normalization."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(
        self, run_id: str, provider: str, page_number: int, page: ProviderPage
    ) -> str:
        payload = canonical_json(
            {
                "provider": provider,
                "request_url": page.request_url,
                "total_results": page.total_results,
                "records": page.records,
            }
        ).encode("utf-8")
        digest = sha256(payload).hexdigest()
        path = self.root / run_id / "raw" / provider / f"page-{page_number:05d}-{digest}.json"
        if path.exists() and path.read_bytes() != payload:
            raise RuntimeError("Raw provider page integrity conflict")
        if not path.exists():
            atomic_write(path, payload)
        return digest
