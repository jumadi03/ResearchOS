"""
ResearchOS Discovery Transformer.

Sprint-001B.3

Evidence Integration Transformer.

Transforms validated scientific evidence
into a ScientificPhenomenon.

Contains transformation logic only.
"""

from app.discovery.models.scientific_evidence import (
    ScientificEvidence,
)

from app.discovery.models.scientific_phenomenon import (
    ScientificPhenomenon,
)


class EvidenceIntegrationTransformer:
    """
    Integrates validated evidence
    into one ScientificPhenomenon.
    """

    def transform(
        self,
        evidences: tuple[
            ScientificEvidence,
            ...
        ],
    ) -> ScientificPhenomenon:

        if not evidences:
            raise ValueError(
                "At least one ScientificEvidence is required."
            )

        #
        # Placeholder synthesis.
        #
        # Future implementation will perform:
        #
        # - clustering
        # - semantic similarity
        # - contradiction analysis
        # - evidence weighting
        #

        description = evidences[0].content

        return ScientificPhenomenon(
            phenomenon_id=evidences[0].evidence_id,
            description=description,
            evidences=evidences,
        )