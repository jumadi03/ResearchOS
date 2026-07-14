"""
ResearchOS Discovery Transformer.

Sprint-001B.1

Evidence Extraction Transformer.

Transforms a ScientificObservationRecord
contained in DiscoveryContext into
ScientificEvidence.

Contains transformation logic only.
"""

from app.discovery.execution.discovery_context import (
    DiscoveryContext,
)

from app.discovery.models.scientific_evidence import (
    ScientificEvidence,
)


class EvidenceExtractionTransformer:
    """
    Transforms ScientificObservationRecord
    into ScientificEvidence.
    """

    def transform(
        self,
        context: DiscoveryContext,
    ) -> ScientificEvidence:

        observation = context.observation

        return ScientificEvidence(
            evidence_id=observation.observation_id,
            content=observation.content,
            observation=observation,
        )