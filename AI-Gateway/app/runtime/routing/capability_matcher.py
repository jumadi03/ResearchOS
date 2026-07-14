"""
ResearchOS Runtime Capability Matcher.

Sprint:
    Sprint-001O

Performs capability matching between
registered providers and routing requirements.

Current implementation is read-only.
"""

from app.runtime.models import (
    ProviderCandidate,
    ProviderEvaluation,
)


class CapabilityMatcher:
    """
    Read-only capability matcher.

    The matcher evaluates providers but does
    not choose one.
    """

    def evaluate(
        self,
        candidate: ProviderCandidate,
    ) -> ProviderEvaluation:

        profile = candidate.profile

        #
        # Sprint-001O
        #
        # No capability filtering yet.
        #

        return ProviderEvaluation(
            candidate=candidate,
            accepted=True,
            score=1.0,
            reason="Capability evaluation not enabled.",
            metadata={
                "matcher": "read_only",
            },
        )