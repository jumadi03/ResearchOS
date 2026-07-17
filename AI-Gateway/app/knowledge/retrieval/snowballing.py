"""Reproducible, contract-bound citation snowballing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.discovery.providers import CitationPage, ProviderError
from app.knowledge.models import DiscoveryContract, DiscoveryRun


class CitationDirection(StrEnum):
    BACKWARD = "backward"
    FORWARD = "forward"


class CitationStoppingReason(StrEnum):
    COMPLETE = "complete"
    DEPTH_LIMIT = "depth_limit"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PARTIAL_PROVIDER_FAILURE = "partial_provider_failure"


@dataclass(frozen=True, slots=True)
class CitationTraversalEdge:
    source_identifier: str
    target_identifier: str
    direction: CitationDirection
    depth: int
    provider: str
    response_hash: str
    request_url: str

    def __post_init__(self) -> None:
        if not self.source_identifier.strip() or not self.target_identifier.strip():
            raise ValueError("Citation edge identifiers are required")
        if self.depth < 1:
            raise ValueError("Citation edge depth must be positive")
        if len(self.response_hash) != 64:
            raise ValueError("Citation edge response hash is invalid")
        if not self.request_url.startswith("https://"):
            raise ValueError("Citation edge request URL must use HTTPS")


@dataclass(frozen=True, slots=True)
class CitationTraversalCandidate:
    identifier: str
    provider: str
    depth: int
    response_hash: str
    request_url: str
    title: str | None = None
    doi: str | None = None

    def __post_init__(self) -> None:
        if not self.identifier.strip() or not self.provider.strip():
            raise ValueError("Citation candidate identity is required")
        if self.depth < 1:
            raise ValueError("Citation candidate depth must be positive")
        if len(self.response_hash) != 64:
            raise ValueError("Citation candidate response hash is invalid")
        if not self.request_url.startswith("https://"):
            raise ValueError("Citation candidate request URL must use HTTPS")


@dataclass(frozen=True, slots=True)
class CitationTraversalFailure:
    provider: str
    identifier: str
    direction: CitationDirection
    depth: int
    error_type: str
    message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class CitationTraversalRun:
    traversal_id: str
    discovery_run_id: str
    discovery_contract_id: str
    seed_record_id: str
    directions: tuple[CitationDirection, ...]
    maximum_depth: int
    retrieval_budget: int
    created_at: str
    candidates: tuple[CitationTraversalCandidate, ...]
    edges: tuple[CitationTraversalEdge, ...]
    failures: tuple[CitationTraversalFailure, ...]
    stopping_reasons: tuple[CitationStoppingReason, ...]
    manifest_hash: str = ""
    schema_version: str = "1.0"

    def expected_manifest_hash(self) -> str:
        payload = asdict(replace(self, manifest_hash=""))
        return sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    def finalized(self) -> "CitationTraversalRun":
        return replace(self, manifest_hash=self.expected_manifest_hash())

    def verify(self) -> bool:
        return (
            len(self.manifest_hash) == 64
            and self.manifest_hash == self.expected_manifest_hash()
            and len(self.edges) <= self.retrieval_budget
            and len(self.candidates) <= self.retrieval_budget
            and all(edge.depth <= self.maximum_depth for edge in self.edges)
            and all(
                item.depth <= self.maximum_depth for item in self.candidates
            )
        )


class CitationProvider(Protocol):
    name: str
    citation_directions: tuple[CitationDirection, ...]

    def citation_links(
        self, identifier: str, direction: CitationDirection, limit: int,
    ) -> tuple[CitationPage, ...]: ...


class CitationSnowballingEngine:
    def __init__(self, providers: tuple[CitationProvider, ...]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def traverse(
        self, run: DiscoveryRun, *, seed_record_id: str,
        directions: tuple[CitationDirection, ...], maximum_depth: int,
        retrieval_budget: int, created_at: str,
    ) -> CitationTraversalRun:
        self._validate_request(
            run.discovery_contract, directions, maximum_depth, retrieval_budget,
        )
        seed = next(
            (record for record in run.records if record.record_id == seed_record_id),
            None,
        )
        if seed is None:
            raise KeyError(f"Unknown citation seed record: {seed_record_id}")

        frontier = [
            (source.provider, source.source_id, 0)
            for source in seed.source_records
        ]
        visited = {(provider, identifier) for provider, identifier, _ in frontier}
        seed_keys = set(visited)
        edges: list[CitationTraversalEdge] = []
        candidates: dict[tuple[str, str], CitationTraversalCandidate] = {}
        failures: list[CitationTraversalFailure] = []
        budget_exhausted = False

        while frontier and not budget_exhausted:
            provider_name, identifier, current_depth = frontier.pop(0)
            depth = current_depth + 1
            if depth > maximum_depth:
                continue
            provider = self._providers.get(provider_name)
            if provider is None:
                for direction in directions:
                    failures.append(CitationTraversalFailure(
                        provider_name, identifier, direction, depth,
                        "ProviderNotConfigured",
                        "Citation provider is not configured", False,
                    ))
                continue
            for direction in directions:
                if direction not in tuple(provider.citation_directions):
                    failures.append(CitationTraversalFailure(
                        provider_name, identifier, direction, depth,
                        "DirectionNotSupported",
                        f"{provider_name} does not support {direction.value} traversal",
                        False,
                    ))
                    continue
                remaining = retrieval_budget - len(edges)
                if remaining <= 0:
                    budget_exhausted = True
                    break
                try:
                    pages = provider.citation_links(identifier, direction, remaining)
                    for page in pages:
                        response_hash = sha256(
                            canonical_json(page.records).encode("utf-8")
                        ).hexdigest()
                        for candidate in page.records:
                            candidate_id = str(candidate.get("identifier") or "").strip()
                            if not candidate_id:
                                raise ValueError(
                                    "Citation provider returned an unidentified candidate"
                                )
                            source_id, target_id = (
                                (identifier, candidate_id)
                                if direction is CitationDirection.BACKWARD
                                else (candidate_id, identifier)
                            )
                            edge = CitationTraversalEdge(
                                source_id, target_id, direction, depth,
                                provider_name, response_hash, page.request_url,
                            )
                            if edge not in edges:
                                edges.append(edge)
                            candidate_key = (provider_name, candidate_id)
                            if candidate_key not in seed_keys:
                                candidates.setdefault(
                                    candidate_key,
                                    CitationTraversalCandidate(
                                        candidate_id, provider_name, depth,
                                        response_hash, page.request_url,
                                        str(candidate.get("title")).strip()
                                        if candidate.get("title") else None,
                                        str(candidate.get("doi")).strip()
                                        if candidate.get("doi") else None,
                                    ),
                                )
                            if (
                                candidate_key not in visited
                                and depth < maximum_depth
                            ):
                                visited.add(candidate_key)
                                frontier.append((provider_name, candidate_id, depth))
                            if len(edges) >= retrieval_budget:
                                budget_exhausted = True
                                break
                        if budget_exhausted:
                            break
                except (ProviderError, ValueError, KeyError, TypeError) as exc:
                    failures.append(CitationTraversalFailure(
                        provider_name, identifier, direction, depth,
                        type(exc).__name__, str(exc),
                        getattr(exc, "retryable", False),
                    ))

        reasons = []
        if budget_exhausted:
            reasons.append(CitationStoppingReason.BUDGET_EXHAUSTED)
        elif any(edge.depth == maximum_depth for edge in edges):
            reasons.append(CitationStoppingReason.DEPTH_LIMIT)
        else:
            reasons.append(CitationStoppingReason.COMPLETE)
        if failures:
            reasons.append(CitationStoppingReason.PARTIAL_PROVIDER_FAILURE)

        identity = canonical_json({
            "discovery_run_id": run.run_id,
            "seed_record_id": seed_record_id,
            "directions": directions,
            "maximum_depth": maximum_depth,
            "retrieval_budget": retrieval_budget,
            "created_at": created_at,
        })
        traversal = CitationTraversalRun(
            f"citation-{sha256(identity.encode('utf-8')).hexdigest()[:24]}",
            run.run_id, run.discovery_contract.contract_id, seed_record_id,
            directions, maximum_depth, retrieval_budget, created_at,
            tuple(sorted(
                candidates.values(),
                key=lambda item: (item.depth, item.provider, item.identifier),
            )),
            tuple(sorted(
                edges,
                key=lambda item: (
                    item.depth, item.provider, item.direction.value,
                    item.source_identifier, item.target_identifier,
                ),
            )),
            tuple(failures), tuple(dict.fromkeys(reasons)),
        ).finalized()
        if not traversal.verify():
            raise ValueError("Citation traversal manifest integrity verification failed")
        return traversal

    @staticmethod
    def _validate_request(
        contract: DiscoveryContract, directions: tuple[CitationDirection, ...],
        maximum_depth: int, retrieval_budget: int,
    ) -> None:
        if not directions or len(set(directions)) != len(directions):
            raise ValueError("Citation traversal directions must be unique and non-empty")
        if not 1 <= maximum_depth <= contract.maximum_depth:
            raise ValueError("Citation traversal exceeds discovery contract maximum depth")
        if not 1 <= retrieval_budget <= contract.retrieval_budget:
            raise ValueError("Citation traversal exceeds discovery contract retrieval budget")
