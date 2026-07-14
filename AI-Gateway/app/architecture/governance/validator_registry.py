"""
ResearchOS Validator Registry.

Immutable registry of architecture
validators.
"""

from dataclasses import dataclass

from .validator import Validator


@dataclass(
    frozen=True,
    slots=True,
)
class ValidatorRegistry:
    """
    Immutable Validator Registry.

    Stores the canonical collection of
    architecture validators.
    """

    validators: tuple[
        Validator,
        ...
    ] = ()

    def get_all(
        self,
    ) -> tuple[
        Validator,
        ...
    ]:
        """
        Return every registered validator.
        """
        return self.validators

    def count(self) -> int:
        """
        Return the number of registered
        validators.
        """
        return len(self.validators)