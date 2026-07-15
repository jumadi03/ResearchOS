"""Lawful document acquisition and registry (SK-001C)."""

from .acquisition import DocumentAcquirer
from .registry import DocumentRegistry

__all__ = ["DocumentAcquirer", "DocumentRegistry"]
