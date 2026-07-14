"""
ResearchOS Discovery Transformer.

Sprint-001B.4

Scientific Object Discovery Transformer.

Transforms one or more scientific phenomena
into a ScientificObject.

Contains transformation logic only.
"""

from app.discovery.models.scientific_object import (
    ScientificObject,
)

from app.discovery.models.scientific_phenomenon import (
    ScientificPhenomenon,
)


class ScientificObjectDiscoveryTransformer:
    """
    Discovers a ScientificObject from
    one or more ScientificPhenomenon.
    """

    def transform(
        self,
        phenomena: tuple[
            ScientificPhenomenon,
            ...
        ],
    ) -> ScientificObject:

        if not phenomena:
            raise ValueError(
                "At least one ScientificPhenomenon is required."
            )

        #
        # Placeholder implementation.
        #
        # Future implementation will perform:
        #
        # - phenomenon clustering
        # - object identity resolution
        # - cross-study integration
        # - semantic consolidation
        #

        first = phenomena[0]

        return ScientificObject(
            object_id=first.phenomenon_id,
            name=first.description,
            description=first.description,
            phenomena=phenomena,
        )