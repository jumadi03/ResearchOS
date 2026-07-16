"""Deterministic, provenance-bearing scientific query planning."""

from hashlib import sha256
import re

from app.knowledge.models import (
    DiscoveryContract, QueryConcept, QueryFamily, ScientificQuestion,
    SearchPlan, SourceDefinition, SourceQuery,
)


class ScientificQueryPlanner:
    method = "scientific-query-planner-v1"

    def plan(
        self, question: ScientificQuestion, contract: DiscoveryContract,
        draft: SearchPlan, concepts: tuple[QueryConcept, ...],
        sources: tuple[SourceDefinition, ...],
    ) -> SearchPlan:
        contract.validate_binding(question, draft)
        if not concepts:
            raise ValueError("Scientific query concepts must not be empty")
        concept_ids = tuple(item.concept_id for item in concepts)
        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("Scientific query concept IDs must be unique")
        source_by_name = {item.name: item for item in sources}
        if set(source_by_name) != set(draft.providers):
            raise ValueError(
                "Scientific query sources do not match search plan providers"
            )

        if self._is_doi(draft.query):
            terms = (draft.query.strip(),)
            purpose = "Exact DOI lookup"
            query = terms[0]
        else:
            terms = tuple(
                term for concept in concepts
                for term in (concept.preferred_term, *concept.synonyms)
            )
            purpose = "Combined concept discovery"
            query = " AND ".join(
                self._concept_expression(concept) for concept in concepts
            )
        family_identity = ":".join((
            question.question_id, contract.contract_id,
            "|".join(concept_ids), "|".join(terms),
        ))
        family = QueryFamily(
            f"query-family-{sha256(family_identity.encode()).hexdigest()[:24]}",
            concept_ids, terms, purpose,
        )
        source_queries = tuple(
            SourceQuery(
                provider, source_by_name[provider].source_id,
                family.family_id, query,
            )
            for provider in draft.providers
        )
        return SearchPlan(
            draft.plan_id, draft.query, draft.providers,
            draft.limit_per_provider, draft.year_from, draft.year_to,
            concepts, (family,), source_queries, self.method,
        )

    @staticmethod
    def _concept_expression(concept: QueryConcept) -> str:
        terms = (concept.preferred_term, *concept.synonyms)
        escaped = tuple(
            '"' + item.replace('"', '\\"') + '"' for item in terms
        )
        return escaped[0] if len(escaped) == 1 else f"({' OR '.join(escaped)})"

    @staticmethod
    def _is_doi(value: str) -> bool:
        normalized = re.sub(
            r"^https?://(?:dx\.)?doi\.org/", "", value.strip(),
            flags=re.IGNORECASE,
        )
        return bool(re.fullmatch(
            r"10\.\d{4,9}/\S+", normalized, flags=re.IGNORECASE,
        ))
