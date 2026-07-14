"""
ResearchOS Runtime Provider Ranker.

Sprint:
    Sprint-001O

Selects the best provider evaluation.

Current implementation simply selects the
highest-scored accepted provider.
"""

from app.runtime.models import (
    ProviderEvaluation,
    ProviderEvaluationSet,
)


class ProviderRanker:
    """
    Selects the best provider evaluation.
    """

    def rank(
        self,
        evaluations: ProviderEvaluationSet,
    ) -> ProviderEvaluation:

        accepted = tuple(
            evaluation
            for evaluation in evaluations.evaluations
            if evaluation.accepted
        )

        if not accepted:
            raise RuntimeError(
                "No provider satisfies routing requirements."
            )

        return max(
            accepted,
            key=lambda evaluation: evaluation.score,
        )