"""
ResearchOS Runtime Routing Engine.

ASR-001B

Coordinates the Runtime Routing Pipeline.

The RoutingEngine orchestrates transformation
stages only. It does not build domain models.
"""

from app.infrastructure.ai.provider_registry import ProviderRegistry

from app.runtime.models import (
    ProviderEvaluationSet,
    RoutingDecision,
)

from app.runtime.models.runtime_request import RuntimeRequest

from .provider_enumerator import ProviderEnumerator
from .capability_matcher import CapabilityMatcher
from .provider_ranker import ProviderRanker


class RoutingEngine:
    """
    Coordinates the Runtime Routing Pipeline.

    The engine orchestrates independent
    transformation stages without embedding
    routing logic inside itself.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
    ):

        self.registry = registry

        self.enumerator = ProviderEnumerator()

        self.matcher = CapabilityMatcher()

        self.ranker = ProviderRanker()

    def route(
        self,
        request: RuntimeRequest,
    ) -> RoutingDecision:

        #
        # Sprint-001P
        #
        # RuntimeRequest telah menjadi
        # Canonical Runtime Input Model.
        #
        # Routing saat ini belum
        # menggunakan isi request.
        #

        candidates = self.enumerator.enumerate(
            self.registry
        )

        evaluations = []

        for candidate in candidates:

            evaluation = self.matcher.evaluate(
                candidate
            )

            evaluations.append(
                evaluation
            )

        evaluation_set = ProviderEvaluationSet(
            evaluations=tuple(evaluations)
        )

        winner = self.ranker.rank(
            evaluation_set
        )

        return RoutingDecision(
            provider=winner.candidate.name,
            reason=winner.reason,
            metadata={
                "engine": "routing_engine",
                "score": str(winner.score),
            },
        )